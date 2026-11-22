#!/usr/bin/env python3
"""Tests für Normen v16: Schreibweise von Pfaden (#74), `python -m` und Projekt-Importe (#71), Sitzungsprobe (#66),
G9 bei Testlöschung samt Altcode (#61), Stufen-Label in `melden` (#75). Startet nie echte Agenten."""
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


def neues_repo(t, name, *opt):
    repo = Path(os.path.realpath(t)) / name
    repo.mkdir()
    sh("git", "init", "-q", "-b", "arbeit", cwd=repo)
    sh("git", "config", "user.email", "test@example.org", cwd=repo)
    sh("git", "config", "user.name", "Test", cwd=repo)
    r = sh("bash", str(VORLAGE / "einrichten.sh"), str(repo), "--test", "echo ok", *opt)
    check(f"einrichten {name}", r.returncode == 0, r.stdout + r.stderr)
    return repo, r.stdout


def hook_roh(repo, rolle, werkzeug, data):
    data.setdefault("cwd", str(repo))
    return sh(sys.executable, "normen/normen.py", "hook", "--rolle", rolle, "--werkzeug", werkzeug,
              cwd=repo, eingabe=json.dumps(data)).stdout


def hook(repo, rolle, werkzeug, data):
    aus = hook_roh(repo, rolle, werkzeug, data)
    if werkzeug == "claude":
        if not aus.strip():
            return "ja"
        return {"deny": "nein", "ask": "fragen"}[json.loads(aus)["hookSpecificOutput"]["permissionDecision"]]
    return "nein" if aus.strip() and json.loads(aus.splitlines()[0])["decision"] == "deny" else "ja"


def normen(repo, *args, env=None):
    return sh(sys.executable, "normen/normen.py", *args, cwd=repo, env=env)


def V(c):
    return {"tool_name": "bash", "tool_input": {"command": c}}


with tempfile.TemporaryDirectory() as t:
    t = os.path.realpath(t)

    # A. #74 Groß-/Kleinschreibung
    repo, aus_einrichten = neues_repo(t, "MeinProjekt", "--sperre", "daten/geheim/")
    (repo / "daten/geheim").mkdir(parents=True)
    (repo / "modul.py").write_text("X = 1\n")
    (repo / ".normen-auftrag").write_text("modul.py\n")
    probe = Path(t) / "probe-schreibweise"
    probe.write_text("x")
    ohne_schreibweise = (Path(t) / "PROBE-SCHREIBWEISE").exists()
    klein = str(repo).replace("MeinProjekt", "meinprojekt")
    check("A: .claude/settings.json fragt",
          hook(repo, "claude", "claude", {"tool_name": "Write", "tool_input": {"file_path": f"{repo}/.claude/settings.json", "content": "x"}}) == "fragen")
    check("A: .env gesperrt", hook(repo, "claude", "claude", {"tool_name": "Read", "tool_input": {"file_path": f"{repo}/.env"}}) == "nein")
    check("A: modul.py absolut ja",
          hook(repo, "mistral-team", "vibe", {"tool_name": "write_file", "tool_input": {"path": f"{repo}/modul.py", "content": "x"}}) == "ja")
    check("A: andere.py nein",
          hook(repo, "mistral-team", "vibe", {"tool_name": "write_file", "tool_input": {"path": f"{repo}/andere.py", "content": "x"}}) == "nein")
    if ohne_schreibweise:
        check("A: .Claude/settings.json fragt",
              hook(repo, "claude", "claude", {"tool_name": "Write", "tool_input": {"file_path": f"{repo}/.Claude/settings.json", "content": "x"}}) == "fragen")
        check("A: NORMEN/normen.toml fragt",
              hook(repo, "claude", "claude", {"tool_name": "Write", "tool_input": {"file_path": f"{repo}/NORMEN/normen.toml", "content": "x"}}) == "fragen")
        check("A: .ENV gesperrt", hook(repo, "claude", "claude", {"tool_name": "Read", "tool_input": {"file_path": f"{repo}/.ENV"}}) == "nein")
        check("A: read_file Daten/Geheim gesperrt",
              hook(repo, "mistral-team", "vibe", {"tool_name": "read_file", "tool_input": {"path": f"{repo}/Daten/Geheim/a.txt"}}) == "nein")
        check("A: write_file mit Projektordner in anderer Schreibweise ja",
              hook(repo, "mistral-team", "vibe", {"tool_name": "write_file", "tool_input": {"path": f"{klein}/modul.py", "content": "x"}}) == "ja")
    else:
        print("A übersprungen (Dateisystem unterscheidet Schreibweise)")
    check("A: bash cat Daten/Geheim gesperrt", hook(repo, "mistral-team", "vibe", V("cat Daten/Geheim/a.txt")) == "nein")
    (repo / ".normen-auftrag").unlink()
    # Konfiguration in anderer Schreibweise als die Platte (Advisor-Befund): Sperrpfad `Daten/Geheim/`, Auftrag `Modul.py`
    if ohne_schreibweise:
        repo_k, _ = neues_repo(t, "Konfig", "--sperre", "Daten/Geheim/")
        (repo_k / "daten/geheim").mkdir(parents=True)
        (repo_k / "modul.py").write_text("X = 1\n")
        (repo_k / ".normen-auftrag").write_text("Modul.py\n")
        for pfad in ("daten/geheim/a.txt", "Daten/Geheim/a.txt"):
            check(f"A: Sperre Daten/Geheim/, read_file {pfad} gesperrt",
                  hook(repo_k, "mistral-team", "vibe", {"tool_name": "read_file", "tool_input": {"path": f"{repo_k}/{pfad}"}}) == "nein")
        check("A: Auftrag Modul.py, write_file modul.py ja",
              hook(repo_k, "mistral-team", "vibe", {"tool_name": "write_file", "tool_input": {"path": f"{repo_k}/modul.py", "content": "x"}}) == "ja")
        check("A: Auftrag Modul.py, bash echo > modul.py ja", hook(repo_k, "mistral-team", "vibe", V("echo x > modul.py")) == "ja")
        (repo_k / ".normen-auftrag").unlink()

    # B. #71 python -m und Projekt-Importe
    lauf = Path(t) / "lauf"
    (lauf / "pk").mkdir(parents=True)
    (lauf / "pruef.py").write_text("import os\nos.remove('/tmp/gibt-es-nicht-v15')\n")
    (lauf / "harmlos.py").write_text("print(1)\n")
    (lauf / "modul.py").write_text("import shutil\nshutil.rmtree('/tmp/gibt-es-nicht-v15')\n")
    (lauf / "pk" / "__main__.py").write_text("import os\nos.remove('/tmp/gibt-es-nicht-v15')\n")
    faelle = [
        ("python3 -c 'import modul; print(modul.X)'", "ja"),
        (f"cd {lauf} && PYTHONPATH={repo} python3 -c 'import modul'", "nein"),
        (f"cd {lauf} && PYTHONPATH={repo} python3 -m pruef", "nein"),
        (f"cd {lauf} && python3 -m harmlos", "ja"),
        (f"cd {lauf} && python3 -m pk", "nein"),
        (f"cd {lauf} && python3 -mpruef", "nein"),
        (f"PYTHONPATH={lauf} python3 -m pruef", "nein"),
        (f"env PYTHONPATH={lauf} python3 -m pruef", "nein"),
        (f"export PYTHONPATH={lauf}; python3 -m pruef", "nein"),
        ("PYTHONPATH=$X python3 -m pruef", "nein"),
        ("python3 -m modul", "ja"),
        ("python3 -m pytest -q", "ja"),
        ("python3 -m pip install -r requirements.txt", "ja"),
        ("python3 -m venv .venv", "ja"),
    ]
    for befehl, soll in faelle:
        check(f"B: {befehl} → {soll}", hook(repo, "mistral-team", "vibe", V(befehl)) == soll)
    check("B: Meldung nennt os.remove", "os.remove" in hook_roh(repo, "mistral-team", "vibe", V(f"cd {lauf} && python3 -m pruef")))
    r = normen(repo, "auftrag", "--rolle", "mistral-team", "--dateien", "x.py")
    check("B: Pflichtsatz gegen Umgehen", "denselben Zweck nicht auf anderem Weg erreichen" in r.stdout, r.stdout + r.stderr)
    normen(repo, "auftrag", "--ende")

    # C. #66 Sitzungsprobe
    koeder = "touch .normen/normen-koeder.txt"
    check("C: Köder gesperrt", hook(repo, "claude", "claude", {"tool_name": "Bash", "tool_input": {"command": koeder},
                                                              "session_id": "s-123"}) == "nein")
    probe_datei = repo / ".normen/sitzungsprobe.txt"
    check("C: Sitzungsprobe geschrieben", probe_datei.exists() and "s-123" in probe_datei.read_text().splitlines())
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_CODE_SESSION_ID"}
    r = normen(repo, "selbsttest", "--sitzung", env=dict(env, CLAUDE_CODE_SESSION_ID="s-123"))
    check("C: eigene Sitzung bestanden", r.returncode == 0 and "Sitzungsprobe bestanden" in r.stdout, r.stdout + r.stderr)
    r = normen(repo, "selbsttest", "--sitzung", env=dict(env, CLAUDE_CODE_SESSION_ID="s-999"))
    check("C: fremde Sitzung nicht bestanden", r.returncode == 1 and "NICHT bestanden" in r.stdout, r.stdout + r.stderr)
    r = normen(repo, "selbsttest", "--sitzung", env=env)
    check("C: ohne Sitzungs-ID nicht bestanden", r.returncode == 1, r.stdout + r.stderr)
    vorher = probe_datei.read_text()
    check("C: vibe-Köder gesperrt", hook(repo, "mistral-team", "vibe", {"tool_name": "bash", "tool_input": {"command": koeder},
                                                                      "session_id": "v-1"}) == "nein")
    check("C: vibe schreibt keine Sitzungsprobe", probe_datei.read_text() == vorher)
    check("C: einrichten nennt selbsttest --sitzung", "selbsttest --sitzung" in aus_einrichten)

    # D. #61 G9 – Testdatei samt Altcode gelöscht
    def g9_repo(name):
        r, _ = neues_repo(t, name)
        (r / "src").mkdir()
        (r / "tests").mkdir()
        (r / "src/kartenrechner.py").write_text("def hoehe():\n    return 1\n")
        (r / "src/utils.py").write_text("X = 1\n")
        (r / "tests/test_island.py").write_text("from src.kartenrechner import hoehe\n\n\ndef test_a():\n"
                                                "    assert hoehe() == 1\n    assert hoehe() > 0\n")
        (r / "src/__init__.py").write_text("")
        (r / "tests/test_andere.py").write_text("# prüft nichts aus __init__\ndef test_b():\n    assert 1 == 1\n    assert 2 == 2\n")
        sh("git", "add", "-A", cwd=r)
        sh("git", "commit", "-q", "--no-verify", "-m", "basis", cwd=r)
        return r

    nr = 0
    for fall, dateien, soll_ok in [("Test + Altcode", ["tests/test_island.py", "src/kartenrechner.py"], True),
                                   ("nur Test", ["tests/test_island.py"], False),
                                   ("Test + fremder Code", ["tests/test_andere.py", "src/utils.py"], False),
                                   ("Test + __init__", ["tests/test_andere.py", "src/__init__.py"], False)]:
        for eingang in ("--diff", "--staged", "--diff HEAD~1"):
            nr += 1
            r = g9_repo(f"g9-{nr}")
            sh("git", "rm", "-q", *dateien, cwd=r)
            if eingang == "--diff":
                sh("git", "reset", "-q", cwd=r)  # Löschung nur im Arbeitsbaum (Index zurück auf HEAD)
                p = normen(r, "pruefen", "--diff")
            elif eingang == "--staged":
                p = normen(r, "pruefen", "--staged")
            else:
                sh("git", "commit", "-q", "--no-verify", "-m", "weg", cwd=r)
                p = normen(r, "pruefen", "--diff", "HEAD~1")
            aus = p.stdout + p.stderr
            name = f"D: {fall} {eingang}"
            if soll_ok:
                check(f"{name} → Exit 0", p.returncode == 0, aus)
                check(f"{name} → kein „Assert entfernt“", "Assert entfernt" not in aus, aus)
                check(f"{name} → Hinweis nennt beide Dateien", "tests/test_island.py" in aus and "src/kartenrechner.py" in aus, aus)
            else:
                check(f"{name} → Exit ≠ 0", p.returncode != 0, aus)
                check(f"{name} → „Assert entfernt“", "Assert entfernt" in aus, aus)

    # E. #75 Stufen-Label
    rep = Path(t) / "text.md"
    rep.write_text("Harmlos.\n")
    pt = repo / "normen/projekt.toml"
    pt.write_text(pt.read_text().replace('[rueckmeldung]\n', '[rueckmeldung]\nrepo = "jemand/sammlung"\n', 1)
                  .replace('\nrepo = ""', "\n"))
    bin_ = Path(t) / "bin"
    bin_.mkdir()
    log = Path(t) / "gh.log"
    (bin_ / "gh").write_text(f'#!/usr/bin/env bash\necho "$*" >> "{log}"\n'
                             'case "$1 $2" in "repo view") echo PRIVATE ;; "issue create") echo https://x/issues/1 ;; esac\n')
    (bin_ / "gh").chmod(0o755)
    env = dict(os.environ, PATH=f"{bin_}:{os.environ['PATH']}")
    m = ["melden", "--art", "zu-streng", "--titel", "Probe", "--text-datei", str(rep)]
    r = normen(repo, *m, "--stufe", "hoch", env=env)
    check("E: melden --stufe hoch", r.returncode == 0, r.stdout + r.stderr)
    check("E: Label stufe:hoch", "--label stufe:hoch" in log.read_text())
    log.write_text("")
    r = normen(repo, *m, env=env)
    check("E: ohne --stufe kein Stufen-Label", r.returncode == 0 and "stufe:" not in log.read_text(), r.stdout + r.stderr)

print(f"{OK} ok, {FAIL} Fehler")
sys.exit(1 if FAIL else 0)
