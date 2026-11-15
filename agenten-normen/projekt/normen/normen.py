#!/usr/bin/env python3
"""Agenten-Normen: prüfen, durchsetzen, erklären. Nur Standardbibliothek, Python ≥ 3.11.

  python3 normen/normen.py pruefen [--diff [BASIS] | --staged] [--nur-melden]
  python3 normen/normen.py hook --rolle ROLLE --werkzeug claude|vibe|gemini   (stdin: JSON des Werkzeugs)
  python3 normen/normen.py stop --werkzeug claude                             (Claude-Stop-Hook: Test + Diff-Prüfung)
  python3 normen/normen.py auftrag --rolle ROLLE [--dateien PFAD …] | --ende  (Pflichtsätze; .normen-auftrag schreiben/entfernen)
  python3 normen/normen.py merge PR                                            (PR nach main – nur mit grünem Prüftor)
  python3 normen/normen.py aktualisieren [--quelle PFAD]                      (Normen aus der Quelle neu einspielen)
  python3 normen/normen.py melden --art ART --titel TITEL --text-datei PFAD    (Rückmeldung als Issue, privat)
  python3 normen/normen.py kurz | sync

Regelwerk: normen.toml · Rollen: rollen.toml · Projektwerte: projekt.toml (alle neben diesem Skript).
"""
import argparse
import fnmatch
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import time
import tomllib
from pathlib import Path

HIER = Path(__file__).resolve().parent
ROOT = HIER.parent
AUFTRAG = ROOT / ".normen-auftrag"
MARKE_ANFANG = "<!-- normen:anfang (erzeugt von normen/normen.py sync – nicht von Hand ändern) -->"
MARKE_ENDE = "<!-- normen:ende -->"
RANG = {"ja": 0, "fragen": 1, "nein": 2}
# Schreiben hier braucht die Fähigkeit „einstellungen“ (Regeln dürfen sich nicht selbst aufweichen).
GESCHUETZT = ["normen/", ".normen-auftrag", ".claude/", ".vibe/", ".gemini/", ".githooks/", "AGENTS.md", "CLAUDE.md", "GEMINI.md"]


# ---------------------------------------------------------------- Laden
def inhaberin(cfg: dict) -> str:
    """Anzeigename aus projekt.toml [projekt].inhaberin; leer → „die Inhaberin“."""
    return cfg["projekt"].get("projekt", {}).get("inhaberin") or "die Inhaberin"


def _platzhalter(obj, name: str):
    """{inhaberin} in allen Texten (auch in Listen/Tabellen) durch den Anzeigenamen ersetzen."""
    if isinstance(obj, str):
        return obj.replace("{inhaberin}", name)
    if isinstance(obj, list):
        return [_platzhalter(v, name) for v in obj]
    if isinstance(obj, dict):
        return {k: _platzhalter(v, name) for k, v in obj.items()}
    return obj


def laden() -> dict:
    p = tomllib.loads((HIER / "projekt.toml").read_text(encoding="utf-8"))
    name = p.get("projekt", {}).get("inhaberin") or "die Inhaberin"
    n = _platzhalter(tomllib.loads((HIER / "normen.toml").read_text(encoding="utf-8")), name)
    r = _platzhalter(tomllib.loads((HIER / "rollen.toml").read_text(encoding="utf-8")), name)
    rollen = r["rollen"]
    for name, abw in p.get("rollen", {}).items():
        ziel = rollen.setdefault(name, {"art": "agent", "faehigkeiten": {}})
        ziel.setdefault("faehigkeiten", {}).update(abw.get("faehigkeiten", {}))
        for k, v in abw.items():
            if k != "faehigkeiten":
                ziel[k] = v
    for norm in n["norm"]:
        for m in norm.get("muster", []):
            m["_rx"] = re.compile(m["regex"], re.MULTILINE)
            if "ausser_regex" in m:
                m["_ausser"] = re.compile(m["ausser_regex"])
            m.setdefault("schwere", "fehler" if norm["stufe"] == "muss" else "hinweis")
    return {"normen": n["norm"], "meta": n["meta"], "rollen": rollen, "projekt": p}


def passt(rel: str, muster: str) -> bool:
    rel = rel.replace(os.sep, "/")
    if fnmatch.fnmatchcase(rel, muster):
        return True
    if muster.startswith("**/") and fnmatch.fnmatchcase(rel, muster[3:]):
        return True
    return "/" not in muster and fnmatch.fnmatchcase(rel.rsplit("/", 1)[-1], muster)


def darf(cfg: dict, rolle: str, faehigkeit: str) -> str:
    r = cfg["rollen"].get(rolle)
    if r is None:
        return "nein"
    return r.get("faehigkeiten", {}).get(faehigkeit, "nein")


# ---------------------------------------------------------------- Hook
def _sammeln(obj, schluessel: set[str], aus: list):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in schluessel and isinstance(v, str):
                aus.append(v)
            elif k in schluessel and isinstance(v, list):
                aus.extend(x for x in v if isinstance(x, str))
            else:
                _sammeln(v, schluessel, aus)
    elif isinstance(obj, list):
        for v in obj:
            _sammeln(v, schluessel, aus)


def _art(tool: str, befehle: list) -> str:
    t = tool.lower()
    if befehle or re.search(r"bash|shell|command|terminal", t):
        return "befehl"
    if re.search(r"write|edit|replace|create|notebook|patch|move|delete|rename|save", t):
        return "schreiben"
    return "lesen"


def _rel(pfad: str, cwd: str) -> str | None:
    p = Path(os.path.expanduser(pfad))
    p = (Path(cwd) / p) if not p.is_absolute() else p
    p = Path(os.path.realpath(p))  # Symlinks auflösen wie bei ROOT (macOS: /var → /private/var)
    try:
        return p.relative_to(ROOT).as_posix()
    except ValueError:
        return None


def _branch(cwd: str) -> str:
    try:
        return subprocess.run(["git", "-C", cwd, "rev-parse", "--abbrev-ref", "HEAD"],
                              capture_output=True, text=True, timeout=5).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def _lauf_ordner(cfg) -> list[Path]:
    aus = []
    for o in cfg["projekt"].get("pfade", {}).get("lauf_ordner", []):
        e = os.path.expandvars(o)
        if "$" not in e:
            aus.append(Path(os.path.realpath(e)))
    return aus


def _lesbar_extern(cfg) -> list[Path]:
    """[pfade].lesbar_extern ohne die Ordner, in denen dieses Projekt selbst liegt (dort darf es schreiben)."""
    aus = []
    for o in cfg["projekt"].get("pfade", {}).get("lesbar_extern", []):
        q = Path(os.path.realpath(os.path.expanduser(os.path.expandvars(o))))
        if q != ROOT and q not in ROOT.parents:
            aus.append(q)
    return aus


# Befehlsketten in Einzelbefehle trennen (für Ausnahmen je Teilbefehl).
SEGMENT = re.compile(r"&&|\|\||[;|&\n]")


def _loeschbar(cfg) -> list[tuple[Path, bool]]:
    """[pfade].loeschbar als (Pfad, Ordner selbst löschbar). Relativ zum Projekt: Ordner samt Inhalt;
    absolut (Temp-Wurzeln, Umgebungsvariablen erlaubt): nur der Inhalt."""
    aus = []
    for o in cfg["projekt"].get("pfade", {}).get("loeschbar", []):
        e = os.path.expandvars(o)
        if "$" in e or not e.strip("/"):
            continue
        relativ = not os.path.isabs(e)
        pfad = Path(os.path.realpath(ROOT / e if relativ else e))
        if pfad != ROOT:
            aus.append((pfad, relativ))
    return aus


def _wiederherstellbar(ziel: Path) -> bool:
    """Ziel liegt im Projekt und lässt sich aus git zurückholen: fehlt schon, oder ist getrackt ohne
    uncommittete, untracked oder ignorierte Inhalte (bei Ordnern für alles darunter)."""
    if not os.path.lexists(ziel):
        return True
    rel = ziel.relative_to(ROOT).as_posix()
    try:
        getrackt = _git("ls-files", "--", rel).strip()
        offen = _git("status", "--porcelain", "--ignored", "--untracked-files=all", "--", rel).strip()
    except (OSError, subprocess.CalledProcessError):
        return False
    return bool(getrackt) and not offen


def _rm_bewerten(seg: str, cfg, cwd: str, rinfo: dict) -> str | None:
    """Einfaches rm/git rm: "frei" (alle Ziele in [pfade].loeschbar oder – bei Rollen mit
    loeschen_wiederherstellbar – getrackt und unverändert), "committen" (im Projekt, aber nicht
    wiederherstellbar) oder None (sonst: normale Regel)."""
    try:
        w = shlex.split(re.sub(r"\$\{(\w+):\?\}", r"${\1}", seg))
    except ValueError:
        return None
    if w[:2] == ["git", "rm"]:
        w = w[1:]
    elif not w or w[0] not in ("rm", "/bin/rm"):
        return None
    ziele = [x for x in w[1:] if not x.startswith("-")]
    erlaubt = _loeschbar(cfg)
    if not ziele:
        return None
    ergebnis = "frei"
    for z in ziele:
        z = os.path.expandvars(os.path.expanduser(z))
        if re.search(r"[$`*?\[]", z):
            return None  # unaufgelöste Variable oder Glob: lieber fragen
        ziel = Path(os.path.realpath(Path(cwd) / z))
        im_projekt = ziel == ROOT or ROOT in ziel.parents
        # Im Projekt zählen nur die relativen Einträge (sonst wäre ein Projekt unter $TMPDIR ganz löschbar).
        if any((relativ or not im_projekt) and (o in ziel.parents or (relativ and ziel == o)) for o, relativ in erlaubt):
            continue
        if not (rinfo.get("loeschen_wiederherstellbar") and ROOT in ziel.parents) \
                or ziel.relative_to(ROOT).parts[0] == ".git":
            return None  # außerhalb, Projekt selbst, .git oder Rolle ohne Lockerung
        if not _wiederherstellbar(ziel):
            ergebnis = "committen"
    return ergebnis


TEXT_HEREDOC = re.compile(r"\b(git\s+(-C\s+\S+\s+)?commit|gh\s+(pr|issue)\s+(create|comment|edit|review))\b[^\n]*<<-?\s*['\"]?(\w+)['\"]?")
TEXT_ARG = re.compile(r"""(\s(-m|--message|--title|--body|-b|-t)[\s=]+)("(?:[^"\\]|\\.)*"|'[^']*')""")


def _ohne_textdaten(cmd: str) -> str:
    """Entfernt reinen Text (Commit-Nachrichten, PR-/Issue-Texte), damit Wörter darin nicht als Befehle gelten."""
    if not re.search(r"\bgit\b[^\n]*\bcommit\b|\bgh\s+(pr|issue)\b", cmd):
        return cmd
    zeilen, aus, ende = cmd.split("\n"), [], None
    for z in zeilen:
        if ende is not None:
            if z.strip() == ende:
                ende = None
                aus.append(z)
            continue
        m = TEXT_HEREDOC.search(z)
        if m:
            ende = m.group(5)
        aus.append(TEXT_ARG.sub(lambda t: t.group(1) + '""', z))
    return "\n".join(aus)


def _rolle_frei(rinfo: dict, ziel: Path) -> bool:
    """Ziel liegt in [rollen.X].frei_schreiben (Globs, ~ und Umgebungsvariablen erlaubt)."""
    for g in rinfo.get("frei_schreiben", []):
        e = os.path.expandvars(os.path.expanduser(g))
        if "$" in e:
            continue
        e = os.path.realpath(e) if not re.search(r"[*?\[]", e) else e
        if fnmatch.fnmatchcase(str(ziel), e) or fnmatch.fnmatchcase(str(ziel), e.rstrip("/") + "/*"):
            return True
    return False


def _befehl_trifft(m: dict, cmd: str, cfg, cwd: str, rinfo: dict) -> str | None:
    """None: Muster trifft nicht (oder jeder treffende Teilbefehl ist ausgenommen); "trifft": normale Regel;
    "committen": nur Löschen im Projekt, das erst nach einem Commit wiederherstellbar wäre."""
    if not m["_rx"].search(cmd):
        return None
    if "_ausser" not in m and not m.get("loeschbar_ausnehmen"):
        return "trifft"
    treffer = [t for t in SEGMENT.split(cmd) if m["_rx"].search(t)]
    if not treffer:
        return "trifft"  # Treffer über Teilbefehle hinweg: nicht ausnehmen
    ergebnis = None
    for t in treffer:
        if "_ausser" in m and m["_ausser"].search(t):
            continue
        r = _rm_bewerten(t.strip(), cfg, cwd, rinfo) if m.get("loeschbar_ausnehmen") else None
        if r is None:
            return "trifft"
        if r == "committen":
            ergebnis = "committen"
    return ergebnis


def _auftrag_globs() -> list[str] | None:
    if not AUFTRAG.exists():
        return None
    return [z.strip() for z in AUFTRAG.read_text(encoding="utf-8").splitlines() if z.strip() and not z.startswith("#")]


def bewerten(cfg: dict, rolle: str, tool: str, eingabe: dict, cwd: str) -> tuple[str, list[str]]:
    """Liefert (ja|fragen|nein, Gründe)."""
    pf = cfg["projekt"].get("pfade", {})
    rinfo = cfg["rollen"].get(rolle, {})
    befehle: list[str] = []
    pfade: list[str] = []
    _sammeln(eingabe, {"command", "cmd", "script"}, befehle)
    befehle = [_ohne_textdaten(c) for c in befehle]
    _sammeln(eingabe, {"file_path", "path", "absolute_path", "filePath", "notebook_path", "paths", "target_file", "file"}, pfade)
    art = _art(tool, befehle)
    gruende: list[tuple[str, str]] = []

    def pruefe(faehigkeit: str, text: str):
        e = darf(cfg, rolle, faehigkeit)
        if e != "ja":
            gruende.append((e, f"{text} [Fähigkeit {faehigkeit}: {e} für Rolle {rolle}]"))

    for cmd in befehle:
        if rinfo.get("auftrag_pflicht") and "normen-auftrag" in cmd:
            # Teams dürfen ihre Auftragsliste (und deren Prüfsumme) weder schreiben noch per Shell verändern.
            gruende.append(("nein", "N06-NUR-ERLAUBTE-PFADE: .normen-auftrag vergibt nur Claude"))
        for norm in cfg["normen"]:
            for m in norm.get("muster", []):
                if m["ziel"] != "befehl":
                    continue
                t = _befehl_trifft(m, cmd, cfg, cwd, rinfo)
                if t == "trifft":
                    pruefe(m.get("faehigkeit", "loeschen"), f"{norm['id']}: {m['meldung']}")
                elif t == "committen":  # keine Rückfrage: erst sichern, dann löschen
                    gruende.append(("nein", f"{norm['id']}: Ziel ist untracked oder geändert – erst committen "
                                            "(dann wiederherstellbar), danach erneut löschen."))
        if re.search(r"\bgit\s+(-C\s+\S+\s+|-c\s+\S+\s+)*(commit|push|merge|rebase|cherry-pick|revert|am)\b", cmd) \
                and _branch(cwd) in ("main", "master"):
            pruefe("main", "N11-ARBEITSZWEIG: aktueller Branch ist main – erst eigenen Branch anlegen")
        for wort in re.split(r"[\s;&|<>()'\"`=]+", cmd):
            if not wort:
                continue
            name = wort.rstrip("/").rsplit("/", 1)[-1]
            ist_datei = "/" in wort or (Path(cwd) / os.path.expanduser(wort)).exists()
            if ist_datei and any(fnmatch.fnmatchcase(name, g) for g in pf.get("geheimnisse", [])):
                pruefe("geheimnisse-lesen", f"N03-KEINE-GEHEIMNISSE: Befehl berührt {name}")
        for s in pf.get("gesperrt", []):
            if s and s in cmd:
                pruefe("sperrpfade-lesen", f"N06-NUR-ERLAUBTE-PFADE: gesperrter Pfad {s}")

    for p in pfade:
        rel = _rel(p, cwd)
        name = Path(p).name
        if any(fnmatch.fnmatchcase(name, g) for g in pf.get("geheimnisse", [])):
            pruefe("geheimnisse-lesen", f"N03-KEINE-GEHEIMNISSE: {name}")
        if rel is not None and any(rel.startswith(s) for s in pf.get("gesperrt", []) if s):
            pruefe("sperrpfade-lesen", f"N06-NUR-ERLAUBTE-PFADE: gesperrter Pfad {rel}")
        if art != "schreiben":
            continue
        if rel is None:
            ziel = Path(os.path.realpath(Path(cwd) / os.path.expanduser(p)))
            # [pfade].lesbar_extern (z. B. claude-tools): lesen ja, schreiben nie – außer aus diesem Projekt selbst.
            if any(ziel == q or q in ziel.parents for q in _lesbar_extern(cfg)):
                gruende.append(("nein", f"N06-NUR-ERLAUBTE-PFADE: {ziel} liegt in [pfade].lesbar_extern – nur lesen"))
            elif not any(ziel == o or o in ziel.parents for o in _lauf_ordner(cfg)) and not _rolle_frei(rinfo, ziel):
                pruefe("ausserhalb-schreiben", f"N06-NUR-ERLAUBTE-PFADE: außerhalb des Projekts: {ziel}")
            continue
        pruefe("schreiben", f"N06-NUR-ERLAUBTE-PFADE: {rel}")
        if any(rel == s.rstrip("/") or rel.startswith(s) for s in GESCHUETZT):
            pruefe("einstellungen", f"N10-KEIN-COMMIT-DURCH-TEAMS: Normen/Agenten-Einstellungen {rel}")
        if rinfo.get("auftrag_pflicht"):
            globs = _auftrag_globs()
            if globs is None:
                gruende.append(("nein", f"N06-NUR-ERLAUBTE-PFADE: kein .normen-auftrag – Rolle {rolle} darf nichts schreiben"))
            elif not any(passt(rel, g) for g in globs):
                gruende.append(("nein", f"N06-NUR-ERLAUBTE-PFADE: {rel} steht nicht in .normen-auftrag"))
        if (ROOT / rel).exists() and any(passt(rel, g) for g in pf.get("tests", [])):
            pruefe("tests-aendern", f"N02-TESTS-SIND-TABU: bestehender Test {rel}")

    if not gruende:
        return "ja", []
    stufe = max((g[0] for g in gruende), key=lambda x: RANG[x])
    return stufe, [g[1] for g in gruende]


def cmd_hook(a) -> int:
    try:
        cfg = laden()
        roh = sys.stdin.read()
        data = json.loads(roh) if roh.strip() else {}
        tool = str(data.get("tool_name") or data.get("tool") or data.get("name") or "")
        eingabe = data.get("tool_input") or data.get("arguments") or data.get("args") or data.get("input") or data
        if isinstance(eingabe, str):
            try:
                eingabe = json.loads(eingabe)
            except json.JSONDecodeError:
                eingabe = {"command": eingabe}
        entscheid, gruende = bewerten(cfg, a.rolle, tool, eingabe, str(data.get("cwd") or os.getcwd()))
    except Exception as e:  # normen-ausnahme: N08-KEINE-ALTLASTEN – Hook muss bei jedem Fehler sperren (fail-closed)
        entscheid, gruende = "nein", [f"Normen-Hook fehlerhaft ({type(e).__name__}: {e}) – gesperrt"]
    if a.werkzeug != "claude" and entscheid == "fragen":
        entscheid = "nein"
    if entscheid == "ja":
        return 0
    grund = "Agenten-Normen: " + "; ".join(gruende) + (f" – bitte {inhaberin(cfg)} fragen." if entscheid == "fragen" else
                                                     " – nicht ausführen, im Bericht melden.")
    if a.werkzeug == "claude":
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                                 "permissionDecision": "ask" if entscheid == "fragen" else "deny",
                                                 "permissionDecisionReason": grund}}, ensure_ascii=False))
        return 0
    print(json.dumps({"decision": "deny", "reason": grund}, ensure_ascii=False))
    print(grund, file=sys.stderr)
    return 2 if a.werkzeug == "gemini" else 0


# ---------------------------------------------------------------- Prüfen
def _git(*args) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=True).stdout


def _alle_dateien() -> list[str]:
    try:
        return [z for z in _git("ls-files", "-co", "--exclude-standard").splitlines() if z]
    except (OSError, subprocess.CalledProcessError):
        return [p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*") if p.is_file()]


def _diff(basis: str | None, staged: bool) -> tuple[dict[str, set[int] | None], dict[str, tuple[int, int]]]:
    """Geänderte Dateien → hinzugefügte Zeilennummern (None = ganze Datei neu/untracked); dazu numstat."""
    args = ["diff", "--unified=0", "--no-color", "--no-ext-diff"] + (["--cached"] if staged else [basis or "HEAD"])
    geaendert: dict[str, set[int] | None] = {}
    datei = None
    for z in _git(*args).splitlines():
        if z.startswith("+++ "):
            datei = None if z[4:] == "/dev/null" else z[6:]
            if datei:
                geaendert.setdefault(datei, set())
        elif z.startswith("@@") and datei:
            m = re.search(r"\+(\d+)(?:,(\d+))?", z)
            start, anz = int(m.group(1)), int(m.group(2) or 1)
            geaendert[datei].update(range(start, start + anz))
    stat = {}
    for z in _git(*(["diff", "--numstat"] + (["--cached"] if staged else [basis or "HEAD"]))).splitlines():
        teile = z.split("\t")
        if len(teile) == 3:
            stat[teile[2]] = (int(teile[0]) if teile[0] != "-" else 0, int(teile[1]) if teile[1] != "-" else 0)
    if not staged:
        for f in _git("ls-files", "-o", "--exclude-standard").splitlines():
            if f:
                geaendert[f] = None
                try:
                    stat[f] = (len((ROOT / f).read_text(encoding="utf-8").splitlines()), 0)
                except (OSError, UnicodeDecodeError):
                    stat[f] = (0, 0)
    for z in _git(*(["diff", "--name-status"] + (["--cached"] if staged else [basis or "HEAD"]))).splitlines():
        if z.startswith("D\t"):
            geaendert.setdefault(z[2:], set())
    return geaendert, stat


def erzeugt_kurz(cfg: dict) -> str:
    meta, pj = cfg["meta"], cfg["projekt"]
    z = [f"# Agenten-Normen (Kurzfassung, v{meta['version']}, Stand {meta['stand']})", "",
         "Gilt für alle Agenten in diesem Projekt (Claude Code, Mistral Vibe, Antigravity/Gemini, lokale Modelle). "
         "Volltext mit Begründungen und Quellen: `normen/normen.toml`; Zuständigkeiten: `normen/rollen.toml`; "
         "Projektwerte: `normen/projekt.toml`. Bei Widerspruch gilt die strengere Regel.", ""]
    for stufe, titel in (("muss", "Muss (technisch durchgesetzt, soweit möglich)"), ("soll", "Soll")):
        z += [f"## {titel}"]
        for n in cfg["normen"]:
            if n["stufe"] == stufe:
                z.append(f"- **{n['id']} – {n['titel']}:** {n['prompt']}")
        z.append("")
    z += ["## Rollen", "", "| Rolle | darf | nur mit Rückfrage | verantwortet |", "|---|---|---|---|"]
    for name, r in cfg["rollen"].items():
        f = r.get("faehigkeiten", {})
        ja = ", ".join(k for k, v in f.items() if v == "ja") or "–"
        fr = ", ".join(k for k, v in f.items() if v == "fragen") or "–"
        zusatz = " (nur Pfade aus .normen-auftrag)" if r.get("auftrag_pflicht") else ""
        z.append(f"| {name} | {ja}{zusatz} | {fr} | {'; '.join(r.get('verantwortet', []))} |")
    gesperrt = ", ".join(f"`{s}`" for s in pj.get("pfade", {}).get("gesperrt", [])) or "–"
    z += ["", "## Durchsetzung",
          f"- Testbefehl: `{pj['projekt']['testbefehl']}`; vor jeder Abgabe zusätzlich `python3 normen/normen.py pruefen --diff`.",
          "- Hooks (Claude Code, Vibe) sperren Verstöße vor der Ausführung; der Claude-Stop-Hook prüft Tests und Diff.",
          f"- Gesperrte Pfade (nicht an externe Teams): {gesperrt}.",
          f"- Begründete Ausnahme im Code: `{meta['ausnahme_marker']} <ID> – Begründung` (Zeile davor oder dieselbe).",
          "- Aufträge an Teams: Pflichtsätze mit `python3 normen/normen.py auftrag --rolle <rolle> --dateien …` erzeugen.", ""]
    return "\n".join(z)


def _agents_block(cfg) -> str:
    return f"{MARKE_ANFANG}\n{erzeugt_kurz(cfg)}{MARKE_ENDE}\n"


def _sync_soll(cfg) -> dict[Path, str]:
    agents = ROOT / "AGENTS.md"
    alt = agents.read_text(encoding="utf-8") if agents.exists() else ""
    block = _agents_block(cfg)
    if MARKE_ANFANG in alt and MARKE_ENDE in alt:
        a, rest = alt.split(MARKE_ANFANG, 1)
        danach = rest.split(MARKE_ENDE, 1)[1].lstrip("\n")
        neu = a + block + ("\n" + danach if danach else "")
    else:
        neu = block + ("\n" + alt if alt else "")
    return {HIER / "kurz.md": erzeugt_kurz(cfg), agents: neu}


def pruefen(cfg, diff: bool, basis: str | None, staged: bool) -> tuple[int, int, int, list[str]]:
    pj = cfg["projekt"]
    aus = pj.get("pruefen", {}).get("ausschliessen", [])
    marker = cfg["meta"]["ausnahme_marker"]
    zeilen_out: list[str] = []
    fehler = hinweise = ausnahmen = 0

    def melde(ort, nid, schwere, text):
        nonlocal fehler, hinweise
        zeilen_out.append(f"{ort} [{nid}] {schwere}: {text}")
        if schwere == "fehler":
            fehler += 1
        else:
            hinweise += 1

    if diff or staged:
        geaendert, stat = _diff(basis, staged)
    else:
        geaendert, stat = {f: None for f in _alle_dateien()}, {}

    for rel in sorted(geaendert):
        if any(rel.startswith(x) for x in aus):
            continue
        pfad = ROOT / rel
        name = pfad.name
        neu_zeilen = geaendert[rel]
        if not pfad.exists():
            continue
        try:
            text = pfad.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            text = None
        zeilen = text.splitlines() if text is not None else []
        for norm in cfg["normen"]:
            for m in norm.get("muster", []):
                ziel = m["ziel"]
                if ziel == "befehl" or (m.get("nur_diff") and not (diff or staged)):
                    continue
                if any(rel.startswith(x) for x in m.get("ausser", [])):
                    continue
                if ziel == "dateiname":
                    if m["_rx"].search(name):
                        melde(rel, norm["id"], m["schwere"], m["meldung"])
                    continue
                if text is None or not any(passt(rel, g) for g in m.get("dateien", ["*"])):
                    continue
                if ziel == "fehlt":
                    if zeilen and zeilen[0].startswith("#!") and "bash" in zeilen[0] and not m["_rx"].search(text) \
                            and not any(f"{marker} {norm['id']}" in z for z in zeilen[:5]):
                        melde(rel, norm["id"], m["schwere"], m["meldung"])
                    continue
                for i, z in enumerate(zeilen, 1):
                    if neu_zeilen is not None and i not in neu_zeilen:
                        continue
                    if not m["_rx"].search(z.split(marker)[0]):  # Begründungstext im Marker zählt nicht
                        continue
                    vorher = zeilen[i - 2] if i > 1 else ""
                    if f"{marker} {norm['id']}" in z or f"{marker} {norm['id']}" in vorher:
                        ausnahmen += 1
                        continue
                    melde(f"{rel}:{i}", norm["id"], m["schwere"], m["meldung"])
        if name.endswith(".py") and text is not None:
            try:
                compile(text, str(pfad), "exec")
            except (SyntaxError, ValueError) as e:
                melde(rel, "S04-KEINE-ERFUNDENEN-APIS", "fehler", f"Python übersetzt nicht: {e}")

    if diff or staged:
        tests = pj.get("pfade", {}).get("tests", [])
        for rel, nz in geaendert.items():
            if nz is not None and any(passt(rel, g) for g in tests):
                melde(rel, "N02-TESTS-SIND-TABU", "hinweis", f"Testdatei geändert – Review nötig (nur Orchestrator/{inhaberin(cfg)})")
        # Auftragsliste gilt für die Arbeit externer Teams (--diff). Commits macht nur Claude (N10) – pre-commit
        # (--staged) misst sie deshalb nicht dagegen, sonst blockiert ein laufender Auftrag Claudes eigene Commits.
        globs = None if staged else _auftrag_globs()
        if globs is not None:
            if not _siegel_ok():
                melde(".normen-auftrag", "N06-NUR-ERLAUBTE-PFADE", "fehler",
                      "seit `normen.py auftrag` verändert (Prüfsumme passt nicht) – Rechte ausgeweitet? Auftrag neu vergeben.")
            for rel in geaendert:
                if rel != ".normen-auftrag" and not any(passt(rel, g) for g in globs):
                    melde(rel, "N06-NUR-ERLAUBTE-PFADE", "fehler", "geändert, steht aber nicht in .normen-auftrag")
        dateien, zeilen_sum = len(stat), sum(a + b for a, b in stat.values())
        mx = pj.get("pruefen", {})
        if dateien > mx.get("diff_max_dateien", 10**9) or zeilen_sum > mx.get("diff_max_zeilen", 10**9):
            melde("(Diff)", "S02-MINIMALE-LOESUNG", "hinweis", f"{dateien} Dateien / {zeilen_sum} Zeilen – Umfang prüfen")

    for pfad, soll in _sync_soll(cfg).items():
        ist = pfad.read_text(encoding="utf-8") if pfad.exists() else ""
        if ist != soll:
            melde(pfad.relative_to(ROOT).as_posix(), "NORMEN", "fehler", "veraltet – `python3 normen/normen.py sync` ausführen")
    for text in _herkunft_befunde(cfg):
        melde("normen/herkunft.toml", "NORMEN", "hinweis", text)
    return fehler, hinweise, ausnahmen, zeilen_out


# ---------------------------------------------------------------- Herkunft, Aktualisieren
HERKUNFT = HIER / "herkunft.toml"
STANDARD_QUELLE = "~/Documents/Projekte/claude-tools"


def _quelle(cfg, option: str | None = None) -> Path:
    o = option or cfg["projekt"].get("quelle", {}).get("pfad") or STANDARD_QUELLE
    return Path(os.path.realpath(os.path.expanduser(os.path.expandvars(o))))


def _von_hand_geaendert(herkunft: dict) -> list[str]:
    """Eingespielte Dateien, deren Prüfsumme nicht mehr zu herkunft.toml passt."""
    aus = []
    for rel, sha in herkunft.get("dateien", {}).items():
        p = ROOT / rel
        if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest() != sha:
            aus.append(rel)
    return aus


def _quell_version(quelle: Path) -> int | None:
    t = quelle / "agenten-normen" / "projekt" / "normen" / "normen.toml"
    if not t.exists():
        return None
    return tomllib.loads(t.read_text(encoding="utf-8"))["meta"]["version"]


def _herkunft_befunde(cfg) -> list[str]:
    if not HERKUNFT.exists():
        return ["fehlt – Normen mit `einrichten.sh` bzw. `normen.py aktualisieren` einspielen"]
    h = tomllib.loads(HERKUNFT.read_text(encoding="utf-8"))
    aus = [f"{rel} seit dem Einspielen von Hand geändert (Änderungen gehören in die Quelle)" for rel in _von_hand_geaendert(h)]
    qv = _quell_version(_quelle(cfg))
    if qv is not None and qv > h["quelle"]["version"]:
        aus.append(f"Quelle hat Normen v{qv}, eingespielt ist v{h['quelle']['version']} – `normen.py aktualisieren`")
    return aus


def cmd_aktualisieren(a) -> int:
    cfg = laden()
    quelle = _quelle(cfg, a.quelle)
    skript = quelle / "agenten-normen" / "einrichten.sh"
    if not skript.exists():
        print(f"Quelle nicht gefunden: {skript} – Es wurde nichts verändert.", file=sys.stderr)
        return 1
    if HERKUNFT.exists():
        h = tomllib.loads(HERKUNFT.read_text(encoding="utf-8"))
        geaendert = _von_hand_geaendert(h)
        if geaendert:
            print("Von Hand geändert seit dem Einspielen: " + ", ".join(geaendert) +
                  f"\nÄnderungen erst in die Quelle übernehmen bzw. mit {inhaberin(cfg)} klären. Es wurde nichts verändert.",
                  file=sys.stderr)
            return 1
        print(f"Normen v{h['quelle']['version']} → v{_quell_version(quelle)} (Quelle {quelle})")
    pj = cfg["projekt"]["projekt"]
    befehl = ["bash", str(skript), str(ROOT), "--test", pj["testbefehl"], "--name", pj["name"]]
    r = subprocess.run(befehl)
    if r.returncode == 0:
        print(f"Abnahme jetzt: `{pj['testbefehl']}` und `python3 normen/normen.py pruefen --diff`.")
    return r.returncode


# ---------------------------------------------------------------- Rückmeldungen
MELDE_ARTEN = ["agent-verhalten", "zu-streng", "zu-locker", "ablauf", "fehler"]
DATENSCHUTZ = [
    ("E-Mail-Adresse", r"[\w.+-]+@[\w-]+(\.[\w-]+)+"),
    ("IBAN", r"\b[A-Z]{2}\d{2}(\s?[A-Z0-9]{4}){3,7}\b"),
    ("Telefonnummer", r"(\+\d{2}|\b0\d{2,4})[\s/-]?\d{3,}[\s/-]?\d{2,}\b"),
]


def _datenschutz_funde(cfg, text: str) -> list[str]:
    funde = []
    muster = [(f"{n['id']}", m["_rx"]) for n in cfg["normen"] if n["id"].startswith("N03")
              for m in n.get("muster", []) if m["ziel"] == "inhalt"]
    muster += [(name, re.compile(rx)) for name, rx in DATENSCHUTZ]
    for i, z in enumerate(text.splitlines(), 1):
        for name, rx in muster:
            if rx.search(z):
                funde.append(f"Zeile {i}: {name}")
        for s in cfg["projekt"].get("pfade", {}).get("gesperrt", []):
            if s and s in z:
                funde.append(f"Zeile {i}: gesperrter Pfad {s}")
    return funde


def cmd_melden(a) -> int:
    cfg = laden()
    pj = cfg["projekt"]
    repo = pj.get("rueckmeldung", {}).get("repo", "")
    text = Path(a.text_datei).read_text(encoding="utf-8")
    funde = _datenschutz_funde(cfg, a.titel + "\n" + text)
    if funde:
        print("Nicht gesendet – Text enthält möglicherweise Geheimnisse oder personenbezogene Daten:\n  " +
              "\n  ".join(funde), file=sys.stderr)
        return 1
    body = "\n".join([
        f"**Art:** {a.art}  ",
        f"**Projekt:** {ROOT.name}  ",
        f"**Normen:** v{cfg['meta']['version']}  ",
        f"**Agent/Rolle:** {a.agent or '–'}  ",
        f"**Norm:** {a.norm or '–'}  ",
        f"**Stufe:** {a.stufe or '–'}",
        "", text.strip(), "",
        "_Gesendet mit `normen.py melden`._", ""])
    ordner = ROOT / ".normen" / "rueckmeldungen"
    ordner.mkdir(parents=True, exist_ok=True)
    kopie = ordner / f"{time.strftime('%Y%m%d-%H%M%S')}-{a.art}.md"
    kopie.write_text(f"# {a.titel}\n\n{body}", encoding="utf-8")
    print(f"Lokale Kopie: {kopie.relative_to(ROOT)}")
    if a.trocken:
        print("Trocken – nichts gesendet.")
        return 0
    if not repo:
        print("Kein Ziel: [rueckmeldung].repo in normen/projekt.toml eintragen (ein PRIVATES Repository).", file=sys.stderr)
        return 1
    r = subprocess.run(["gh", "repo", "view", repo, "--json", "visibility", "-q", ".visibility"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f"Ziel {repo} nicht prüfbar: {r.stderr.strip()}", file=sys.stderr)
        return 1
    if r.stdout.strip() != "PRIVATE":
        print(f"Nicht gesendet: {repo} ist nicht privat ({r.stdout.strip()}). Rückmeldungen nur an private Repositories.",
              file=sys.stderr)
        return 1
    basis = ["gh", "issue", "create", "--repo", repo, "--title", a.titel, "--body-file", str(kopie)]
    r = subprocess.run(basis + ["--label", "rueckmeldung", "--label", f"art:{a.art}"], capture_output=True, text=True)
    if r.returncode != 0 and "label" in r.stderr.lower():
        r = subprocess.run(basis, capture_output=True, text=True)
        if r.returncode == 0:
            print("Hinweis: Labels fehlen im Ziel – Issue ohne Labels angelegt.")
    if r.returncode != 0:
        print(f"Senden fehlgeschlagen: {r.stderr.strip()} – Text liegt in {kopie.relative_to(ROOT)}.", file=sys.stderr)
        return 1
    print("Gesendet: " + r.stdout.strip())
    return 0


def cmd_pruefen(a) -> int:
    cfg = laden()
    diff = a.diff is not None
    fehler, hinweise, ausnahmen, aus = pruefen(cfg, diff, a.diff or None, a.staged)
    print("\n".join(aus + [f"— {fehler} Fehler, {hinweise} Hinweise, {ausnahmen} begründete Ausnahmen "
                           f"(Normen v{cfg['meta']['version']}, {'Diff' if diff or a.staged else 'gesamt'})"]))
    return 0 if a.nur_melden or fehler == 0 else 1


# ---------------------------------------------------------------- Stop, Auftrag, Sync
def cmd_stop(a) -> int:
    cfg = laden()
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        data = {}
    try:
        if not _git("status", "--porcelain").strip():
            return 0
    except (OSError, subprocess.CalledProcessError):
        return 0
    if AUFTRAG.exists():  # Team arbeitet noch: Zwischenstand nicht abnehmen; Abnahme nach `auftrag --ende`
        print(json.dumps({"systemMessage": "Agenten-Normen: Team-Auftrag läuft (.normen-auftrag) – Test und Diff-Prüfung "
                          "nach `normen.py auftrag --ende`."}, ensure_ascii=False))
        return 0
    probleme = []
    test = cfg["projekt"]["projekt"]["testbefehl"]
    r = subprocess.run(test, shell=True, cwd=ROOT, capture_output=True, text=True, timeout=540)  # normen-ausnahme: N09-SICHERE-MUSTER – Testbefehl aus projekt.toml
    if r.returncode != 0:
        probleme.append(f"`{test}` schlägt fehl:\n" + "\n".join((r.stdout + r.stderr).splitlines()[-25:]))
    fehler, _, _, aus = pruefen(cfg, True, "HEAD", False)
    if fehler:
        probleme.append("`normen.py pruefen --diff` meldet Fehler:\n" + "\n".join(x for x in aus if " fehler: " in x))
    if not probleme:
        return 0
    text = f"Agenten-Normen (N04): Vor dem Abschluss beheben oder {inhaberin(cfg)} den Befund melden.\n\n" + "\n\n".join(probleme)
    if data.get("stop_hook_active"):
        print(json.dumps({"systemMessage": text}, ensure_ascii=False))
        return 0
    print(json.dumps({"decision": "block", "reason": text}, ensure_ascii=False))
    return 0


def cmd_merge(a) -> int:
    """PR nach main mergen – nur mit grünem Prüftor (N11): sauberer Stand = PR-Kopf, enthält origin/main,
    Testbefehl grün, `pruefen --diff origin/<basis>` ohne Fehler. Danach lokalen main aktualisieren."""
    cfg = laden()

    def stopp(text: str) -> int:
        print(f"Nicht gemergt: {text}", file=sys.stderr)
        return 1

    if AUFTRAG.exists():
        return stopp("laufender Team-Auftrag (.normen-auftrag) – erst `python3 normen/normen.py auftrag --ende`.")
    try:
        if _git("status", "--porcelain", "--untracked-files=no").strip():
            return stopp("nicht committete Änderungen – erst committen.")
        pr = json.loads(subprocess.run(["gh", "pr", "view", str(a.pr), "--json", "state,baseRefName,headRefName,headRefOid"],
                                       cwd=ROOT, capture_output=True, text=True, check=True).stdout)
        basis = pr["baseRefName"]
        if pr["state"] != "OPEN" or basis not in ("main", "master"):
            return stopp(f"PR {a.pr} ist {pr['state']} bzw. zielt auf {basis}.")
        _git("fetch", "-q", "origin")
        kopf = _git("rev-parse", "HEAD").strip()
        if kopf != pr["headRefOid"]:
            return stopp(f"lokaler Stand {kopf[:7]} ist nicht der PR-Kopf {pr['headRefOid'][:7]} – Branch {pr['headRefName']} "
                         "auschecken bzw. pushen.")
        if subprocess.run(["git", "-C", str(ROOT), "merge-base", "--is-ancestor", f"origin/{basis}", "HEAD"]).returncode:
            return stopp(f"origin/{basis} ist nicht enthalten – erst `git merge origin/{basis}`, testen, pushen.")
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError, KeyError) as e:
        return stopp(f"Vorprüfung fehlgeschlagen ({type(e).__name__}: {e}).")
    test = cfg["projekt"]["projekt"]["testbefehl"]
    print(f"Prüftor: {test} …", flush=True)
    r = subprocess.run(test, shell=True, cwd=ROOT, capture_output=True, text=True, timeout=1200)  # normen-ausnahme: N09-SICHERE-MUSTER – Testbefehl aus projekt.toml
    if r.returncode != 0:
        return stopp(f"`{test}` schlägt fehl:\n" + "\n".join((r.stdout + r.stderr).splitlines()[-25:]))
    fehler, hinweise, _, aus = pruefen(cfg, True, f"origin/{basis}", False)
    if fehler:
        return stopp(f"`pruefen --diff origin/{basis}` meldet {fehler} Fehler:\n" + "\n".join(aus))
    print("\n".join([z for z in aus if " hinweis: " in z] + [f"Prüftor grün ({hinweise} Hinweise). Merge PR {a.pr} …"]), flush=True)
    m = subprocess.run(["gh", "pr", "merge", str(a.pr), "--merge"], cwd=ROOT, capture_output=True, text=True)
    if m.returncode != 0:
        return stopp(f"gh pr merge fehlgeschlagen:\n{m.stdout}{m.stderr}")
    try:
        _git("switch", "-q", basis)
        _git("pull", "-q", "--ff-only", "origin", basis)
    except subprocess.CalledProcessError as e:
        print(f"Gemergt, aber lokaler {basis} nicht aktualisiert: {e.stderr}", file=sys.stderr)
        return 1
    print(f"Gemergt; lokaler {basis} = {_git('log', '--oneline', '-1').strip()}")
    return 0


def _siegel() -> Path:
    """Prüfsumme der Auftragsliste – im git-Verzeichnis, also außerhalb des Arbeitsstands der Teams."""
    p = Path(_git("rev-parse", "--git-path", "normen-auftrag.sha256").strip())
    return p if p.is_absolute() else ROOT / p


def _siegel_ok() -> bool:
    try:
        return _siegel().read_text(encoding="utf-8").strip() == hashlib.sha256(AUFTRAG.read_bytes()).hexdigest()
    except (OSError, subprocess.CalledProcessError):
        return False


def cmd_auftrag(a) -> int:
    cfg = laden()
    if a.ende:
        for p in (AUFTRAG, _siegel()):
            if p.exists():
                p.unlink()
        print(".normen-auftrag entfernt.")
        return 0
    if a.rolle not in cfg["rollen"]:
        print(f"Unbekannte Rolle: {a.rolle}", file=sys.stderr)
        return 64
    if a.dateien:
        if any(re.search(r"\s", d.strip()) for d in a.dateien):
            print("Hinweis: Einträge mit Leerraum wurden an Leerraum getrennt (Pfade einzeln übergeben).", file=sys.stderr)
            a.dateien = [t for d in a.dateien for t in d.split()]
        AUFTRAG.write_text("# erlaubte Pfade (Globs) für den laufenden Auftrag – von normen.py auftrag geschrieben\n"
                           + "\n".join(a.dateien) + "\n", encoding="utf-8")
        _siegel().write_text(hashlib.sha256(AUFTRAG.read_bytes()).hexdigest() + "\n", encoding="utf-8")
    globs = _auftrag_globs() or []
    pj = cfg["projekt"]
    z = [f"Normen für diesen Auftrag (Rolle {a.rolle}, Normen v{cfg['meta']['version']}) – verbindlich:",
         "- Außerhalb des Projektordners wird ohne ausdrückliche Erlaubnis nichts gelöscht oder geändert.",
         "- Lösche niemals Dateien, die du in diesem Lauf nicht selbst angelegt hast, auch keine unbekannten oder untracked "
         "Dateien. Kein rm, kein git clean, kein git restore auf fremde Dateien.",
         "- Du darfst NUR diese Pfade ändern: " + (", ".join(f"`{g}`" for g in globs) if globs else "keine (nur lesen)."),
         "- `.normen-auftrag` nie lesen, ändern oder erweitern – nur Claude vergibt Pfade. Brauchst du eine weitere Datei: "
         "anhalten und im Bericht nennen."]
    for n in cfg["normen"]:
        z.append(f"- {n['id']}: {n['prompt']}")
    gesperrt = pj.get("pfade", {}).get("gesperrt", [])
    if gesperrt and darf(cfg, a.rolle, "sperrpfade-lesen") != "ja":
        z.append("- Diese Pfade nicht lesen und nicht öffnen: " + ", ".join(f"`{s}`" for s in gesperrt))
    z.append(f"- Abnahme: `{pj['projekt']['testbefehl']}` grün und `python3 normen/normen.py pruefen --diff` ohne Fehler – "
             "beide Befehle mit Ergebnis in den Bericht.")
    print("\n".join(z))
    return 0


def cmd_kurz(a) -> int:
    print(erzeugt_kurz(laden()), end="")
    return 0


def cmd_sync(a) -> int:
    for pfad, soll in _sync_soll(laden()).items():
        ist = pfad.read_text(encoding="utf-8") if pfad.exists() else None
        if ist != soll:
            pfad.write_text(soll, encoding="utf-8")
            print(f"aktualisiert  {pfad.relative_to(ROOT).as_posix()}")
        else:
            print(f"gleich       {pfad.relative_to(ROOT).as_posix()}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Agenten-Normen")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pruefen")
    p.add_argument("--diff", nargs="?", const="HEAD", default=None, metavar="BASIS")
    p.add_argument("--staged", action="store_true")
    p.add_argument("--nur-melden", action="store_true")
    p.set_defaults(f=cmd_pruefen)
    p = sub.add_parser("hook")
    p.add_argument("--rolle", required=True)
    p.add_argument("--werkzeug", choices=["claude", "vibe", "gemini"], required=True)
    p.set_defaults(f=cmd_hook)
    p = sub.add_parser("stop")
    p.add_argument("--werkzeug", choices=["claude"], default="claude")
    p.set_defaults(f=cmd_stop)
    p = sub.add_parser("merge", help="PR nach main mergen, nur mit grünem Prüftor")
    p.add_argument("pr", type=int)
    p.set_defaults(f=cmd_merge)
    p = sub.add_parser("auftrag")
    p.add_argument("--rolle", default="mistral-team")
    p.add_argument("--dateien", nargs="+")
    p.add_argument("--ende", action="store_true")
    p.set_defaults(f=cmd_auftrag)
    sub.add_parser("kurz").set_defaults(f=cmd_kurz)
    sub.add_parser("sync").set_defaults(f=cmd_sync)
    p = sub.add_parser("aktualisieren", help="Normen aus der Quelle (claude-tools) neu einspielen")
    p.add_argument("--quelle", default=None, help="Quellordner (Standard: [quelle].pfad aus projekt.toml)")
    p.set_defaults(f=cmd_aktualisieren)
    p = sub.add_parser("melden", help="Rückmeldung als Issue an das private Repository aus [rueckmeldung].repo")
    p.add_argument("--art", required=True, choices=MELDE_ARTEN, help="Art der Rückmeldung")
    p.add_argument("--titel", required=True, help="Titel der Rückmeldung")
    p.add_argument("--text-datei", required=True, help="Datei mit dem Rückmeldungstext")
    p.add_argument("--agent", default=None, help="Agent/Rolle")
    p.add_argument("--norm", default=None, help="Norm-ID")
    p.add_argument("--stufe", default=None, choices=["niedrig", "mittel", "hoch"], help="Stufe")
    p.add_argument("--trocken", action="store_true", help="Nur lokale Kopie erstellen, nicht senden")
    p.set_defaults(f=cmd_melden)
    
    a = ap.parse_args()
    return a.f(a)


if __name__ == "__main__":
    sys.exit(main())
