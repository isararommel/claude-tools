#!/usr/bin/env python3
"""Tests für Paket HT (Hook-Zeitlimit fail-open schließen): interne Frist in `normen.py hook` (Ergebnis nein für
alle Rollen – auch wenn `bewerten` Exception abfängt), `onFailure: block` mit knappem `timeout` am PreToolUse-Hook der
Vorlage, überlange Wörter/Pfade (ENAMETOOLONG) ohne Hook-Fehler und Laufzeit, die mit der Größe einer geprüften
Skriptdatei nicht mehr quadratisch wächst. Vom Orchestrator als Abnahme geschrieben (vor der Umsetzung rot)."""
import json
import os
import subprocess
import sys
import tempfile
import time
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


def hook(repo, tool, eingabe, rolle="claude"):
    """(Entscheidung, Grund) des Hooks (Werkzeug claude: fragen bleibt fragen)."""
    data = {"tool_name": tool, "tool_input": eingabe, "cwd": str(repo)}
    r = sh(sys.executable, "normen/normen.py", "hook", "--rolle", rolle, "--werkzeug", "claude", cwd=repo,
           eingabe=json.dumps(data))
    if not r.stdout.strip():
        return "ja", r.stderr
    d = json.loads(r.stdout)["hookSpecificOutput"]
    return {"deny": "nein", "ask": "fragen"}[d["permissionDecision"]], d["permissionDecisionReason"]


# ---------------------------------------------------------------- Vorlage: PreToolUse sperrt bei Zeitüberschreitung/Fehler
einst = json.loads((VORLAGE / "projekt" / ".claude" / "settings.json").read_text(encoding="utf-8"))
pre = [h for e in einst["hooks"]["PreToolUse"] for h in e["hooks"]]
check("PreToolUse-Hook vorhanden", len(pre) == 1, str(pre))
for h in pre:
    check("PreToolUse onFailure block", h.get("onFailure") == "block", str(h))
    check("PreToolUse timeout knapp (≤ 60 s)", isinstance(h.get("timeout"), int) and h["timeout"] <= 60, str(h))

# Bestehendes Projekt (v19-Hook ohne timeout/onFailure, eigener Stop-Hook-Wert): einrichten ergänzt die fehlenden Felder
with tempfile.TemporaryDirectory() as t:
    alt = Path(t) / "alt"
    (alt / ".claude").mkdir(parents=True)
    sh("git", "init", "-q", cwd=alt)
    befehl = 'python3 "$CLAUDE_PROJECT_DIR/normen/normen.py" hook --rolle claude --werkzeug claude'
    (alt / ".claude" / "settings.json").write_text(json.dumps({"hooks": {"PreToolUse": [
        {"matcher": "Bash", "hooks": [{"type": "command", "command": befehl}]}]}}), encoding="utf-8")
    r = sh("bash", str(VORLAGE / "einrichten.sh"), str(alt), "--test", "make test")
    check("einrichten (Projekt mit v19-Hook)", r.returncode == 0, r.stdout[-300:] + r.stderr[-300:])
    neu = json.loads((alt / ".claude" / "settings.json").read_text(encoding="utf-8"))
    treffer = [h for e in neu["hooks"]["PreToolUse"] for h in e["hooks"] if h.get("command") == befehl]
    check("v19-Hook genau einmal", len(treffer) == 1, str(neu["hooks"]["PreToolUse"]))
    check("v19-Hook ergänzt: onFailure block", all(h.get("onFailure") == "block" for h in treffer), str(treffer))
    check("v19-Hook ergänzt: timeout", all(h.get("timeout") == pre[0].get("timeout") for h in treffer), str(treffer))

# Eigener Wert eines Projekts (timeout 45) bleibt beim Ergänzen erhalten (Review HT, Mistral Nr. 5a)
with tempfile.TemporaryDirectory() as t:
    eigen = Path(t) / "eigen"
    (eigen / ".claude").mkdir(parents=True)
    sh("git", "init", "-q", cwd=eigen)
    (eigen / ".claude" / "settings.json").write_text(json.dumps({"hooks": {"PreToolUse": [
        {"matcher": "Bash", "hooks": [{"type": "command", "command": befehl, "timeout": 45}]}]}}), encoding="utf-8")
    sh("bash", str(VORLAGE / "einrichten.sh"), str(eigen), "--test", "make test")
    neu = json.loads((eigen / ".claude" / "settings.json").read_text(encoding="utf-8"))
    treffer = [h for e in neu["hooks"]["PreToolUse"] for h in e["hooks"] if h.get("command") == befehl]
    check("eigenes timeout bleibt", [h.get("timeout") for h in treffer] == [45], str(treffer))
    check("eigenes timeout: onFailure ergänzt", all(h.get("onFailure") == "block" for h in treffer), str(treffer))

with tempfile.TemporaryDirectory() as t, tempfile.TemporaryDirectory() as skripte:
    repo = Path(t) / "projekt"
    repo.mkdir()
    sh("git", "init", "-q", cwd=repo)
    (repo / "Makefile").write_text("test:\n\techo ok\n")
    r = sh("bash", str(VORLAGE / "einrichten.sh"), str(repo), "--test", "make test")
    check("einrichten", r.returncode == 0, r.stdout + r.stderr)
    sh("git", "add", "-A", cwd=repo)
    sh("git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "start", "--no-verify", cwd=repo)
    sh("git", "checkout", "-q", "-b", "arbeit", cwd=repo)

    # Frist größer als der Abbruch, kleiner als das timeout der Vorlage (sonst bricht Claude Code vorher ab)
    code = ("import ast, sys; sys.path.insert(0, 'normen'); import normen; print(normen.FRIST_S)")
    r = sh(sys.executable, "-c", code, cwd=repo)
    frist = int(r.stdout.strip()) if r.stdout.strip().isdigit() else None
    check("FRIST_S vorhanden", frist is not None, r.stdout + r.stderr)
    if frist is not None:
        check("FRIST_S kleiner als timeout", all(frist < h.get("timeout", 0) for h in pre), f"{frist} {pre}")
        check("FRIST_S kleiner als Vibe-Standard 60 s", frist < 60, str(frist))

    # ------------------------------------------------------------ Frist: langsames bewerten → nein (alle Rollen)
    LANGSAM = r"""
import argparse, io, json, signal, sys, time
sys.path.insert(0, 'normen')
import normen
normen.FRIST_S = 1
def langsam(*a, **k):
    try:
        time.sleep(6)
    except Exception:  # normen-ausnahme: N08-KEINE-ALTLASTEN – Attrappe: eine Frist, die von Exception erbt, würde hier verschluckt
        pass
    return 'ja', []
normen.bewerten = langsam
sys.stdin = io.StringIO(json.dumps({'tool_name': 'Bash', 'tool_input': {'command': 'ls'}, 'cwd': '.'}))
normen.cmd_hook(argparse.Namespace(rolle=sys.argv[1], werkzeug=sys.argv[2]))
print('REST-ALARM', signal.alarm(0))
"""
    for rolle, werkzeug, soll in (("claude", "claude", '"deny"'), ("mistral-team", "vibe", '"deny"')):
        t0 = time.monotonic()
        r = sh(sys.executable, "-c", LANGSAM, rolle, werkzeug, cwd=repo)
        dauer = time.monotonic() - t0
        check(f"Frist {werkzeug}: Entscheidung {soll}", soll in r.stdout, r.stdout[-300:] + r.stderr[-300:])
        check(f"Frist {werkzeug}: Grund nennt die Frist", "Frist" in r.stdout, r.stdout[-300:])
        check(f"Frist {werkzeug}: abgebrochen statt ausgesessen", dauer < 5, f"{dauer:.1f}s")
        check(f"Frist {werkzeug}: Alarm danach gelöscht", "REST-ALARM 0" in r.stdout, r.stdout[-200:])

    # Andere Ausnahme in bewerten: gesperrt (wie bisher) und Alarm danach gelöscht (Review HT, Mistral Nr. 5c)
    KAPUTT = LANGSAM.replace("time.sleep(6)", "raise ValueError('kaputt')").replace(
        "    except Exception:", "    except KeyError:")
    r = sh(sys.executable, "-c", KAPUTT, "claude", "claude", cwd=repo)
    check("andere Ausnahme: gesperrt", '"deny"' in r.stdout and "ValueError" in r.stdout, r.stdout[-300:] + r.stderr[-300:])
    check("andere Ausnahme: Alarm danach gelöscht", "REST-ALARM 0" in r.stdout, r.stdout[-200:])

    # ------------------------------------------------------------ ENAMETOOLONG: kein Hook-Fehler, Geheimnis-Muster greift
    for n in (300, 1100, 5000):
        w = "a" * n
        for name, tool, ein, soll in (
                (f"echo {n}", "Bash", {"command": f"echo {w}"}, "ja"),
                (f"echo zitiert {n}", "Bash", {"command": f"echo '{w}' | wc -c"}, "ja"),
                (f"Heredoc {n}", "Bash", {"command": f"cat <<'E'\n{w}\nE"}, "ja"),
                (f"Geheimnis mit / {n}", "Bash", {"command": f"cat x/{w}.secret"}, "nein"),
                (f"Write langer Pfad {n}", "Write", {"file_path": f"x/{w}", "content": "1"}, "ja")):  # Projektpfad wie jeder andere
            stufe, grund = hook(repo, tool, ein)
            check(f"{name}: kein Hook-Fehler", "fehlerhaft" not in grund, grund[:300])
            if soll:
                check(f"{name} → {soll}", stufe == soll and (soll != "nein" or "N03" in grund), f"({stufe}) {grund[:300]}")

    # ------------------------------------------------------------ Laufzeit wächst mit der Skriptgröße nicht quadratisch
    # (gemessen 26.11.: v19 300→1200 Zeilen Faktor 14, linear wäre 4; Grenze 8 lässt Spielraum für Messrauschen)
    dauern = {}
    for n in (300, 1200):
        s = Path(skripte) / f"s{n}.sh"
        s.write_text("".join(f'echo "zeile {i}" | grep -c zeile; x{i}=$(date +%s)\n' for i in range(n)), encoding="utf-8")
        laeufe = []
        for _ in range(3):  # Minimum aus drei Läufen: robust gegen Last auf dem Rechner (Stop-Hook)
            t0 = time.monotonic()
            stufe, grund = hook(repo, "Bash", {"command": f"bash -n {s}"})
            laeufe.append(time.monotonic() - t0)
        dauern[n] = min(laeufe)
        check(f"Skript {n} Zeilen → ja", stufe == "ja", f"({stufe}) {grund[:300]}")
    check("Skript 4× länger: Dauer < 8×", dauern[1200] < 8 * dauern[300], f"{dauern}")

print(f"test_hook_frist: {OK} ok, {FAIL} fehlgeschlagen")
sys.exit(1 if FAIL else 0)
