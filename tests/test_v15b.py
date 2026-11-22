#!/usr/bin/env python3
"""Tests für V15b-1 (Normen v16): gemeinsamer Python-Modul-Auflöser für `python3 -m` und Importe in `-c`, `$PWD` aus dem
Basisordner, geschriebene Modul-Kandidaten, Code-Starter, vertraute Werkzeuge nur für die Rolle claude.
Befund-Nummern: docs/reviews/2026-11-20-paket-v15-hooks.md. Startet nie echte Agenten."""
import importlib.machinery
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


def hook(repo, befehl, rolle="claude"):
    """Stufe aus dem Claude-Hook (fragen bleibt fragen, auch für Team-Rollen)."""
    data = {"tool_name": "Bash", "tool_input": {"command": befehl}, "cwd": str(repo)}
    r = sh(sys.executable, "normen/normen.py", "hook", "--rolle", rolle, "--werkzeug", "claude", cwd=repo,
           eingabe=json.dumps(data))
    if not r.stdout.strip():
        return "ja", r.stderr
    out = json.loads(r.stdout)["hookSpecificOutput"]
    return {"deny": "nein", "ask": "fragen"}[out["permissionDecision"]], out.get("permissionDecisionReason", "")


BOESE = "import os\nos.remove('/tmp/gibt-es-nicht-v15b')\n"
HARMLOS = "print(1)\n"
WERKZEUG = "import os, urllib.request\nos.replace('a', 'b')\nurllib.request.urlopen('https://example.invalid')\n"

with tempfile.TemporaryDirectory() as t:
    t = Path(os.path.realpath(t))
    repo = t / "projekt"
    repo.mkdir()
    sh("git", "init", "-q", "-b", "arbeit", cwd=repo)
    (repo / "Makefile").write_text("test:\n\techo ok\n")
    r = sh("bash", str(VORLAGE / "einrichten.sh"), str(repo), "--test", "make test")
    check("einrichten", r.returncode == 0, r.stdout + r.stderr)
    spec = importlib.util.spec_from_file_location("normen_v15b", repo / "normen" / "normen.py")
    N = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(N)

    # 0. Suchreihenfolge des Auflösers gegen den echten Interpreter (Dateien geben ihren __file__ aus)
    fx = t / "fx"
    basis, pp = fx / "basis", fx / "pp"
    for d in (basis / "zzm", basis / "zza", basis / "zzn", pp / "zzn", basis / "zzr", pp / "zzr", basis / "zzq"):
        d.mkdir(parents=True, exist_ok=True)
    druck = "print(__file__)\n"
    for f in (basis / "zzm.py", basis / "zzm" / "__init__.py", basis / "zzm" / "__main__.py",
              basis / "zza" / "__init__.py", basis / "zza" / "b.py", pp / "zzn" / "x.py",
              pp / "zzr" / "__init__.py", basis / "zzq.py"):
        f.write_text(druck)
    env = dict(os.environ, PYTHONPATH=str(pp))
    env.pop("PYTHONSTARTUP", None)
    check("0: Auflöser vorhanden", hasattr(N, "_py_modul_aufloesen"))
    for art, ziel in () if not hasattr(N, "_py_modul_aufloesen") else (("-m", "zzm"), ("-m", "zza.b"), ("-m", "zzn.x"), ("-m", "zzr"), ("-m", "zzq"),
                      ("-c", "import zza.b"), ("-c", "from zzn import x"), ("-c", "import zzr"), ("-c", "import zzq")):
        r = sh(sys.executable, "-S", "-B", art, ziel, cwd=basis, env=env)
        echt = [Path(os.path.realpath(z)) for z in r.stdout.split()]
        if art == "-m":
            dateien, grund = N._py_modul_aufloesen(ziel, [str(basis), str(pp)], als_main=True)
        else:
            mod = ziel.split()[1] + ("." + ziel.split()[3] if ziel.startswith("from") else "")
            dateien, grund = N._py_modul_aufloesen(mod, [str(basis), str(pp)], als_main=False)
        # -m zzr: Paket ohne __main__ – Python lädt __init__ und bricht dann ab (Rückgabewert 1)
        check(f"0: Auflöser = Interpreter: {art} {ziel}", (r.returncode == 0 or ziel == "zzr") and grund is None
              and [Path(os.path.realpath(d)) for d in dateien] == echt, f"{r.stderr} echt={echt} hook={dateien} {grund}")

    lauf = t / "lauf"
    (lauf / "sub").mkdir(parents=True)
    (lauf / "sub" / "boese.py").write_text(BOESE)
    (lauf / "harmlos.py").write_text(HARMLOS)
    (lauf / "evil.py").write_text(HARMLOS)
    (lauf / "pk2").mkdir()
    (lauf / "pk2" / "__init__.py").write_text(BOESE)
    (lauf / "pk2" / "sub.py").write_text(HARMLOS)
    (lauf / "pq").mkdir()
    (lauf / "pq.py").write_text(HARMLOS)
    (lauf / "pq" / "__init__.py").write_text(HARMLOS)
    (lauf / "pq" / "__main__.py").write_text(BOESE)
    (lauf / "zzso.py").write_text(HARMLOS)
    (lauf / ("zzso" + importlib.machinery.EXTENSION_SUFFIXES[0])).write_text("")
    (lauf / "x.zip").write_text("")
    schatten = t / "schatten"
    schatten.mkdir()
    (schatten / "json.py").write_text(BOESE)
    (schatten / "nutzt.py").write_text("import json\nprint(json.dumps(1))\n")
    (lauf / "ns").mkdir()
    (lauf / "ns" / "boese.py").write_text(BOESE)
    (repo / "ns").mkdir()
    (repo / "modul.py").write_text("X = 1\n")
    schreib = "printf 'import os\\nos.remove(1)\\n'"

    faelle = [
        # Nr. 1: Modul im selben Befehl geschrieben
        (f"cd {lauf} && {schreib} > neu.py && python3 -m neu", "fragen"),
        (f"cd {lauf} && {schreib} > json.py && python3 -c 'import json'", "fragen"),
        # Nr. 2: geschrieben in anderer Schreibweise
        (f"cd {lauf} && {schreib} > Evil.py && python3 -m evil", "fragen"),
        # Nr. 3: $PWD aus dem Basisordner
        ("PYTHONPATH=$PWD/src python3 -m pytest -q", "ja"),
        (f"cd {lauf}; export PYTHONPATH=$PWD/sub; cd {repo} && python3 -m boese", "nein"),
        (f"cd {lauf} && cd \"$PWD/sub\" && python3 -m boese", "nein"),
        (f"cd {lauf} && {schreib} > \"$PWD/neu2.py\" && python3 -m neu2", "fragen"),
        ("cd \"$(mktemp -d)\" && python3 -m pytest", "fragen"),
        # Nr. 4, 5: Eltern-__init__ und Paket vor Modul
        (f"cd {lauf} && python3 -m pk2.sub", "nein"),
        (f"cd {lauf} && python3 -m pq", "nein"),
        # Nr. 6 und Advisor: Schatten-Modul einer Positivlisten-Bibliothek
        (f"cd {schatten} && python3 -c 'import json'", "fragen"),
        (f"PYTHONPATH={schatten} python3 -c 'import json'", "fragen"),
        (f"cd {schatten} && python3 -m nutzt", "fragen"),
        # Namespace und `from ns import x`
        (f"PYTHONPATH={lauf} python3 -c 'from ns import boese'", "fragen"),  # Untermodul außerhalb, nicht prüfbar
        ("python3 -c 'import ns'", "fragen"),
        # andere Importformen
        (f"cd {lauf} && python3 -m zzso", "fragen"),
        (f"PYTHONPATH={lauf}/x.zip python3 -m irgendwas", "fragen"),
        # Nr. 7: Code-Starter
        ("python3 -m timeit 'pass'", "fragen"),
        (f"python3 -m cProfile {lauf}/harmlos.py", "fragen"),
        ("python3 -m runpy x", "fragen"),
        ("python3 -m pdb x.py", "fragen"),
        ("python3 -m trace --count x.py", "fragen"),
        ("python3 -m profile x.py", "fragen"),
        # Positivfälle bleiben ja
        ("python3 -m pytest -q", "ja"),
        ("python3 -m pytest -q > pytest.log", "ja"),
        (f"LOG={lauf}/p.log; python3 -m pytest -q > \"$LOG\"", "ja"),
        ("python3 -m pip install -r requirements.txt", "ja"),
        ("python3 -m venv .venv", "ja"),
        (f"cd {lauf} && python3 -m harmlos", "ja"),
        ("python3 -c 'import modul; print(modul.X)'", "ja"),
        ("python3 -c 'import json; print(json.dumps(1))'", "ja"),
    ]
    for befehl, soll in faelle:
        s, g = hook(repo, befehl)
        check(f"1: {befehl} → {soll}", s == soll, f"ist {s}: {g[:200]}")

    # Schatten bei `python3 <datei>.py`: der Skriptordner ist der erste Suchordner (vor V15b: ja)
    s, g = hook(repo, f"python3 {schatten}/nutzt.py")
    check("1: python3 <schatten>/nutzt.py → fragen", s == "fragen", f"ist {s}: {g[:200]}")

    # 10. vertraute Werkzeuge: nur Rolle claude; Teams nie, auf keinem Weg
    ext = t / "ext"
    ext.mkdir()
    (ext / "wz.py").write_text(WERKZEUG)
    (ext / "wz.py").chmod(0o755)
    (repo / "wp.py").write_text(WERKZEUG)
    (repo / "wp.py").chmod(0o755)
    pj = repo / "normen" / "projekt.toml"
    v = pj.read_text(encoding="utf-8")
    eintraege = ", ".join(f'{{pfad = "{p}", unterbefehle = ["status"]}}' for p in (ext / "wz.py", repo / "wp.py"))
    v = v.replace("\nvertraut = []\n", f"\nvertraut = [{eintraege}]\n")
    import re
    v, n = re.subn(r"^lesbar_extern = \[", f'lesbar_extern = ["{ext}", ', v, flags=re.M)
    check("10: projekt.toml vorbereitet", n == 1 and "wz.py" in v)
    pj.write_text(v, encoding="utf-8")
    fz = [
        (f"{ext}/wz.py status", "ja", "nein"),
        (f"{ext}/wz.py schluessel", "nein", "nein"),
        ("./wp.py status", "ja", "nein"),
        ("./wp.py schluessel", "nein", "nein"),
        (f"W={ext}/wz.py; $W status", "ja", "nein"),
        (f"python3 {ext}/wz.py status", "nein", "nein"),
        (f"cd {ext} && python3 -m wz status", "nein", "nein"),
        (f"PYTHONPATH={ext} python3 -m wz schluessel", "nein", "nein"),
        (f"PYTHONPATH={ext} python3 -c 'import wz'", "nein", "nein"),
        ("python3 -m wp schluessel", "nein", "nein"),
        ("python3 -c 'import wp'", "nein", "nein"),
        ("python3 -c 'from wp import x'", "nein", "nein"),
        # Schreibweise (#74): gleiche Datei auf Dateisystem ohne Groß-/Kleinschreibung
        ("./WP.py schluessel", "nein", "nein"),
        ("python3 WP.py status", "nein", "nein"),
    ]
    gross = (repo / "WP.py").exists()
    for befehl, soll_claude, soll_team in fz:
        if "WP.py" in befehl and not gross:
            continue
        for rolle, soll in (("claude", soll_claude), ("mistral-team", soll_team), ("gemini-analyst", soll_team)):
            s, g = hook(repo, befehl, rolle)
            check(f"10: {rolle}: {befehl} → {soll}", s == soll, f"ist {s}: {g[:200]}")

print(f"{OK} ok, {FAIL} Fehler")
sys.exit(1 if FAIL else 0)
