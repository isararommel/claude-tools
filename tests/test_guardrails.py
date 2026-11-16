#!/usr/bin/env python3
"""Tests für die Guardrail-Pakete aus Normen v7 (G2 ff., siehe docs/plaene/guardrails-v7-entwurf.md)."""
import json
import re
import shutil
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
               "git status --short", "git commit -m x --signoff",
               'git commit -q -m "v7: nice -n 10 erkannt\n\nZweiter Absatz (-n, --no-verify)."']
    for befehl in erlaubt:
        check(f"claude erlaubt: {befehl}", hook(repo, "claude", "claude", befehl) == "ja")
    data = {"tool_name": "Bash", "tool_input": {"command": "git commit --no-verify -m x"}, "cwd": str(repo)}
    aus = sh(sys.executable, "normen/normen.py", "hook", "--rolle", "claude", "--werkzeug", "claude", cwd=repo,
             eingabe=json.dumps(data)).stdout
    check("Meldung nennt den Grund", "pre-commit-Hook nicht umgehen" in aus, aus)

    # G3 (L3): Bash-Schreibziele gegen GESCHUETZT – Claude fragt, Teams gesperrt (wie bei Edit/Write)
    schreibt_geschuetzt = ["sed -i '' s/a/b/ .claude/settings.json", "echo x > normen/x.toml", "echo x >> CLAUDE.md",
                           "tee AGENTS.md < /tmp/a", "cp /tmp/a.json .claude/settings.json", "mv /tmp/x .githooks/pre-commit",
                           "cd normen && echo x > kurz.md", "printf x 2>/dev/null > .vibe/hooks.toml", "touch .normen-auftrag",
                           "rm -f normen/kurz.md", "ln -s /tmp/x .claude/agents", 'echo "a;b" > CLAUDE.md',
                           'echo "a|b" > AGENTS.md', "echo x &> normen/x.toml", "> normen/x.toml"]
    for befehl in schreibt_geschuetzt:
        check(f"G3 claude fragt: {befehl}", hook(repo, "claude", "claude", befehl) == "fragen")
        check(f"G3 vibe sperrt: {befehl}", hook(repo, "mistral-team", "vibe", befehl) == "nein")
    liest_geschuetzt = ["cat normen/kurz.md > /tmp/kurz.txt", "cp normen/normen.py /tmp/normen-kopie.py", "diff CLAUDE.md AGENTS.md",
                        'grep -rn hook .claude/ > "$TMPDIR/treffer.txt"', "ls -la .claude/", "python3 normen/normen.py sync",
                        "git diff -- normen/ 2>&1 | head", "echo x > notizen.txt"]
    for befehl in liest_geschuetzt:
        check(f"G3 claude ja: {befehl}", hook(repo, "claude", "claude", befehl) == "ja")

    # Betriebsbefehle des Orchestrators: müssen nach jedem Paket „ja“ bleiben (Hook ist fail-closed)
    for befehl in ['bash ~/Documents/Projekte/claude-tools/agenten-normen/einrichten.sh . --test "make test"',
                   "python3 normen/normen.py auftrag --rolle mistral-team --dateien a.py", "python3 normen/normen.py auftrag --ende",
                   "python3 normen/normen.py pruefen --diff", "python3 normen/normen.py merge 7", "python3 normen/normen.py selbsttest",
                   "make test", 'git commit -q -m "x"', "git push -q -u origin arbeit", "git add -A tests",
                   'make test 2>&1 | grep -E "ok,|FAIL"', "python3 normen/normen.py pruefen --diff | tail -2"]:
        check(f"Betrieb ja: {befehl}", hook(repo, "claude", "claude", befehl) == "ja")

    # G4-A (L1): Inline-Code – python3 -c / python3 - <<EOF per AST, bash|sh -c rekursiv, Präfixe, Heredoc-Rümpfe als Daten
    lauf = Path(t) / "code-mode-runs" / "g4"
    lauf.mkdir(parents=True)
    (lauf / "commit.py").write_text('import subprocess\nsubprocess.run(["git", "commit", "-m", "x"])\n')
    inline = [
        ("python3 -c 'import sys; print(sys.version)'", "ja"),
        ("python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'", "ja"),
        ('echo "Fertig. Prüfen: cd x && python3 normen/normen.py pruefen --diff"', "ja"),
        ("""python3 -c "import json;d=json.load(open('$RUN/out/export.json'));print(d['outcome'],d.get('steps'))\"""", "ja"),
        ("python3 - <<'PY'\nimport json\nprint(json.dumps({'a': 1}))\nPY", "ja"),
        ('sh -c "ls -la"', "ja"),
        ("bash -c 'git status --short'", "ja"),
        ("cat >> notizen.md <<'EOF'\ngit config core.hooksPath x\npython3 -c 'import sys; x'\nrm -rf /\nEOF", "ja"),
        ("cat > /tmp/normen-g4.txt <<EOF\ngit push --force\nEOF", "ja"),
        ("""python3 -c "import subprocess; subprocess.run(['git', 'push'])\"""", "nein"),
        ("""python3 -c "import os; os.system('ls')\"""", "nein"),
        ("python3 - <<'PY'\nimport subprocess\nsubprocess.run(['git', 'commit', '-m', 'x'])\nPY", "nein"),
        ("python3 - <<'PY'\nfrom pathlib import Path\nPath('CLAUDE.md').write_text('x')\nPY", "nein"),
        ("bash -c 'git commit --no-verify -m x'", "nein"),
        (f"FOO=1 python3 {lauf}/commit.py", "nein"),
        (f"time python3 {lauf}/commit.py", "nein"),
        (f"env A=1 python3 {lauf}/commit.py", "nein"),
        ("cat > CLAUDE.md <<'EOF'\nx\nEOF", "fragen"),
        ('python3 -c "import urllib.request"', "fragen"),
        ("bash -c 'rm -rf /tmp/normen-g4'", "fragen"),
        # Rückschritte: Heredoc mit Umleitung UND Kette ist kein reiner Datenrumpf; python3 ohne `-` liest den Heredoc als Code
        ("cat <<'EOF' 2>/dev/null | bash\ngit push --force\nEOF", "fragen"),
        ("cat > /tmp/normen-g4.sh <<'EOF' && bash /tmp/normen-g4.sh\ngit push --force\nEOF", "fragen"),
        ("cat <<'EOF' > /tmp/normen-g4.txt; bash\ngit push --force\nEOF", "fragen"),
        ("python3 <<'PY'\nimport subprocess\nsubprocess.run(['git', 'push'])\nPY", "nein"),
        ("python3 /dev/stdin <<'PY'\nimport subprocess\nsubprocess.run(['git', 'push'])\nPY", "nein"),
        # Rückschritte (Advisor): Schein-Heredoc, Nicht-Daten-Befehle, zweiter Python-Heredoc, Optionsgruppen
        ('echo "<<X" > /tmp/normen-g4.txt\ngit push --force', "fragen"),
        ("echo $((1<<2)) > /tmp/normen-g4.txt\ngit push --force", "fragen"),
        ("timeout 5 bash <<'EOF' > /tmp/normen-g4.log\ngit push --force\nEOF", "fragen"),
        ("psql db <<'EOF' > /tmp/normen-g4.txt\nDROP TABLE t;\nEOF", "fragen"),
        ("python3 - <<'PY'\nprint(1)\nPY\npython3 - <<'PY'\nimport subprocess\nsubprocess.run(['git', 'push'])\nPY", "nein"),
        ("""bash -lc "python3 -c 'import os; os.system(1)'\"""", "nein"),
        ("""bash -e -c "python3 -c 'import os; os.system(1)'\"""", "nein"),
        ("""python3 -Bc "import os; os.system('ls')\"""", "nein"),
        ("echo 'print(1)' | python3 -", "fragen"),
        ("tee notizen.md <<'EOF'\ngit push --force\nEOF", "ja"),
    ]
    for befehl, soll in inline:
        check(f"G4-A {soll}: {befehl[:60]!r}", hook(repo, "claude", "claude", befehl) == soll)
    check("G4-A vibe: os.system nein", hook(repo, "mistral-team", "vibe", """python3 -c "import os; os.system('ls')\"""") == "nein")

    # G4-B (L1): Skriptdateien außerhalb des Projekts (und außerhalb lesbar_extern) – Shell-Inhalt als ein Befehl durch
    # bewerten, Python ohne .py per AST, node/perl/ruby fragen, nicht vorhanden fragen; Projektskripte wie bisher
    def skript(name, inhalt, ausfuehrbar=False):
        p = lauf / name
        p.write_text(inhalt)
        if ausfuehrbar:
            p.chmod(0o755)
        return p

    sauber = skript("sauber.sh", "#!/bin/bash\nset -uo pipefail\n# git push --force steht nur im Kommentar\ngit status --short\n"
                    "if [ -d x ]; then echo ja; fi\nfor f in *.md; do wc -l \"$f\"; done\n"
                    "cat > notiz.txt <<'EOF'\ngit push --force\nEOF\n", True)
    hart = skript("hart.sh", "#!/bin/bash\ngit push --force origin x\n", True)
    ohne_shebang = skript("ohne-shebang", "git push --force origin x\n", True)
    umgeht = skript("umgeht.sh", "git status\ngit commit --no-verify -m x\n")
    tief = skript("tief.sh", f"echo start\nbash {hart}\n")
    py_ohne_endung = skript("auswerten", "#!/usr/bin/env python3\nimport subprocess\nsubprocess.run(['git', 'commit', '-m', 'x'])\n",
                            True)
    js = skript("x.js", "console.log(1)\n")
    pl = skript("x.pl", "print 1;\n")
    (repo / "werkzeug.sh").write_text("git push --force origin x\n")
    dateien = [
        (f"bash {sauber}", "ja"), (f"sh {sauber}", "ja"), (f"{sauber}", "ja"), (f"source {sauber}", "ja"),
        (f"cd {lauf} && ./sauber.sh", "ja"),
        (f"bash {hart}", "fragen"), (f"zsh {hart}", "fragen"), (f"FOO=1 bash -x {hart}", "fragen"), (f". {hart}", "fragen"),
        (f"{hart}", "fragen"), (f"cd {lauf} && ./hart.sh", "fragen"), (f"{ohne_shebang}", "fragen"),
        (f"bash {tief}", "fragen"), (f"bash {umgeht}", "nein"),
        (f"python3 {py_ohne_endung}", "nein"), (f"{py_ohne_endung}", "nein"),
        (f"pushd {lauf} && ./hart.sh", "fragen"), (f"pushd {lauf} && bash hart.sh", "fragen"),
        (f"{{ cd {lauf}; ./hart.sh; }}", "fragen"), (f"cd {lauf} && bash tief.sh", "fragen"),
        # Gemini-Review G4: Code über stdin, Präfix-Optionen, dynamischer Zugriff
        ("cat <<'EOF' | python3\nimport subprocess\nsubprocess.run(['git', 'push'])\nEOF", "fragen"),
        (f"python3 < {lauf}/commit.py", "fragen"), (f"bash < {hart}", "fragen"), (f"cat {hart} | bash", "fragen"),
        (f"cat {hart} | sh -s", "fragen"), (f"source /dev/stdin < {hart}", "fragen"), (f"cat {js} | node", "fragen"),
        ("node -e 'console.log(1)'", "fragen"), (f"nice -n 10 python3 {lauf}/commit.py", "nein"),
        (f"time -p python3 {lauf}/commit.py", "nein"), (f"timeout 60 python3 {lauf}/commit.py", "nein"),
        ("""python3 -c "import subprocess; getattr(subprocess, 'run')(['git', 'push'])\"""", "nein"),
        ("""python3 -c "import subprocess; r = subprocess.run; r(['git', 'push'])\"""", "nein"),
        ("""python3 -c "import os; list(map(os.system, ['ls']))\"""", "nein"),
        ("""python3 -c "import json; print(getattr(json, 'dumps')({}))\"""", "ja"),
        ("git log --oneline | head -3", "ja"), ("echo x | python3 -c 'import sys; print(sys.stdin.read())'", "ja"),
        (f"python3 {lauf}/../g4/sauber.py < /dev/null", "fragen"),  # nicht vorhanden
        (f"/usr/bin/env bash {hart}", "fragen"), (f"/usr/bin/env python3 {py_ohne_endung}", "nein"),
        (f"node {js}", "fragen"), (f"perl {pl}", "fragen"), ("bash /tmp/normen-g4b-gibt-es-nicht.sh", "fragen"),
        (f"printf 'ls\\n' > {sauber} && bash {sauber}", "fragen"),  # Inhalt wird im selben Befehl ersetzt
        ("bash werkzeug.sh", "ja"),  # Projektskript: wie bisher
        ("/usr/bin/git status --short", "ja"), ("/bin/ls -la", "ja"), (f"{sys.executable} -c 'print(1)'", "ja"),
    ]
    for befehl, soll in dateien:
        check(f"G4-B {soll}: {befehl[-70:]!r}", hook(repo, "claude", "claude", befehl) == soll)
    for befehl in (f"bash {hart}", f"bash {umgeht}", f"python3 {py_ohne_endung}", f"node {js}", f"{hart}"):
        check(f"G4-B vibe nein: {befehl[-60:]!r}", hook(repo, "mistral-team", "vibe", befehl) == "nein")
    (repo / "werkzeug.sh").unlink()

    # Entscheidung 10: Fehlalarm bei Arbeitsordner in [pfade].lesbar_extern
    extern = Path(t) / "werkzeuge"
    (extern / "quelle").mkdir(parents=True)
    pt = repo / "normen/projekt.toml"
    pt.write_text(pt.read_text().replace('lesbar_extern = ["~/Documents/Projekte/claude-tools"]', f'lesbar_extern = ["{extern}"]'))

    def hook_in(cwd, befehl):
        data = {"tool_name": "Bash", "tool_input": {"command": befehl}, "cwd": str(cwd)}
        r = sh(sys.executable, str(repo / "normen/normen.py"), "hook", "--rolle", "claude", "--werkzeug", "claude", cwd=repo,
               eingabe=json.dumps(data))
        if not r.stdout.strip():
            return "ja"
        return {"deny": "nein", "ask": "fragen"}[json.loads(r.stdout)["hookSpecificOutput"]["permissionDecision"]]

    fehlalarm = ['grep -rn "=>" quelle/', "grep -c '>' quelle/a.md", 'git status --short > "$TMPDIR/status.txt"',
                 'RUN=/tmp/normen-lauf-x; git log --oneline -3 > "$RUN/log.txt"', "git diff > /tmp/normen-diff.txt",
                 "awk '$1 > 3' quelle/a.txt"]
    for befehl in fehlalarm:
        check(f"Fehlalarm behoben: {befehl}", hook_in(extern, befehl) == "ja")
    weiter_gesperrt = ["echo x > quelle/a.md", "git status > status.txt", 'echo x > "$GIBT_ES_NICHT_V7/a.md"',
                       f"echo x > {extern}/quelle/a.md", "sed -i '' s/a/b/ quelle/a.md", "cd quelle && echo x > a.md",
                       'echo "a|b" > quelle/a.md', 'echo "a;b" > quelle/a.md', "> quelle/a.md"]
    for befehl in weiter_gesperrt:
        check(f"lesbar_extern weiter gesperrt: {befehl}", hook_in(extern, befehl) == "nein")
    check("lesbar_extern aus dem Projekt: Ziel extern gesperrt", hook_in(repo, f"echo x > {extern}/quelle/a.md") == "nein")

    # G5 (L5): Datenschutz vor vibe/agy – Prompt-Datei (und *.md daneben) bzw. -p-Text vor dem Start prüfen
    pt.write_text(re.sub(r"gesperrt = \[\s*\]", 'gesperrt = ["daten/geheim/"]', pt.read_text())
                  .replace("forschungsdaten = []", 'forschungsdaten = ["daten/roh/**", "PROBAND-"]'))
    check("G5 Vorlage hat forschungsdaten", 'forschungsdaten = ["daten/roh/**"' in pt.read_text())
    block = sh(sys.executable, "normen/normen.py", "auftrag", "--rolle", "gemini-analyst", cwd=repo).stdout
    check("G5 Auftragsblock nennt den Sperrpfad", "daten/geheim/" in block, block[-300:])
    runs = Path(t) / "agy-runs"

    def prompt(name, text, neben=None):
        d = runs / name
        d.mkdir(parents=True)
        (d / "prompt.md").write_text(text)
        if neben:
            (d / "spezifikation.md").write_text(neben)
        return d

    def agy(d, datei="prompt.md"):
        return (f'RUN={d}; ALLOW=x; agy --model gemini-3.8-flash-high --disable-slash-commands --print-timeout 540s '
                f'--settings "$ALLOW" -p "$(cat "$RUN/{datei}")" < /dev/null > "$RUN/antwort.txt" 2>&1')

    def vibe(d, datei="prompt.md"):
        return (f'RUN="{d}"; cd {repo} && vibe --trust --smart-approve --time-limit 540 --max-turns 60 '
                f'--output-dir "$RUN/out" --prompt-file "$RUN/{datei}" < /dev/null > "$RUN/antwort.txt" 2>&1')

    schluessel = "-----BEGIN " + "OPENSSH PRIVATE KEY-----"
    echt = prompt("echt", block + "\n## Ziel\nAnalysiere src/app.py und docs/plan.md. Ändere keine Dateien.\n")
    sperr = prompt("sperr", block + "\nLies auch daten/geheim/liste.csv.\n")
    neben = prompt("neben", block + "\nSpezifikation: spezifikation.md\n", neben="Vergleiche mit daten/geheim/x.csv.\n")
    geheim_inhalt = prompt("geheim-inhalt", f"Nutze diesen Schlüssel:\n{schluessel}\nabc\n")
    geheim_pfad = prompt("geheim-pfad", "Prüfe, ob config/.env im Deploy-Skript gelesen wird.\n")
    marker = prompt("marker", "Werte die Antworten von PROBAND-017 aus.\n")
    glob_rel = prompt("glob-rel", "Lies daten/roh/p1.csv.\n")
    glob_abs = prompt("glob-abs", f"Lies {repo}/daten/roh/p1.csv.\n")
    glob_ordner = prompt("glob-ordner", "Fasse den Ordner daten/roh/ zusammen.\n")
    vibe_bin = shutil.which("vibe") or "/usr/local/bin/vibe"
    g5 = [
        (agy(echt), "ja"), (vibe(echt), "ja"),
        (agy(sperr), "nein"), (vibe(sperr), "nein"), (vibe(neben), "nein"), (agy(neben), "nein"),
        (agy(geheim_inhalt), "nein"), (vibe(geheim_inhalt), "nein"),
        (agy(geheim_pfad), "nein"), (vibe(geheim_pfad), "ja"),  # Vibe-Hook sperrt das Lesen selbst; agy hat keine Hooks
        (agy(marker), "nein"), (vibe(marker), "fragen"),
        (agy(glob_rel), "nein"), (agy(glob_abs), "nein"), (agy(glob_ordner), "nein"), (vibe(glob_rel), "fragen"),
        ('vibe --trust --prompt-file "$GIBT_ES_NICHT_G5/prompt.md" < /dev/null', "nein"),
        (vibe(echt, "fehlt.md"), "nein"),
        (f'RUN={echt}; printf x > "$RUN/prompt.md" && vibe --trust --prompt-file "$RUN/prompt.md" < /dev/null', "nein"),
        ('vibe --trust -p "Lies daten/geheim/x.csv" < /dev/null', "nein"), ('agy -p "Fasse README.md zusammen" < /dev/null', "ja"),
        (f"vibe --trust --prompt-file={sperr}/prompt.md < /dev/null", "nein"),
        (f"env vibe --trust --prompt-file {sperr}/prompt.md < /dev/null", "nein"),
        (f"{vibe_bin} --trust --prompt-file {sperr}/prompt.md < /dev/null", "nein"),
        (f"bash -c 'vibe --trust --prompt-file {sperr}/prompt.md < /dev/null'", "nein"),
        (f"vibe -c --trust --prompt-file {echt}/prompt.md < /dev/null", "ja"),
        (f'RUN={sperr}; vibe --trust -p "$(cat "$RUN/prompt.md")" < /dev/null', "nein"),
        ('vibe --trust -p "$PROMPT_GIBT_ES_NICHT" < /dev/null', "nein"),
        ("vibe --trust -p \"Fasse `cat daten/x` zusammen\" < /dev/null", "nein"),
        ("vibe --version", "ja"), ("agy --help", "ja"), ("vibe --trust < /dev/null", "nein"),
    ]
    for befehl, soll in g5:
        check(f"G5 {soll}: {befehl[-90:]!r}", hook(repo, "claude", "claude", befehl) == soll)

print(f"{OK} ok, {FAIL} Fehler")
sys.exit(1 if FAIL else 0)
