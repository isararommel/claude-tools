#!/usr/bin/env python3
"""Tests für Normen v6: nur_rollen, Rollenkette, Rollen fable/skript, `normen.py skript --pruefen` (S06, AST-Prüfung)
und der Hook für `python3 <skript>.py` außerhalb des Projekts. Testskripte entstehen im Temp-Ordner (nicht unter tests/)."""
import json
import re
import subprocess
import sys
import os
import tempfile
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("NORMEN_PROTOKOLL", os.path.join(tempfile.gettempdir(), "normen-test-protokoll.jsonl"))  # v18: Hooks der Tests nie ins echte Protokoll
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


STUFE = {0: "ja", 1: "fragen", 2: "nein"}


def pruefe_skript(repo, pfad):
    """(Stufe aus dem Exit-Code, erste Ausgabezeile, ganze Ausgabe)."""
    r = sh(sys.executable, "normen/normen.py", "skript", "--pruefen", str(pfad), cwd=repo)
    erste = r.stdout.splitlines()[0].strip() if r.stdout.strip() else ""
    return STUFE.get(r.returncode, f"exit {r.returncode}"), erste, r.stdout + r.stderr


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

    # 1. nur_rollen, Rollenkette, Rollen fable/skript
    kurz = (repo / "normen/kurz.md").read_text()
    agents = (repo / "AGENTS.md").read_text()
    mt = sh(sys.executable, "normen/normen.py", "auftrag", "--rolle", "mistral-team", cwd=repo).stdout
    ga = sh(sys.executable, "normen/normen.py", "auftrag", "--rolle", "gemini-analyst", cwd=repo).stdout
    cl = sh(sys.executable, "normen/normen.py", "auftrag", "--rolle", "claude", cwd=repo).stdout
    for nid in ("S06-CODE-MODE", "S07-SUPERVISOR"):
        check(f"{nid} in kurz.md", nid in kurz)
        check(f"{nid} nicht im mistral-Auftrag", nid not in mt and "S05-SELBSTSTAENDIG" in mt, mt[-200:])
        check(f"{nid} nicht im gemini-Auftrag", nid not in ga)
        check(f"{nid} im claude-Auftrag", nid in cl)
        check(f"{nid} nicht im AGENTS-Block", nid not in agents and "N01-KEINE-ZERSTOERUNG" in agents)
    zeilen = [z for z in kurz.splitlines() if "S06-CODE-MODE" in z or "S07-SUPERVISOR" in z]
    check("kurz.md: Kennzeichnung Hauptsitzung", len(zeilen) == 2 and all("_(nur Hauptsitzung/Orchestrator)_" in z for z in zeilen),
          str(zeilen)[:300])
    check("kurz.md: S05 ohne Kennzeichnung", "_(nur Hauptsitzung" not in next(z for z in kurz.splitlines() if "S05-" in z))
    rollen = kurz.split("## Rollen", 1)[1].split("## Durchsetzung", 1)[0]
    check("kurz.md: Rollenkette", "Fable (Advisor) prüft → Claude/Opus entscheidet" in rollen and "{inhaberin}" not in rollen,
          rollen[:300])
    check("kurz.md: Rolle fable in der Tabelle", "| fable |" in rollen)
    check("kurz.md: Regelsatz skript nicht in der Tabelle", "| skript |" not in rollen)
    for rolle in ("fable", "skript"):
        r = sh(sys.executable, "normen/normen.py", "auftrag", "--rolle", rolle, cwd=repo)
        check(f"auftrag --rolle {rolle}: Exit 64", r.returncode == 64 and "bekommt keine Aufträge" in r.stderr + r.stdout,
              r.stdout + r.stderr)
    check("auftrag fable legt nichts an", not (repo / ".normen-auftrag").exists())
    check("pruefen nach Einrichten ohne Fehler", "0 Fehler" in sh(sys.executable, "normen/normen.py", "pruefen", cwd=repo).stdout)

    # 2. skript --pruefen: Abnahmefälle aus dem Plan (nachgebaut, neutrale Namen)
    lauf = Path(t) / "code-mode-runs" / "20261116-1200-test"
    lauf.mkdir(parents=True)

    def skript(name, text):
        p = lauf / name
        p.write_text(textwrap.dedent(text).lstrip(), encoding="utf-8")
        return p

    repos_py = skript("repos.py", """
        import json
        import subprocess

        REPOS = ["beispiel/eins", "beispiel/zwei"]
        for repo in REPOS:
            r = subprocess.run(["gh", "api", f"repos/{repo}"], capture_output=True, text=True, check=True)
            d = json.loads(r.stdout)
            print(repo, (d.get("license") or {}).get("spdx_id"), d.get("pushed_at"), d.get("archived"))
        """)
    claims_py = skript("claims.py", """
        import base64
        import json
        import re
        import subprocess

        ZIELE = [("beispiel/eins", "README.md"), ("beispiel/zwei", "docs/LIES-MICH.md")]
        for repo, pfad in ZIELE:
            r = subprocess.run(["gh", "api", f"repos/{repo}/contents/{pfad}"], capture_output=True, text=True, check=True)
            text = base64.b64decode(json.loads(r.stdout)["content"]).decode("utf-8", "replace")
            print(repo, len(re.findall(r"(?i)sandbox|hook", text)))
        """)
    claims2_py = skript("claims2.py", claims_py.read_text() + textwrap.dedent("""
        for repo, pfad in ZIELE:
            roh = subprocess.run(["curl", "-s", f"https://raw.githubusercontent.com/{repo}/main/{pfad}"],
                                 capture_output=True, text=True)
            print(repo, len(roh.stdout))
        """))
    ablauf = (ROOT / "multi-ki" / "multi-ki-ablauf.md").read_text(encoding="utf-8")
    m = re.search(r"## 9\. Code Mode.*?```python\n(.*?)```", ablauf, re.S)
    check("Beispielskript in multi-ki-ablauf.md §9", m is not None)
    beispiel_py = skript("auswerten.py", m.group(1) if m else "")
    for p, soll in [(repos_py, "ja"), (claims_py, "ja"), (claims2_py, "fragen"), (beispiel_py, "ja")]:
        stufe, erste, aus = pruefe_skript(repo, p)
        check(f"skript {p.name} → {soll}", stufe == soll and erste == soll, aus)

    # 3. skript --pruefen: weitere Fälle
    faelle = [
        ("commit.py", 'import subprocess\nsubprocess.run(["git", "commit", "-m", "x"])\n', "nein"),
        ("push.py", 'import subprocess\nsubprocess.run(["git", "push"])\n', "nein"),
        ("add.py", 'import subprocess\nsubprocess.run(["git", "add", "-A"])\n', "nein"),
        ("argv.py", 'import subprocess, sys\nsubprocess.run([sys.argv[1], "status"])\n', "fragen"),
        ("liste.py", 'import subprocess, sys\nbefehl = sys.argv[1:]\nsubprocess.run(befehl)\n', "fragen"),
        ("stern.py", 'import subprocess, sys\nsubprocess.run(["git", *sys.argv[1:]])\n', "fragen"),
        ("option.py", 'import subprocess, sys\nx = sys.argv[1]\nsubprocess.run(["gh", "api", f"{x}"])\n', "fragen"),
        ("shell.py", 'import subprocess\nsubprocess.run("git status", shell=True)\n', "nein"),  # normen-ausnahme: N09-SICHERE-MUSTER – Testfall der Skriptprüfung
        ("system.py", 'import os\nos.system("ls")\n', "nein"),
        ("eval.py", 'import sys\neval(sys.argv[1])\n', "nein"),
        ("netz.py", 'import urllib.request\nprint(urllib.request.urlopen("https://example.org").status)\n', "fragen"),
        ("fremd.py", 'import shutil\nprint(shutil.which("git"))\n', "fragen"),
        ("schreibt_hier.py", 'from pathlib import Path\nHIER = Path(__file__).resolve().parent\n'
                             '(HIER / "ergebnis.txt").write_text("x")\nopen(HIER / "b.txt", "w").write("y")\n', "ja"),
        ("schreibt_projekt.py", f'from pathlib import Path\nPath("{repo}/app.py").write_text("x")\n', "nein"),
        ("schreibt_relativ.py", 'open("ausgabe.txt", "w").write("x")\n', "nein"),
        ("loescht.py", 'from pathlib import Path\nHIER = Path(__file__).resolve().parent\n(HIER / "a.txt").unlink()\n', "nein"),
        ("gh_post.py", 'import subprocess\nsubprocess.run(["gh", "api", "-X", "POST", "repos/a/b/issues"])\n', "nein"),
        ("gh_feld.py", 'import subprocess\nsubprocess.run(["gh", "api", "repos/a/b/issues", "-f", "title=x"])\n', "nein"),
        ("gh_pr.py", 'import subprocess\nsubprocess.run(["gh", "pr", "create", "--fill"])\n', "nein"),
        ("vibe.py", 'import subprocess\nsubprocess.run(["vibe", "--prompt-file", "p.md"])\n', "nein"),
        ("agy.py", 'import subprocess\nsubprocess.run(["agy", "-p", "x"])\n', "nein"),
        ("merge.py", 'import subprocess, sys\nsubprocess.run([sys.executable, "normen/normen.py", "merge", "3"])\n', "nein"),
        ("auftrag.py", 'import subprocess\nsubprocess.run(["python3", "normen/normen.py", "auftrag", "--ende"])\n', "nein"),
        ("pruefen.py", 'import subprocess, sys\nr = subprocess.run([sys.executable, "normen/normen.py", "pruefen", "--diff"])\n'
                       'print(r.returncode)\n', "ja"),
        ("test.py", 'import subprocess\nprint(subprocess.run(["make", "test"]).returncode)\n', "ja"),
        ("git_c.py", 'import subprocess\nfrom pathlib import Path\nZ = Path("/tmp")\n'
                     'subprocess.run(["git", "-C", str(Z), "log", "--oneline", "-3"])\n', "ja"),
        ("branch_d.py", 'import subprocess\nsubprocess.run(["git", "branch", "-D", "alt"])\n', "nein"),
        ("branch_anlegen.py", 'import subprocess\nsubprocess.run(["git", "branch", "zweig"])\n', "fragen"),
        ("branch_liste.py", 'import subprocess\nsubprocess.run(["git", "branch", "--show-current"])\n', "ja"),
        ("rm.py", 'import subprocess\nsubprocess.run(["rm", "-rf", "build"])\n', "nein"),
        ("unbekannt.py", 'import subprocess\nsubprocess.run(["ls", "-la"])\n', "fragen"),
        ("geheimnis.py", 'print(open(".env").read())\n', "nein"),
        ("kaputt.py", 'def f(:\n', "nein"),
        ("diff_geheim.py", 'import subprocess\nsubprocess.run(["git", "diff", "--", "daten/.env"])\n', "nein"),
        ("konstante.py", 'import subprocess\nBASIS = "origin/main"\nsubprocess.run(["git", "diff", BASIS])\n', "ja"),
        ("konstante_option.py", 'import subprocess\nOPT = "--output=/tmp/x"\nsubprocess.run(["git", "diff", OPT])\n', "fragen"),
    ]
    for name, text, soll in faelle:
        stufe, erste, aus = pruefe_skript(repo, skript(name, text))
        check(f"skript {name} → {soll}", stufe == soll and erste == soll, aus)
    stufe, _, aus = pruefe_skript(repo, lauf / "gibtsnicht.py")
    check("skript fehlt → nein", stufe == "nein", aus)
    _, _, aus = pruefe_skript(repo, lauf / "commit.py")
    check("skript: Grund genannt", "commit" in aus and "S06" in aus, aus)

    # 4. Hook: python3 <skript>.py außerhalb des Projekts wird geprüft
    check("hook: repos.py ja", hook(repo, "claude", "claude", f"python3 {repos_py}") == "ja")
    check("hook: -I und Argumente", hook(repo, "claude", "claude", f'python3 -I "{beispiel_py}" /tmp/lauf') == "ja")
    check("hook: claims2.py fragt", hook(repo, "claude", "claude", f"python3 {claims2_py}") == "fragen")
    check("hook: commit-Skript nein", hook(repo, "claude", "claude", f"python3 {lauf / 'commit.py'}") == "nein")
    check("hook: in Kette", hook(repo, "claude", "claude", f"cd {repo} && python3 {lauf / 'commit.py'} | tail -3") == "nein")
    check("hook: Variable unaufgelöst fragt",
          hook(repo, "claude", "claude", "python3 $GIBT_ES_NICHT_V6/auswerten.py") == "fragen")
    check("hook: Zitat mit | nicht ja", hook(repo, "claude", "claude", f'python3 {lauf / "commit.py"} "a|b"') != "ja")
    check("hook: cd + relativer Pfad nicht ja", hook(repo, "claude", "claude", f"cd {lauf} && python3 commit.py") != "ja")
    check("hook: Projektskript wie bisher", hook(repo, "claude", "claude", "python3 normen/normen.py pruefen --diff") == "ja")
    check("hook: python3 -c unverändert", hook(repo, "claude", "claude", 'python3 -c "print(1)"') == "ja")
    check("hook: vibe-Rolle, fragen wird nein", hook(repo, "mistral-team", "vibe", f"python3 {claims2_py}") == "nein")

# 5. Agent-Definitionen, Vorlagen
for a in ("mistral-team", "gemini-analyst", "Explore"):
    text = (ROOT / "multi-ki/benutzer/agents" / f"{a}.md").read_text(encoding="utf-8")
    check(f"{a}.md: Advisor nie aufrufen", "**Den Advisor nie aufrufen.**" in text)
check("PLAN-Vorlage vorhanden", (ROOT / "multi-ki/projekt/PLAN.md").exists())
check("CLAUDE-Abschnitt: PLAN.md lesen", "Zu Beginn jeder Sitzung `PLAN.md` lesen." in
      (ROOT / "multi-ki/projekt/CLAUDE-abschnitt.md").read_text(encoding="utf-8"))
with tempfile.TemporaryDirectory() as t:
    ziel = Path(t) / "p"
    ziel.mkdir()
    sh("git", "init", "-q", cwd=ziel)
    r = sh("bash", str(ROOT / "multi-ki/einrichten.sh"), str(ziel), "--test", "make test")
    check("multi-ki/einrichten.sh legt PLAN.md an", r.returncode == 0 and (ziel / "PLAN.md").exists(), r.stdout + r.stderr)
    (ziel / "PLAN.md").write_text("eigen\n")
    r = sh("bash", str(ROOT / "multi-ki/einrichten.sh"), str(ziel), "--test", "make test")
    check("PLAN.md wird nie überschrieben", r.returncode == 0 and (ziel / "PLAN.md").read_text() == "eigen\n", r.stdout)

print(f"{OK} ok, {FAIL} Fehler")
sys.exit(1 if FAIL else 0)
