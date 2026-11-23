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


def normen(repo, prot, *args, eingabe=""):
    env = dict(os.environ, NORMEN_PROTOKOLL=str(prot))
    return sh(sys.executable, "normen/normen.py", *args, cwd=repo, eingabe=eingabe, env=env)


def eintrag(tid, stufe="fragen", zeit="2026-11-20T10:00:00+0100", norm="N01-KEINE-ZERSTOERUNG", projekt="p1",
            grund="N01-KEINE-ZERSTOERUNG: Destruktiver Befehl", inhalt="git push --force"):
    entscheid = stufe
    return {"zeit": zeit, "projekt": projekt, "rolle": "claude", "werkzeug": "claude", "tool": "Bash", "stufe": stufe,
            "entscheid": entscheid, "normen": [norm], "gruende": [grund], "inhalt": inhalt, "session_id": "s-1",
            "tool_use_id": tid, "permission_mode": "default"}


def schreibe(prot, eintraege):
    prot.parent.mkdir(parents=True, exist_ok=True)
    with open(prot, "a", encoding="utf-8") as f:
        for e in eintraege:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")


def test_hook_nach(t):
    """PostToolUse/PostToolUseFailure: Ausgang nur zu vorher protokollierten fragen-Einträgen; Exit 0, keine Ausgabe."""
    repo = t / "repo"
    prot = t / "nach" / "p.jsonl"
    schreibe(prot, [eintrag("toolu_a"), eintrag("toolu_n", stufe="nein")])

    def nach(ereignis, tid, **zusatz):
        return normen(repo, prot, "hook-nach", "--werkzeug", "claude",
                      eingabe=json.dumps({"hook_event_name": ereignis, "tool_use_id": tid, "session_id": "s-1",
                                          "tool_name": "Bash", "tool_input": {"command": "x"}, **zusatz}))

    r = nach("PostToolUse", "toolu_a")
    check("hook-nach: Exit 0", r.returncode == 0, r.stdout + r.stderr)
    check("hook-nach: keine Ausgabe", r.stdout == "", r.stdout)
    z = zeilen(prot)
    check("hook-nach: Ausgang ausgefuehrt", len(z) == 3 and z[-1].get("ausgang") == "ausgefuehrt"
          and z[-1].get("tool_use_id") == "toolu_a", str(z[-1:]))
    r = nach("PostToolUse", "toolu_a")
    check("hook-nach: zweiter Post schreibt nicht doppelt", len(zeilen(prot)) == 3, str(zeilen(prot)[3:]))
    r = nach("PostToolUse", "toolu_unbekannt")
    check("hook-nach: ohne fragen-Eintrag nichts", r.returncode == 0 and len(zeilen(prot)) == 3, str(zeilen(prot)[3:]))
    r = nach("PostToolUse", "toolu_n")
    check("hook-nach: nein-Eintrag bekommt keinen Ausgang", len(zeilen(prot)) == 3, str(zeilen(prot)[3:]))
    schreibe(prot, [eintrag("toolu_f")])
    r = nach("PostToolUseFailure", "toolu_f", error="Exit code 1", is_interrupt=False)
    z = zeilen(prot)
    check("hook-nach: Ausgang fehlgeschlagen", r.returncode == 0 and z[-1].get("ausgang") == "fehlgeschlagen"
          and z[-1].get("tool_use_id") == "toolu_f", str(z[-1:]))
    check("hook-nach: Fehlertext nicht protokolliert", "Exit code 1" not in json.dumps(z[-1]), str(z[-1]))

    # Nur das Dateiende wird gelesen: fragen-Eintrag vor vielen Zeilen (weit über 200) wird nicht mehr gefunden,
    # ein frischer am Ende schon – und die Laufzeit bleibt bei großer Datei klein
    gross = t / "nach" / "gross.jsonl"
    schreibe(gross, [eintrag("toolu_frueh")] + [eintrag(f"toolu_{i}", stufe="nein") for i in range(20000)]
             + [eintrag("toolu_spaet")])
    env = dict(os.environ, NORMEN_PROTOKOLL=str(gross))
    for tid in ("toolu_spaet", "toolu_frueh"):
        r = sh(sys.executable, "normen/normen.py", "hook-nach", "--werkzeug", "claude", cwd=repo, env=env,
               eingabe=json.dumps({"hook_event_name": "PostToolUse", "tool_use_id": tid, "session_id": "s-1"}))
        check(f"hook-nach groß {tid}: Exit 0", r.returncode == 0, r.stderr)
    z = zeilen(gross)
    check("hook-nach groß: frischer Eintrag gefunden", z[-2].get("ausgang") == "ausgefuehrt"
          and z[-2].get("tool_use_id") == "toolu_spaet", str(z[-2:]))
    check("hook-nach groß: alter Eintrag nicht mehr", z[-1].get("tool_use_id") != "toolu_frueh" or "ausgang" not in z[-1],
          str(z[-1:]))

    # Fehler (Protokoll fehlt, kaputtes JSON, Pfad ist Ordner): Exit 0, keine Ausgabe auf stdout
    for name, p, ein in (("fehlt", t / "nach" / "gibt-es-nicht.jsonl", '{"tool_use_id": "x"}'),
                         ("kaputtes JSON", prot, "{kein json"), ("Ordner", t / "nach", '{"tool_use_id": "toolu_a"}')):
        r = normen(repo, p, "hook-nach", "--werkzeug", "claude", eingabe=ein)
        check(f"hook-nach {name}: Exit 0, keine Ausgabe", r.returncode == 0 and r.stdout == "", r.stdout + r.stderr)


def test_auswertung(t):
    repo = t / "repo"
    prot = t / "ausw" / "p.jsonl"
    marke = prot.with_suffix(".marke")
    schreibe(prot, [eintrag("t1", zeit="2026-11-01T10:00:00+0100"), {"zeit": "2026-11-01T10:00:02+0100",
                                                                      "tool_use_id": "t1", "session_id": "s-1",
                                                                      "ausgang": "ausgefuehrt"},
                    eintrag("t2", zeit="2026-11-02T10:00:00+0100"),
                    eintrag("t3", stufe="nein", zeit="2026-11-03T10:00:00+0100", norm="N06-NUR-ERLAUBTE-PFADE",
                            projekt="p2", grund="N06-NUR-ERLAUBTE-PFADE: schreibt in lesbar_extern", inhalt="cp a b")])
    r = normen(repo, prot, "protokoll")
    out = r.stdout
    check("protokoll: Exit 0", r.returncode == 0, out + r.stderr)
    check("protokoll: 3 Einträge (Ausgang-Zeilen zählen nicht)", "3 Einträge" in out, out)
    check("protokoll: Norm und Projekt", "N01-KEINE-ZERSTOERUNG" in out and "p1" in out and "N06-NUR-ERLAUBTE-PFADE" in out
          and "p2" in out, out)
    check("protokoll: fragen 2, davon 1 ausgeführt, 1 kein Beleg", "fragen 2" in out and "ausgeführt 1" in out
          and "kein Beleg 1" in out, out)
    check("protokoll: nein 1", "nein 1" in out, out)
    check("protokoll: Gründe", "schreibt in lesbar_extern" in out, out)
    check("protokoll: Beispiel", "git push --force" in out, out)
    check("protokoll: ohne --gelesen keine Marke", not marke.exists())

    r = normen(repo, prot, "protokoll", "--seit", "2026-11-03")
    check("protokoll --seit: nur 1 Eintrag", r.returncode == 0 and "1 Einträge" in r.stdout and "p1" not in r.stdout,
          r.stdout + r.stderr)
    r = normen(repo, prot, "protokoll", "--seit", "kein-datum")
    check("protokoll --seit ungültig: Exit ≠ 0", r.returncode != 0, r.stdout + r.stderr)

    r = normen(repo, prot, "protokoll", "--gelesen")
    check("protokoll --gelesen: Marke gesetzt", r.returncode == 0 and marke.is_file(), r.stdout + r.stderr)
    r = normen(repo, prot, "protokoll")
    check("protokoll nach Marke: 0 Einträge", r.returncode == 0 and "0 Einträge" in r.stdout, r.stdout)
    r = normen(repo, prot, "protokoll", "--alle")
    check("protokoll --alle: trotz Marke 3", "3 Einträge" in r.stdout, r.stdout)

    # --faellig: Ausgabe nur ab ≥ 7 Tagen seit der Marke und ≥ 1 neuem Eintrag, oder ≥ 30 neuen Einträgen
    from datetime import datetime, timedelta
    jetzt = datetime.now().astimezone()

    def fall(name, marke_tage, neue, erwartet):
        p = t / "ausw" / f"{name}.jsonl"
        m = p.with_suffix(".marke")
        if marke_tage is not None:
            m.write_text((jetzt - timedelta(days=marke_tage)).isoformat(timespec="seconds") + "\n", encoding="utf-8")
        alt = (jetzt - timedelta(days=40)).isoformat(timespec="seconds")
        neu = (jetzt - timedelta(hours=1)).isoformat(timespec="seconds")
        schreibe(p, [eintrag("alt", zeit=alt)] + [eintrag(f"n{i}", zeit=neu) for i in range(neue)])
        r = normen(repo, p, "protokoll", "--faellig")
        check(f"fällig {name}: Exit 0", r.returncode == 0, r.stderr)
        if erwartet:
            check(f"fällig {name}: Hinweis", f"Normen-Protokoll: {neue} neue Einträge" in r.stdout
                  and "normen.py protokoll" in r.stdout, r.stdout)
            check(f"fällig {name}: keine Inhalte", "git push" not in r.stdout and "p1" not in r.stdout, r.stdout)
        else:
            check(f"fällig {name}: still", r.stdout.strip() == "", r.stdout)

    fall("frisch-wenige", 2, 5, False)
    fall("alt-einer", 8, 1, True)
    fall("alt-keiner", 8, 0, False)
    fall("frisch-viele", 1, 30, True)
    fall("frisch-29", 1, 29, False)
    r = normen(repo, t / "ausw" / "gibt-es-nicht.jsonl", "protokoll", "--faellig")
    check("fällig ohne Protokoll: still, Exit 0", r.returncode == 0 and r.stdout.strip() == "", r.stdout + r.stderr)
    r = normen(repo, t / "ausw" / "gibt-es-nicht.jsonl", "protokoll")
    check("protokoll ohne Datei: Exit 0, 0 Einträge", r.returncode == 0 and "0 Einträge" in r.stdout, r.stdout + r.stderr)


def test_einstellungen(t):
    """Hook-Einträge der Quelle: PostToolUse/PostToolUseFailure → hook-nach, SessionStart startup|clear → --faellig."""
    s = json.loads((VORLAGE / "projekt" / ".claude" / "settings.json").read_text(encoding="utf-8"))
    hooks = s.get("hooks", {})
    pre = hooks.get("PreToolUse", [{}])[0].get("matcher")
    for ereignis in ("PostToolUse", "PostToolUseFailure"):
        e = hooks.get(ereignis, [])
        check(f"settings {ereignis}: hook-nach mit Matcher wie PreToolUse",
              any(x.get("matcher") == pre and any("hook-nach --werkzeug claude" in h.get("command", "")
                                                  for h in x.get("hooks", [])) for x in e), json.dumps(e))
    st = hooks.get("SessionStart", [])
    check("settings SessionStart: startup|clear → protokoll --faellig",
          any(x.get("matcher") == "startup|clear" and any("protokoll --faellig" in h.get("command", "")
                                                          for h in x.get("hooks", [])) for x in st), json.dumps(st))
    check("settings SessionStart: compact bleibt", any(x.get("matcher") == "compact" for x in st), json.dumps(st))


def main():
    with tempfile.TemporaryDirectory() as d:
        t = Path(d)
        for f in (test_schreibstelle, test_hook_nach, test_auswertung, test_einstellungen):
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
