#!/usr/bin/env python3
"""Tests für `normen.py selbsttest` (v7, G1): Köder im Hook und Auswertung der Live-Läufe.
Startet nie echte Agenten – `claude` und `vibe` sind Attrappen im PATH (Modus über NORMEN_ATTRAPPE)."""
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


def hook(repo, rolle, werkzeug, befehl):
    data = {"tool_name": "Bash" if werkzeug == "claude" else "bash", "tool_input": {"command": befehl}, "cwd": str(repo)}
    r = sh(sys.executable, "normen/normen.py", "hook", "--rolle", rolle, "--werkzeug", werkzeug, cwd=repo,
           eingabe=json.dumps(data))
    if werkzeug == "claude":
        if not r.stdout.strip():
            return "ja"
        return {"deny": "nein", "ask": "fragen"}[json.loads(r.stdout)["hookSpecificOutput"]["permissionDecision"]]
    return "nein" if r.stdout.strip() and json.loads(r.stdout.splitlines()[0])["decision"] == "deny" else "ja"


# Attrappen: sperrt = Hook-Meldung mit Marke, keine Datei; durch = Datei angelegt; nichts = weder noch.
CLAUDE = r"""#!/usr/bin/env bash
echo "$*" >> "$ATTRAPPE_LOG"
# erstnichts: erster Aufruf wie nichts, jeder weitere wie sperrt (Wiederholung bei „unklar“, v10)
if [ "$NORMEN_ATTRAPPE" = erstnichts ]; then if [ -e "$ATTRAPPE_LOG.n" ]; then NORMEN_ATTRAPPE=sperrt; else touch "$ATTRAPPE_LOG.n"; NORMEN_ATTRAPPE=nichts; fi; fi
case "$NORMEN_ATTRAPPE" in
  sperrt) echo '{"type":"user","message":{"content":[{"type":"tool_result","is_error":true,"content":"PreToolUse:Bash hook error: Agenten-Normen: SELBSTTEST-KOEDER: Köder des Selbsttests – absichtlich gesperrt."}]}}' ;;
  durch) mkdir -p .normen && touch .normen/normen-koeder.txt && echo '{"type":"result","result":"FERTIG"}' ;;
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
  durch) mkdir -p .normen && touch .normen/normen-koeder.txt; echo FERTIG ;;
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
    data = {"tool_name": "Bash", "tool_input": {"command": k}, "cwd": str(repo)}
    aus = sh(sys.executable, "normen/normen.py", "hook", "--rolle", "claude", "--werkzeug", "claude", cwd=repo,
             eingabe=json.dumps(data)).stdout
    check("Sperrgrund enthält Marke SELBSTTEST-KOEDER", "SELBSTTEST-KOEDER" in aus, aus)
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

    for werkzeug in ("claude", "vibe"):
        r = selbsttest("sperrt", "--werkzeug", werkzeug)
        check(f"{werkzeug} sperrt → Exit 0", r.returncode == 0 and f"{werkzeug}: gesperrt" in r.stdout, r.stdout + r.stderr)
        r = selbsttest("durch", "--werkzeug", werkzeug)
        check(f"{werkzeug} durch → Exit 1, NICHT GESPERRT", r.returncode == 1 and f"{werkzeug}: NICHT GESPERRT" in r.stdout,
              r.stdout + r.stderr)
        check(f"{werkzeug} durch → Köder-Datei danach entfernt", not koeder.exists())
        r = selbsttest("nichts", "--werkzeug", werkzeug)
        check(f"{werkzeug} nichts → Exit 1, unklar", r.returncode == 1 and f"{werkzeug}: unklar" in r.stdout, r.stdout + r.stderr)
    for werkzeug in ("claude", "vibe"):  # v10: bei „unklar“ einmal wiederholen
        Path(f"{log}.n").unlink(missing_ok=True)
        r = selbsttest("erstnichts", "--werkzeug", werkzeug)
        check(f"{werkzeug} erst unklar, dann gesperrt → Exit 0", r.returncode == 0 and f"{werkzeug}: gesperrt" in r.stdout
              and "Wiederholung" in r.stdout, r.stdout + r.stderr)
        r = selbsttest("durch", "--werkzeug", werkzeug)
        check(f"{werkzeug} durch → keine Wiederholung", "Wiederholung" not in r.stdout and "NICHT GESPERRT" in r.stdout,
              r.stdout + r.stderr)
    r = selbsttest("sperrt")
    check("ohne --werkzeug: beide geprüft", r.returncode == 0 and "claude: gesperrt" in r.stdout and "vibe: gesperrt" in r.stdout,
          r.stdout + r.stderr)
    koeder.parent.mkdir(exist_ok=True)
    koeder.write_text("alt\n")
    r = selbsttest("sperrt", "--werkzeug", "claude")
    check("alter Köder wird vorher entfernt", r.returncode == 0 and not koeder.exists(), r.stdout + r.stderr)
    aufrufe = log.read_text() if log.exists() else ""
    check("Attrappen wurden aufgerufen", bool(aufrufe))
    check("claude ohne Bypass-Schalter", "--dangerously-skip-permissions" not in aufrufe and "bypassPermissions" not in aufrufe)
    check("vibe ohne --auto-approve/--yolo", "--auto-approve" not in aufrufe and "--yolo" not in aufrufe)
    check("claude mit enger Freigabe", "Bash(touch .normen/normen-koeder.txt)" in aufrufe, aufrufe[-400:])
    leer = Path(t) / "leer"
    leer.mkdir()
    r = selbsttest("sperrt", "--werkzeug", "vibe", pfad=f"{leer}:/usr/bin:/bin")
    check("vibe fehlt → unklar, Exit 1", r.returncode == 1 and "vibe: unklar" in r.stdout, r.stdout + r.stderr)
    check("vibe fehlt → keine Wiederholung", "Wiederholung" not in r.stdout, r.stdout)
    check("Hook: selbsttest für Claude ja", hook(repo, "claude", "claude", "python3 normen/normen.py selbsttest") == "ja")

print(f"{OK} ok, {FAIL} Fehler")
sys.exit(1 if FAIL else 0)
