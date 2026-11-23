#!/usr/bin/env python3
"""Tests für Paket R2 (Normen v17): `normen.py review` (Vorbereitung der Review-Ordner mit Datenschutzfilter) und das
Review-Tor in `normen.py merge` (reine Entscheidungsfunktion + Sammeln aus git). Startet nie echte Agenten, ruft nie gh."""
import importlib.util
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


def commit(repo, text):
    sh("git", "add", "-A", cwd=repo)
    r = sh("git", "commit", "-qm", text, "--no-verify", cwd=repo)
    assert r.returncode == 0, r.stdout + r.stderr


def neues_repo(t, name, versionsdateien=""):
    repo = t / name
    repo.mkdir()
    sh("git", "init", "-q", "-b", "main", cwd=repo)
    sh("git", "config", "user.email", "test@example.org", cwd=repo)
    sh("git", "config", "user.name", "Test", cwd=repo)
    r = sh("bash", str(VORLAGE / "einrichten.sh"), str(repo), "--test", "echo ok", "--sperre", "geheim/")
    check(f"einrichten {name}", r.returncode == 0, r.stdout + r.stderr)
    if versionsdateien:  # die Vorlage hat [review] schon – Zeile ersetzen, nicht zweiten Abschnitt anhängen
        pt = repo / "normen" / "projekt.toml"
        s = pt.read_text(encoding="utf-8")
        check(f"vorlage {name}: versionsdateien leer", "\nversionsdateien = []\n" in s)
        pt.write_text(s.replace("\nversionsdateien = []\n", f"\nversionsdateien = {versionsdateien}\n"), encoding="utf-8")
    (repo / "app.py").write_text("x = 1\n")
    commit(repo, "start")
    sh("git", "switch", "-q", "-c", "arbeit/r2", cwd=repo)
    return repo


def modul(repo):
    spec = importlib.util.spec_from_file_location(f"normen_rt_{repo.name}", repo / "normen" / "normen.py")
    N = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(N)
    return N


def hook(repo, rolle, werkzeug, ereignis):
    r = sh(sys.executable, "normen/normen.py", "hook", "--rolle", rolle, "--werkzeug", werkzeug, cwd=repo,
           eingabe=json.dumps(ereignis))
    out = r.stdout
    if '"deny"' in out or '"block"' in out or r.returncode == 2:
        return "nein"
    if '"ask"' in out:
        return "fragen"
    return "ja"


def daten(numstat=(), status=(), versionen=None, berichte=None):
    return {"numstat": list(numstat), "status": list(status), "versionen": versionen or {}, "berichte": berichte or {}}


BERICHT_JA = "# Review\n\n## Ergebnis\nMergereif: ja\n"


def test_tor(t):
    repo = neues_repo(t, "tor")
    N = modul(repo)
    cfg = N.laden()
    cfg["projekt"]["review"] = {"code": ["*.py", "*.sh", "Makefile", "*.json"],
                                "kritisch": ["normen/projekt.toml", "werkzeug/rechte.py", "hooks/**"],
                                "versionsdateien": ["quelle/normen.toml"]}
    E = N.review_entscheidung
    B = "arbeit/r2"

    # Nicht-Meilenstein: klein, nichts Kritisches → weiter
    ok, _ = E(cfg, daten([(10, 2, "app.py")], [("M", "app.py")]), [], B, None)
    check("tor: kleine Code-Änderung weiter", ok)
    # 400 Zeilen Markdown zählen nicht
    ok, _ = E(cfg, daten([(400, 0, "docs/text.md")], [("A", "docs/text.md")]), [], B, None)
    check("tor: 400 Zeilen Markdown weiter", ok)
    # Grenze 149/150 (hinzugefügt + gelöscht)
    ok, _ = E(cfg, daten([(100, 49, "app.py")], [("M", "app.py")]), [], B, None)
    check("tor: 149 Code-Zeilen weiter", ok)
    ok, text = E(cfg, daten([(100, 50, "app.py")], [("M", "app.py")]), [], B, None)
    check("tor: 150 Code-Zeilen halt", not ok and "Review empfohlen" in text and "150" in text, text)
    ok, text = E(cfg, daten([(160, 0, "src/x.py")], [("A", "src/x.py")]), [], B, None)
    check("tor: 160 Zeilen .py in Unterordner halt", not ok and "--klein" in text and "meilenstein" in text, text)
    ok, _ = E(cfg, daten([(160, 0, "sub/Makefile")], [("M", "sub/Makefile")]), [], B, None)
    check("tor: Makefile im Unterordner zählt", not ok)
    # Tests und eingespielte Kopien zählen nicht
    ok, _ = E(cfg, daten([(300, 0, "tests/test_x.py")], [("A", "tests/test_x.py")]), [], B, None)
    check("tor: Tests zählen nicht", ok)
    ok, _ = E(cfg, daten([(900, 300, "normen/normen.py"), (40, 0, ".claude/settings.json"), (30, 0, ".githooks/pre-commit"),
                          (30, 0, ".vibe/hooks.toml")],
                         [("M", "normen/normen.py"), ("M", ".claude/settings.json"), ("M", ".githooks/pre-commit"),
                          ("M", ".vibe/hooks.toml")]), [], B, None)
    check("tor: eingespielte Kopien zählen nicht", ok)
    # Binärdateien ("-") stören nicht
    ok, _ = E(cfg, daten([(None, None, "bild.json"), (5, 0, "app.py")], [("M", "bild.json"), ("M", "app.py")]), [], B, None)
    check("tor: Binärdatei ohne Zeilen", ok)
    # Kritische Stellen zählen immer – auch klein, auch normen/projekt.toml (liegt unter normen/, ist aber keine Kopie)
    ok, text = E(cfg, daten([(1, 1, "werkzeug/rechte.py")], [("M", "werkzeug/rechte.py")]), [], B, None)
    check("tor: kritisch 2 Zeilen halt", not ok and "werkzeug/rechte.py" in text, text)
    ok, text = E(cfg, daten([(1, 0, "normen/projekt.toml")], [("M", "normen/projekt.toml")]), [], B, None)
    check("tor: normen/projekt.toml kritisch", not ok and "normen/projekt.toml" in text, text)
    ok, _ = E(cfg, daten([(0, 3, "hooks/a.sh")], [("D", "hooks/a.sh")]), [], B, None)
    check("tor: gelöschte kritische Datei halt", not ok)
    ok, _ = E(cfg, daten([(1, 0, "HOOKS/a.sh")], [("A", "HOOKS/a.sh")]), [], B, None)
    check("tor: kritisch ohne Groß-/Kleinschreibung", not ok)
    # --klein mit Grund lässt Halt passieren
    ok, text = E(cfg, daten([(160, 0, "app.py")], [("M", "app.py")]), [], B, "nur umbenannt")
    check("tor: --klein weiter", ok and "nur umbenannt" in text, text)
    ok, _ = E(cfg, daten([(1, 0, "werkzeug/rechte.py")], [("M", "werkzeug/rechte.py")]), [], B, "Tippfehler")
    check("tor: --klein bei kritisch weiter", ok)

    # Meilenstein per Label: Bericht Pflicht, --klein hilft nicht
    ok, text = E(cfg, daten([(1, 0, "app.py")], [("M", "app.py")]), ["meilenstein"], B, None)
    check("tor: Label ohne Bericht stopp", not ok and "ohne Review-Bericht" in text and "docs/reviews/" in text, text)
    ok, text = E(cfg, daten([(1, 0, "app.py")], [("M", "app.py")]), ["meilenstein"], B, "klein")
    check("tor: Label + --klein bleibt stopp", not ok, text)
    ok, _ = E(cfg, daten([(1, 0, "app.py")], [("M", "app.py")]), ["Meilenstein"], B, None)
    check("tor: Label ohne Groß-/Kleinschreibung", not ok)
    pfad = "docs/reviews/2026-11-23-arbeit-r2.md"
    d = daten([(1, 0, "app.py"), (5, 0, pfad)], [("M", "app.py"), ("A", pfad)], berichte={pfad: BERICHT_JA})
    ok, text = E(cfg, d, ["meilenstein"], B, None)
    check("tor: Label mit Bericht weiter", ok, text)
    d = daten([(5, 0, pfad)], [("M", pfad)], berichte={pfad: BERICHT_JA})
    ok, _ = E(cfg, d, ["meilenstein"], B, None)
    check("tor: geänderter Bericht zählt", ok)
    # Bericht nicht im PR-Diff (nur vorhanden) zählt nicht
    ok, _ = E(cfg, daten([(1, 0, "app.py")], [("M", "app.py")], berichte={}), ["meilenstein"], B, None)
    check("tor: Bericht nicht im Diff stopp", not ok)
    # Bericht gelöscht zählt nicht
    ok, _ = E(cfg, daten([(0, 5, pfad)], [("D", pfad)], berichte={pfad: BERICHT_JA}), ["meilenstein"], B, None)
    check("tor: gelöschter Bericht stopp", not ok)
    # Falscher Branch im Namen: Branch `r2` darf nicht von …-arbeit-r2.md profitieren
    ok, _ = E(cfg, daten([(5, 0, pfad)], [("A", pfad)], berichte={pfad: BERICHT_JA}), ["meilenstein"], "r2", None)
    check("tor: Bericht anderer Branch (endswith) stopp", not ok)
    andere = "docs/reviews/2026-11-23-arbeit-r2-alt.md"
    ok, _ = E(cfg, daten([(5, 0, andere)], [("A", andere)], berichte={andere: BERICHT_JA}), ["meilenstein"], B, None)
    check("tor: Bericht mit Zusatz im Namen stopp", not ok)
    falsch = "docs/reviews/23-11-2026-arbeit-r2.md"
    ok, _ = E(cfg, daten([(5, 0, falsch)], [("A", falsch)], berichte={falsch: BERICHT_JA}), ["meilenstein"], B, None)
    check("tor: Bericht ohne ISO-Datum stopp", not ok)
    # Inhalt: nur eine ganze Zeile `Mergereif: ja`
    for name, inhalt in [("Vorlage", "## Ergebnis\nMergereif: <ja|nein>\n"),
                         ("nein", "## Ergebnis\nMergereif: nein\n"),
                         ("ja und nein", "Mergereif: ja\n\nMergereif: nein\n"),
                         ("nur Ergebnis", "## Ergebnis\nmergereif ja\n"),
                         ("im Satz", "Ergebnis: Mergereif: ja, nach Nachbesserung\n"),
                         ("leer", "")]:
        ok, text = E(cfg, daten([(5, 0, pfad)], [("A", pfad)], berichte={pfad: inhalt}), ["meilenstein"], B, None)
        check(f"tor: Bericht '{name}' stopp", not ok and "Mergereif: ja" in text, text)
    ok, _ = E(cfg, daten([(5, 0, pfad)], [("A", pfad)], berichte={pfad: "x\n  Mergereif:  ja  \ny\n"}), ["meilenstein"], B, None)
    check("tor: Leerraum um Mergereif-Zeile erlaubt", ok)

    # Meilenstein per Version (nur Dateien aus [review].versionsdateien)
    v = {"quelle/normen.toml": (16, 17)}
    ok, text = E(cfg, daten([(1, 1, "quelle/normen.toml")], [("M", "quelle/normen.toml")], versionen=v), [], B, None)
    check("tor: neue Version ohne Bericht stopp", not ok and "ohne Review-Bericht" in text, text)
    d = daten([(1, 1, "quelle/normen.toml"), (5, 0, pfad)], [("M", "quelle/normen.toml"), ("A", pfad)], versionen=v,
              berichte={pfad: BERICHT_JA})
    ok, _ = E(cfg, d, [], B, None)
    check("tor: neue Version mit Bericht weiter", ok)
    ok, _ = E(cfg, daten([(1, 1, "quelle/normen.toml")], [("M", "quelle/normen.toml")],
                         versionen={"quelle/normen.toml": (16, 16)}), [], B, None)
    check("tor: gleiche Version kein Meilenstein", ok)
    for alt, neu in [(None, 17), (16, None), ("?", 17)]:
        ok, _ = E(cfg, daten([(1, 0, "app.py")], [("M", "app.py")], versionen={"quelle/normen.toml": (alt, neu)}), [], B, None)
        check(f"tor: Version {alt}->{neu} gilt als Meilenstein", not ok)
    # Ohne [review]-Abschnitt (ältere Projekte): Vorgaben, keine kritischen Stellen, keine Versionsdateien
    cfg2 = N.laden()
    cfg2["projekt"].pop("review", None)
    ok, _ = E(cfg2, daten([(10, 0, "app.py")], [("M", "app.py")]), [], B, None)
    check("tor: ohne [review] klein weiter", ok)
    ok, _ = E(cfg2, daten([(160, 0, "x.ts")], [("A", "x.ts")]), [], B, None)
    check("tor: ohne [review] Vorgabe-Endungen (.ts) zählen", not ok)
    ok, _ = E(cfg2, daten([(160, 0, "x.md")], [("A", "x.md")]), [], B, None)
    check("tor: ohne [review] Markdown zählt nicht", ok)


def test_sammeln(t):
    repo = neues_repo(t, "sammeln", '["quelle/normen.toml"]')
    sh("git", "switch", "-q", "main", cwd=repo)
    (repo / "quelle").mkdir()
    (repo / "quelle" / "normen.toml").write_text("[meta]\nversion = 16\n")
    (repo / "alt.py").write_text("a = 1\n")
    commit(repo, "quelle")
    sh("git", "switch", "-q", "arbeit/r2", cwd=repo)
    sh("git", "merge", "-q", "main", cwd=repo)
    (repo / "quelle" / "normen.toml").write_text("[meta]\nversion = 17\n")
    (repo / "neu name.py").write_text("b = 2\nc = 3\n")
    sh("git", "mv", "alt.py", "umbenannt.py", cwd=repo)
    (repo / "docs" / "reviews").mkdir(parents=True, exist_ok=True)
    (repo / "docs" / "reviews" / "2026-11-23-arbeit-r2.md").write_text(BERICHT_JA)
    (repo / "bin.json").write_bytes(b"\x00\x01\x02")
    commit(repo, "arbeit")
    N = modul(repo)
    d = N.review_daten(N.laden(), "main")
    status = dict((p, s) for s, p in d["status"])
    check("sammeln: Umbenennung ohne renames (alt D, neu A)", status.get("alt.py") == "D" and status.get("umbenannt.py") == "A", d["status"])
    check("sammeln: Pfad mit Leerzeichen", status.get("neu name.py") == "A", d["status"])
    zeilen = {p: (a, b) for a, b, p in d["numstat"]}
    check("sammeln: numstat", zeilen.get("neu name.py") == (2, 0), d["numstat"])
    check("sammeln: Binärdatei None", zeilen.get("bin.json") == (None, None), d["numstat"])
    check("sammeln: Version alt/neu", d["versionen"].get("quelle/normen.toml") == (16, 17), d["versionen"])
    check("sammeln: Bericht gelesen", d["berichte"].get("docs/reviews/2026-11-23-arbeit-r2.md") == BERICHT_JA, d["berichte"])
    ok, text = N.review_entscheidung(N.laden(), d, [], "arbeit/r2", None)
    check("sammeln+tor: Version mit Bericht weiter", ok, text)
    # Versionsdatei an der Basis nicht vorhanden → None (gilt als Meilenstein)
    cfg = N.laden()
    cfg["projekt"]["review"] = {"versionsdateien": ["fehlt/normen.toml"]}
    d = N.review_daten(cfg, "main")
    check("sammeln: fehlende Versionsdatei None", d["versionen"].get("fehlt/normen.toml") == (None, None), d["versionen"])
    (repo / "quelle" / "normen.toml").write_text("kaputt = [\n")
    commit(repo, "kaputt")
    d = N.review_daten(N.laden(), "main")
    check("sammeln: unlesbare Version '?'", d["versionen"].get("quelle/normen.toml") == (16, "?"), d["versionen"])


def test_merge_cli(t):
    repo = neues_repo(t, "merge")
    r = sh(sys.executable, "normen/normen.py", "merge", "4", "--klein", "   ", cwd=repo)
    check("merge --klein ohne Grund Fehler", r.returncode != 0 and "Grund" in r.stderr and "Nicht gemergt" in r.stderr,
          r.stdout + r.stderr)
    B = lambda c: {"tool_name": "Bash", "tool_input": {"command": c}}
    check("hook: merge --klein ja", hook(repo, "claude", "claude", B('python3 normen/normen.py merge 4 --klein "nur Doku"')) == "ja")
    check("hook: merge --klein mit ; im Grund ja", hook(repo, "claude", "claude",
          B("python3 normen/normen.py merge 4 --klein 'nur Doku; Tippfehler'")) == "ja")
    check("hook: claude review ja", hook(repo, "claude", "claude", B("python3 normen/normen.py review --basis main")) == "ja")
    check("hook: claude auftrag ja", hook(repo, "claude", "claude", B("python3 normen/normen.py auftrag --ende")) == "ja")
    # v17: Teams rufen von normen.py nur pruefen/kurz auf (vorher ungeprüft: auftrag --dateien erweiterte die eigenen Rechte)
    V = lambda c: {"tool_name": "bash", "arguments": {"command": c}}
    G = lambda c: {"tool_name": "run_shell_command", "tool_input": {"command": c}, "cwd": str(repo)}
    for befehl in ("python3 normen/normen.py review", "python3 normen/normen.py auftrag --rolle mistral-team --dateien '**'",
                   "python3 normen/normen.py auftrag --ende", "python3 ./normen/normen.py merge 4",
                   "cd normen && python3 normen.py aktualisieren", "python3 -m normen.normen melden --art x",
                   "make test && python3 normen/normen.py 'auftrag' --ende",
                   # Review 23.11. (Mistral Nr. 1): doppelte Anführungszeichen, Befehlsersetzung, exec
                   'python3 normen/normen.py ""auftrag --ende', "python3 normen/normen.py ''auftrag --ende",
                   "python3 $(echo normen/normen.py) auftrag --ende", "python3 NORMEN/Normen.py auftrag --ende",
                   # normen-ausnahme: N09-SICHERE-MUSTER – Befehlstext als Hook-Eingabe, wird nie ausgeführt
                   "python3 -c \"exec(open('normen/normen.py').read())\" auftrag --ende",
                   "X=auf; python3 normen/normen.py ${X}trag --ende"):
        check(f"hook: vibe `{befehl}` nein", hook(repo, "mistral-team", "vibe", V(befehl)) == "nein")
        check(f"hook: agy `{befehl}` nein", hook(repo, "gemini-analyst", "gemini", G(befehl)) == "nein")
    hilfe = sh(sys.executable, "normen/normen.py", "-h", cwd=repo).stdout
    wahl = set(hilfe.split("{", 1)[1].split("}", 1)[0].split(",")) if "{" in hilfe else set()
    check("NORMEN_UNTERBEFEHLE = argparse-Unterbefehle", wahl == modul(repo).NORMEN_UNTERBEFEHLE, f"{wahl}")
    for befehl in ("python3 normen/normen.py pruefen --diff", "python3 normen/normen.py kurz", "make test",
                   "grep -n 'def cmd_merge' normen/normen.py"):
        check(f"hook: vibe `{befehl}` ja", hook(repo, "mistral-team", "vibe", V(befehl)) == "ja")
    lauf = t / "skripte"
    lauf.mkdir()
    s = lauf / "r.py"
    s.write_text('import subprocess, sys\nsubprocess.run([sys.executable, "normen/normen.py", "review"])\n')
    r = sh(sys.executable, "normen/normen.py", "skript", "--pruefen", str(s), cwd=repo)
    check("skript: normen.py review verboten", r.returncode == 2, r.stdout + r.stderr)


def review(repo, tmp, *args):
    env = dict(os.environ, TMPDIR=str(tmp))
    return sh(sys.executable, "normen/normen.py", "review", "--basis", "main", *args, cwd=repo, env=env)


def lauf_ordner(tmp):
    wurzel = tmp / "review-runs"
    ordner = sorted(wurzel.iterdir()) if wurzel.exists() else []
    return ordner[-1] if ordner else None


def test_review(t):
    repo = neues_repo(t, "review")
    pt = repo / "normen" / "projekt.toml"
    s = pt.read_text(encoding="utf-8").replace("forschungsdaten = []", 'forschungsdaten = ["daten/roh/**", "PROBAND-"]')
    pt.write_text(s, encoding="utf-8")
    commit(repo, "forschung")
    sh("git", "switch", "-q", "main", cwd=repo)
    sh("git", "merge", "-q", "arbeit/r2", cwd=repo)
    (repo / "geheim").mkdir()
    (repo / "geheim" / "a.txt").write_text("".join(f"zeile {i}\n" for i in range(20)))
    (repo / "daten" / "roh").mkdir(parents=True)
    (repo / "daten" / "roh" / "basis.csv").write_text("".join(f"messung {i},{i * 7}\n" for i in range(20)))
    (repo / "daten" / "roh" / "umbau.csv").write_text("".join(f"wert {i},{i * 3}\n" for i in range(20)))
    commit(repo, "basis")
    sh("git", "switch", "-q", "arbeit/r2", cwd=repo)
    sh("git", "merge", "-q", "main", cwd=repo)
    tmp = t / "tmp-review"
    tmp.mkdir()

    r = review(repo, tmp)
    check("review: leerer Diff Exit ≠ 0", r.returncode != 0, r.stdout + r.stderr)
    r = sh(sys.executable, "normen/normen.py", "review", "--basis", "gibt-es-nicht", cwd=repo, env=dict(os.environ, TMPDIR=str(tmp)))
    check("review: unbekannte Basis Exit ≠ 0", r.returncode != 0, r.stdout + r.stderr)

    (repo / "src").mkdir()
    (repo / "src" / "a.py").write_text("def a():\n    return 1\n")
    (repo / "docs").mkdir(exist_ok=True)
    (repo / "docs" / "text.md").write_text("Beschreibung\n")
    (repo / "geheim" / "a.txt").write_text("".join(f"zeile {i}\n" for i in range(20)) + "neu\n")  # gesperrt ("geheim/")
    sh("git", "mv", "geheim/a.txt", "frei.txt", cwd=repo)                  # Umbenennung aus Sperrpfad heraus
    (repo / "unter" / "GEHEIM").mkdir(parents=True)
    (repo / "unter" / "GEHEIM" / "x.txt").write_text("x\n")              # gesperrt, andere Schreibweise
    (repo / "conf.env").write_text("TOKEN=x\n")                           # Geheimnis-Muster
    (repo / "daten" / "roh" / "m.csv").write_text("1,2\n")                # Forschungsdaten (Pfad)
    # Review 23.11. (Mistral Nr. 2): unveränderte Kopie und stark umgebaute Umbenennung aus Forschungsdaten heraus
    (repo / "kopie.csv").write_text((repo / "daten" / "roh" / "basis.csv").read_text())
    sh("git", "mv", "daten/roh/umbau.csv", "src/umbau.csv", cwd=repo)
    (repo / "src" / "umbau.csv").write_text("".join(f"wert {i},{i * 3}\n" for i in range(8))
                                            + "".join(f"neu {i}\n" for i in range(12)))
    (repo / "daten" / "Roh2.csv").write_text("1\n")                     # keine Forschungsdaten (für „ohne Gruppe“)
    (repo / "src" / "liste.py").write_text("IDS = ['proband-0042']\n")    # Forschungsdaten (Marker, andere Schreibweise)
    commit(repo, "änderungen")

    r = review(repo, tmp)
    check("review: Exit 0", r.returncode == 0, r.stdout + r.stderr)
    lauf = lauf_ordner(tmp)
    check("review: Lauf-Ordner mit Branch ohne /", lauf is not None and lauf.name.endswith("-arbeit-r2") and "/" not in lauf.name,
          str(lauf))
    if lauf is None:
        return
    g = lauf / "alles"
    for rolle in ("mistral", "gemini"):
        check(f"review: {rolle}/diff.patch", (g / rolle / "diff.patch").is_file(), str(list(g.rglob("*"))))
        check(f"review: {rolle}/pflicht.txt", (g / rolle / "pflicht.txt").is_file())
    check("review: mistral/bericht.md", (g / "mistral" / "bericht.md").is_file())
    check("review: gemini ohne bericht.md", not (g / "gemini" / "bericht.md").exists())
    zweit = (g / "mistral" / "bericht.md").read_text(encoding="utf-8") if (g / "mistral" / "bericht.md").is_file() else ""
    check("review: bericht.md mit Text für den zweiten Schritt", "Schreibe jetzt den Bericht" in zweit, repr(zweit))
    pm = (g / "mistral" / "pflicht.txt").read_text(encoding="utf-8") if (g / "mistral" / "pflicht.txt").is_file() else ""
    pg = (g / "gemini" / "pflicht.txt").read_text(encoding="utf-8") if (g / "gemini" / "pflicht.txt").is_file() else ""
    check("review: pflicht mistral", "Rolle mistral-team" in pm and "Außerhalb des Projektordners" in pm, pm[:200])
    check("review: pflicht gemini", "Rolle gemini-analyst" in pg, pg[:200])
    dm = (g / "mistral" / "diff.patch").read_text(encoding="utf-8") if (g / "mistral" / "diff.patch").is_file() else ""
    dg = (g / "gemini" / "diff.patch").read_text(encoding="utf-8") if (g / "gemini" / "diff.patch").is_file() else ""
    for name, d in (("mistral", dm), ("gemini", dg)):
        check(f"review {name}: Code drin", "src/a.py" in d and "docs/text.md" in d, d[:300])
        check(f"review {name}: gesperrt fehlt", "geheim/a.txt" not in d and "GEHEIM/x.txt" not in d, d)
        check(f"review {name}: Umbenennung aus Sperrpfad fehlt", "frei.txt" not in d, d)
        check(f"review {name}: Geheimnis fehlt", "conf.env" not in d and "TOKEN" not in d, d)
        check(f"review {name}: Forschungspfad fehlt", "daten/roh/m.csv" not in d, d)
        check(f"review {name}: Marker-Datei fehlt", "proband-0042" not in d.lower(), d)
        check(f"review {name}: Kopie aus Forschungsdaten fehlt", "kopie.csv" not in d and "messung 3" not in d, d)
        check(f"review {name}: umgebaute Umbenennung fehlt", "src/umbau.csv" not in d and "wert 3" not in d, d)
    check("review: Ausgabe nennt Gefiltertes", "gefiltert" in r.stdout and "daten/roh/m.csv" in r.stdout
          and "src/liste.py" in r.stdout and "frei.txt" in r.stdout, r.stdout)
    check("review: Ausgabe nennt Ordner und Zeilen", str(g) in r.stdout or "alles" in r.stdout, r.stdout)
    check("review: gesperrter Inhalt nicht in Ausgabe", "zeile 3" not in r.stdout and "TOKEN" not in r.stdout, r.stdout)

    # Gruppen: Datei in erster passender Gruppe, nicht zugeordnete Dateien werden genannt
    tmp2 = t / "tmp-gruppen"
    tmp2.mkdir()
    r = review(repo, tmp2, "--gruppe", "code=src/*.py", "--gruppe", "doku=docs/**,*.md")
    check("review gruppen: Exit 0", r.returncode == 0, r.stdout + r.stderr)
    lauf = lauf_ordner(tmp2)
    if lauf is not None:
        code = (lauf / "code" / "gemini" / "diff.patch").read_text(encoding="utf-8") if (lauf / "code" / "gemini" / "diff.patch").is_file() else ""
        doku = (lauf / "doku" / "gemini" / "diff.patch").read_text(encoding="utf-8") if (lauf / "doku" / "gemini" / "diff.patch").is_file() else ""
        check("review gruppen: code", "src/a.py" in code and "docs/text.md" not in code, code[:300])
        check("review gruppen: doku", "docs/text.md" in doku and "src/a.py" not in doku, doku[:300])
        check("review gruppen: kein Ordner alles", not (lauf / "alles").exists())
    check("review gruppen: ohne Gruppe genannt", "ohne Gruppe" in r.stdout and "daten/Roh2.csv" in r.stdout, r.stdout)
    r = review(repo, tmp2, "--gruppe", "../x=*.py")
    check("review gruppen: ungültiger Name Exit ≠ 0", r.returncode != 0, r.stdout + r.stderr)
    r = review(repo, tmp2, "--gruppe", "ohne-gleich")
    check("review gruppen: ohne = Exit ≠ 0", r.returncode != 0, r.stdout + r.stderr)

    # Hinweis ab 150 Diff-Zeilen
    (repo / "src" / "gross.py").write_text("".join(f"z{i} = {i}\n" for i in range(200)))
    commit(repo, "gross")
    tmp3 = t / "tmp-gross"
    tmp3.mkdir()
    r = review(repo, tmp3)
    check("review: Hinweis ab 150 Zeilen", r.returncode == 0 and "150" in r.stdout and "teilen" in r.stdout, r.stdout)


def main():
    with tempfile.TemporaryDirectory() as d:
        t = Path(d)
        for f in (test_tor, test_sammeln, test_merge_cli, test_review):
            try:
                f(t)
            except Exception as e:  # normen-ausnahme: N08-KEINE-ALTLASTEN – wird als FAIL gezählt, nicht verschluckt
                global FAIL
                FAIL += 1
                print(f"FAIL {f.__name__} abgebrochen: {type(e).__name__}: {e}")
    print(f"test_review_tor: {OK} ok, {FAIL} fehlgeschlagen")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
