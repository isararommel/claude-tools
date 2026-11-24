#!/usr/bin/env python3
"""Tests für `normen.py selbsttest` (v7, G1; v14: auch Datei-Werkzeuge): Köder im Hook und Auswertung der Live-Läufe.
Startet nie echte Agenten – `claude` und `vibe` sind Attrappen im PATH (Modus über NORMEN_ATTRAPPE)."""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("NORMEN_PROTOKOLL", os.path.join(tempfile.gettempdir(), "normen-test-protokoll.jsonl"))  # v18: Hooks der Tests nie ins echte Protokoll
VORLAGE = ROOT / "agenten-normen"
OK = FAIL = 0
WEGE = {"claude": ["bash", "write"], "vibe": ["bash", "write_file", "edit"]}


def check(name, bedingung, info=""):
    global OK, FAIL
    if bedingung:
        OK += 1
    else:
        FAIL += 1
        print(f"FAIL {name} {info}")


def sh(*args, cwd=None, eingabe=None, env=None):
    return subprocess.run(args, cwd=cwd, input=eingabe, capture_output=True, text=True, env=env)


def hook_roh(repo, rolle, werkzeug, tool, eingabe):
    data = {"tool_name": tool, "tool_input": eingabe, "cwd": str(repo)}
    r = sh(sys.executable, "normen/normen.py", "hook", "--rolle", rolle, "--werkzeug", werkzeug, cwd=repo,
           eingabe=json.dumps(data))
    if werkzeug == "claude":
        if not r.stdout.strip():
            return "ja", r.stdout
        return {"deny": "nein", "ask": "fragen"}[json.loads(r.stdout)["hookSpecificOutput"]["permissionDecision"]], r.stdout
    nein = r.stdout.strip() and json.loads(r.stdout.splitlines()[0])["decision"] == "deny"
    return ("nein" if nein else "ja"), r.stdout


def hook(repo, rolle, werkzeug, befehl):
    return hook_roh(repo, rolle, werkzeug, "Bash" if werkzeug == "claude" else "bash", {"command": befehl})[0]


# Attrappen: sperrt = Hook-Meldung mit Marke, Köder unverändert; durch = Köder geschrieben (legt an bzw. ändert den Inhalt);
# nichts = weder noch.
CLAUDE = r"""#!/usr/bin/env bash
echo "$*" >> "$ATTRAPPE_LOG"
# erstnichts: erster Aufruf wie nichts, jeder weitere wie sperrt (Wiederholung bei „unklar“, v10)
if [ "$NORMEN_ATTRAPPE" = erstnichts ]; then if [ -e "$ATTRAPPE_LOG.n" ]; then NORMEN_ATTRAPPE=sperrt; else touch "$ATTRAPPE_LOG.n"; NORMEN_ATTRAPPE=nichts; fi; fi
case "$NORMEN_ATTRAPPE" in
  sperrt) echo '{"type":"user","message":{"content":[{"type":"tool_result","is_error":true,"content":"PreToolUse hook error: Agenten-Normen: SELBSTTEST-KOEDER: Köder des Selbsttests – absichtlich gesperrt."}]}}' ;;
  durch) mkdir -p .normen && echo geaendert > .normen/normen-koeder.txt && echo '{"type":"result","result":"FERTIG-ATTRAPPE"}' ;;
  *) echo '{"type":"result","result":"Ich führe keine Befehle aus."}' ;;
esac
"""
VIBE = r"""#!/usr/bin/env bash
echo "$*" >> "$ATTRAPPE_LOG"
# erstnichts: erster Aufruf wie nichts, jeder weitere wie sperrt (Wiederholung bei „unklar“, v10)
if [ "$NORMEN_ATTRAPPE" = erstnichts ]; then if [ -e "$ATTRAPPE_LOG.n" ]; then NORMEN_ATTRAPPE=sperrt; else touch "$ATTRAPPE_LOG.n"; NORMEN_ATTRAPPE=nichts; fi; fi
OUT=""; while [ $# -gt 0 ]; do [ "$1" = "--output-dir" ] && OUT="$2"; shift; done
case "$NORMEN_ATTRAPPE" in
  sperrt) mkdir -p "$OUT/session/journal" && echo '{"hook":"Agenten-Normen: SELBSTTEST-KOEDER: Köder des Selbsttests – absichtlich gesperrt."}' > "$OUT/session/journal/1.jsonl"; echo "blockiert" ;;
  durch) mkdir -p .normen && echo geaendert > .normen/normen-koeder.txt; mkdir -p "$OUT/session" && echo JOURNAL-ATTRAPPE > "$OUT/session/1.jsonl"; echo FERTIG-ATTRAPPE ;;
  *) echo "Ich führe keine Befehle aus." ;;
esac
"""

with tempfile.TemporaryDirectory() as t:
    repo = Path(t) / "projekt"
    repo.mkdir()
    sh("git", "init", "-q", cwd=repo)
    (repo / "Makefile").write_text("test:\n\techo ok\n")
    r = sh("bash", str(VORLAGE / "einrichten.sh"), str(repo), "--test", "make test")
    check("einrichten", r.returncode == 0, r.stdout + r.stderr)
    sh("git", "add", "-A", cwd=repo)
    sh("git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "start", "--no-verify", cwd=repo)
    sh("git", "checkout", "-q", "-b", "arbeit", cwd=repo)

    # 1. Köder im Hook: genau dieser Befehl ist für alle Rollen gesperrt, nichts anderes
    k = "touch .normen/normen-koeder.txt"
    for rolle, werkzeug in [("claude", "claude"), ("inhaberin", "claude"), ("mistral-team", "vibe"), ("gemini-analyst", "gemini")]:
        check(f"Köder gesperrt für {rolle}", hook(repo, rolle, werkzeug, k) == "nein")
    check("Köder in Kette gesperrt", hook(repo, "claude", "claude", f"cd . && {k}") == "nein")
    for befehl in ["ls .normen/normen-koeder.txt", "cat .normen/normen-koeder.txt", "grep -r normen-koeder normen/",
                   "touch .normen/anderes.txt", "touch .normen/normen-koeder.txt.alt"]:
        check(f"kein Köder: {befehl}", hook(repo, "claude", "claude", befehl) == "ja")
    aus = hook_roh(repo, "claude", "claude", "Bash", {"command": k})[1]
    check("Sperrgrund enthält Marke SELBSTTEST-KOEDER", "SELBSTTEST-KOEDER" in aus, aus)

    # 1b. v14: Köder über Datei-Werkzeuge – alle Rollen, jede Schreibweise des Pfads, mit Marke; Lesen bleibt erlaubt
    pfade = [".normen/normen-koeder.txt", "./.normen/normen-koeder.txt", str(repo / ".normen" / "normen-koeder.txt")]
    faelle = [("claude", "claude", "Write"), ("claude", "claude", "Edit"), ("inhaberin", "claude", "Write"),
              ("mistral-team", "vibe", "write_file"), ("mistral-team", "vibe", "edit"),
              ("mistral-team", "vibe", "search_replace"), ("gemini-analyst", "gemini", "write_file")]
    for rolle, werkzeug, tool in faelle:
        for pfad in pfade:
            ent, aus = hook_roh(repo, rolle, werkzeug, tool, {"file_path": pfad, "content": "x"})
            check(f"Datei-Köder {rolle}/{tool} {pfad}", ent == "nein" and "SELBSTTEST-KOEDER" in aus, aus)
    for rolle, werkzeug, tool in [("claude", "claude", "Read"), ("mistral-team", "vibe", "read_file")]:
        ent, aus = hook_roh(repo, rolle, werkzeug, tool, {"file_path": pfade[0]})
        check(f"Datei-Köder lesen erlaubt: {rolle}/{tool}", ent == "ja" and "SELBSTTEST-KOEDER" not in aus, aus)
    ent, aus = hook_roh(repo, "claude", "claude", "Write", {"file_path": ".normen/normen-koeder.txt.alt", "content": "x"})
    check("kein Datei-Köder: ähnlicher Name", "SELBSTTEST-KOEDER" not in aus, aus)

    for datei in ("AGENTS.md", "normen/kurz.md"):
        check(f"Köder unsichtbar in {datei}", "koeder" not in (repo / datei).read_text().lower())
    auftrag = sh(sys.executable, "normen/normen.py", "auftrag", "--rolle", "mistral-team", cwd=repo).stdout
    check("Köder unsichtbar im Auftrag", "koeder" not in auftrag.lower())

    # 2. selbsttest mit Attrappen
    bin_ = Path(t) / "bin"
    bin_.mkdir()
    for name, text in (("claude", CLAUDE), ("vibe", VIBE)):
        (bin_ / name).write_text(text)
        (bin_ / name).chmod(0o755)
    log = Path(t) / "attrappe.log"
    koeder = repo / ".normen" / "normen-koeder.txt"

    def selbsttest(modus, *args, pfad=None):
        env = dict(os.environ, PATH=pfad or f"{bin_}:{os.environ['PATH']}", NORMEN_ATTRAPPE=modus, ATTRAPPE_LOG=str(log))
        return sh(sys.executable, "normen/normen.py", "selbsttest", *args, cwd=repo, env=env)

    def belege():
        return sorted((repo / ".normen").glob("selbsttest-*.log"))

    for werkzeug, wege in WEGE.items():
        vorher = set(belege())
        r = selbsttest("sperrt", "--werkzeug", werkzeug)
        check(f"{werkzeug} sperrt → Exit 0, alle Wege gesperrt",
              r.returncode == 0 and all(f"{werkzeug}/{w}: gesperrt" in r.stdout for w in wege), r.stdout + r.stderr)
        check(f"{werkzeug} sperrt → kein Beleg-Log", set(belege()) == vorher, str(belege()))
        for weg in wege:
            vorher = set(belege())
            r = selbsttest("durch", "--werkzeug", werkzeug, "--weg", weg)
            check(f"{werkzeug}/{weg} durch → Exit 1, NICHT GESPERRT",
                  r.returncode == 1 and f"{werkzeug}/{weg}: NICHT GESPERRT" in r.stdout, r.stdout + r.stderr)
            check(f"{werkzeug}/{weg} durch → nur dieser Weg", sum(f"{werkzeug}/" in z for z in r.stdout.splitlines()) == 1,
                  r.stdout)
            check(f"{werkzeug}/{weg} durch → Köder-Datei danach entfernt", not koeder.exists())
            neu = sorted(set(belege()) - vorher)
            check(f"{werkzeug}/{weg} durch → genau ein Beleg-Log", len(neu) == 1 and f"-{werkzeug}-{weg}.log" in neu[0].name
                  if neu else False, str(neu))
            if neu:
                inhalt = neu[0].read_text()
                check(f"{werkzeug}/{weg} Beleg enthält Ausgabe", "FERTIG-ATTRAPPE" in inhalt, inhalt[-300:])
                check(f"{werkzeug}/{weg} Pfad des Belegs gemeldet", neu[0].name in r.stdout, r.stdout)
                if werkzeug == "vibe":
                    check(f"vibe/{weg} Beleg enthält Ausgabeordner", "JOURNAL-ATTRAPPE" in inhalt, inhalt[-300:])
            check(f"{werkzeug}/{weg} durch → keine Wiederholung", "Wiederholung" not in r.stdout, r.stdout)
        r = selbsttest("nichts", "--werkzeug", werkzeug)
        check(f"{werkzeug} nichts → Exit 1, unklar", r.returncode == 1 and f"{werkzeug}/bash: unklar" in r.stdout,
              r.stdout + r.stderr)
    for b in belege():
        b.unlink()  # Belege der Attrappen-Läufe (eigene Testdateien)
    for werkzeug, weg in [("claude", "bash"), ("vibe", "bash"), ("vibe", "edit")]:  # v10: bei „unklar“ einmal wiederholen
        Path(f"{log}.n").unlink(missing_ok=True)
        r = selbsttest("erstnichts", "--werkzeug", werkzeug, "--weg", weg)
        check(f"{werkzeug}/{weg} erst unklar, dann gesperrt → Exit 0", r.returncode == 0 and f"{werkzeug}/{weg}: gesperrt"
              in r.stdout and "Wiederholung" in r.stdout, r.stdout + r.stderr)

    # Edit-Weg: Köder liegt vorher mit bekanntem Inhalt bereit; „gesperrt“ nur, wenn der Inhalt unverändert bleibt
    r = selbsttest("sperrt", "--werkzeug", "vibe", "--weg", "edit")
    check("vibe/edit sperrt → gesperrt", r.returncode == 0 and "vibe/edit: gesperrt" in r.stdout, r.stdout + r.stderr)
    check("vibe/edit Köder danach entfernt", not koeder.exists())

    r = selbsttest("sperrt")
    check("ohne --werkzeug: alle Wege beider Werkzeuge",
          r.returncode == 0 and all(f"{n}/{w}: gesperrt" in r.stdout for n, ws in WEGE.items() for w in ws),
          r.stdout + r.stderr)
    r = selbsttest("sperrt", "--weg", "edit")
    check("nur --weg edit: nur vibe", r.returncode == 0 and "vibe/edit: gesperrt" in r.stdout and "claude/" not in r.stdout,
          r.stdout + r.stderr)
    r = selbsttest("sperrt", "--werkzeug", "claude", "--weg", "edit")
    check("Weg passt nicht zum Werkzeug → Exit 64", r.returncode == 64 and "claude/" not in r.stdout, r.stdout + r.stderr)
    koeder.parent.mkdir(exist_ok=True)
    koeder.write_text("alt\n")
    r = selbsttest("sperrt", "--werkzeug", "claude", "--weg", "bash")
    check("alter Köder wird vorher entfernt", r.returncode == 0 and not koeder.exists(), r.stdout + r.stderr)

    aufrufe = log.read_text() if log.exists() else ""
    check("Attrappen wurden aufgerufen", bool(aufrufe))
    check("claude ohne Bypass-Schalter", "--dangerously-skip-permissions" not in aufrufe and "bypassPermissions" not in aufrufe)
    check("vibe ohne --auto-approve/--yolo", "--auto-approve" not in aufrufe and "--yolo" not in aufrufe)
    check("claude bash mit enger Freigabe", "Bash(touch .normen/normen-koeder.txt)" in aufrufe, aufrufe[-400:])
    check("claude write mit enger, absoluter Freigabe", f"Edit(/{repo.resolve() / '.normen' / 'normen-koeder.txt'})" in aufrufe,
          aufrufe[-400:])
    check("claude ohne pauschale Freigabe", not any(f" {w} " in f" {z} " for z in aufrufe.splitlines() for w in ("Write", "Edit")),
          aufrufe[-400:])
    leer = Path(t) / "leer"
    leer.mkdir()
    r = selbsttest("sperrt", "--werkzeug", "vibe", "--weg", "bash", pfad=f"{leer}:/usr/bin:/bin")
    check("vibe fehlt → unklar, Exit 1", r.returncode == 1 and "vibe/bash: unklar" in r.stdout, r.stdout + r.stderr)
    check("vibe fehlt → keine Wiederholung", "Wiederholung" not in r.stdout, r.stdout)
    check("Hook: selbsttest für Claude ja", hook(repo, "claude", "claude", "python3 normen/normen.py selbsttest") == "ja")

print(f"{OK} ok, {FAIL} Fehler")
sys.exit(1 if FAIL else 0)
