#!/usr/bin/env python3
"""Tests für agenten-normen: Einrichten in ein Wegwerf-Repository, dann Hook-Entscheidungen, Prüfung, Auftrag, Sync."""
import json
import os
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


def hook(repo, rolle, werkzeug, data):
    data.setdefault("cwd", str(repo))
    r = sh(sys.executable, "normen/normen.py", "hook", "--rolle", rolle, "--werkzeug", werkzeug,
           cwd=repo, eingabe=json.dumps(data))
    if werkzeug == "claude":
        if not r.stdout.strip():
            return "ja"
        return {"deny": "nein", "ask": "fragen"}[json.loads(r.stdout)["hookSpecificOutput"]["permissionDecision"]]
    return "nein" if r.stdout.strip() and json.loads(r.stdout.splitlines()[0])["decision"] == "deny" else "ja"


with tempfile.TemporaryDirectory() as t:
    repo = Path(t) / "projekt"
    (repo / "tests").mkdir(parents=True)
    (repo / "daten").mkdir()
    sh("git", "init", "-q", cwd=repo)
    (repo / "CLAUDE.md").write_text("# Testprojekt\n\nText\n")
    (repo / "AGENTS.md").write_text("# Regeln\n- alt\n")
    (repo / "tests" / "test_a.py").write_text("def test_a():\n    assert 1 + 1 == 2\n")
    (repo / "app.py").write_text("def f():\n    return 1\n")
    (repo / ".env").write_text("X=1\n")
    r = sh("bash", str(VORLAGE / "einrichten.sh"), str(repo), "--test", "python3 -m pytest -q", "--sperre", "daten/")
    check("einrichten läuft", r.returncode == 0, r.stdout + r.stderr)
    for f in ["normen/normen.toml", "normen/rollen.toml", "normen/normen.py", "normen/projekt.toml", "normen/kurz.md",
              ".claude/settings.json", ".vibe/hooks.toml", ".githooks/pre-commit"]:
        check(f"angelegt {f}", (repo / f).exists())
    check("CLAUDE.md importiert", "@normen/kurz.md" in (repo / "CLAUDE.md").read_text())
    agents = (repo / "AGENTS.md").read_text()
    check("AGENTS.md Block + alter Inhalt", "normen:anfang" in agents and "- alt" in agents)
    check("projekt.toml gefüllt", '"daten/"' in (repo / "normen/projekt.toml").read_text())
    check("hooksPath", sh("git", "config", "core.hooksPath", cwd=repo).stdout.strip() == ".githooks")
    r2 = sh("bash", str(VORLAGE / "einrichten.sh"), str(repo), "--test", "x")
    check("einrichten idempotent", r2.returncode == 0 and "neu " not in r2.stdout and "ergänzt      .claude" not in r2.stdout, r2.stdout)
    sh("git", "add", "-A", cwd=repo)
    sh("git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "start", "--no-verify", cwd=repo)

    sh("git", "branch", "-M", "main", cwd=repo)
    B = lambda c: {"tool_name": "Bash", "tool_input": {"command": c}}
    W = lambda p: {"tool_name": "Write", "tool_input": {"file_path": str(repo / p) if not p.startswith("/") else p}}
    # Claude
    check("claude commit auf main fragt", hook(repo, "claude", "claude", B("git commit -m x")) == "fragen")
    sh("git", "checkout", "-q", "-b", "arbeit", cwd=repo)
    check("claude ls", hook(repo, "claude", "claude", B("ls -la")) == "ja")
    # Löschen im Projekt (Rolle claude, loeschen_wiederherstellbar): getrackt + unverändert → ja; sonst erst committen
    (repo / "neu").mkdir()
    (repo / "neu" / "x.py").write_text("x = 1\n")
    check("claude rm untracked: erst committen", hook(repo, "claude", "claude", B("rm -rf neu")) == "nein")
    check("claude /bin/rm außerhalb fragt", hook(repo, "claude", "claude", B("/bin/rm -r /etc/x")) == "fragen")
    check("claude git rm getrackt ja", hook(repo, "claude", "claude", B("git rm -r app.py")) == "ja")
    check("claude rm Projekt selbst fragt", hook(repo, "claude", "claude", B(f"rm -rf {repo}")) == "fragen")
    check("claude rm . fragt", hook(repo, "claude", "claude", B("rm -rf .")) == "fragen")
    check("claude rm ~ fragt", hook(repo, "claude", "claude", B("rm -rf ~/x")) == "fragen")
    check("claude rm .git fragt", hook(repo, "claude", "claude", B("rm -rf .git/hooks")) == "fragen")
    (repo / "app.py").write_text("def f():\n    return 3\n")
    check("claude rm geändert: erst committen", hook(repo, "claude", "claude", B("rm -f app.py")) == "nein")
    sh("git", "checkout", "-q", "--", "app.py", cwd=repo)
    check("claude push branch ja", hook(repo, "claude", "claude", B("git push -u origin arbeit")) == "ja")
    check("claude push main fragt", hook(repo, "claude", "claude", B("git -C . push origin main")) == "fragen")
    check("claude push HEAD:main fragt", hook(repo, "claude", "claude", B("git push origin HEAD:main")) == "fragen")
    check("claude pr merge fragt", hook(repo, "claude", "claude", B("gh pr merge 3")) == "fragen")
    check("claude force-push fragt", hook(repo, "claude", "claude", B("git push --force origin arbeit")) == "fragen")
    check("claude commit ja", hook(repo, "claude", "claude", B("git commit -m x")) == "ja")
    check("claude pip fragt", hook(repo, "claude", "claude", B("pip install requests")) == "fragen")
    # Ausnahmen v3: Wegwerf-Pfade ([pfade].loeschbar) und Installation aus vorhandenen Manifesten
    check("claude rm .venv ja", hook(repo, "claude", "claude", B("rm -rf .venv && python3 -m venv .venv")) == "ja")
    check("claude rm build/x ja", hook(repo, "claude", "claude", B('rm -rf "build/x" __pycache__')) == "ja")
    check("claude rm .venv + untracked: committen", hook(repo, "claude", "claude", B("rm -rf .venv; rm -rf neu")) == "nein")
    check("claude rm .venv + getrackt ja", hook(repo, "claude", "claude", B("rm -rf .venv app.py")) == "ja")
    check("claude rm .venv + außerhalb fragt", hook(repo, "claude", "claude", B("rm -rf .venv /etc/x")) == "fragen")
    check("claude rm .venv/.. fragt", hook(repo, "claude", "claude", B("rm -rf .venv/..")) == "fragen")
    check("claude rm Glob fragt", hook(repo, "claude", "claude", B("rm -rf build/*")) == "fragen")
    check("claude rm Variable fragt", hook(repo, "claude", "claude", B('rm -rf "$UNBEKANNT_X/y"')) == "fragen")
    check("claude rm Projektdatei unter TMPDIR: committen", hook(repo, "claude", "claude", B(f"rm -rf {repo}/neu")) == "nein")
    check("claude rm TMPDIR-Inhalt ja", hook(repo, "claude", "claude", B('rm -rf "${TMPDIR:?}/agy-runs/lauf1"')) == "ja")
    check("claude rm TMPDIR selbst fragt", hook(repo, "claude", "claude", B('rm -rf "$TMPDIR"')) == "fragen")
    check("claude sudo rm .venv fragt", hook(repo, "claude", "claude", B("sudo rm -rf .venv")) == "fragen")
    check("claude git reset bleibt fragen", hook(repo, "claude", "claude", B("rm -rf .venv && git reset --hard")) == "fragen")
    check("claude pip -r ja", hook(repo, "claude", "claude", B("python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt")) == "ja")
    check("claude npm ci ja", hook(repo, "claude", "claude", B("npm ci")) == "ja")
    check("claude pip -r + Paket fragt", hook(repo, "claude", "claude", B("pip install -r requirements.txt requests")) == "fragen")
    check("claude normen merge ja", hook(repo, "claude", "claude", B("python3 normen/normen.py merge 4")) == "ja")
    (repo / "app.py").write_text("def f():\n    return 2\n")
    r = sh(sys.executable, "normen/normen.py", "merge", "4", cwd=repo)
    check("merge sperrt bei offenen Änderungen", r.returncode == 1 and "nicht committete" in r.stderr, r.stdout + r.stderr)
    sh("git", "checkout", "-q", "--", "app.py", cwd=repo)
    r = sh(sys.executable, "normen/normen.py", "merge", "4", cwd=repo)
    check("merge sperrt ohne PR/Remote", r.returncode == 1 and "Nicht gemergt" in r.stderr, r.stdout + r.stderr)
    check("claude pip -r && pip Paket fragt", hook(repo, "claude", "claude", B("pip install -r requirements.txt && pip install x")) == "fragen")
    check("claude .env nein", hook(repo, "claude", "claude", B("cat .env")) == "nein")
    check("claude Read .env nein", hook(repo, "claude", "claude", {"tool_name": "Read", "tool_input": {"file_path": str(repo / ".env")}}) == "nein")
    check("claude obj.key ja", hook(repo, "claude", "claude", B("grep -n 'x.key=1' src/app.js")) == "ja")  # .key im Text ist kein Geheimnis (node -e fragt seit v7/G4)
    check("claude yolo nein", hook(repo, "claude", "claude", B("vibe --yolo -p x")) == "nein")
    check("claude test ändern ja", hook(repo, "claude", "claude", W("tests/test_a.py")) == "ja")
    check("claude außerhalb fragt", hook(repo, "claude", "claude", W("/etc/hosts")) == "fragen")
    check("claude normen fragt", hook(repo, "claude", "claude", W("normen/normen.toml")) == "fragen")
    # Text in Commit-Nachrichten/PR-Texten ist kein Befehl; Claude-Gedächtnis und Temp sind frei
    check("claude commit-text ja", hook(repo, "claude", "claude",
          B("git commit -q -F - <<'EOF'\nDirekt gh pr merge oder rm -rf x fragt\nEOF")) == "ja")
    check("claude commit -m text ja", hook(repo, "claude", "claude", B('git commit -m "gh pr merge; rm -rf src"')) == "ja")
    check("claude gh pr create body ja", hook(repo, "claude", "claude",
          B("gh pr create --title x --body-file - <<'EOF'\ngit push origin main\nEOF")) == "ja")
    check("claude nach heredoc rm fragt", hook(repo, "claude", "claude",
          B("git commit -F - <<'EOF'\ntext\nEOF\nrm -rf /etc/x")) == "fragen")
    check("claude cat-heredoc bleibt geprüft", hook(repo, "claude", "claude", B("cat <<'EOF'\nrm -rf /etc/x\nEOF")) == "fragen")
    shutil.rmtree(repo / "neu")
    gedaechtnis = os.path.expanduser("~/.claude/projects/-x-projekt/memory/notiz.md")
    check("claude Gedächtnis schreiben ja", hook(repo, "claude", "claude", W(gedaechtnis)) == "ja")
    check("claude Gedächtnis per Bash ja", hook(repo, "claude", "claude", B(f"echo x >> {gedaechtnis}")) == "ja")
    check("claude ~/.claude/settings fragt", hook(repo, "claude", "claude", W(os.path.expanduser("~/.claude/settings.json"))) == "fragen")
    check("claude ~/.claude/agents per Bash fragt", hook(repo, "claude", "claude", B("cat > ~/.claude/agents/x.md")) == "fragen")
    check("claude TMPDIR schreiben ja", hook(repo, "claude", "claude", W(os.path.join(os.environ.get("TMPDIR", "/tmp"), "x.txt"))) == "ja")
    check("claude kaputte Eingabe sperrt", sh(sys.executable, "normen/normen.py", "hook", "--rolle", "claude", "--werkzeug",
                                             "claude", cwd=repo, eingabe="{kaputt").stdout.count('"deny"') == 1)
    # Mistral (Vibe)
    V = lambda c: {"tool_name": "bash", "arguments": {"command": c}}
    check("vibe rm nein", hook(repo, "mistral-team", "vibe", V("rm -rf src")) == "nein")
    check("vibe rm getrackt bleibt nein", hook(repo, "mistral-team", "vibe", V("rm -rf app.py")) == "nein")
    check("vibe commit nein", hook(repo, "mistral-team", "vibe", V("git add -A && git commit -m x")) == "nein")
    check("vibe make ja", hook(repo, "mistral-team", "vibe", V("make test")) == "ja")
    check("vibe sperrpfad nein", hook(repo, "mistral-team", "vibe", V("cat daten/x.json")) == "nein")
    check("vibe ~/.claude nein", hook(repo, "mistral-team", "vibe", V("cat ~/.claude/agents/x.md")) == "nein")
    wf = lambda p: {"tool_name": "write_file", "arguments": {"path": p}}
    check("vibe ohne auftrag nein", hook(repo, "mistral-team", "vibe", wf("app.py")) == "nein")
    r = sh(sys.executable, "normen/normen.py", "auftrag", "--rolle", "mistral-team", "--dateien", "app.py", "tests/test_neu.py", cwd=repo)
    check("auftrag text", "NUR diese Pfade" in r.stdout and "`app.py`" in r.stdout and "daten/" in r.stdout, r.stdout)
    check("vibe mit auftrag ja", hook(repo, "mistral-team", "vibe", wf("app.py")) == "ja")
    check("vibe fremde datei nein", hook(repo, "mistral-team", "vibe", wf("anderes.py")) == "nein")
    check("vibe neuer test ja", hook(repo, "mistral-team", "vibe", wf("tests/test_neu.py")) == "ja")
    sh(sys.executable, "normen/normen.py", "auftrag", "--rolle", "mistral-team", "--dateien", "tests/**", cwd=repo)
    check("vibe bestehender test nein", hook(repo, "mistral-team", "vibe", wf("tests/test_a.py")) == "nein")
    check("vibe auftrag-datei nein", hook(repo, "mistral-team", "vibe", wf(".normen-auftrag")) == "nein")
    # Fund in einem Projekt 15.11.: Team erweiterte .normen-auftrag per Shell und damit seine Rechte
    check("vibe echo >> auftrag nein", hook(repo, "mistral-team", "vibe", V("echo 'README.md' >> .normen-auftrag")) == "nein")
    check("vibe sed auftrag nein", hook(repo, "mistral-team", "vibe", V("sed -i '' '$a x' .normen-auftrag")) == "nein")
    check("vibe siegel nein", hook(repo, "mistral-team", "vibe", V("cat .git/normen-auftrag.sha256")) == "nein")
    check("auftrag-text verbietet Ändern", ".normen-auftrag` nie lesen, ändern" in sh(
        sys.executable, "normen/normen.py", "auftrag", "--rolle", "mistral-team", cwd=repo).stdout)
    r = sh(sys.executable, "normen/normen.py", "pruefen", "--diff", cwd=repo)
    check("siegel passt", ".normen-auftrag [N06" not in r.stdout, r.stdout)
    with open(repo / ".normen-auftrag", "a", encoding="utf-8") as f:
        f.write("README.md\n")
    r = sh(sys.executable, "normen/normen.py", "pruefen", "--diff", cwd=repo)
    check("erweiterte Auftragsliste erkannt", ".normen-auftrag [N06" in r.stdout and "Prüfsumme" in r.stdout, r.stdout)
    sh(sys.executable, "normen/normen.py", "auftrag", "--rolle", "mistral-team", "--dateien", "tests/**", cwd=repo)
    check("vibe lauf-ordner ja", hook(repo, "mistral-team", "vibe", wf("/tmp/vibe-runs/1/prompt.md")) == "ja")
    check("vibe Claude-Gedächtnis nein", hook(repo, "mistral-team", "vibe",
          wf(os.path.expanduser("~/.claude/projects/-x/memory/a.md"))) == "nein")
    r = sh(sys.executable, "normen/normen.py", "merge", "4", cwd=repo)
    check("merge sperrt bei laufendem Auftrag", r.returncode == 1 and "auftrag --ende" in r.stderr, r.stdout + r.stderr)
    (repo / "notiz.md").write_text("Orchestrator-Datei\n")
    sh("git", "add", "notiz.md", cwd=repo)
    r = sh(sys.executable, "normen/normen.py", "pruefen", "--staged", cwd=repo)
    check("pre-commit ignoriert Auftragsliste", "notiz.md [N06" not in r.stdout, r.stdout)
    r = sh(sys.executable, "normen/normen.py", "pruefen", "--diff", cwd=repo)
    check("diff misst Auftragsliste", "notiz.md [N06" in r.stdout, r.stdout)
    sh("git", "rm", "-q", "--cached", "notiz.md", cwd=repo)
    (repo / "notiz.md").unlink()
    (repo / "app.py").write_text("def f(:\n")
    r = sh(sys.executable, "normen/normen.py", "stop", cwd=repo, eingabe="{}")
    check("stop blockt nicht bei laufendem Auftrag", '"block"' not in r.stdout and "Team-Auftrag läuft" in r.stdout, r.stdout)
    sh("git", "checkout", "-q", "--", "app.py", cwd=repo)
    r = sh(sys.executable, "normen/normen.py", "auftrag", "--rolle", "mistral-team", "--dateien", "app.py anderes.py", cwd=repo)
    check("auftrag trennt Leerraum", "`app.py`, `anderes.py`" in r.stdout and "Leerraum" in r.stderr, r.stdout + r.stderr)
    # Gemini
    r = sh(sys.executable, "normen/normen.py", "hook", "--rolle", "gemini-analyst", "--werkzeug", "gemini", cwd=repo,
           eingabe=json.dumps({"tool_name": "run_shell_command", "tool_input": {"command": "git push -f"}, "cwd": str(repo)}))
    check("gemini push exit 2", r.returncode == 2 and "deny" in r.stdout)
    sh(sys.executable, "normen/normen.py", "auftrag", "--ende", cwd=repo)
    check("auftrag entfernt", not (repo / ".normen-auftrag").exists()
          and not (repo / ".git" / "normen-auftrag.sha256").exists())

    # Prüfen
    r = sh(sys.executable, "normen/normen.py", "pruefen", cwd=repo)
    check("pruefen sauber", r.returncode == 0, r.stdout)
    (repo / "app_v2.py").write_text("import requests\n")
    (repo / "app.py").write_text("import subprocess\ndef f():\n    try:\n        return 1\n    except Exception:\n        pass\n"
                                 "subprocess.run('x', shell=True)\n")
    (repo / "ui.js").write_text("setInterval(()=>load(), 5000);\n// normen-ausnahme: S01-KEIN-POLLING – Messwert\nsetInterval(x, 60000);\n")
    (repo / "tests" / "test_a.py").write_text("import pytest\n@pytest.mark.skip\ndef test_a():\n    assert True\n")
    (repo / "aufraeumen.sh").write_text('#!/usr/bin/env bash\nset -uo pipefail\nrm -rf "${ZIEL:?}"\nrm -rf "${ARBEIT:?}/x"\nrm -rf "$ZIEL"\n')
    r = sh(sys.executable, "normen/normen.py", "pruefen", "--diff", cwd=repo)
    o = r.stdout
    check("diff exit 1", r.returncode == 1, o)
    check("v2-Datei", "app_v2.py [N08" in o, o)
    check("shell=True", "app.py:7 [N09" in o, o)
    check("rm ohne :? gemeldet, mit :? nicht", "aufraeumen.sh:5 [N09" in o and "aufraeumen.sh:3" not in o
          and "aufraeumen.sh:4" not in o, o)
    check("except-Hinweis", "app.py:5 [N08-KEINE-ALTLASTEN] hinweis" in o, o)
    check("polling", "ui.js:1 [S01" in o and "ui.js:3" not in o and "1 begründete Ausnahmen" in o, o)
    check("test-skip", "tests/test_a.py:2 [N02" in o and "Review nötig" in o, o)
    (repo / "kaputt.py").write_text("def f(:\n")
    check("syntaxfehler", "kaputt.py [S04" in sh(sys.executable, "normen/normen.py", "pruefen", "--diff", cwd=repo).stdout)
    (repo / "normen" / "kurz.md").write_text("alt\n")
    check("sync-drift erkannt", "normen/kurz.md [NORMEN]" in sh(sys.executable, "normen/normen.py", "pruefen", cwd=repo).stdout)
    sh(sys.executable, "normen/normen.py", "sync", cwd=repo)
    check("sync repariert", "normen/kurz.md [NORMEN]" not in sh(sys.executable, "normen/normen.py", "pruefen", cwd=repo).stdout)
    # Stop-Hook: Änderungen + Fehler → block
    r = sh(sys.executable, "normen/normen.py", "stop", cwd=repo, eingabe="{}")
    check("stop blockt", '"block"' in r.stdout, r.stdout + r.stderr)
    r = sh(sys.executable, "normen/normen.py", "stop", cwd=repo, eingabe='{"stop_hook_active": true}')
    check("stop nur einmal", '"block"' not in r.stdout and "systemMessage" in r.stdout)
    # pre-commit
    sh("git", "add", "app_v2.py", cwd=repo)
    r = sh("git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "x", cwd=repo)
    check("pre-commit sperrt", r.returncode != 0 and "N08" in r.stdout + r.stderr, r.stdout + r.stderr)

print(f"{OK} ok, {FAIL} Fehler")
sys.exit(1 if FAIL else 0)
