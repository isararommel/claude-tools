#!/usr/bin/env python3
"""Tests für v15: vertraute Werkzeuge ([werkzeuge].vertraut) und Befehle über Variablen im S06-Hook.
Das Werkzeug ist ein Python-Skript mit Netz, Schlüsselbund-Aufruf und os.replace im Temp-Ordner (außerhalb des Projekts) –
ohne Eintrag sperrt die AST-Prüfung es, mit Eintrag gelten nur die freigegebenen Unterbefehle."""
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


def hook(repo, befehl, rolle="claude", env=None):
    data = {"tool_name": "Bash", "tool_input": {"command": befehl}, "cwd": str(repo)}
    r = sh(sys.executable, "normen/normen.py", "hook", "--rolle", rolle, "--werkzeug", "claude", cwd=repo,
           eingabe=json.dumps(data), env=env)
    if not r.stdout.strip():
        return "ja", r.stderr
    out = json.loads(r.stdout)["hookSpecificOutput"]
    return {"deny": "nein", "ask": "fragen"}[out["permissionDecision"]], out.get("permissionDecisionReason", "")


WERKZEUG = """#!/usr/bin/env python3
import argparse, os, subprocess, urllib.request
schluessel = subprocess.run(["security", "find-generic-password", "-s", "dienst", "-w"], capture_output=True).stdout
os.replace("a", "b")
urllib.request.urlopen("https://example.invalid")
"""

with tempfile.TemporaryDirectory() as t:
    t = Path(os.path.realpath(t))
    repo = t / "projekt"
    repo.mkdir()
    sh("git", "init", "-q", cwd=repo)
    (repo / "Makefile").write_text("test:\n\techo ok\n")
    r = sh("bash", str(VORLAGE / "einrichten.sh"), str(repo), "--test", "make test")
    check("einrichten", r.returncode == 0, r.stdout + r.stderr)
    sh("git", "add", "-A", cwd=repo)
    sh("git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "start", "--no-verify", cwd=repo)
    sh("git", "checkout", "-q", "-b", "arbeit", cwd=repo)
    bindir = t / "werkzeug" / "bin"
    bindir.mkdir(parents=True)
    wz = bindir / "werkzeug"
    wz.write_text(WERKZEUG)
    wz.chmod(0o755)
    pj = repo / "normen" / "projekt.toml"
    vorlage = pj.read_text(encoding="utf-8")
    check("Vorlage hat [werkzeuge] mit leerer Liste", "[werkzeuge]\n" in vorlage and "\nvertraut = []\n" in vorlage)

    # ohne Eintrag: wie bisher per AST gesperrt; Variable ohne Eintrag ebenfalls geprüft (Lücke aus #87 geschlossen)
    s, g = hook(repo, f"{wz} status x")
    check("ohne Eintrag: Pfadaufruf per AST gesperrt", s == "nein", f"{s} {g}")
    s, g = hook(repo, f"B={wz}; $B status x")
    check("ohne Eintrag: $B wird aufgelöst und geprüft", s == "nein", f"{s} {g}")

    pj.write_text(vorlage.replace(
        "\nvertraut = []\n",
        f'\nvertraut = [{{pfad = "{wz}", unterbefehle = ["status", "holen", "einreichen"]}}]\n'), encoding="utf-8")
    faelle = [
        (f"{wz} status b-1", "ja", "freigegebener Unterbefehl"),
        (f"{wz} holen b-1 --ziel {t}/aus", "ja", "freigegebener Unterbefehl mit Optionen"),
        (f"{wz} schluessel-anlegen", "nein", "nicht freigegebener Unterbefehl"),
        (f"{wz}", "nein", "ohne Unterbefehl"),
        (f"{wz} --hilfe", "nein", "Option statt Unterbefehl"),
        (f"X=status; {wz} $X", "nein", "Unterbefehl über Variable"),
        (f"B={wz}; $B status b-1", "ja", "$B aufgelöst"),
        (f'B={wz}; "${{B}}" status b-1', "ja", '"${B}" aufgelöst'),
        (f"B={wz}; $B schluessel-anlegen", "nein", "$B mit verbotenem Unterbefehl"),
        (f"if x; then B={wz}; else B=/bin/ls; fi; $B status", "fragen", "doppelt zugewiesene Variable"),
        ("$UNBEKANNT_NORMEN_X status", "fragen", "unaufgelöste Variable als Befehl"),
        (f"{wz} status b-1; git reset --hard", "fragen", "Rest des Befehls wird weiter geprüft"),
        (f"python3 {wz} status", "nein", "python3 davor: AST wie bisher"),
        (f"cd {bindir} && ./werkzeug status", "ja", "relativer Aufruf nach cd"),
        (f"cd {bindir} && ./werkzeug schluessel-anlegen", "nein", "relativer Aufruf, verboten"),
        (f"echo x > {wz}; {wz} status", "fragen", "Werkzeug im selben Befehl geschrieben"),
    ]
    for befehl, soll, name in faelle:
        s, g = hook(repo, befehl)
        check(f"vertraut: {name}", s == soll, f"{befehl!r}: {s} (soll {soll}) {g}")
    s, g = hook(repo, f"{wz} status", rolle="mistral-team")
    check("vertraut gilt nur für Rolle claude", s == "nein", f"{s} {g}")

    env = dict(os.environ, PATH=f"{bindir}{os.pathsep}{os.environ['PATH']}")
    s, g = hook(repo, "werkzeug status", env=env)
    check("Name aus $PATH, freigegeben", s == "ja", f"{s} {g}")
    s, g = hook(repo, "werkzeug schluessel-anlegen", env=env)
    check("Name aus $PATH, verboten", s == "nein", f"{s} {g}")

    # lesbar_extern hebelt die Unterbefehl-Liste nicht aus
    pj.write_text(pj.read_text(encoding="utf-8").replace(
        'lesbar_extern = [', f'lesbar_extern = ["{t}/werkzeug", '), encoding="utf-8")
    s, g = hook(repo, f"{wz} schluessel-anlegen")
    check("lesbar_extern: verbotener Unterbefehl bleibt nein", s == "nein", f"{s} {g}")

    # fehlerhafter Eintrag: Hook sperrt mit Meldung (fail-closed)
    pj.write_text(vorlage.replace("\nvertraut = []\n", f'\nvertraut = [{{pfad = "{wz}"}}]\n'), encoding="utf-8")
    s, g = hook(repo, f"{wz} status")
    check("fehlerhafter Eintrag sperrt mit Meldung", s == "nein" and "unterbefehle" in g, f"{s} {g}")

print(f"{OK} ok, {FAIL} Fehler")
sys.exit(1 if FAIL else 0)
