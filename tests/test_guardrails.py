#!/usr/bin/env python3
"""Tests für die Guardrail-Pakete aus Normen v7 (G2 ff., siehe docs/plaene/guardrails-v7-entwurf.md)."""
import json
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


def sh(*args, cwd=None, eingabe=None):
    return subprocess.run(args, cwd=cwd, input=eingabe, capture_output=True, text=True)


def hook(repo, rolle, werkzeug, befehl):
    data = {"tool_name": "Bash" if werkzeug == "claude" else "bash", "tool_input": {"command": befehl}, "cwd": str(repo)}
    r = sh(sys.executable, "normen/normen.py", "hook", "--rolle", rolle, "--werkzeug", werkzeug, cwd=repo,
           eingabe=json.dumps(data))
    if werkzeug == "claude":
        if not r.stdout.strip():
            return "ja"
        return {"deny": "nein", "ask": "fragen"}[json.loads(r.stdout)["hookSpecificOutput"]["permissionDecision"]]
    return "nein" if r.stdout.strip() and json.loads(r.stdout.splitlines()[0])["decision"] == "deny" else "ja"


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

    # G2 (L6): pre-commit-Hook nicht umgehen – für alle Rollen außer inhaberin gesperrt
    umgehen = ["git commit --no-verify -m x", "git commit -an", "git commit -n -m x", "git commit -qnm x",
               "git -c core.hooksPath=/dev/null commit -m x", "git config core.hooksPath /tmp/leer",
               "git config --local core.hooksPath x", "git push --no-verify", "git -C . commit --no-verify -m x",
               "cd . && git commit --no-verify -m x"]
    for befehl in umgehen:
        check(f"claude sperrt: {befehl}", hook(repo, "claude", "claude", befehl) == "nein")
        check(f"vibe sperrt: {befehl}", hook(repo, "mistral-team", "vibe", befehl) == "nein")
        check(f"inhaberin darf: {befehl}", "hooks-umgehen" not in sh(
            sys.executable, "normen/normen.py", "hook", "--rolle", "inhaberin", "--werkzeug", "claude", cwd=repo,
            eingabe=json.dumps({"tool_name": "Bash", "tool_input": {"command": befehl}, "cwd": str(repo)})).stdout)
    erlaubt = ['git commit -m "x"', "git commit -qm x", "git commit --amend --no-edit", 'git commit -m "fix: --no-verify entfernt"',
               "git config --get core.hooksPath", "git config core.hooksPath", "git log -n 3", "git push -u origin arbeit",
               "git status --short", "git commit -m x --signoff"]
    for befehl in erlaubt:
        check(f"claude erlaubt: {befehl}", hook(repo, "claude", "claude", befehl) == "ja")
    data = {"tool_name": "Bash", "tool_input": {"command": "git commit --no-verify -m x"}, "cwd": str(repo)}
    aus = sh(sys.executable, "normen/normen.py", "hook", "--rolle", "claude", "--werkzeug", "claude", cwd=repo,
             eingabe=json.dumps(data)).stdout
    check("Meldung nennt den Grund", "pre-commit-Hook nicht umgehen" in aus, aus)

print(f"{OK} ok, {FAIL} Fehler")
sys.exit(1 if FAIL else 0)
