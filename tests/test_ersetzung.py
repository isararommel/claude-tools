#!/usr/bin/env python3
"""Tests für Normen v19, Paket S06-ERS: Befehlsersetzungen `$(…)`, Backticks, Prozess-Ersetzungen `<(…)`/`>(…)`/zsh
`=(…)`, Subshell `( … )` und `case`-Muster in der S06-Prüfung – die Lücke (Befehle darin liefen ungeprüft), die
Fehlalarme K1 (`R=$(realpath …)` galt als Pfadaufruf `…)`), K3 (for-Schleife über einen Glob) und K4 (N10-Rückfall bei
reinem grep/sed -n für Teams) sowie Regressionen für K2. Vom Orchestrator als Abnahme geschrieben (vor der Umsetzung rot).
Testskripte entstehen in einem eigenen Temp-Ordner (nicht unter tests/)."""
import json
import os
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


def sh(*args, cwd=None, eingabe=None):
    return subprocess.run(args, cwd=cwd, input=eingabe, capture_output=True, text=True)


def hook(repo, befehl, rolle):
    """(Entscheidung, Grund) des Hooks (Werkzeug claude: fragen bleibt fragen)."""
    data = {"tool_name": "Bash", "tool_input": {"command": befehl}, "cwd": str(repo)}
    r = sh(sys.executable, "normen/normen.py", "hook", "--rolle", rolle, "--werkzeug", "claude", cwd=repo,
           eingabe=json.dumps(data))
    if not r.stdout.strip():
        return "ja", r.stderr
    d = json.loads(r.stdout)["hookSpecificOutput"]
    return {"deny": "nein", "ask": "fragen"}[d["permissionDecision"]], d["permissionDecisionReason"]


with tempfile.TemporaryDirectory() as t, tempfile.TemporaryDirectory() as skripte:
    repo = Path(t) / "projekt"
    repo.mkdir()
    sh("git", "init", "-q", cwd=repo)
    (repo / "Makefile").write_text("test:\n\techo ok\n")
    (repo / "tests").mkdir()
    (repo / "tests" / "test_a.py").write_text("print(1)\n")
    (repo / "tests" / "test_b.py").write_text("print(2)\n")
    r = sh("bash", str(VORLAGE / "einrichten.sh"), str(repo), "--test", "make test")
    check("einrichten", r.returncode == 0, r.stdout + r.stderr)
    sh("git", "add", "-A", cwd=repo)
    sh("git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "start", "--no-verify", cwd=repo)
    sh("git", "checkout", "-q", "-b", "arbeit", cwd=repo)

    sk = Path(skripte)
    B = sk / "boese.py"
    B.write_text('import os\nos.system("echo x")\n', encoding="utf-8")
    H = sk / "harmlos.py"
    H.write_text('print("hallo")\n', encoding="utf-8")
    (sk / "x.sh").write_text("echo hallo\n", encoding="utf-8")
    (sk / "b.sh").write_text("rm -rf /tmp/egal\n", encoding="utf-8")
    SB = sk / "b.sh"
    lauf = sk / "agy-runs" / "geheim"
    lauf.mkdir(parents=True)
    (lauf / "prompt.md").write_text("Nutze diesen Schlüssel:\n-----BEGIN " + "OPENSSH PRIVATE KEY-----\nabc\n", encoding="utf-8")

    def fall(name, befehl, soll, grund="", rolle="claude", nie=""):
        """soll: ja | fragen | nein | nicht (fragen oder nein). grund/nie: Teiltext, der in der Meldung stehen muss
        bzw. nicht stehen darf (belegt, dass die Entscheidung aus der richtigen Prüfung kommt)."""
        stufe, ausgabe = hook(repo, befehl, rolle)
        ok = stufe in ("fragen", "nein") if soll == "nicht" else stufe == soll
        ok = ok and (not grund or grund in ausgabe) and (not nie or nie not in ausgabe)
        check(f"{name} → {soll} [{rolle}]", ok, f"({stufe}) {ausgabe[:300]}")

    # ---------------------------------------------------------------- Lücke: Befehle in Ersetzungen werden geprüft
    OS = "os.system"
    fall("echo $()", f"echo $(python3 {B})", "nicht", OS)
    fall("Zuweisung $()", f"R=$(python3 {B})", "nicht", OS, nie="nicht gefunden")
    fall("$() in doppelten Anführungszeichen", f'echo "$(python3 {B})"', "nicht", OS)
    fall("Backticks", f"echo `python3 {B}`", "nicht", OS)
    fall("Shell-Skript in Backticks", f"echo `bash {SB}`", "nicht", "b.sh")
    fall("Prozess-Ersetzung <()", f"cat <(python3 {B})", "nicht", OS)
    fall("Prozess-Ersetzung >()", f"echo x > >(python3 {B})", "nicht", OS)
    fall("zsh =()", f"cat =(python3 {B})", "nicht", OS)
    fall("Klammer im Zitat innerhalb $()", f"""echo "$(echo ')' ; python3 {B})" """, "nicht", OS)
    fall("verschachtelt $(echo $())", f"echo $(echo $(python3 {B}))", "nicht", OS)
    fall("drei Ebenen", f"echo $(echo $(echo $(python3 {B})))", "nicht", OS)
    fall("vier Ebenen zu tief", f"echo $(echo $(echo $(echo $(python3 {H}))))", "fragen", "zu tief")
    fall("verschachtelte Backticks", f"echo `echo \\`python3 {B}\\``", "nicht", OS)
    fall("$() in Arithmetik", f"echo $(( $(python3 {B}) + 1 ))", "nicht", OS)
    fall("$(( ohne )) ist Subshell", f"echo $((python3 {B}) )", "nicht", OS)
    fall("$() im Variablen-Standard", f"echo ${{X:-$(python3 {B})}}", "nicht", OS)
    fall("$() mit case-Muster", f"echo $(case a in a) python3 {B};; esac)", "nicht", OS)
    fall("$() mit Heredoc ohne Zitat", f"X=$(cat <<EOF\n$(python3 {B})\nEOF\n)", "nicht", OS)
    fall("cat > Datei, Heredoc ohne Zitat", f"cat > /tmp/egal.txt <<EOF\n$(python3 {B})\nEOF", "nicht", OS)
    fall("Commit-Nachricht mit $()", f'git commit -qm "Text $(python3 {B})"', "nicht", OS)
    fall("Pipe in $() zu python3 -", 'echo "$(echo code | python3 -)"', "nicht", "stdin")
    # Review v19 (Large 4, Teil A): Kommentar mit `)`, time/coproc vor Subshell, sehr tiefe Verschachtelung
    fall("Kommentar mit ) in $() im case-Muster", f"case a in $(echo a # )\npython3 {B}) echo hi;; esac", "nicht")
    fall("Kommentar mit ) in $()", f"X=$(echo a # )\npython3 {B}\n)", "nicht", OS)
    fall("time ( … )", f"time (python3 {B})", "nicht", OS)
    fall("coproc ( … )", f"coproc (python3 {B})", "nicht", OS)
    fall("# direkt nach ) ist kein Kommentar", f"echo $(echo a)#$(python3 {B})", "nicht", OS)
    fall("# nach escaptem Leerzeichen", f"echo a\\ #; (python3 {B})", "nicht", OS)
    fall("# in ${…}", f"echo ${{X:- #}}; (python3 {B})", "nicht", OS)
    fall("# im case-Zweig", f"case a in a) echo a\\ #; (python3 {B})\n;; esac", "nicht", OS)
    fall("Kommentar in $() mit Subshell danach", f"X=$(echo a # )\n(python3 {B})\n)", "nicht", OS)
    fall("# nach Zeilenfortsetzung", f"cat x\\\n#: <(python3 {B})", "nicht", OS)
    fall("<() im Kommentar", f"echo hi # <(python3 {B})", "nicht", OS)
    fall("Kommentar mit $() darin", f"echo hi # $(python3 {B})", "nicht", OS)
    fall("30 Ebenen $(( ohne )) – Laufzeit", "echo " + "$(( " * 30 + f"$((python3 {B}) )" + ") )" * 30, "fragen",
         "zu tief")
    fall("600 Ebenen", "echo " + "$(echo " * 600 + "x" + ")" * 600, "fragen", "zu tief", nie="fehlerhaft")
    fall("mehrzeilig ohne Zitat, böse", f"X=$(\n  ls /tmp\n  python3 {B}\n)", "nicht", OS)
    # oberste Ebene: Subshell und case-Muster
    fall("Subshell", f"(python3 {B})", "nicht", OS)
    fall("Subshell mit cd", f"(cd /tmp; python3 {B})", "nicht", OS)
    fall("case-Muster", f"case a in a) python3 {B};; esac", "nicht", OS)
    fall("case-Muster, zweiter Zweig", f"case a in b) echo b;; (a) python3 {B};; esac", "nicht", OS)
    # nicht zerlegbar / nicht auflösbar
    fall("unbalanciert", f"echo $(python3 {B}", "fragen", "nicht zerlegbar")
    fall("Befehlswort aus $()", f"$(echo python3) {B}", "fragen", "Befehl über")
    fall("mktemp-Ordner", 'D=$(mktemp -d); python3 "$D/x.py"', "fragen", "unaufgelöst", nie="nicht gefunden")
    fall("cd in $()-Ordner", f'cd "$(dirname {B})" && python3 boese.py', "fragen", "Basisordner unbekannt")
    # Datenschutz vor vibe/agy auch innerhalb einer Ersetzung
    fall("agy mit $(cat) (Regression)", f'agy -p "$(cat {lauf}/prompt.md)" < /dev/null', "nein", "Private Key")
    fall("agy innerhalb $()", f'X=$(agy -p "$(cat {lauf}/prompt.md)" < /dev/null)', "nein", "Private Key")

    # ---------------------------------------------------------------- erlaubt: Alltagsformen ohne Fehlalarm
    fall("K1 realpath", 'RUN=/tmp/x/gemini; R=$(realpath "$RUN"); echo "$R"', "ja")
    fall("K1 realpath direkt", "R=$(realpath /tmp/x/gemini)", "ja")
    fall("Backticks realpath", "R=`realpath /tmp/x`", "ja")
    fall("dirname", "D=$(dirname /tmp/x/y.sh); echo $D", "ja")
    fall("date im Dateinamen", 'cp a.txt "b-$(date +%s).txt"', "ja")
    fall("date in Anführungszeichen", 'R="$(date +%s)"; echo $R', "ja")
    fall("harmloses Skript in $()", f"R=$(python3 {H})", "ja")
    fall("Pipe in $()", "N=$(git status --short | wc -l); echo $N", "ja")
    fall("$(< datei)", "X=$(< Makefile); echo $X", "ja")
    fall("Arithmetik", "echo $((1+2))", "ja")
    fall("Arithmetik mit Klammern", "echo $(( (1+2) * 3 ))", "ja")
    fall("einfache Anführungszeichen schützen", f"echo '$(python3 {B})'", "ja")
    fall("escaped", f"echo \\$(python3 {B})", "ja")
    fall("Klammer im Zitat, harmlos", """echo "$(echo ')')" """, "ja")
    fall("mehrzeilig ohne Zitat", "X=$(\n  ls /tmp\n  date\n)\necho $X", "ja")
    fall("$() mit zitiertem Heredoc = Daten", f"X=$(cat <<'EOF'\n$(python3 {B})\nEOF\n)", "ja")
    fall("$() mit zitiertem Heredoc, Klammern", "X=$(cat <<'EOF'\nText mit ) und ( und 'x'\nEOF\n)", "ja")
    fall("cat > Datei, zitierter Heredoc", f"cat > /tmp/egal.txt <<'EOF'\n$(python3 {B})\nEOF", "ja")
    fall("Commit-Heredoc mit Klammer", "git commit -qm \"$(cat <<'EOF'\nText (mit Klammer :)\nEOF\n)\"", "ja")
    fall("Commit-Heredoc mit Sonderzeichen",
         "git commit -qm \"$(cat <<'EOF'\nIt's `x` $(y) und )\n\nCo-Authored-By: Name <a@b>\nEOF\n)\"", "ja")
    fall("Subshell harmlos", "(cd /tmp && ls)", "ja")
    fall("case harmlos", 'case "$X" in a) echo a;; *) echo b;; esac', "ja")
    fall("$() mit case harmlos", "echo $(case a in a) echo a;; esac)", "ja")

    # ---------------------------------------------------------------- K2: Regressionen (Fehlalarm nicht nachstellbar)
    fall("K2 Variable im Skriptpfad", f'S={sk}; bash "$S/x.sh"', "ja")
    fall("K2 mit cd", f'S={sk}; cd /tmp && bash "$S/x.sh"', "ja")
    fall("K2 böses Skript", f'S={sk}; bash "$S/b.sh"', "nicht", "b.sh")

    # ---------------------------------------------------------------- K3: for-Schleife über Glob/Wörter
    fall("K3 Glob im Projekt", 'for f in tests/test_*.py; do python3 "$f"; done', "ja")
    fall("K3 Wort außerhalb harmlos", f'for f in {H}; do python3 "$f"; done', "ja")
    fall("K3 Wort außerhalb böse", f'for f in {H} {B}; do python3 "$f"; done', "nicht", OS)
    fall("K3 Glob außerhalb böse", f'for f in {sk}/*.py; do python3 "$f"; done', "nicht", OS)
    fall("K3 Schreiben im selben Befehl", f'cp {B} tests/test_z.py; for f in tests/test_*.py; do python3 "$f"; done',
         "nicht")
    fall("K3 Variable sonst zugewiesen", f'for f in tests/test_*.py; do f={B}; python3 "$f"; done', "nicht")
    fall("K3 Wörter aus $()", 'for f in $(ls tests); do python3 "$f"; done', "fragen")
    (sk / "tief").mkdir()
    (sk / "tief" / "boese2.py").write_text('import os\nos.system("echo x")\n', encoding="utf-8")
    lz = sk / "leer"
    lz.mkdir()
    (lz / "evil").write_text('import os\nos.system("echo x")\n', encoding="utf-8")
    (lz / "evil b.py").write_text('print("hallo")\n', encoding="utf-8")
    fall("K3 Treffer mit Leerzeichen, unzitiert", f"for f in {lz}/*.py; do python3 $f; done", "nicht")
    # Review v19 (Large 4, Teil B): Schreiben, das _schreibziele nicht sieht; Shell-Klammerausdrücke im Glob
    vz = sk / "voll"
    vz.mkdir()
    (vz / "x.py").write_text('print("hallo")\n', encoding="utf-8")
    (vz / "e.py").write_text('import os\nos.system("echo x")\n', encoding="utf-8")
    (vz / "h.sh").write_text("echo hallo\n", encoding="utf-8")
    fall("K3 nur Glob, harmloses Shell-Skript", f'for f in {vz}/*.sh; do bash "$f"; done', "ja")
    fall("K3 tar vor der Schleife", f'tar -xf /tmp/gibt-es-nicht.tar -C {vz}; for f in {vz}/*.sh; do bash "$f"; done',
         "nicht")
    fall("K3 git checkout vor der Schleife", 'git checkout -q -- tests; for f in tests/test_*.py; do python3 "$f"; done',
         "nicht")
    fall("K3 Klammerausdruck [^x]", f'for f in {vz}/[^x]*.py; do python3 "$f"; done', "nicht")
    fall("K3 cd mit Umleitung davor", f'cd 2>/tmp/egal-k3; for f in {vz}/*.sh; do bash "$f"; done', "nicht")
    fall("K3 Zuweisung mit Umleitung davor", f'X=1>/tmp/egal-k3; for f in {vz}/*.sh; do bash "$f"; done', "nicht")
    fall("K3 nach cd", f'cd {repo} && for f in tests/test_*.py; do python3 "$f"; done', "ja")
    fall("K3 zsh-** rekursiv", f'for f in {sk}/**/*.py; do python3 "$f"; done', "nicht")
    fall("K3 Glob ohne Treffer", 'for f in tests/gibt_es_nicht_*.py; do python3 "$f"; done', "nicht")

    # ---------------------------------------------------------------- K4: reines Lesen von normen.py durch Teams
    T = "mistral-team"
    fall("K4 grep", "grep -n 'selbsttest\\|hook' normen/normen.py", "ja", rolle=T)
    fall("K4 sed -n und grep", f"cd {repo} && sed -n '1,5p' normen/normen.py && grep -n hook normen/normen.py", "ja", rolle=T)
    fall("K4 head | grep", "head -20 normen/normen.py | grep merge", "ja", rolle=T)
    fall("K4 cat | grep -c", "cat normen/normen.py | grep -c merge", "ja", rolle=T)
    fall("K4 xargs", "echo merge | xargs python3 normen/normen.py", "nein", "N10", rolle=T)
    fall("K4 zweiter Teilbefehl", "grep -n hook normen/normen.py; python3 normen/normen.py merge 1", "nein", "N10", rolle=T)
    fall("K4 Subshell", "(python3 normen/normen.py merge 1)", "nein", "N10", rolle=T)
    fall("K4 Pipe in sh", "grep merge normen/normen.py | sh", "nein", "N10", rolle=T)
    fall("K4 sed mit e", "sed -n '1e python3 normen/normen.py merge' normen/normen.py", "nein", "N10", rolle=T)
    fall("K4 sed mit w", "sed -n '/hook/w /tmp/x' normen/normen.py", "nein", "N10", rolle=T)
    fall("K4 rg --pre", "rg --pre bash hook normen/normen.py", "nein", "N10", rolle=T)
    fall("K4 zsh-Glob-Qualifier", "ls *(e:'python3 normen/normen.py merge 1':)", "nein", "N10", rolle=T)
    fall("K4 Klammern im grep-Muster", "grep -n 'merge(' normen/normen.py", "ja", rolle=T)
    fall("K4 $() im grep", "grep hook normen/normen.py $(python3 normen/normen.py merge 1)", "nein", "N10", rolle=T)

    # ---------------------------------------------------------------- vertraute Werkzeuge auch innerhalb von $()
    wz = sk / "werkzeug"
    wz.write_text("#!/usr/bin/env python3\nimport urllib.request\nprint('status')\n", encoding="utf-8")
    wz.chmod(0o755)
    fall("Werkzeug in $() ohne Eintrag geprüft", f"s=$({wz} status b-1); echo $s", "nicht", "urllib")
    pj = repo / "normen" / "projekt.toml"
    pj.write_text(pj.read_text(encoding="utf-8").replace(
        "\nvertraut = []\n", f'\nvertraut = [{{pfad = "{wz}", unterbefehle = ["status"]}}]\n'), encoding="utf-8")
    fall("vertrautes Werkzeug in $()", f'until s=$({wz} status b-1 2>&1); echo "$s" | grep -q FERTIG; do sleep 1; done',
         "ja")
    fall("vertrautes Werkzeug in $(), verbotener Unterbefehl", f"s=$({wz} schluessel-anlegen)", "nein")

print(f"test_ersetzung: {OK} ok, {FAIL} fehlgeschlagen")
sys.exit(1 if FAIL else 0)
