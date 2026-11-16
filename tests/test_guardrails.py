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

print(f"{OK} ok, {FAIL} Fehler")
sys.exit(1 if FAIL else 0)
