#!/usr/bin/env python3
"""Tests für V15b-2 (Normen v16): G9-Beleg nur aus Importzeilen (Nr. 9), Sitzungsprobe geschützt (Nr. 10),
lesbar_extern ohne Groß-/Kleinschreibung (Nr. 12), Forschungsdaten im Prompt ohne Groß-/Kleinschreibung (Nr. 20),
`cd "$D"` mit bekannter Zuweisung. Befund-Nummern: docs/reviews/2026-11-20-paket-v15-hooks.md. Startet nie echte Agenten."""
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("NORMEN_PROTOKOLL", os.path.join(tempfile.gettempdir(), "normen-test-protokoll/protokoll.jsonl"))  # v18: Hooks der Tests nie ins echte Protokoll
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


def neues_repo(t, name):
    repo = t / name
    repo.mkdir()
    sh("git", "init", "-q", "-b", "arbeit", cwd=repo)
    sh("git", "config", "user.email", "test@example.org", cwd=repo)
    sh("git", "config", "user.name", "Test", cwd=repo)
    r = sh("bash", str(VORLAGE / "einrichten.sh"), str(repo), "--test", "echo ok")
    check(f"einrichten {name}", r.returncode == 0, r.stdout + r.stderr)
    return repo


def hook(repo, data, rolle="claude"):
    """Stufe aus dem Claude-Hook (fragen bleibt fragen, auch für Team-Rollen)."""
    data.setdefault("cwd", str(repo))
    r = sh(sys.executable, "normen/normen.py", "hook", "--rolle", rolle, "--werkzeug", "claude", cwd=repo,
           eingabe=json.dumps(data))
    if not r.stdout.strip():
        return "ja", r.stderr
    out = json.loads(r.stdout)["hookSpecificOutput"]
    return {"deny": "nein", "ask": "fragen"}[out["permissionDecision"]], out.get("permissionDecisionReason", "")


def B(befehl):
    return {"tool_name": "Bash", "tool_input": {"command": befehl}}


with tempfile.TemporaryDirectory() as t:
    t = Path(os.path.realpath(t))
    repo = neues_repo(t, "projekt")
    ohne_gross = (t / "PROJEKT").exists()  # Dateisystem ohne Groß-/Kleinschreibung (macOS-Standard)

    # Nr. 9 G9: Beleg nur, wenn der Stamm in einer Importzeile der gelöschten Testdatei steht
    def g9(name, testtext, code, codetext="X = 1\n"):
        r = neues_repo(t, name)
        (r / "tests").mkdir()
        (r / "src").mkdir()
        (r / code).write_text(codetext)
        (r / "tests/test_x.py").write_text(testtext + "\n\ndef test_a():\n    assert 1 == 1\n    assert 2 == 2\n")
        sh("git", "add", "-A", cwd=r)
        sh("git", "commit", "-q", "--no-verify", "-m", "basis", cwd=r)
        sh("git", "rm", "-q", "tests/test_x.py", code, cwd=r)
        p = sh(sys.executable, "normen/normen.py", "pruefen", "--staged", cwd=r)
        return p.returncode, p.stdout + p.stderr

    for fall, text, code, soll_ok in [
        ("import-Zeile", "import utils", "src/utils.py", True),
        ("from-Zeile", "from src.utils import X", "src/utils.py", True),
        ("Stamm nur im Kommentar", "# nutzt utils nicht", "src/utils.py", False),
        ("auskommentierter Import", "# import utils", "src/utils.py", False),
        ("Stamm im Text", 'NAME = "utils"', "src/utils.py", False),
        ("Daten-Datei", "import data", "src/data.json", False),
        ("Doku-Datei", "import main", "src/main.md", False),
    ]:
        rc, aus = g9(f"g9-{fall.replace(' ', '-')}", text, code)
        if soll_ok:
            check(f"Nr. 9: {fall} → Exit 0", rc == 0 and "Assert entfernt" not in aus, aus[-400:])
        else:
            check(f"Nr. 9: {fall} → Assert entfernt", rc != 0 and "Assert entfernt" in aus, aus[-400:])

    # Nr. 10: Sitzungsprobe geschützt; --sitzung schließt --werkzeug/--weg aus
    for data, soll_claude in [(B("echo s-1 >> .normen/sitzungsprobe.txt"), "fragen"),
                              ({"tool_name": "Write", "tool_input": {"file_path": str(repo / ".normen/sitzungsprobe.txt"),
                                                                     "content": "s-1\n"}}, "fragen")]:
        for rolle, soll in (("claude", soll_claude), ("mistral-team", "nein")):
            s, g = hook(repo, dict(data), rolle)
            check(f"Nr. 10: {rolle} {data['tool_name']} sitzungsprobe → {soll}", s == soll, f"ist {s}: {g[:200]}")
    for zusatz in (["--werkzeug", "claude"], ["--weg", "bash"]):
        r = sh(sys.executable, "normen/normen.py", "selbsttest", "--sitzung", *zusatz, cwd=repo,
               env=dict(os.environ, CLAUDE_CODE_SESSION_ID="s-1"))
        check(f"Nr. 10: --sitzung {zusatz[0]} → Exit 64", r.returncode == 64 and "--sitzung" in r.stderr,
              f"{r.returncode}: {r.stdout}{r.stderr}")

    # Nr. 12: lesbar_extern-Ordner in anderer Schreibweise
    ext = t / "werkzeugkiste"
    (ext / "quelle").mkdir(parents=True)
    (ext / "quelle/a.md").write_text("a\n")
    pt = repo / "normen/projekt.toml"
    v, n = re.subn(r"^lesbar_extern = \[[^\]]*\]", f'lesbar_extern = ["{ext}"]', pt.read_text(), flags=re.M)
    check("Nr. 12: projekt.toml vorbereitet", n == 1)
    pt.write_text(v)
    gross = str(t / "WERKZEUGKISTE")
    if ohne_gross:
        for befehl, soll in [(f"touch {gross}/x", "nein"), (f"echo x > {gross}/quelle/a.md", "nein"),
                             (f"cd {gross} && touch x", "nein"), (f"cat {gross}/quelle/a.md", "ja")]:
            s, g = hook(repo, B(befehl))
            check(f"Nr. 12: {befehl.replace(str(t), '<t>')} → {soll}", s == soll, f"ist {s}: {g[:200]}")

    # Nr. 20: Forschungsdaten im Prompt an agy in anderer Schreibweise
    pt.write_text(pt.read_text().replace("forschungsdaten = []", 'forschungsdaten = ["daten/roh/**"]'))
    (repo / "daten/roh").mkdir(parents=True)
    (repo / "daten/roh/p1.csv").write_text("a\n")
    faelle = [('agy -p "Lies daten/roh/p1.csv" < /dev/null', "nein"),
              ('agy -p "Fasse README.md zusammen" < /dev/null', "ja")]
    if ohne_gross:
        faelle += [('agy -p "Lies Daten/Roh/p1.csv" < /dev/null', "nein"),
                   (f'agy -p "Lies {t}/PROJEKT/daten/roh/p1.csv" < /dev/null', "nein")]
    for befehl, soll in faelle:
        s, g = hook(repo, B(befehl))
        check(f"Nr. 20: {befehl.replace(str(t), '<t>')} → {soll}", s == soll, f"ist {s}: {g[:200]}")

    # cd "$D": bekannte Zuweisung aus einem eigenen Teilbefehl gilt als Basisordner; sonst unbekannt (fragen)
    schatten = t / "schatten"
    schatten.mkdir()
    (schatten / "json.py").write_text("import os\nos.remove('/tmp/gibt-es-nicht-v15b2')\n")
    leer = t / "leer"
    leer.mkdir()
    imp = "python3 -c 'import json'"
    for befehl, soll in [
        (f"D={repo}; cd \"$D\" && {imp}", "ja"),
        (f"D={leer}; cd \"$D\"; {imp}", "ja"),
        (f"D={schatten}; cd \"$D\" && {imp}", "fragen"),       # jetzt über die Schatten-Erkennung
        (f"D={repo} cd \"$D\"; {imp}", "fragen"),               # Präfix-Zuweisung: $D wird vorher eingesetzt
        (f"false && D={repo}; cd \"$D\"; {imp}", "fragen"),     # bedingte Zuweisung
        (f"(D={repo}); cd \"$D\"; {imp}", "fragen"),            # Zuweisung in der Subshell
        (f"D={repo} | true; cd \"$D\"; {imp}", "fragen"),       # Zuweisung in der Pipeline
        (f"cd \"$(mktemp -d)\" && {imp}", "fragen"),
        # Wert über eine zweite Variable aus einer bedingten Zuweisung (Advisor 22.11.)
        (f"cd {schatten}; false && X={repo}; D=$X; cd \"$D\"; {imp}", "fragen"),
        # Variable ändert sich ohne NAME=
        (f"cd {schatten}; D={repo}; unset D; cd \"$D\"; {imp}", "fragen"),
        (f"cd {schatten}; D={repo}; eval 'D={schatten}'; cd \"$D\"; {imp}", "fragen"),
        (f"cd {schatten}; D={repo}; . ./setzen.sh; cd \"$D\"; {imp}", "fragen"),
        (f"cd {schatten}; D={repo}; source ./setzen.sh; cd \"$D\"; {imp}", "fragen"),
        (f"cd {schatten}; D={repo}; printf -v D %s {schatten}; cd \"$D\"; {imp}", "fragen"),
        (f"cd {schatten}; D={repo}; read D < /dev/null; cd \"$D\"; {imp}", "fragen"),
        (f"cd {schatten}; cat <<EOF\nD={repo}\nEOF\ncd \"$D\"; {imp}", "fragen"),
        # ${NAME} im Wert schaltet die Lockerung nicht ab
        (f"T={t}; D=${{T}}/leer; cd \"$D\" && {imp}", "ja"),
    ]:
        s, g = hook(repo, B(befehl))
        check(f"cd $D: {befehl.replace(str(t), '<t>')} → {soll}", s == soll, f"ist {s}: {g[:200]}")
    s, g = hook(repo, B(f"D={schatten}; cd \"$D\" && {imp}"))
    check("cd $D: Schatten-Fall fragt wegen des Schatten-Moduls", "Schatten-Modul" in g, g[:200])
    # Gegenprobe an der echten Shell: wo die Shell nach den Fällen „fragen“ wirklich steht
    (schatten / "setzen.sh").write_text(f"D={schatten}\n")
    for befehl in (f"D={leer} cd \"$D\"; pwd", f"false && D={leer}; cd \"$D\"; pwd", f"(D={leer}); cd \"$D\"; pwd",
                   f"D={leer} | true; cd \"$D\"; pwd", f"false && X={leer}; D=$X; cd \"$D\"; pwd",
                   f"cd {schatten}; D={leer}; . ./setzen.sh; cd \"$D\"; pwd",
                   f"cd {schatten}; D={leer}; eval 'D={schatten}'; cd \"$D\"; pwd"):
        r = sh("bash", "-c", befehl, cwd=repo, env={k: v for k, v in os.environ.items() if k != "D"})
        check(f"Shell: {befehl.replace(str(t), '<t>')} bleibt nicht in leer", r.stdout.strip() != str(leer), r.stdout)
    r = sh("bash", "-c", f"D={leer}; cd \"$D\"; pwd", cwd=repo)
    check("Shell: D=…; cd \"$D\" wechselt", r.stdout.strip() == str(leer), r.stdout)

print(f"{OK} ok, {FAIL} Fehler")
sys.exit(1 if FAIL else 0)
