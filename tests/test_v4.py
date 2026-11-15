#!/usr/bin/env python3
"""Tests für Normen v4: Rolle inhaberin, N10 Lesen frei, lesbar_extern, herkunft/aktualisieren, melden, Einstieg einrichten.sh,
Öffentlich-Prüfung (private Begriffe aus ~/.config/claude-tools/privat-begriffe.txt, falls vorhanden)."""
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
    repo = Path(t) / name
    repo.mkdir()
    sh("git", "init", "-q", cwd=repo)
    r = sh("bash", str(VORLAGE / "einrichten.sh"), str(repo), "--test", "echo ok", *opt)
    check(f"einrichten {name}", r.returncode == 0, r.stdout + r.stderr)
    return repo


def hook(repo, rolle, werkzeug, data):
    data.setdefault("cwd", str(repo))
    r = sh(sys.executable, "normen/normen.py", "hook", "--rolle", rolle, "--werkzeug", werkzeug,
           cwd=repo, eingabe=json.dumps(data))
    if werkzeug == "claude":
        if not r.stdout.strip():
            return "ja"
        return {"deny": "nein", "ask": "fragen"}[json.loads(r.stdout)["hookSpecificOutput"]["permissionDecision"]]
    return "nein" if r.stdout.strip() and json.loads(r.stdout.splitlines()[0])["decision"] == "deny" else "ja"


def B(c):
    return {"tool_name": "Bash", "tool_input": {"command": c}}


def V(c):
    return {"tool_name": "bash", "tool_input": {"command": c}}


def W(p):
    return {"tool_name": "Write", "tool_input": {"file_path": p, "content": "x"}}


def R(p):
    return {"tool_name": "Read", "tool_input": {"file_path": p}}


def normen(repo, *args, env=None):
    return sh(sys.executable, "normen/normen.py", *args, cwd=repo, env=env)


with tempfile.TemporaryDirectory() as t:
    # 1. Rolle inhaberin / Platzhalter
    repo = neues_repo(t, "p1", "--inhaberin", "Testperson")
    kurz = (repo / "normen/kurz.md").read_text()
    check("kurz.md nennt Anzeigename", "Testperson" in kurz)
    check("kurz.md ohne Platzhalter", "{inhaberin}" not in kurz)
    check("Rolle inhaberin", "| inhaberin |" in kurz)
    r = hook(repo, "claude", "claude", B("rm -rf /tmp/irgendwo-ausserhalb"))
    check("Rückfrage mit Anzeigename", r == "fragen")
    aus = sh(sys.executable, "normen/normen.py", "hook", "--rolle", "claude", "--werkzeug", "claude", cwd=repo,
             eingabe=json.dumps(B("rm -rf /tmp/irgendwo-ausserhalb") | {"cwd": str(repo)})).stdout
    check("Meldung „bitte Testperson fragen“", "bitte Testperson fragen" in aus, aus)
    repo0 = neues_repo(t, "p0")
    check("ohne Name: „die Inhaberin“", "die Inhaberin" in (repo0 / "normen/kurz.md").read_text())

    # 2. N10: Lesen frei, Schreiben fragt, Teams gesperrt; N03 für ~/.ssh und ~/.config/gh
    check("claude cat ~/.claude ja", hook(repo, "claude", "claude", B("cat ~/.claude/agents/x.md")) == "ja")
    check("claude ls/grep ~/.vibe ja", hook(repo, "claude", "claude", B("ls ~/.vibe && grep -r x ~/.gemini")) == "ja")
    check("claude diff ~/.claude ja", hook(repo, "claude", "claude", B("diff ~/.claude/agents/a.md agenten/a.md")) == "ja")
    check("claude > ~/.claude fragt", hook(repo, "claude", "claude", B("echo x > ~/.claude/settings.json")) == "fragen")
    check("claude cp nach ~/.claude fragt", hook(repo, "claude", "claude", B("cp a.md ~/.claude/agents/")) == "fragen")
    check("claude sed -i ~/.claude fragt", hook(repo, "claude", "claude", B("sed -i '' 's/a/b/' ~/.claude/CLAUDE.md")) == "fragen")
    check("claude find -delete fragt", hook(repo, "claude", "claude", B("find ~/.claude/agents -name x -delete")) == "fragen")
    check("claude Gedächtnis per Bash ja",
          hook(repo, "claude", "claude", B("echo x > ~/.claude/projects/-x/memory/a.md")) == "ja")
    check("claude Write ~/.claude fragt",
          hook(repo, "claude", "claude", W(os.path.expanduser("~/.claude/settings.json"))) == "fragen")
    check("vibe cat ~/.claude nein", hook(repo, "mistral-team", "vibe", V("cat ~/.claude/agents/x.md")) == "nein")
    check("claude ls ~/.ssh nein", hook(repo, "claude", "claude", B("ls ~/.ssh")) == "nein")
    check("claude cat ~/.config/gh nein", hook(repo, "claude", "claude", B("cat ~/.config/gh/hosts.yml")) == "nein")

    # 3. lesbar_extern: lesen ja, schreiben nein (auch nicht mit Rückfrage)
    extern = Path(t) / "werkzeuge"
    (extern / "agenten-normen").mkdir(parents=True)
    pt = repo / "normen/projekt.toml"
    pt.write_text(pt.read_text().replace('lesbar_extern = ["~/Documents/Projekte/claude-tools"]',
                                         f'lesbar_extern = ["{extern}"]'))
    check("lesbar_extern lesen ja", hook(repo, "claude", "claude", R(str(extern / "agenten-normen/x.md"))) == "ja")
    check("lesbar_extern schreiben nein", hook(repo, "claude", "claude", W(str(extern / "agenten-normen/x.md"))) == "nein")
    check("anderswo außerhalb fragt", hook(repo, "claude", "claude", W("/opt/anderswo/x.md")) == "fragen")

    # 4. herkunft.toml, pruefen-Hinweise, aktualisieren
    h = (repo / "normen/herkunft.toml").read_text()
    check("herkunft: Version", "version = 4" in h)
    check("herkunft: drei Prüfsummen", h.count(' = "') >= 3 and '"normen/normen.py"' in h)
    check("herkunft: kein lokaler Pfad", str(Path.home()) not in h and str(ROOT) not in h)
    aus = normen(repo, "pruefen", "--nur-melden").stdout
    check("pruefen: frisch ohne Herkunft-Hinweis", "herkunft" not in aus, aus)
    (repo / "normen/rollen.toml").write_text((repo / "normen/rollen.toml").read_text() + "\n# von Hand\n")
    aus = normen(repo, "pruefen", "--nur-melden").stdout
    check("pruefen: Handänderung als Hinweis", "von Hand geändert" in aus and "0 Fehler" in aus, aus)
    r = normen(repo, "aktualisieren", "--quelle", str(ROOT))
    check("aktualisieren verweigert bei Handänderung", r.returncode == 1 and "normen/rollen.toml" in r.stderr, r.stderr)
    r = normen(repo0, "aktualisieren", "--quelle", str(ROOT))
    check("aktualisieren läuft", r.returncode == 0 and "v4 → v4" in r.stdout, r.stdout + r.stderr)
    r = normen(repo0, "aktualisieren", "--quelle", str(Path(t) / "gibtsnicht"))
    check("aktualisieren: Quelle fehlt", r.returncode == 1)

    # 5. melden
    rep = Path(t) / "text.md"
    rep.write_text("Vibe hat eine Datei außerhalb des Auftrags geändert.\n")
    m = ["melden", "--art", "agent-verhalten", "--titel", "Vibe außerhalb des Auftrags", "--text-datei", str(rep)]
    r = normen(repo0, *m, "--trocken")
    kopien = list((repo0 / ".normen/rueckmeldungen").glob("*-agent-verhalten.md"))
    check("melden --trocken", r.returncode == 0 and len(kopien) == 1, r.stdout + r.stderr)
    check(".normen/ ignoriert", ".normen/" in (repo0 / ".gitignore").read_text())
    r = normen(repo0, *m)
    check("melden ohne Ziel scheitert", r.returncode == 1 and "[rueckmeldung].repo" in r.stderr, r.stderr)
    for name, inhalt in [("E-Mail", "Kontakt: jemand@example.org"), ("IBAN", "DE89 3704 0044 0532 0130 00"),
                         ("Geheimnis", 'token = "abcdefghijklmnopqrstuvwxyz"'), ("Telefon", "Ruf an: +49 170 1234567")]:
        rep.write_text(inhalt + "\n")
        r = normen(repo0, *m, "--trocken")
        check(f"melden sperrt {name}", r.returncode == 1 and "Nicht gesendet" in r.stderr, r.stdout + r.stderr)
    rep.write_text("Harmlos.\n")
    pt0 = repo0 / "normen/projekt.toml"
    pt0.write_text(pt0.read_text().replace('[rueckmeldung]\n', '[rueckmeldung]\nrepo = "jemand/sammlung"\n', 1)
                   .replace('\nrepo = ""', "\n"))
    bin_ = Path(t) / "bin"
    bin_.mkdir()
    log = Path(t) / "gh.log"
    (bin_ / "gh").write_text(f'#!/usr/bin/env bash\necho "$*" >> "{log}"\n'
                             'case "$1 $2" in "repo view") echo "$GH_SICHT" ;; "issue create") echo https://x/issues/1 ;; esac\n')
    (bin_ / "gh").chmod(0o755)
    env = dict(os.environ, PATH=f"{bin_}:{os.environ['PATH']}", GH_SICHT="PUBLIC")
    r = normen(repo0, *m, env=env)
    check("melden: öffentliches Ziel abgelehnt", r.returncode == 1 and "nicht privat" in r.stderr, r.stderr)
    check("melden: öffentlich → kein Issue", "issue create" not in (log.read_text() if log.exists() else ""))
    env["GH_SICHT"] = "PRIVATE"
    r = normen(repo0, *m, env=env)
    gh = log.read_text()
    check("melden: privat → Issue", r.returncode == 0 and "issue create --repo jemand/sammlung" in gh, r.stdout + r.stderr)
    check("melden: Labels", "--label rueckmeldung --label art:agent-verhalten" in gh)
    check("hook: claude melden fragt", hook(repo0, "claude", "claude", B("python3 normen/normen.py melden --art ablauf")) == "fragen")
    check("hook: claude melden --trocken ja",
          hook(repo0, "claude", "claude", B("python3 normen/normen.py melden --art ablauf --trocken")) == "ja")
    check("hook: vibe melden nein", hook(repo0, "mistral-team", "vibe", V("python3 normen/normen.py melden --art x")) == "nein")

    # 6. Einstieg einrichten.sh (Normen + Multi-KI, Optionen richtig verteilt)
    repo2 = Path(t) / "p2"
    repo2.mkdir()
    sh("git", "init", "-q", cwd=repo2)
    r = sh("bash", str(ROOT / "einrichten.sh"), str(repo2), "--test", "echo ok", "--sperre", "daten/", "--inhaberin", "X Y")
    check("Einstieg läuft", r.returncode == 0, r.stdout + r.stderr)
    check("Einstieg: Normen", (repo2 / "normen/herkunft.toml").exists() and 'inhaberin = "X Y"' in
          (repo2 / "normen/projekt.toml").read_text())
    check("Einstieg: Multi-KI", (repo2 / "docs/multi-ki-ablauf.md").exists() and "daten/" in (repo2 / ".geminiignore").read_text())
    r = sh("bash", str(ROOT / "einrichten.sh"), str(repo2), "--test", "echo ok")
    check("Einstieg mehrfach ausführbar", r.returncode == 0, r.stderr)
    check("Einstieg: falsche Option", sh("bash", str(ROOT / "einrichten.sh"), str(repo2), "--gibtsnicht").returncode == 64)

# 7. Öffentlich-Prüfung: keine privaten Begriffe im Repository (Liste liegt bewusst NICHT im Repository)
liste = Path(os.path.expanduser("~/.config/claude-tools/privat-begriffe.txt"))
if liste.exists():
    begriffe = [z.strip().lower() for z in liste.read_text(encoding="utf-8").splitlines() if z.strip() and not z.startswith("#")]
    dateien = sh("git", "ls-files", "--cached", "--others", "--exclude-standard", cwd=ROOT).stdout.split()
    for rel in dateien:
        try:
            text = (ROOT / rel).read_text(encoding="utf-8").lower()
        except (UnicodeDecodeError, OSError):
            continue
        for b in begriffe:
            check(f"öffentlich: {rel} ohne privaten Begriff", b not in text and b not in rel.lower(), f"({b!r})")
else:
    print("Hinweis: Öffentlich-Prüfung übersprungen (~/.config/claude-tools/privat-begriffe.txt fehlt).")

print(f"{OK} ok, {FAIL} Fehler")
sys.exit(1 if FAIL else 0)
