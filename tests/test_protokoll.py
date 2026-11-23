#!/usr/bin/env python3
"""Tests für Paket P (Normen v18): Normen-Protokoll – Schreibstelle im Hook (fragen/nein, Schwärzen, Fehlerweg).
Schreibt nur in ein Protokoll im Temp-Ordner (NORMEN_PROTOKOLL), nie in ~/.config."""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VORLAGE = ROOT / "agenten-normen"
OK = FAIL = 0


def check(name, bedingung, info=""):
    global OK, FAIL
    if bedingung:
        OK += 1
    else:
        FAIL += 1
        print(f"FAIL {name} {info}")


def sh(*args, cwd=None, eingabe=None, env=None):
    return subprocess.run(args, cwd=cwd, input=eingabe, capture_output=True, text=True, env=env)


def neues_repo(t):
    repo = t / "repo"
    repo.mkdir()
    sh("git", "init", "-q", "-b", "main", cwd=repo)
    r = sh("bash", str(VORLAGE / "einrichten.sh"), str(repo), "--test", "echo ok", "--sperre", "geheim/")
    check("einrichten", r.returncode == 0, r.stdout + r.stderr)
    return repo


def hook(repo, prot, ereignis, rolle="claude", werkzeug="claude"):
    """Gibt (Entscheidung, Ergebnis) zurück."""
    env = dict(os.environ, NORMEN_PROTOKOLL=str(prot))
    r = sh(sys.executable, "normen/normen.py", "hook", "--rolle", rolle, "--werkzeug", werkzeug, cwd=repo,
           eingabe=ereignis if isinstance(ereignis, str) else json.dumps(ereignis), env=env)
    out = r.stdout
    if '"deny"' in out or r.returncode == 2:
        return "nein", r
    if '"ask"' in out:
        return "fragen", r
    return "ja", r


def zeilen(prot):
    return [json.loads(z) for z in prot.read_text(encoding="utf-8").splitlines()] if prot.is_file() else []


def bash(befehl, repo, tid="toolu_1"):
    return {"tool_name": "Bash", "tool_input": {"command": befehl}, "cwd": str(repo), "session_id": "s-1",
            "tool_use_id": tid, "permission_mode": "default"}


def test_schreibstelle(t):
    repo = neues_repo(t)
    prot = t / "prot" / "p.jsonl"

    (repo / "frisch").mkdir()  # untracked → rm -r gesperrt (nein)
    e, _ = hook(repo, prot, bash("ls", repo))
    check("ja: Entscheidung", e == "ja")
    check("ja: kein Eintrag", zeilen(prot) == [], str(zeilen(prot)))

    e, _ = hook(repo, prot, bash("rm -r frisch", repo, "toolu_nein"))
    check("nein: Entscheidung", e == "nein")
    z = zeilen(prot)
    check("nein: ein Eintrag", len(z) == 1, str(z))
    if z:
        k = z[0]
        check("nein: Felder", k.get("stufe") == "nein" and k.get("entscheid") == "nein" and k.get("rolle") == "claude"
              and k.get("werkzeug") == "claude" and k.get("tool") == "Bash" and k.get("projekt") == "repo"
              and k.get("session_id") == "s-1" and k.get("tool_use_id") == "toolu_nein"
              and k.get("permission_mode") == "default" and "zeit" in k, str(k))
        check("nein: Norm-ID", "N01-KEINE-ZERSTOERUNG" in k.get("normen", []), str(k))
        check("nein: Befehl", "rm -r frisch" in k.get("inhalt", ""), str(k))
    check("Datei Rechte 600", prot.is_file() and (prot.stat().st_mode & 0o777) == 0o600,
          oct(prot.stat().st_mode) if prot.is_file() else "fehlt")

    # fragen (Claude) – force-push braucht Rückfrage
    e, _ = hook(repo, prot, bash("git push --force origin x", repo, "toolu_fragen"))
    check("fragen: Entscheidung", e == "fragen")
    z = zeilen(prot)
    check("fragen: Eintrag", len(z) == 2 and z[-1].get("stufe") == "fragen" and z[-1].get("entscheid") == "fragen",
          str(z[-1:]))

    # Teams: fragen → nein, Stufe ursprünglich bleibt sichtbar
    e, _ = hook(repo, prot, bash("git push --force origin x", repo, "toolu_vibe"), rolle="mistral-team", werkzeug="vibe")
    z = zeilen(prot)
    check("vibe: nein", e == "nein")
    check("vibe: Eintrag mit Stufe und Endstufe", z and z[-1].get("entscheid") == "nein" and z[-1].get("rolle") == "mistral-team"
          and z[-1].get("werkzeug") == "vibe", str(z[-1:]))

    # Schwärzen: Token, E-Mail, gesperrter Pfad – auch über 300 Zeichen hinaus erst schwärzen, dann kürzen
    token = "ghp_" + "A1b2C3d4" * 5
    mail = "jemand" + "@" + "example.org"
    vor = len(zeilen(prot))
    e, _ = hook(repo, prot, bash(f"echo {mail} {token} > geheim/x.txt; git push --force", repo, "toolu_s"))
    z = zeilen(prot)
    roh = json.dumps(z[vor:], ensure_ascii=False)
    check("schwärzen: Eintrag", len(z) == vor + 1, roh)
    check("schwärzen: Token weg", token not in roh and "ghp_" not in roh, roh)
    check("schwärzen: E-Mail weg", mail not in roh, roh)
    check("schwärzen: gesperrter Pfad weg", "geheim/" not in roh.casefold(), roh)
    check("schwärzen: Marke", "[geschwärzt]" in roh, roh)
    lang = "echo " + "x" * 400 + " " + token + "; git push --force"
    hook(repo, prot, bash(lang, repo, "toolu_l"))
    k = zeilen(prot)[-1]
    check("kürzen: 300 Zeichen", len(k.get("inhalt", "")) <= 300, str(len(k.get("inhalt", ""))))
    check("kürzen: Token weg", token[:12] not in json.dumps(k), str(k)[:200])

    # Edit/Write: nur der Pfad, nie der Inhalt; mcp: nur der Tool-Name
    vor = len(zeilen(prot))
    e, _ = hook(repo, prot, {"tool_name": "Write", "tool_input": {"file_path": str(repo / "normen" / "x.toml"),
                                                                  "content": "INHALT-GEHEIMNIS"},
                             "cwd": str(repo), "tool_use_id": "toolu_w"}, rolle="mistral-team", werkzeug="vibe")
    z = zeilen(prot)
    check("write: gesperrt", e == "nein")
    check("write: Eintrag nur mit Pfad", len(z) == vor + 1 and "INHALT-GEHEIMNIS" not in json.dumps(z[-1])
          and "x.toml" in z[-1].get("inhalt", ""), str(z[-1:]))

    # Selbsttest-Köder: kein Eintrag
    vor = len(zeilen(prot))
    e, _ = hook(repo, prot, bash("touch .normen/normen-koeder.txt", repo, "toolu_k"))
    check("köder: gesperrt", e == "nein")
    check("köder: kein Eintrag", len(zeilen(prot)) == vor, str(zeilen(prot)[vor:]))

    # Schreibfehler (Protokoll-Pfad ist ein Ordner): Entscheidung unverändert, Hinweis auf stderr
    ordner = t / "ordner.jsonl"
    ordner.mkdir()
    e, r = hook(repo, ordner, bash("rm -r frisch", repo))
    check("schreibfehler: nein bleibt nein", e == "nein", r.stdout + r.stderr)
    check("schreibfehler: Hinweis stderr", "Normen-Protokoll nicht geschrieben" in r.stderr, r.stderr)
    e, r = hook(repo, ordner, bash("ls", repo))
    check("schreibfehler: ja bleibt ja", e == "ja", r.stdout + r.stderr)
    e, r = hook(repo, ordner, bash("git push --force origin x", repo))
    check("schreibfehler: fragen bleibt fragen", e == "fragen", r.stdout + r.stderr)

    # Kaputte Eingabe bzw. Konfiguration: Hook sperrt (fail-closed), Protokoll wirft nicht
    e, r = hook(repo, prot, "{kein json")
    check("kaputtes JSON: gesperrt", e == "nein", r.stdout + r.stderr)
    pt = repo / "normen" / "projekt.toml"
    alt = pt.read_text(encoding="utf-8")
    pt.write_text(alt + "\n[[kaputt\n", encoding="utf-8")
    vor = len(zeilen(prot))
    e, r = hook(repo, prot, bash("ls", repo))
    check("kaputte Konfiguration: gesperrt", e == "nein", r.stdout + r.stderr)
    check("kaputte Konfiguration: kein Eintrag ohne Schwärzen", len(zeilen(prot)) == vor, str(zeilen(prot)[vor:]))
    pt.write_text(alt, encoding="utf-8")


def main():
    with tempfile.TemporaryDirectory() as d:
        t = Path(d)
        for f in (test_schreibstelle,):
            try:
                f(t)
            except Exception as e:  # normen-ausnahme: N08-KEINE-ALTLASTEN – wird als FAIL gezählt, nicht verschluckt
                global FAIL
                FAIL += 1
                print(f"FAIL {f.__name__}: {type(e).__name__}: {e}")
    print(f"test_protokoll: {OK} ok, {FAIL} fehlgeschlagen")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
