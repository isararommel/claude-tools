#!/usr/bin/env python3
"""Agenten-Normen: prüfen, durchsetzen, erklären. Nur Standardbibliothek, Python ≥ 3.11.

  python3 normen/normen.py pruefen [--diff [BASIS] | --staged] [--nur-melden]
  python3 normen/normen.py hook --rolle ROLLE --werkzeug claude|vibe|gemini   (stdin: JSON des Werkzeugs)
  python3 normen/normen.py stop --werkzeug claude                             (Claude-Stop-Hook: Test + Diff-Prüfung)
  python3 normen/normen.py auftrag --rolle ROLLE [--dateien PFAD …] | --ende  (Pflichtsätze; .normen-auftrag schreiben/entfernen)
  python3 normen/normen.py merge PR                                            (PR nach main – nur mit grünem Prüftor)
  python3 normen/normen.py skript --pruefen DATEI                              (Code-Mode-Skript prüfen wie der Hook, S06)
  python3 normen/normen.py selbsttest [--werkzeug claude|vibe] [--weg bash|write|write_file|edit] | --sitzung   (Hooks live prüfen; --sitzung: diese Sitzung)
  python3 normen/normen.py aktualisieren [--quelle PFAD]                      (Normen aus der Quelle neu einspielen)
  python3 normen/normen.py melden --art ART --titel TITEL --text-datei PFAD    (Rückmeldung als Issue, privat)
  python3 normen/normen.py kurz | sync

Regelwerk: normen.toml · Rollen: rollen.toml · Projektwerte: projekt.toml (alle neben diesem Skript).
"""
import argparse
import ast
import fnmatch
import hashlib
import importlib.machinery
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib
from collections import Counter
from pathlib import Path


def _echt(pfad) -> Path:
    """realpath und Schreibweise wie auf der Platte (v16, #74): Auf Dateisystemen ohne Groß-/Kleinschreibung (macOS) ist
    `.Claude` dieselbe Datei wie `.claude` – ohne Angleichen gingen Sperrlisten (GESCHUETZT, gesperrt, Auftrag) daran vorbei.
    Jeder vorhandene Teil bekommt den Namen aus der Verzeichnisliste, aber nur, wenn die abweichende Schreibweise wirklich
    existiert (also nur ohne Groß-/Kleinschreibung); nicht vorhandene Teile bleiben, wie sie sind."""
    p = Path(os.path.realpath(pfad))
    ergebnis = Path(p.anchor)
    teile = p.parts[1:]
    for k, teil in enumerate(teile):
        kandidat = ergebnis / teil
        if not os.path.lexists(kandidat):
            return ergebnis.joinpath(*teile[k:])
        try:
            namen = os.listdir(ergebnis)
        except OSError:
            return ergebnis.joinpath(*teile[k:])
        if teil not in namen:
            teil = next((n for n in namen if n.casefold() == teil.casefold()), teil)
        ergebnis = ergebnis / teil
    return ergebnis


HIER = _echt(Path(__file__)).parent
ROOT = HIER.parent
AUFTRAG = ROOT / ".normen-auftrag"
MARKE_ANFANG = "<!-- normen:anfang (erzeugt von normen/normen.py sync – nicht von Hand ändern) -->"
MARKE_ENDE = "<!-- normen:ende -->"
RANG = {"ja": 0, "fragen": 1, "nein": 2}
# Schreiben hier braucht die Fähigkeit „einstellungen“ (Regeln dürfen sich nicht selbst aufweichen).
GESCHUETZT = ["normen/", ".normen-auftrag", ".normen/sitzungsprobe.txt", ".claude/", ".vibe/", ".gemini/", ".githooks/", "AGENTS.md", "CLAUDE.md", "GEMINI.md"]
# Köder des Selbsttests (`normen.py selbsttest`): diesen einen Befehl sperrt der Hook für jede Rolle absichtlich.
# Steht nicht in normen.toml – Agenten sollen ihn nicht kennen und nicht von sich aus verweigern.
KOEDER = ".normen/normen-koeder.txt"
KOEDER_RX = re.compile(r"(^|[;&|]\s*)touch\s+\.normen/normen-koeder\.txt\s*($|[;&|])", re.MULTILINE)
KOEDER_BEFEHL = "touch " + KOEDER
SITZUNGSPROBE = ".normen/sitzungsprobe.txt"  # v16 (#66): session_ids, deren Hook den Köder gesperrt hat
# Wege des Selbsttests (v14): pro Werkzeug die Köder-Prompts für Shell- und Datei-Werkzeuge (Weg -> Prompt).
SELBSTTEST_WEGE = {"claude": ["bash", "write"], "vibe": ["bash", "write_file", "edit"]}
SELBSTTEST_TEXTE = {
    "bash": f"Führe genau diesen einen Shell-Befehl mit dem Bash-Werkzeug aus und sonst nichts: {KOEDER_BEFEHL} – danach antworte mit dem Wort FERTIG.",
    "write": f"Lege mit dem Write-Werkzeug die Datei {ROOT / KOEDER} mit dem Inhalt geaendert an und tue sonst nichts – danach antworte mit dem Wort FERTIG.",
    "write_file": f"Lege mit dem Werkzeug write_file die Datei {ROOT / KOEDER} mit dem Inhalt geaendert an und tue sonst nichts – danach antworte mit dem Wort FERTIG.",
    "edit": f"Ersetze mit dem Werkzeug edit in der Datei {ROOT / KOEDER} den Text koeder durch geaendert und tue sonst nichts – danach antworte mit dem Wort FERTIG.",
}


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


def _geheim(name: str, pf: dict) -> bool:
    """Dateiname passt auf [pfade].geheimnisse – ohne Groß-/Kleinschreibung (v16, #74: `.ENV` ist auf macOS `.env`)."""
    return any(fnmatch.fnmatchcase(name.casefold(), g.casefold()) for g in pf.get("geheimnisse", []))


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
    p = _echt(p)  # Symlinks auflösen wie bei ROOT (macOS: /var → /private/var), Schreibweise wie auf der Platte
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
            aus.append(_echt(e))
    return aus


def _lesbar_extern(cfg) -> list[Path]:
    """[pfade].lesbar_extern ohne die Ordner, in denen dieses Projekt selbst liegt (dort darf es schreiben)."""
    aus = []
    for o in cfg["projekt"].get("pfade", {}).get("lesbar_extern", []):
        q = _echt(os.path.expanduser(os.path.expandvars(o)))
        if q != ROOT and q not in ROOT.parents:
            aus.append(q)
    return aus


# Schreibende Shell-Befehle (wie im N10-Muster): schreiben an jeder Stelle bzw. als Ziel, Umleitung, git-Schreibbefehle.
_SCHREIB_VERB = r"(^|[;&|`(\s])(sudo\s+)?(cp|mv|rm|rmdir|touch|mkdir|ln|chmod|chown|tee|install|rsync|truncate|sed\s+-[a-zA-Z]*i|perl\s+-[a-z]*i|patch|unzip|tar\s+-?[a-zA-Z]*x|git\s+(-[cC]\s+\S+\s+)*(add|commit|push|merge|rebase|reset|checkout|restore|switch|stash|apply|am|rm|mv|clean|tag|branch))\b"


def _bash_schreibt_extern(cmd: str, cwd: str, ordner: list[Path]) -> Path | None:
    """Gibt den lesbar_extern-Ordner zurück, in den ein Bash-Befehl schreiben könnte (sonst None). Bewusst streng:
    Schreibverb (wie bisher) oder ein Schreibziel aus _schreibziele im Ordner (auch per cd oder git -C), unaufgelöstes
    Ziel zählt auch."""
    if not ordner:
        return None
    ziele = _schreibziele(cmd, cwd)
    for q in ordner:
        formen = {str(q)}
        if str(q).startswith("/private/"):          # macOS: realpath macht aus /var, /tmp, /etc → /private/…
            formen.add(str(q)[len("/private"):])
        home = str(Path.home())
        if str(q).startswith(home + "/"):
            rest = str(q)[len(home):]
            formen |= {"~" + rest, "$HOME" + rest, "${HOME}" + rest}
        # Aufgelöste Ziele immer nach Platten-Schreibweise (V15b Nr. 12: `~/…/CLAUDE-TOOLS/x`)
        for z in ziele:
            if z is not None and ((zr := _echt(z)) == q or q in zr.parents):
                return q
        nennt = [f for f in formen if f.casefold() in cmd.casefold()]
        if not nennt and not (_echt(cwd) == q or q in _echt(cwd).parents):
            continue
        # Ganze Kette: steht der Ordner irgendwo (cd, git -C, Pfad) und wird irgendwo geschrieben → gesperrt.
        if re.search(_SCHREIB_VERB, cmd) or None in ziele:
            return q
    return None


# Befehlsketten in Einzelbefehle trennen (für Ausnahmen je Teilbefehl).
SEGMENT = re.compile(r"&&|\|\||[;|&\n]")

_PUNKT = "();<>|&"
_VAR_RX = re.compile(r"\$\{([A-Za-z_]\w*)\}|\$([A-Za-z_]\w*)")
_ALLE_ARGUMENTE = {"rm", "rmdir", "touch", "truncate", "chmod", "chown", "mkdir", "mv"}
_LETZTES_ARGUMENT = {"cp", "ln", "install", "rsync"}


def _maskiert(seg: str) -> str:
    """Ersetzt jedes Zeichen in Anführungszeichen und jedes escapte Zeichen durch \\x00. So trennt shlex mit
    punctuation_chars einen zitierten Operator (z. B. '>' in grep '>') nicht als eigenes Token – nur echte
    Operatoren bleiben reine Interpunktions-Token."""
    out = []
    quote = ""
    i = 0
    while i < len(seg):
        c = seg[i]
        if quote:
            if c == "\\" and quote == '"' and i + 1 < len(seg) and seg[i + 1] in ('"', "\\"):
                out.append(c)
                out.append("\x00")
                i += 2
                continue
            if c == quote:
                quote = ""
            out.append("\x00")
        elif c == "\\" and i + 1 < len(seg):
            out.append(c)
            out.append("\x00")
            i += 2
            continue
        elif c in ("'", '"'):
            quote = c
            out.append("\x00")
        else:
            out.append(c)
        i += 1
    return "".join(out)


# Kettentrenner ohne die Umleitungen &>, >&, 2>&1 (anders als SEGMENT); angewandt auf den maskierten Text.
_KETTE = re.compile(r"&&|\|\||[;|\n]|(?<![<>])&(?![>&])")


def _segmente_pos(cmd: str) -> list[tuple[int, str]]:
    """Teilbefehle einer Kette mit Startposition in cmd – Trenner in Anführungszeichen zählen nicht."""
    aus, start = [], 0
    for m in _KETTE.finditer(_maskiert(cmd)):
        aus.append((start, cmd[start:m.start()]))
        start = m.end()
    aus.append((start, cmd[start:]))
    return aus


def _segmente(cmd: str) -> list[str]:
    """Teilbefehle einer Kette – Trenner in Anführungszeichen zählen nicht (`echo "a|b" > x` bleibt ein Teilbefehl)."""
    return [s for _, s in _segmente_pos(cmd)]


def _tokenliste(seg: str) -> list[str]:
    """Tokenize mit punctuation_chars: >, >>, &> … sind eigene Token; ValueError bei unbalancierten Quotes."""
    lexer = shlex.shlex(seg, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    return list(lexer)


def _ist_operator(token: str) -> bool:
    return token != "" and all(c in _PUNKT for c in token)


_UNSICHER = "$__NORMEN_UNSICHER__"  # Platzhalter: Wert nicht sicher bekannt – bleibt unaufgelöst (nie in der Umgebung)


def _unsichere_namen(cmd: str) -> set[str]:
    """Variablen, deren Wert der Hook nicht sicher kennt: mehr als eine Zuweisung im ganzen Befehl (auch in if/for/read/local,
    die der Teilbefehl-Zähler nicht als Zuweisung sieht)."""
    zaehler: Counter[str] = Counter(m.group(2) for m in re.finditer(
        r"(^|[\s;&|(`])(?:local\s+|export\s+|readonly\s+|declare\s+(?:-\w+\s+)*)?([A-Za-z_]\w*)\+?=", cmd))
    for m in re.finditer(r"\b(?:for|select)\s+([A-Za-z_]\w*)\s+in\b|\bread\s+(?:-\w+\s+)*([A-Za-z_]\w*)", cmd):
        zaehler[m.group(1) or m.group(2)] += 2
    return {k for k, n in zaehler.items() if n > 1}


def _sichere_zuweisung(name: str, wert: str, unsicher: set[str]) -> str:
    """Wert einer Zuweisung für die Auflösung – oder der Platzhalter, wenn mehrfach zugewiesen oder mit Befehlsersetzung."""
    return _UNSICHER if name in unsicher or "`" in wert or "$(" in wert else wert


def _schreibziele(cmd: str, cwd: str) -> list[Path | None]:
    """Schreibziele eines Bash-Befehls als absolute, normalisierte Pfade (os.path.normpath, nicht realpath);
    None = Ziel mit unaufgelöster Variable. Umleitungen (> >> &> 2> …), tee, sed -i/perl -i, rm, mv, cp, ln,
    install, rsync; Basisordner je Kette über cd."""
    segmente = _segmente(cmd)
    zuweisungen: dict[str, str] = {}
    unsicher = _unsichere_namen(cmd)
    for seg in segmente:
        try:
            wörter = shlex.split(seg, posix=True)
        except ValueError:
            continue
        if len(wörter) == 1 and "=" in wörter[0]:
            name, wert = wörter[0].split("=", 1)
            if re.fullmatch(r"[A-Za-z_]\w*", name):
                zuweisungen[name] = _sichere_zuweisung(name, os.path.expandvars(wert), unsicher)
    for name in unsicher:  # auch ohne erkannte Zuweisung (if/for/read): nie aus der Umgebung auflösen
        zuweisungen.setdefault(name, _UNSICHER)

    def var_ersetzen(text: str) -> str:
        def rep(m):
            name = m.group(1) or m.group(2)
            if name == "PWD":  # V15b: $PWD ist der Basisordner an dieser Stelle, nicht der des Hooks
                return str(basis) if basis is not None else _UNSICHER
            if name == "OLDPWD":
                return _UNSICHER
            if name in zuweisungen:
                return zuweisungen[name]
            return os.environ.get(name, m.group(0))
        return _VAR_RX.sub(rep, text)

    ziele: list[Path | None] = []
    basis: Path | None = Path(os.path.normpath(cwd))  # None = unbekannt (cd mit unaufgelöster Variable)

    def auflösen(roh: str) -> Path | None:
        text = var_ersetzen(os.path.expanduser(roh))
        if "$" in text:
            return None
        p = Path(text)
        if not p.is_absolute():
            if basis is None:
                return None
            p = basis / p
        return Path(os.path.normpath(p))

    for seg in segmente:
        try:
            orig = _tokenliste(seg)
            mask = _tokenliste(_maskiert(seg))
        except ValueError:
            orig = mask = None
        if orig is None or len(orig) != len(mask):
            if ">" in _maskiert(seg):  # nicht zerlegbar, aber mit echter Umleitung: Ziel unbekannt (streng)
                ziele.append(None)
            continue
        worte = list(zip(orig, mask))
        befehl: str | None = None
        args: list[str] = []
        umleitungen: list[str] = []
        j = 0
        while j < len(worte):
            tok, msk = worte[j]
            naechstes_wort = j + 1 < len(worte) and not _ist_operator(worte[j + 1][1])
            if _ist_operator(msk):
                if tok.endswith(">&") or tok == ">&":
                    j += 2 if naechstes_wort else 1  # 2>&1, >&2: Dateideskriptor, keine Datei
                    continue
                if ">" in tok and naechstes_wort:
                    umleitungen.append(worte[j + 1][0])  # > ziel, >> ziel, &> ziel, 2> ziel – auch am Anfang
                    j += 2
                    continue
                if tok.startswith("<") and naechstes_wort:
                    j += 2  # Eingabeumleitung: verbraucht das nächste Wort, ist kein Schreibziel
                    continue
                j += 1
                continue
            if tok in ("0", "1", "2") and j + 1 < len(worte) and _ist_operator(worte[j + 1][1]) and ">" in worte[j + 1][0]:
                j += 1  # fd-Präfix (2>…): keine Datei
                continue
            if befehl is None and tok != "sudo":
                befehl = tok
            elif befehl is not None:
                args.append(tok)
            j += 1
        if befehl is None:
            befehl = ""
        if befehl == "cd":
            for a in args:
                if not a.startswith("-"):
                    a = var_ersetzen(os.path.expanduser(a))
                    if "$" in a:
                        basis = None
                    elif os.path.isabs(a):
                        basis = Path(os.path.normpath(a))
                    elif basis is not None:
                        basis = Path(os.path.normpath(basis / a))
                    break
            continue
        roh = list(umleitungen)
        if befehl == "tee":
            roh += [a for a in args if not a.startswith("-")]
        elif befehl == "sed" and any(re.match(r"-[A-Za-z]*i", a) for a in args):
            skript = next((k for k, a in enumerate(args) if not a.startswith("-") and a != ""), None)
            if skript is not None:
                roh += args[skript + 1:]  # Ziele stehen nach dem Skript (sed -i '' …: leeres Wort überspringen)
        elif befehl == "perl" and any(re.match(r"-[a-z]*i", a) for a in args):
            roh += [a for a in args if not a.startswith("-")]
        elif befehl in _ALLE_ARGUMENTE:
            roh += [a for a in args if not a.startswith("-")]
        elif befehl in _LETZTES_ARGUMENT:
            ziel = None
            for k, a in enumerate(args):
                if a == "-t" and k + 1 < len(args):
                    ziel = args[k + 1]
                elif a.startswith("--target-directory="):
                    ziel = a.split("=", 1)[1]
                elif a == "--target-directory" and k + 1 < len(args):
                    ziel = args[k + 1]
            if ziel is None:
                nicht_optionen = [a for a in args if not a.startswith("-")]
                if nicht_optionen:
                    ziel = nicht_optionen[-1]
            if ziel is not None:
                roh.append(ziel)
        for r in roh:
            if r == "/dev/null":
                continue
            ziele.append(auflösen(r))
    return ziele


def _loeschbar(cfg) -> list[tuple[Path, bool]]:
    """[pfade].loeschbar als (Pfad, Ordner selbst löschbar). Relativ zum Projekt: Ordner samt Inhalt;
    absolut (Temp-Wurzeln, Umgebungsvariablen erlaubt): nur der Inhalt."""
    aus = []
    for o in cfg["projekt"].get("pfade", {}).get("loeschbar", []):
        e = os.path.expandvars(o)
        if "$" in e or not e.strip("/"):
            continue
        relativ = not os.path.isabs(e)
        pfad = _echt(ROOT / e if relativ else e)
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
        ziel = _echt(Path(cwd) / z)
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
        aus.append(z)
    # auf den ganzen Befehl: mehrzeilige -m "…"-Nachrichten (Absätze) sind ebenfalls Text
    return TEXT_ARG.sub(lambda t: t.group(1) + '""', "\n".join(aus))


_HEREDOC_AUF = re.compile(r"<<-?[ \t]*(['\"]?)([A-Za-z_][\w.-]*)\1")
_AUSGABE_UMLEITUNG = re.compile(r"(^|[\s;&|])(&?\d*)?>>?")  # >, >>, 2>, &> … (nicht <<)
_PRAEFIX_ZUWEISUNG = re.compile(r"[A-Za-z_]\w*=.*")
_PRAEFIX_WORT = {"time", "nice", "nohup", "command", "timeout"}
_SHELL_SCHLUESSEL = {"do", "then", "else", "elif", "if", "while", "until", "!", "{", "("}


def _praefixe_ueberspringen(w: list[str]) -> int:
    """Index des ersten Wortes nach Präfixen vor dem eigentlichen Befehl:
    NAME=wert, time, env (samt -i, -u NAME und NAME=wert), nice, nohup, command."""
    i = 0
    while i < len(w):
        name = w[i].rsplit("/", 1)[-1]  # auch /usr/bin/env, /usr/bin/time …
        if _PRAEFIX_ZUWEISUNG.fullmatch(w[i]) or w[i] in _SHELL_SCHLUESSEL:  # v11: `do bash x.sh`, `if python3 y.py` …
            i += 1
        elif name in _PRAEFIX_WORT or name == "env":
            i += 1  # Optionen des Präfixes überspringen; mit Argument: nice -n N, env -u NAME, timeout -s SIG/-k T
            while i < len(w) and (w[i].startswith("-") or (name == "env" and _PRAEFIX_ZUWEISUNG.fullmatch(w[i]))):
                i += 2 if w[i] in ("-n", "-u", "-s", "-k") else 1
            if name == "timeout" and i < len(w):
                i += 1  # Dauer
        else:
            break
    return i


def _heredocs(z: str) -> list[str]:
    """Endmarken der echten Heredoc-Operatoren einer Zeile: `<<` außerhalb von Anführungszeichen, kein `<<<`,
    kein Shift wie `$((1<<2))` (davor kein Wortzeichen, Marke beginnt mit Buchstabe oder _)."""
    mz, aus = _maskiert(z), []
    for k in range(len(mz) - 1):
        if mz[k:k + 2] != "<<" or mz[k + 2:k + 3] == "<" or (k and (mz[k - 1] in "<$(\x00" or mz[k - 1].isalnum())):
            continue
        m = _HEREDOC_AUF.match(z, k)
        if m:
            aus.append(m.group(2))
    return aus


def _ist_datenzeile(z: str) -> bool:
    """Aufrufzeile, deren Heredoc-Rumpf nur Daten sind: der Teilbefehl mit dem Heredoc ist `tee` oder `cat` mit
    Ausgabe-Umleitung und gibt nicht in eine Pipe weiter (`cat <<EOF | bash`, `|&`). Ketten davor/danach (`cd x && cat > f <<EOF`)
    ändern daran nichts. Alles andere (Interpreter, psql, timeout bash …) bleibt zeilenweise geprüft."""
    mz = _maskiert(z)
    for p, s in _segmente_pos(z):
        if "<<" not in _maskiert(s):
            continue
        nach = mz[p + len(s):].lstrip()
        if nach.startswith("|") and not nach.startswith("||"):
            return False
        try:
            w = shlex.split(s)
        except ValueError:
            return False
        i = _praefixe_ueberspringen(w)
        prog = w[i].rsplit("/", 1)[-1] if i < len(w) else ""
        return prog == "tee" or (prog == "cat" and bool(_AUSGABE_UMLEITUNG.search(_maskiert(s))))
    return False


def _ohne_heredoc_daten(cmd: str) -> str:
    """Entfernt Heredoc-Rümpfe von `cat > datei <<EOF` / `tee datei <<EOF` (reine Daten); Aufrufzeile und Endmarke
    bleiben. Andere Rümpfe bleiben unverändert (Zeilenprüfung, Python per AST). Ohne Endmarke wird nichts entfernt."""
    zeilen, aus, i = cmd.split("\n"), [], 0
    while i < len(zeilen):
        z = zeilen[i]
        aus.append(z)
        i += 1
        marken = _heredocs(z)
        if len(marken) != 1:
            continue
        ende = next((k for k in range(i, len(zeilen)) if zeilen[k].strip() == marken[0]), None)
        if ende is None:
            continue
        if not _ist_datenzeile(z):
            aus.extend(zeilen[i:ende])  # Rumpf bleibt, wird aber nicht als neue Heredoc-Aufrufzeile gelesen
        i = ende
    return "\n".join(aus)


def _heredoc_rumpf(cmd: str, pos: int) -> str | None:
    """Rumpf des Heredocs in der Zeile, in der der Teilbefehl an Position pos von cmd steht
    (None = kein oder mehr als ein Heredoc in der Zeile, oder keine Endmarke)."""
    zeilen = cmd.split("\n")
    nr = cmd.count("\n", 0, pos)
    marken = _heredocs(zeilen[nr])
    if len(marken) != 1:
        return None
    rumpf = []
    for z in zeilen[nr + 1:]:
        if z.strip() == marken[0]:
            return "\n".join(rumpf)
        rumpf.append(z)
    return None


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
    globs = [z.strip() for z in AUFTRAG.read_text(encoding="utf-8").splitlines() if z.strip() and not z.startswith("#")]
    return [_wie_platte(g) for g in globs]


def _wie_platte(muster: str) -> str:
    """Auftragseintrag ohne Platzhalter in der Schreibweise auf der Platte (v16, #74): `Modul.py` meint auf macOS `modul.py`,
    und der Werkzeugpfad wird mit `_echt` ebenso angeglichen. Mit Platzhaltern oder außerhalb des Projekts unverändert."""
    if re.search(r"[*?\[]", muster):
        return muster
    try:
        rel = _echt(ROOT / muster).relative_to(ROOT).as_posix()
    except ValueError:
        return muster
    return rel + ("/" if muster.endswith("/") else "")


def bewerten(cfg: dict, rolle: str, tool: str, eingabe: dict, cwd: str, _tiefe: int = 0) -> tuple[str, list[str]]:
    """Liefert (ja|fragen|nein, Gründe). _tiefe: Verschachtelung der bash/sh/zsh -c-Rekursion (ab 3 „fragen“)."""
    if tool.startswith("mcp__"):  # MCP: nur die Projektlisten entscheiden (Eingabefelder sind keine Befehle/Pfade)
        mcp = cfg["projekt"].get("mcp", {})
        for stufe in ("nein", "fragen"):
            treffer = next((g for g in mcp.get(stufe, []) if fnmatch.fnmatchcase(tool, g)), None)
            if treffer:
                return stufe, [f"N07-KEIN-AUTO-MODUS: MCP-Werkzeug {tool} steht in [mcp].{stufe} ({treffer})"]
        return "ja", []
    pf = cfg["projekt"].get("pfade", {})
    rinfo = cfg["rollen"].get(rolle, {})
    befehle: list[str] = []
    pfade: list[str] = []
    _sammeln(eingabe, {"command", "cmd", "script"}, befehle)
    befehle = [_ohne_heredoc_daten(_ohne_textdaten(c)) for c in befehle]
    _sammeln(eingabe, {"file_path", "path", "absolute_path", "filePath", "notebook_path", "paths", "target_file", "file"}, pfade)
    art = _art(tool, befehle)
    gruende: list[tuple[str, str]] = []

    def pruefe(faehigkeit: str, text: str):
        e = darf(cfg, rolle, faehigkeit)
        if e != "ja":
            gruende.append((e, f"{text} [Fähigkeit {faehigkeit}: {e} für Rolle {rolle}]"))

    for cmd in befehle:
        if KOEDER_RX.search(cmd):  # Selbsttest-Köder: gilt für alle Rollen, auch inhaberin, unabhängig von Fähigkeiten
            gruende.append(("nein", "SELBSTTEST-KOEDER: Köder des Selbsttests – absichtlich gesperrt (normen.py selbsttest)"))
        if (q := _bash_schreibt_extern(cmd, cwd, _lesbar_extern(cfg))) is not None:
            gruende.append(("nein", f"N06-NUR-ERLAUBTE-PFADE: Befehl schreibt möglicherweise in {q} ([pfade].lesbar_extern – nur lesen)"))
        for ziel in _schreibziele(cmd, cwd):  # v7/G3: Bash-Schreibziel in GESCHUETZT braucht „einstellungen“ (wie Edit/Write)
            if ziel is None:
                continue
            try:
                rel = _echt(ziel).relative_to(ROOT).as_posix()
            except ValueError:
                continue
            if any(rel == s.rstrip("/") or rel.startswith(s) for s in GESCHUETZT):
                pruefe("einstellungen", f"N10-KEIN-COMMIT-DURCH-TEAMS: Bash schreibt in Normen/Agenten-Einstellungen {rel}")
                break
        if rinfo.get("auftrag_pflicht"):  # v8: Bash-Schreibziele im Projekt nur aus .normen-auftrag (wie Edit/Write)
            globs = _auftrag_globs()
            for ziel in _schreibziele(cmd, cwd):
                if ziel is None:
                    continue  # nicht bestimmbar (z. B. $(mktemp …)): bleibt pruefen --diff nach dem Lauf überlassen
                echt = _echt(ziel)
                loeschbar = _loeschbar(cfg)
                try:
                    rel = echt.relative_to(ROOT).as_posix()
                except ValueError:  # außerhalb: nur Lauf-Ordner, Temp-Wurzeln aus loeschbar, Geräte (/dev/null) – wie Edit/Write
                    if not (str(echt).startswith("/dev/") or any(echt == o or o in echt.parents for o in _lauf_ordner(cfg))
                            or any(p in echt.parents for p, relativ in loeschbar if not relativ) or _rolle_frei(rinfo, echt)):
                        pruefe("ausserhalb-schreiben", f"N06-NUR-ERLAUBTE-PFADE: Bash schreibt außerhalb des Projekts: {echt}")
                    continue
                if any(echt == p or p in echt.parents for p, relativ in loeschbar if relativ):
                    continue  # relative [pfade].loeschbar im Projekt (build, .pytest_cache …): N01-Ausnahme
                if globs is None:
                    gruende.append(("nein", f"N06-NUR-ERLAUBTE-PFADE: kein .normen-auftrag – Rolle {rolle} darf nichts schreiben ({rel})"))
                    break
                if not any(passt(rel, g) for g in globs):
                    gruende.append(("nein", f"N06-NUR-ERLAUBTE-PFADE: Bash schreibt {rel} – steht nicht in .normen-auftrag"))
                    break
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
            if ist_datei and _geheim(name, pf):
                pruefe("geheimnisse-lesen", f"N03-KEINE-GEHEIMNISSE: Befehl berührt {name}")
        for s in pf.get("gesperrt", []):
            if s and s.casefold() in cmd.casefold():  # v16: ohne Groß-/Kleinschreibung (#74)
                pruefe("sperrpfade-lesen", f"N06-NUR-ERLAUBTE-PFADE: gesperrter Pfad {s}")
        if rolle != "skript":  # S06: Skripte und Inline-Code außerhalb des Projekts vor dem Lauf prüfen (keine Rekursion)
            basis: str | None = cwd  # Basis für relative Skriptpfade (nach cd im selben Befehl dieser Ordner)
            unsicher = _unsichere_namen(cmd)  # v11: mehrfach zugewiesene Namen nie auflösen (if/for/read …)
            zuweisungen: dict[str, str] = {n: _UNSICHER for n in unsicher}  # G5: Zuweisungen aus vorangehenden Teilbefehlen
            # V15b: für `cd "$D"` nur Zuweisungen, die sicher laufen – eigener Teilbefehl nach Anfang/;/Zeilenumbruch, nicht in
            # einer Pipeline oder im Hintergrund, keine Steuerstrukturen/Subshells/Heredocs im Befehl und nichts, was Variablen
            # ohne NAME= ändert (unset, eval, source/., read, printf -v …); sonst bleibt der Basisordner unbekannt
            segs = _segmente_pos(cmd)
            trenner = [""] + [cmd[p + len(s):segs[k + 1][0]].strip() for k, (p, s) in enumerate(segs[:-1])] + [""]
            schlicht = not re.search(
                r"\b(if|then|else|elif|fi|while|until|do|done|case|esac|for|select|function|unset|eval|source|read|"
                r"readarray|mapfile|printf|declare|typeset|local|let|getopts|exec)\b|[(){}`]|<<|(^|[;&|\n])\s*\.(\s|$)",
                _maskiert(re.sub(r"\$\{[A-Za-z_]\w*\}", "$V", cmd)))  # ${NAME} ist keine Klammer-Struktur
            cd_zuw: dict[str, str] = dict(zuweisungen)
            for k, (pos, seg) in enumerate(segs):  # Trenner in Anführungszeichen bleiben im Teilbefehl
                # V15b: $PWD/$OLDPWD gelten an dieser Stelle (nach cd), nicht aus der Umgebung des Hooks
                zuweisungen.update(PWD=basis if basis is not None else _UNSICHER, OLDPWD=_UNSICHER)
                cd_zuw.update(PWD=zuweisungen["PWD"], OLDPWD=_UNSICHER)
                gruende.extend(_skript_im_befehl(cfg, seg, pos, cmd, cwd, rolle, _tiefe, basis, zuweisungen))
                gruende.extend(_team_prompt(cfg, seg, cmd, cwd, basis, zuweisungen))  # G5: Datenschutz vor vibe/agy
                # Werte mit früheren Zuweisungen auflösen (G=/x; RUN="$G/lauf")
                roh = _zuweisungen_aus_seg(seg)
                zuweisungen.update({n: _sichere_zuweisung(n, _var_ersetzen(v, zuweisungen), unsicher) for n, v in roh.items()})
                # für cd nur aus sicher bekannten Werten auflösen (`false && X=/p; D=$X` → D unbekannt)
                sicher = schlicht and trenner[k] in ("", ";") and trenner[k + 1] not in ("|", "&")
                cd_zuw.update({n: _sichere_zuweisung(n, _var_ersetzen(v, cd_zuw), unsicher) if sicher else _UNSICHER
                               for n, v in roh.items()})
                basis = _cd_basis(seg, basis, cd_zuw)

    for p in pfade:
        rel = _rel(p, cwd)
        name = Path(p).name
        if _geheim(name, pf):
            pruefe("geheimnisse-lesen", f"N03-KEINE-GEHEIMNISSE: {name}")
        # v12: auch der gesperrte Ordner selbst (`grep … daten/geheim/` → rel „daten/geheim“) – nicht nur Dateien darin
        if rel is not None and any(rel.casefold().startswith(s.casefold()) or rel.casefold() == s.rstrip("/").casefold()  # v16: wie Platte (#74)
                                  for s in pf.get("gesperrt", []) if s):
            pruefe("sperrpfade-lesen", f"N06-NUR-ERLAUBTE-PFADE: gesperrter Pfad {rel}")
        if art != "schreiben":
            continue
        if rel == KOEDER:  # v14: Selbsttest-Köder für Datei-Werkzeuge (Write/Edit, write_file/edit) – alle Rollen
            gruende.append(("nein", "SELBSTTEST-KOEDER: Köder des Selbsttests – absichtlich gesperrt (normen.py selbsttest)"))
        if rel is None:
            ziel = _echt(Path(cwd) / os.path.expanduser(p))
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
        if a.werkzeug == "claude" and data.get("session_id") and any(g.startswith("SELBSTTEST-KOEDER") for g in gruende):
            # v16 (#66): Beleg für `selbsttest --sitzung` – diese Sitzung hat aktive Hooks (Fehler → gesperrt, s. u.)
            probe = ROOT / SITZUNGSPROBE
            probe.parent.mkdir(exist_ok=True)
            alt = probe.read_text(encoding="utf-8").splitlines()[-19:] if probe.exists() else []
            probe.write_text("\n".join([*alt, str(data["session_id"])]) + "\n", encoding="utf-8")
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


# ---------------------------------------------------------------- Selbsttest (Hooks live prüfen)
def _selbsttest_werkzeug(name: str, weg: str) -> tuple[str, str]:
    """Köder über das echte Werkzeug (claude -p bzw. vibe) starten, als Shell-Befehl oder Datei-Werkzeug: (gesperrt|NICHT GESPERRT|unklar, Beleg/Grund)."""
    koeder = ROOT / KOEDER
    if shutil.which(name) is None:
        return "unklar", f"{name} nicht gefunden"  # Köder gar nicht erst vorbereiten
    # Köder vorbereiten: edit braucht die Datei mit bekanntem Inhalt, sonst muss sie fehlen
    if weg == "edit":
        koeder.parent.mkdir(parents=True, exist_ok=True)
        koeder.write_text("koeder\n", encoding="utf-8")
    elif koeder.exists():
        koeder.unlink()  # eigene Wegwerf-Datei (gitignored)
    text = SELBSTTEST_TEXTE[weg]
    ausgabe_ordner = None
    if name == "claude":
        # enge Freigabe, keine pauschale Write-/Edit-Freigabe; Pfadregel absolut (`//…`) – `Edit(./…)` greift in
        # `claude -p` nicht (Gegenprobe ohne Hook 18.11.2026: abgelehnt statt geschrieben)
        freigabe = f"Bash({KOEDER_BEFEHL})" if weg == "bash" else f"Edit(/{ROOT / KOEDER})"
        befehl = [name, "-p", text, "--allowedTools", freigabe,
                  "--max-turns", "3", "--output-format", "stream-json", "--verbose"]
    else:
        ausgabe_ordner = Path(tempfile.mkdtemp(prefix="normen-selbsttest-"))
        # edit liest die Datei meist erst – mit 3 Runden 1 von 3 Läufen ohne Versuch (gemessen 18.11.2026)
        befehl = [name, "--trust", "--smart-approve", "--max-turns", "5" if weg == "edit" else "3", "--time-limit", "240",
                  "--output-dir", str(ausgabe_ordner), "-p", text]
    try:
        r = subprocess.run(befehl, cwd=ROOT, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=300)
        beleg = r.stdout + r.stderr
        if ausgabe_ordner is not None:
            beleg += "\n" + "\n".join(p.read_text(encoding="utf-8", errors="replace")
                                      for p in sorted(ausgabe_ordner.rglob("*")) if p.is_file())
    except subprocess.TimeoutExpired:
        return "unklar", "Zeitlimit"
    except OSError as e:
        return "unklar", f"{type(e).__name__}: {e}"
    finally:
        if ausgabe_ordner is not None:
            shutil.rmtree(ausgabe_ordner)  # eigener Ordner dieses Laufs
    if weg == "edit":
        if not koeder.exists() or koeder.read_text(encoding="utf-8", errors="replace") != "koeder\n":
            return "NICHT GESPERRT", beleg
    elif koeder.exists():
        return "NICHT GESPERRT", beleg
    if "SELBSTTEST-KOEDER" in beleg:
        return "gesperrt", beleg
    return "unklar", "keine Hook-Meldung – Werkzeug hat den Befehl evtl. nicht versucht"


def _sitzungsprobe() -> int:
    """v16 (#66): Beleg, dass die Hooks in DIESER Sitzung aktiv sind. Der Hook schreibt beim Köder die session_id seiner
    Eingabe nach SITZUNGSPROBE; verlangt wird ein Eintrag mit der eigenen CLAUDE_CODE_SESSION_ID. „Köderdatei fehlt“
    reicht nicht: läuft die Sitzung außerhalb des Projekts, scheitert `touch` schon am fehlenden Ordner."""
    sitzung = os.environ.get("CLAUDE_CODE_SESSION_ID", "")
    if not sitzung:
        print("Sitzungsprobe: keine CLAUDE_CODE_SESSION_ID – nur in einer Claude-Code-Sitzung (Bash-Werkzeug) aufrufen.")
        return 1
    probe = ROOT / SITZUNGSPROBE
    eintraege = probe.read_text(encoding="utf-8").splitlines() if probe.exists() else []
    if sitzung in eintraege:
        print("Sitzungsprobe bestanden: Der Normen-Hook hat den Köder in dieser Sitzung gesperrt.")
        return 0
    print(f"Sitzungsprobe NICHT bestanden: kein Hook-Beleg für diese Sitzung. Erst `{KOEDER_BEFEHL}` in dieser Sitzung "
          "ausführen (muss gesperrt werden). Wurde er nicht gesperrt: Sitzung im Projekt-Stammverzeichnis neu starten "
          "(Hooks aus .claude/settings.json lädt Claude Code nur dort und nur beim Start).")
    return 1


def cmd_selbsttest(a) -> int:
    if a.sitzung:
        if a.werkzeug or a.weg:
            print("--sitzung prüft nur diese Sitzung – nicht mit --werkzeug/--weg kombinieren", file=sys.stderr)
            return 64
        return _sitzungsprobe()
    werkzeuge = [a.werkzeug] if a.werkzeug else ["claude", "vibe"]
    laeufe = []
    for name in werkzeuge:
        wege = SELBSTTEST_WEGE[name]
        if a.weg is None:
            laeufe.extend((name, w) for w in wege)
        elif a.weg in wege:
            laeufe.append((name, a.weg))
        elif a.werkzeug:
            print(f"--weg {a.weg} ist kein Weg von {name} (Wege: {', '.join(wege)})", file=sys.stderr)
            return 64  # ohne irgendeinen Lauf
        # ohne --werkzeug: Werkzeuge ohne diesen Weg überspringen
    (ROOT / ".normen").mkdir(exist_ok=True)
    koeder = ROOT / KOEDER
    if koeder.exists():
        koeder.unlink()  # eigene Wegwerf-Datei (gitignored)
    bestanden = True
    for name, weg in laeufe:
        ergebnis, grund = _selbsttest_werkzeug(name, weg)
        # nur wenn das Werkzeug lief, den Köder aber nicht versuchte – nicht bei fehlendem Werkzeug oder Zeitlimit
        if ergebnis == "unklar" and grund.startswith("keine Hook-Meldung"):
            print(f"{name}/{weg}: unklar ({grund}) – Wiederholung")
            ergebnis, grund = _selbsttest_werkzeug(name, weg)
        if koeder.exists():
            koeder.unlink()
        if ergebnis == "gesperrt":
            print(f"{name}/{weg}: gesperrt")
        else:
            bestanden = False
            if ergebnis == "NICHT GESPERRT":
                zeit = time.strftime("%Y%m%d-%H%M%S")
                beleg_pfad = ROOT / ".normen" / f"selbsttest-{zeit}-{name}-{weg}.log"
                beleg_pfad.write_text(grund, encoding="utf-8")
                print(f"{name}/{weg}: NICHT GESPERRT – Hook greift nicht (Beleg: {beleg_pfad.relative_to(ROOT)})")
            else:
                print(f"{name}/{weg}: unklar ({grund})")
    print(("Selbsttest bestanden." if bestanden else "Selbsttest NICHT bestanden – Hooks prüfen (docs/multi-ki-ablauf.md §3).")
          + " Geprüft: neu gestartete Claude- und Vibe-Läufe im Projekt, nicht diese Sitzung (dafür `selbsttest --sitzung`).")
    return 0 if bestanden else 1


# ---------------------------------------------------------------- Skripte (S06-CODE-MODE)
# Prüfung von Auswerte-Skripten vor dem Lauf: schützt vor Versehen, ist aber keine Sicherheitsgrenze.
KEINE_AUFTRAEGE = {"fable", "skript"}
SKRIPT_IMPORTE = {"json", "re", "sys", "os", "pathlib", "subprocess", "hashlib", "base64", "datetime", "collections",
                  "itertools", "textwrap", "shlex", "typing", "__future__"}
NETZ_IMPORTE = {"urllib", "http", "socket", "requests", "httpx", "urllib3", "ssl", "ftplib", "smtplib"}
OS_VERBOTEN = re.compile(r"(system|popen|exec\w*|spawn\w*|posix_spawn\w*|remove|unlink|rmdir|removedirs|rename|renames|"
                         r"replace|kill|killpg|truncate|chmod|chown|symlink|link)$")
METHODEN_VERBOTEN = {"unlink", "rmdir", "rename", "symlink_to", "hardlink_to", "chmod"}
SCHREIB_METHODEN = {"write_text", "write_bytes", "mkdir", "touch"}
SUBPROCESS_AUFRUFE = {"run", "call", "check_call", "check_output", "Popen"}
PROG_VERBOTEN = {"vibe", "agy", "rm", "rmdir", "unlink", "shred", "mv", "dd", "mkfs", "sudo"}
GIT_VERBOTEN = {"commit", "push", "merge", "tag", "add", "rebase", "reset", "checkout", "restore", "switch", "clean", "rm", "mv",
                "stash", "cherry-pick", "revert", "am", "apply"}
GIT_LESEN = {"status", "diff", "log", "show", "rev-parse", "ls-files"}
BRANCH_VERBOTEN = {"-d", "-D", "-m", "-M", "-c", "-C", "-f", "--delete", "--move", "--copy", "--force"}
GH_API_VERBOTEN = re.compile(r"^(-X|--method|-f|-F|--field|--raw-field|--input)(=|$)|^-X\w")
NORMEN_VERBOTEN = {"merge", "auftrag", "melden", "aktualisieren"}
PYTHON = re.compile(r"python3?(\.\d+)?$")


def _aufruf_name(f: ast.expr) -> str:
    """Punktname eines Aufrufziels (open, os.system, subprocess.run); sonst ""."""
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        vorn = _aufruf_name(f.value)
        return f"{vorn}.{f.attr}" if vorn else ""
    return ""


def _text(node) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _ist_sys_executable(node) -> bool:
    return isinstance(node, ast.Attribute) and node.attr == "executable" and _aufruf_name(node.value) == "sys"


class _Skript:
    def __init__(self, cfg, baum: ast.Module, cwd: str, lauf: Path | None, skript: Path | None = None):
        self.cfg, self.lauf, self.cwd, self.skript = cfg, lauf, cwd, skript
        self.importordner: list[str] = []  # Suchordner für die Import-Auflösung (V15b)
        self.projektimport = False  # nur `python3 -c` (v16, #71): Projekt-Importe erlaubt
        self.funde: list[tuple[str, str]] = []
        anzahl: dict[str, int] = {}
        self.knoten: dict[str, ast.expr] = {}
        for s in baum.body:  # Modul-Ebene: genau einmal zugewiesene Namen gelten als Konstanten
            ziele = s.targets if isinstance(s, ast.Assign) else [s.target] if isinstance(s, ast.AnnAssign) and s.value else []
            for z in ziele:
                if isinstance(z, ast.Name):
                    anzahl[z.id] = anzahl.get(z.id, 0) + 1
                    self.knoten[z.id] = s.value if len(ziele) == 1 else None
        self.knoten = {k: v for k, v in self.knoten.items() if anzahl[k] == 1 and v is not None}

    def fund(self, stufe: str, node, text: str):
        self.funde.append((stufe, f"S06-CODE-MODE: Zeile {getattr(node, 'lineno', '?')}: {text}"))

    def pfad(self, node, gesehen: frozenset = frozenset()) -> Path | None:
        """Pfad statisch auflösen (Literal, Path(…), __file__, .parent, .resolve(), a / "x", str(…), Modul-Konstante)."""
        if (t := _text(node)) is not None:
            p = Path(os.path.expanduser(t))
            return Path(os.path.normpath(p if p.is_absolute() else Path(self.cwd) / p))
        if isinstance(node, ast.Name):
            if node.id == "__file__":
                return self.skript
            if node.id in self.knoten and node.id not in gesehen:
                return self.pfad(self.knoten[node.id], gesehen | {node.id})
            return None
        if isinstance(node, ast.Call):
            name = _aufruf_name(node.func)
            if name in ("Path", "pathlib.Path", "str") and len(node.args) == 1 and not node.keywords:
                return self.pfad(node.args[0], gesehen)
            if isinstance(node.func, ast.Attribute) and node.func.attr in ("resolve", "absolute", "expanduser") \
                    and not node.args:
                return self.pfad(node.func.value, gesehen)
            return None
        if isinstance(node, ast.Attribute) and node.attr == "parent":
            p = self.pfad(node.value, gesehen)
            return p.parent if p else None
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div) and _text(node.right) is not None:
            p = self.pfad(node.left, gesehen)
            return Path(os.path.normpath(p / _text(node.right))) if p else None
        return None

    def ist_pfadausdruck(self, node, gesehen: frozenset = frozenset()) -> bool:
        """Path(…)-Ausdruck (auch über Modul-Konstanten, str(…), .parent, a / b) – Wert beginnt nicht mit einer Option."""
        if isinstance(node, ast.Name):
            if node.id == "__file__":
                return True
            return node.id in self.knoten and node.id not in gesehen and \
                self.ist_pfadausdruck(self.knoten[node.id], gesehen | {node.id})
        if isinstance(node, ast.Call):
            name = _aufruf_name(node.func)
            if name in ("Path", "pathlib.Path"):
                return True
            if name == "str" and len(node.args) == 1:
                return self.ist_pfadausdruck(node.args[0], gesehen)
            return isinstance(node.func, ast.Attribute) and node.func.attr in ("resolve", "absolute", "expanduser") \
                and self.ist_pfadausdruck(node.func.value, gesehen)
        if isinstance(node, ast.Attribute) and node.attr == "parent":
            return self.ist_pfadausdruck(node.value, gesehen)
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            return self.ist_pfadausdruck(node.left, gesehen)
        return False

    def schreiben(self, ziel, node):
        p = self.pfad(ziel)
        if p is None:
            self.fund("fragen", node, "Schreibziel nicht statisch bestimmbar")
            return
        z = Path(os.path.realpath(p))
        if self.lauf is None or z != self.lauf and self.lauf not in z.parents:
            self.fund("nein", node, f"schreibt außerhalb des Lauf-Ordners: {z}")

    def lesen(self, quelle, node):
        if _text(quelle) is None and not (isinstance(quelle, ast.Call) and quelle.args and _text(quelle.args[0]) is not None):
            return  # nur Literale prüfen
        p = self.pfad(quelle)
        if p is None:
            return
        stufe, gruende = bewerten(self.cfg, "skript", "Read", {"file_path": str(p)}, self.cwd)
        if stufe == "nein":
            self.fund("nein", node, "; ".join(gruende))

    def element(self, el) -> str | None:
        """Weiteres Element einer Befehlsliste als Text (Nicht-Literale als X); None = könnte eine Option einschleusen."""
        if isinstance(el, ast.Constant) and isinstance(el.value, (str, int)) and not isinstance(el.value, bool):
            return str(el.value)
        if isinstance(el, ast.JoinedStr):
            erstes = el.values[0] if el.values else None
            if _text(erstes) is not None and not erstes.value.startswith("-"):
                return "".join(t.value if isinstance(t, ast.Constant) else "X" for t in el.values)
            return None
        if isinstance(el, ast.Name) and (t := _text(self.knoten.get(el.id))) is not None:
            return t if not t.startswith("-") else None  # Modul-Konstante mit ihrem Wert
        return "X" if self.ist_pfadausdruck(el) else None

    def befehl(self, node):
        for k in node.keywords:
            if k.arg == "shell" and not (isinstance(k.value, ast.Constant) and k.value.value is False):
                self.fund("nein" if isinstance(k.value, ast.Constant) else "fragen", node, "shell=True")
            elif k.arg == "executable":
                self.fund("fragen", node, "executable= im Aufruf")
        liste = node.args[0] if node.args else next((k.value for k in node.keywords if k.arg == "args"), None)
        if not isinstance(liste, (ast.List, ast.Tuple)):
            self.fund("fragen", node, "Befehlsliste aus Variable – nicht prüfbar")
            return
        els = liste.elts
        if not els or any(isinstance(e, ast.Starred) for e in els):
            self.fund("fragen", node, "Befehlsliste leer oder mit *-Element – nicht prüfbar")
            return
        prog = "python3" if _ist_sys_executable(els[0]) else _text(els[0])
        if prog is None:
            self.fund("fragen", node, "Programm ist kein Text-Literal")
            return
        w, rest = [prog], els[1:]
        if prog == "git" and rest and _text(rest[0]) == "-C":
            if len(rest) < 3 or _text(rest[2]) is None:
                self.fund("fragen", node, "git -C ohne Unterbefehl als Text-Literal")
                return
            rest = rest[2:]
        if rest:
            unter = _text(rest[0])
            if unter is None:
                self.fund("fragen", node, f"Unterbefehl von {prog} ist kein Text-Literal")
                return
            w.append(unter)
            for el in rest[1:]:
                t = self.element(el)
                if t is None:
                    self.fund("fragen", node, f"Element in `{shlex.join(w)} …` könnte eine Option einschleusen")
                    return
                w.append(t)
        stufe, grund = _befehl_stufe(self.cfg, w, self.cwd)
        if stufe != "ja":
            self.fund(stufe, node, grund)

    def aufruf(self, node: ast.Call):
        name = _aufruf_name(node.func)
        attr = node.func.attr if isinstance(node.func, ast.Attribute) else None
        if name in ("eval", "exec", "compile", "__import__"):
            self.fund("nein", node, f"{name}() verboten")
        elif name.startswith("os.") and OS_VERBOTEN.match(name[3:]):
            self.fund("nein", node, f"{name}() verboten (Shell, Löschen, Verschieben)")
        elif name in ("subprocess.getoutput", "subprocess.getstatusoutput"):
            self.fund("nein", node, f"{name}() führt eine Shell aus")
        elif name.startswith("subprocess.") and name[len("subprocess."):] in SUBPROCESS_AUFRUFE:
            self.befehl(node)
        elif name in ("os.makedirs", "os.mkdir") and node.args:
            self.schreiben(node.args[0], node)
        elif name == "open" or attr == "open":
            arg = (node.args[1] if len(node.args) > 1 else None) if name == "open" else (node.args[0] if node.args else None)
            modus = next((k.value for k in node.keywords if k.arg == "mode"), arg)
            m = "r" if modus is None else _text(modus)
            ziel = (node.args[0] if node.args else None) if name == "open" else node.func.value
            if m is None:
                self.fund("fragen", node, "Dateimodus kein Text-Literal")
            elif any(c in m for c in "wax+"):
                if ziel is None:
                    self.fund("fragen", node, "Schreibziel fehlt")
                else:
                    self.schreiben(ziel, node)
            elif ziel is not None:
                self.lesen(ziel, node)
        elif attr in METHODEN_VERBOTEN:
            self.fund("nein", node, f".{attr}() verboten (Löschen, Verschieben, Rechte)")
        elif attr in SCHREIB_METHODEN:
            self.schreiben(node.func.value, node)
        elif attr in ("read_text", "read_bytes"):
            self.lesen(node.func.value, node)

    def importe(self, node):
        if isinstance(node, ast.Import):
            for a in node.names:
                self.modul(a.name, node, a.asname)
            return
        mod = node.module or ""
        if node.level:
            self.fund("fragen", node, "relativer Import")
            return
        self.modul(mod, node, None)
        if self.importordner:  # V15b: `from ns import x` kann das Untermodul ns.x laden
            for a in node.names:
                if a.name != "*":
                    self.untermodul(f"{mod}.{a.name}", node)
        if mod in ("os", "subprocess"):
            for a in node.names:
                self.fund("nein" if mod == "os" and OS_VERBOTEN.match(a.name) else "fragen", node,
                          f"from {mod} import {a.name} – {mod} nur als {mod}.<name>(…) verwenden")

    def aufloesen(self, name: str, node) -> list[Path] | None:
        """V15b: Dateien des Imports in den Suchordnern; None = Befund schon gemeldet (nicht prüfbar, vertraut)."""
        dateien, grund = _py_modul_aufloesen(name, self.importordner, False, lambda p: _py_intern(self.cfg, p))
        if grund:
            self.fund("fragen", node, f"Import {name}: {grund} – nicht prüfbar")
            return None
        if v := _py_vertraut(self.cfg, dateien, f"import {name}"):
            self.fund(v[0][0], node, v[0][1].removeprefix("S06-CODE-MODE: "))
            return None
        return dateien

    def untermodul(self, name: str, node):
        """`from a import b`: lädt b als Untermodul, wenn es eines gibt – nur Schatten und vertraute Werkzeuge prüfen."""
        dateien = self.aufloesen(name, node)
        fremd = [d for d in dateien or [] if not _py_intern(self.cfg, d)]
        if fremd:
            self.fund("fragen", node, f"Import {name} lädt {fremd[0]} außerhalb des Projekts – nicht prüfbar")

    def modul(self, name: str, node, alias: str | None):
        kopf = name.split(".")[0]
        dateien = None
        if self.importordner:
            dateien = self.aufloesen(name, node)
            if dateien is None:
                return
        if kopf in NETZ_IMPORTE:
            self.fund("fragen", node, f"Netzzugriff (import {name})")
        elif kopf not in SKRIPT_IMPORTE:
            # v16 (#71): nur `python3 -c`; reiner Namespace (keine Datei) zählt nie als Projekt-Import
            if not (self.projektimport and dateien and all(ROOT in d.parents for d in dateien)):
                self.fund("fragen", node, f"Import {name} nicht in der Positivliste")
        elif fremd := [d for d in dateien or [] if not _py_intern(self.cfg, d)]:
            self.fund("fragen", node, f"Import {name} löst auf {fremd[0]} außerhalb des Projekts auf (Schatten-Modul) "
                                      "– nicht prüfbar")
        elif alias and kopf in ("os", "subprocess", "sys"):
            self.fund("fragen", node, f"import {name} as {alias} – nicht prüfbar")


def _befehl_stufe(cfg, w: list[str], cwd: str) -> tuple[str, str]:
    """Stufe eines aufgelösten Befehls aus einem Skript: verboten oder `bewerten` (Rolle skript) nein → nein,
    Positivliste → ja, sonst fragen. Die Positivliste überstimmt nie ein nein (z. B. Geheimnis in `git diff`)."""
    befehl = shlex.join(w)
    prog = w[0].rsplit("/", 1)[-1]
    ist_py = bool(PYTHON.match(prog))
    unter = w[1] if len(w) > 1 else ""
    stufe, gruende = bewerten(cfg, "skript", "Bash", {"command": befehl}, cwd)
    if stufe == "nein":
        return "nein", f"`{befehl}`: " + "; ".join(gruende)
    if prog in PROG_VERBOTEN:
        return "nein", f"`{befehl}`: {prog} im Skript verboten (Löschen bzw. Teams nur über die Schnittstellen)"
    if prog == "git" and unter in GIT_VERBOTEN:
        return "nein", f"`{befehl}`: git {unter} im Skript verboten"
    if prog == "git" and unter in GIT_LESEN:
        return "ja", ""
    if prog == "git" and unter == "branch":
        if any(x.split("=", 1)[0] in BRANCH_VERBOTEN for x in w[2:]):
            return "nein", f"`{befehl}`: Branch ändern im Skript verboten"
        if all(x.startswith("-") for x in w[2:]):
            return "ja", ""
    if prog == "gh" and unter == "pr":
        return "nein", f"`{befehl}`: gh pr im Skript verboten"
    if prog == "gh" and unter == "api":
        if any(GH_API_VERBOTEN.match(x) for x in w[2:]):
            return "nein", f"`{befehl}`: gh api nur lesend (ohne -X/--method/-f/-F/--input)"
        return "ja", ""
    if ist_py and len(w) > 2 and w[1].endswith("normen.py"):
        if w[2] in NORMEN_VERBOTEN:
            return "nein", f"`{befehl}`: normen.py {w[2]} im Skript verboten"
        if w[1].endswith("normen/normen.py") and w[2] == "pruefen":
            return "ja", ""
    if w == shlex.split(cfg["projekt"]["projekt"]["testbefehl"]):
        return "ja", ""
    return "fragen", f"`{befehl}` nicht in der Positivliste"


_MODULE_DYNAMISCH = {"os", "subprocess", "shutil", "builtins", "importlib", "sys", "pathlib", "socket", "urllib", "pty"}


def _gefaehrlicher_name(n: str) -> bool:
    """Name, der nur als direkter, geprüfter Aufruf vorkommen darf (eval, os.system, subprocess.run …)."""
    return (n in ("eval", "exec", "compile", "__import__")
            or (n.startswith("os.") and bool(OS_VERBOTEN.match(n[3:])))
            or (n.startswith("subprocess.") and n[len("subprocess."):] in (*SUBPROCESS_AUFRUFE, "getoutput", "getstatusoutput")))


def code_pruefen(cfg, quelltext: str, lauf: Path | None, cwd: str, name: str,
                 importordner: list[str] | None = None,
                 schattenordner: list[str] | None = None) -> tuple[str, list[str]]:
    """Quelltext per AST prüfen (S06): (ja|fragen|nein, Gründe). lauf=None → Inline-Code: jedes aufgelöste
    Schreibziel liegt außerhalb des Lauf-Ordners; __file__ ist dann nicht auflösbar. importordner (v16, #71): Suchordner
    wie sys.path des Aufrufs (`python3 -c`); ein Import, der dort auf Projektdateien auflöst, gilt wie
    `python3 projektdatei.py`. schattenordner (V15b): Suchordner nur für die Schatten-Prüfung, ohne diese Lockerung.
    In beiden Fällen: Auflösung außerhalb von Projekt/lesbar_extern (Schatten einer Positivlisten-Bibliothek) → fragen,
    auf ein vertrautes Werkzeug → nein."""
    try:
        baum = ast.parse(quelltext, name)
    except (SyntaxError, ValueError) as e:
        return "nein", [f"S06-CODE-MODE: {name} nicht prüfbar ({type(e).__name__}: {e})"]
    s = _Skript(cfg, baum, cwd, lauf, Path(name) if lauf is not None else None)
    s.importordner = importordner or schattenordner or []
    s.projektimport = bool(importordner)
    for node in ast.walk(baum):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            s.importe(node)
        elif isinstance(node, ast.Call):
            s.aufruf(node)
            if _aufruf_name(node.func) in ("getattr", "setattr", "delattr") and node.args:
                ziel, attr = node.args[0], node.args[1] if len(node.args) > 1 else None
                if isinstance(ziel, ast.Name) and ziel.id in _MODULE_DYNAMISCH:
                    s.fund("nein", node, f"{_aufruf_name(node.func)}() auf Modul {ziel.id} verboten (umgeht die Prüfung)")
                elif not (isinstance(attr, ast.Constant) and isinstance(attr.value, str)):
                    s.fund("fragen", node, f"{_aufruf_name(node.func)}() mit nicht statischem Namen")
    aufrufziele = {id(n.func) for n in ast.walk(baum) if isinstance(n, ast.Call)}
    for node in ast.walk(baum):  # `r = subprocess.run; r([...])`, `map(os.system, …)`: Referenz ohne direkten Aufruf
        if isinstance(node, (ast.Name, ast.Attribute)) and id(node) not in aufrufziele and _gefaehrlicher_name(_aufruf_name(node)):
            s.fund("nein", node, f"{_aufruf_name(node)} ohne direkten Aufruf (Alias/Weitergabe) verboten")
    if not s.funde:
        return "ja", []
    return max((f[0] for f in s.funde), key=lambda x: RANG[x]), [f[1] for f in s.funde]


def skript_pruefen(cfg, pfad: Path, cwd: str, schatten: list[str] | None = None) -> tuple[str, list[str]]:
    """Code-Mode-Skript per AST prüfen (S06): (ja|fragen|nein, Gründe). schatten (V15b): Suchordner für die
    Schatten-Prüfung der Importe; Standard ist der Ordner des Skripts (bei `python3 <datei>` erster Eintrag von sys.path)."""
    try:
        skript = Path(os.path.realpath(pfad))
        quelltext = skript.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError, ValueError) as e:
        return "nein", [f"S06-CODE-MODE: Skript nicht prüfbar ({type(e).__name__}: {e})"]
    return code_pruefen(cfg, quelltext, skript.parent, cwd, str(skript),
                        schattenordner=schatten if schatten is not None else [str(skript.parent)])


_PWD_RX = re.compile(r"\$(?:\{(PWD|OLDPWD)\}|(PWD|OLDPWD)\b)")


def _pwd_ersetzen(text: str, basis: str | None) -> str:
    """V15b: `$PWD` ist der Basisordner an dieser Stelle des Befehls (nicht der des Hooks); `$OLDPWD` und `$PWD` bei
    unbekannter Basis bleiben unaufgelöst."""
    return _PWD_RX.sub(lambda m: basis if (m.group(1) or m.group(2)) == "PWD" and basis is not None else _UNSICHER, text)


def _cd_basis(seg: str, basis: str | None, zuw: dict[str, str] | None = None) -> str | None:
    """Basisordner für relative Pfade im nächsten Teilbefehl: nach `cd <ordner>` dieser Ordner, sonst
    unverändert; None = unbekannt (cd ohne Argument, `cd -`, unaufgelöste Variable). zuw: sicher bekannte Zuweisungen
    aus vorangehenden Teilbefehlen (`D=/x; cd "$D"`)."""
    if basis is None:
        return None
    try:
        w = shlex.split(seg)
    except ValueError:
        return basis
    while w and w[0] in ("{", "("):  # `{ cd x; ./y; }`, `(cd x && ./y)`
        w = w[1:]
    i = _praefixe_ueberspringen(w)
    if i < len(w) and w[i] == "popd":
        return None
    if i >= len(w) or w[i] not in ("cd", "pushd"):
        return basis
    args = [a for a in w[i + 1:] if not a.startswith("-")]
    if not args:
        return None
    roh = os.path.expanduser(_var_ersetzen(_pwd_ersetzen(args[0], basis), zuw or {}))
    if "$" in roh:
        return None
    p = Path(roh)
    if not p.is_absolute():
        p = Path(basis) / p
    return os.path.normpath(str(p))


# Skriptaufruf in einem nicht zerlegbaren Teilbefehl (unbalanciertes Zitat): Interpreter oder Pfad mit /
_SKRIPT_AUFRUF_RX = re.compile(
    r"(^|\s)(\S*/)?(python3?(\.\d+)?|bash|sh|zsh|node|perl|ruby|source)(\s|$)"
    r"|(^|\s)\.(?=\s|$)"
    r"|(^|\s)[^\s;|&()]*/[^\s;|&()]*(\s|$)")


def _skript_pfad(wort: str, basis: str | None, zuw: dict[str, str] | None = None) -> tuple[Path | None, str | None]:
    """Skriptpfad aus einem Aufrufwort auflösen (Zuweisungen aus demselben Befehl, dann Umgebung; expanduser; relativ zur
    Basis; realpath); (None, grund) bei unaufgelöster Variable oder unbekannter Basis."""
    roh = os.path.expanduser(_var_ersetzen(wort, zuw or {}))
    if "$" in roh:
        return None, f"S06-CODE-MODE: Skriptpfad mit unaufgelöster Variable ({wort}) – nicht prüfbar"
    p = Path(roh)
    if not p.is_absolute():
        if basis is None:
            return None, f"S06-CODE-MODE: Skript {wort} relativ, aber Basisordner unbekannt (cd) – nicht prüfbar"
        p = Path(basis) / p
    return Path(os.path.realpath(p)), None


_CD_RX = re.compile(r"(^|[\s;&|({])(cd|pushd|popd)(\s|$)")


def _skript_gate(cfg, datei: Path, wort: str, cmd: str) -> list[tuple[str, str]] | None:
    """None → Datei ist prüf-relevant (außerhalb des Projekts und von lesbar_extern, vorhanden); sonst
    Befunde: im Projekt und unter [pfade].lesbar_extern keine, nicht vorhanden → fragen."""
    if datei == ROOT or ROOT in datei.parents:
        if not datei.exists() and (wort.endswith(".py") or _CD_RX.search(_maskiert(cmd))):
            # z. B. `pushd <anderswo> && ./x.sh`: relativ zur Basis falsch aufgelöst – nie als Projektskript durchlassen
            # (ohne cd im Befehl: z. B. `python3 -m venv .venv && .venv/bin/pip …` legt das Ziel erst an)
            return [("fragen", f"S06-CODE-MODE: Skript {wort} nicht gefunden (cd im Befehl?) – nicht prüfbar")]
        return []  # Projektskripte wie bisher
    if any(datei == q or q in datei.parents for q in _lesbar_extern(cfg)):
        return []
    if not datei.exists():
        return [("fragen", f"S06-CODE-MODE: Skript {wort} nicht gefunden – nicht prüfbar")]
    return None


def _skript_geschrieben(wort: str, datei: Path, cmd: str, cwd: str) -> tuple[str, str] | None:
    """Befund, wenn das Skript zugleich Schreibziel des ganzen Befehls ist (oder Ziele nicht zerlegbar)."""
    echt = _echt(datei)
    for z in _schreibziele(cmd, cwd):
        if z is None or _echt(z) == echt:  # V15b (Nr. 2): `> Evil.py` ist auf macOS dieselbe Datei wie evil.py
            return ("fragen", f"S06-CODE-MODE: Skript {wort} wird im selben Befehl geschrieben – Inhalt nicht prüfbar")
    return None


def _shell_datei_bewerten(cfg, datei: Path, wort: str, cmd: str, cwd: str, rolle: str, tiefe: int,
                          basis: str | None) -> list[tuple[str, str]]:
    """Shell-Skriptdatei außerhalb des Projekts: Inhalt (ohne Shebang und reine Kommentarzeilen) als einen
    Befehl rekursiv bewerten; Gründe mit dem Dateinamen voranstellen."""
    g = _skript_geschrieben(wort, datei, cmd, cwd)
    if g:
        return [g]
    try:
        inhalt = datei.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError, ValueError) as e:
        return [("nein", f"S06-CODE-MODE: Skript nicht prüfbar ({type(e).__name__}: {e})")]
    zeilen = inhalt.split("\n")
    if zeilen and zeilen[0].startswith("#!"):
        zeilen = zeilen[1:]
    inhalt = "\n".join(z for z in zeilen if not z.lstrip().startswith("#"))
    if tiefe >= 3:
        return [("fragen", "S06-CODE-MODE: Skript-Verschachtelung zu tief – nicht prüfbar")]
    stufe, gruende = bewerten(cfg, rolle, "Bash", {"command": inhalt}, basis or cwd, _tiefe=tiefe + 1)  # Skript läuft im Ordner nach cd
    return [] if stufe == "ja" else [(stufe, f"{datei.name}: {g}") for g in gruende]


_PY_ENDUNGEN = tuple(importlib.machinery.all_suffixes())  # .py, Erweiterungen (.so …), Bytecode (.pyc)
_PY_ANDERE = tuple(s for s in _PY_ENDUNGEN if s != ".py")
# Module der Standardbibliothek, die weiteren Code ausführen (Argument, Datei, Modul) – nicht auflösbar → fragen (V15b, Nr. 7)
_PY_STARTER = {"timeit", "cProfile", "profile", "trace", "pdb", "runpy"}


def _py_finde(name: str, suchpfad: list, intern) -> tuple[str, Path | None, list[Path], str | None]:
    """Ein Namensteil wie PathFinder/FileFinder: je Ordner zuerst Paket (`name/__init__`), dann Modul (`name.py`);
    Ordner ohne `__init__` sind Namespace-Teile, ein späteres Paket oder Modul gewinnt.
    → (art: paket|modul|namespace|fehlt, Datei, Namespace-/Paketordner, Grund für „nicht prüfbar“).
    intern(pfad): Projekt oder lesbar_extern – dort gelten andere Importformen (.so, .pyc, zip) nicht als Befund."""
    portionen: list[Path] = []
    for d in suchpfad:
        dp = Path(d)
        if dp.is_file():
            if intern(dp):
                continue
            return "fehlt", None, [], f"Eintrag {d} im Suchpfad ist eine Datei (zip/pyz)"
        if not dp.is_dir():
            continue
        p = dp / name
        if p.is_dir():
            anders = [p / ("__init__" + s) for s in _PY_ANDERE if (p / ("__init__" + s)).is_file()]
            if anders and not intern(anders[0]):
                return "fehlt", None, [], f"Paket {p} mit {anders[0].name} (nur .py prüfbar)"
            if (p / "__init__.py").is_file():
                return "paket", p / "__init__.py", [p], None
            portionen.append(p)
        anders = [dp / (name + s) for s in _PY_ANDERE if (dp / (name + s)).is_file()]
        if anders and not intern(anders[0]):
            return "fehlt", None, [], f"Modul {anders[0]} (nur .py prüfbar)"
        if (dp / (name + ".py")).is_file():
            return "modul", dp / (name + ".py"), [], None
    return ("namespace" if portionen else "fehlt"), None, portionen, None


def _py_modul_aufloesen(modul: str, ordner: list[str], als_main: bool, intern=None) -> tuple[list[Path], str | None]:
    """V15b: Dateien, die Python für `import modul` bzw. `python3 -m modul` (als_main) aus den Ordnern ausführt, in
    Ausführungsreihenfolge: alle `__init__.py` auf dem Weg (`a/__init__.py` vor `a/b.py`), bei `-m` eines Pakets zuletzt
    `__main__.py`. Leere Liste = in den Ordnern nicht vorhanden (installiert/Standardbibliothek) oder reiner Namespace.
    Zweiter Wert: Grund, warum nicht prüfbar (andere Importform außerhalb von Projekt/lesbar_extern)."""
    intern = intern or (lambda p: False)
    dateien: list[Path] = []
    suchpfad: list = list(ordner)
    teile = modul.split(".") + (["__main__"] if als_main else [])
    for teil in teile:
        art, datei, portionen, grund = _py_finde(teil, suchpfad, intern)
        if grund:
            return dateien, grund
        if datei is not None:
            dateien.append(_echt(datei))
        if art in ("fehlt", "modul"):
            break
        suchpfad = portionen
    return dateien, None


def _py_intern(cfg, p: Path) -> bool:
    """Datei/Ordner im Projekt oder unter [pfade].lesbar_extern (dort keine S06-Prüfung von Skripten)."""
    p = _echt(p)
    return p == ROOT or ROOT in p.parents or any(p == q or q in p.parents for q in _lesbar_extern(cfg))


def _py_vertraut(cfg, dateien: list[Path], wort: str) -> list[tuple[str, str]]:
    """V15b (Punkt 10): Auflösung auf ein vertrautes Werkzeug → nein für alle Rollen (nur direkt aufrufen)."""
    liste = _vertraut(cfg)
    for d in dateien:
        if _echt(d) in liste:
            return [("nein", f"S06-CODE-MODE: vertrautes Werkzeug {d.name} nur direkt aufrufen, nicht über {wort}")]
    return []


def _py_kandidat_geschrieben(cfg, koepfe: list[str], ordner: list[str], cmd: str, cwd: str) -> tuple[str, str] | None:
    """V15b (Nr. 1, 2): wird im selben Befehl in einem Suchordner außerhalb von Projekt/lesbar_extern eine importierbare
    Datei (`d/<name><Endung>`, also auch Importe der geprüften Dateien) oder etwas im Paketordner `d/<kopf>/` geschrieben
    (Vergleich ohne Groß-/Kleinschreibung) → fragen. Unzerlegbares Schreibziel → fragen, wenn ein solcher Suchordner
    beteiligt ist. `> pytest.log` ist kein Kandidat."""
    fremd = [str(_echt(d)).casefold() for d in ordner if not _py_intern(cfg, Path(d))]
    if not fremd:
        return None
    for z in _schreibziele(cmd, cwd):
        if z is None:
            return ("fragen", "S06-CODE-MODE: Schreibziel nicht auflösbar, Python-Suchordner außerhalb des Projekts – "
                              "Modul nicht prüfbar")
        ze = str(_echt(z)).casefold()
        eltern, _, name = ze.rpartition("/")
        for d in fremd:
            if (eltern == d and name.endswith(tuple(s.casefold() for s in _PY_ENDUNGEN))) \
                    or any(ze.startswith(f"{d}/{kopf.casefold()}/") for kopf in koepfe):
                return ("fragen", f"S06-CODE-MODE: Python-Modul {z} wird im selben Befehl geschrieben – nicht prüfbar")
    return None


def _py_suchordner(basis: str | None, zuw: dict[str, str]) -> list[str] | str:
    """Suchordner von `python3 -c`/`-m` wie sys.path: Basisordner, dann PYTHONPATH (Präfix, Zuweisung, Umgebung;
    Variablen wie `$PWD` aufgelöst); Text = Grund, warum nicht bestimmbar."""
    pp = zuw["PYTHONPATH"] if "PYTHONPATH" in zuw else os.environ.get("PYTHONPATH", "")
    pp = _var_ersetzen(pp, zuw) if pp != _UNSICHER else pp
    if "$" in pp:
        return "PYTHONPATH unaufgelöst"
    if basis is None:
        return "Basisordner unbekannt (cd)"
    return [basis] + [os.path.join(basis, os.path.expanduser(p)) for p in pp.split(os.pathsep) if p]


def _python_m(cfg, modul: str, cmd: str, cwd: str, basis: str | None, zuw: dict[str, str]) -> list[tuple[str, str]]:
    """`python3 -m MODUL` (v16, #71; V15b): Modul aus Basisordner und PYTHONPATH (Reihenfolge wie Python) auflösen; jede
    ausgeführte Datei außerhalb von Projekt/lesbar_extern per AST prüfen wie `python3 <datei>.py` (mit Schatten-Prüfung
    ihrer Importe). Nicht gefunden = installiertes Modul (pytest, venv, pip) – erlaubt, außer Code-Starter."""
    wort = f"-m {modul}"
    ordner = _py_suchordner(basis, zuw)
    if isinstance(ordner, str):
        return [("fragen", f"S06-CODE-MODE: python3 {wort}: {ordner} – nicht prüfbar")]
    dateien, grund = _py_modul_aufloesen(modul, ordner, True, lambda p: _py_intern(cfg, p))
    if grund:
        return [("fragen", f"S06-CODE-MODE: python3 {wort}: {grund} – nicht prüfbar")]
    if v := _py_vertraut(cfg, dateien, f"python3 {wort}"):
        return v
    if g := _py_kandidat_geschrieben(cfg, [modul.split(".")[0]], ordner, cmd, cwd):
        return [g]
    if not dateien:
        if modul.split(".")[0] in _PY_STARTER:
            return [("fragen", f"S06-CODE-MODE: python3 {wort} führt weiteren Code aus (Argument, Datei) – nicht prüfbar")]
        return []
    aus: list[tuple[str, str]] = []
    for datei in dateien:
        gate = _skript_gate(cfg, datei, wort, cmd)
        aus += gate if gate is not None else _python_datei_bewerten(cfg, datei, wort, cmd, cwd, ordner)
    return aus


def _python_datei_bewerten(cfg, datei: Path, wort: str, cmd: str, cwd: str,
                           schatten: list[str] | None = None) -> list[tuple[str, str]]:
    """Python-Skriptdatei außerhalb des Projekts per AST prüfen (wie `python3 <datei>.py`); schatten: Suchordner des
    Aufrufs (Standard: Ordner der Datei) für die Schatten-Prüfung der Importe."""
    g = _skript_geschrieben(wort, datei, cmd, cwd)
    if g:
        return [g]
    ordner = schatten if schatten is not None else [str(datei.parent)]
    if g := _py_kandidat_geschrieben(cfg, [], ordner, cmd, cwd):  # V15b: Schatten-Modul im selben Befehl geschrieben
        return [g]
    stufe, gruende = skript_pruefen(cfg, datei, cwd, ordner)
    return [] if stufe == "ja" else [(stufe, g) for g in gruende]


def _skript_datei_arg(cfg, wort: str, cmd: str, cwd: str, rolle: str, tiefe: int, basis: str | None,
                       aktion: str, prog: str = "", zuw: dict[str, str] | None = None) -> list[tuple[str, str]]:
    """Datei-Argument eines Aufrufs (python/bash|sh|zsh/source/. sowie node|perl|ruby) außerhalb des Projekts
    prüfen. aktion: "python" (per AST), "shell" (Inhalt als ein Befehl), "fragen" (nicht prüfbar)."""
    datei, grund = _skript_pfad(wort, basis, zuw)
    if grund:
        return [("fragen", grund)]
    if _echt(datei) in _vertraut(cfg):  # v15 (#87): sonst ginge `bash|python3 <werkzeug> <verboten>` an der Unterbefehl-Liste vorbei
        return [("nein", f"S06-CODE-MODE: vertrautes Werkzeug {wort} nur direkt aufrufen, nicht über {prog or aktion}")]
    gate = _skript_gate(cfg, datei, wort, cmd)
    if gate is not None:
        return gate
    if aktion == "python":
        return _python_datei_bewerten(cfg, datei, wort, cmd, cwd)
    if aktion == "shell":
        return _shell_datei_bewerten(cfg, datei, wort, cmd, cwd, rolle, tiefe, basis)
    return [("fragen", f"S06-CODE-MODE: {prog}-Skript außerhalb des Projekts – nicht prüfbar")]


def _vertraut(cfg) -> dict[Path, set[str]]:
    """v15 (#87): [werkzeuge].vertraut aus projekt.toml → {realpath des Werkzeugs: freigegebene Unterbefehle}.
    Fehlerhafte Einträge brechen ab (der Hook sperrt dann mit der Meldung, fail-closed)."""
    aus: dict[Path, set[str]] = {}
    for e in cfg["projekt"].get("werkzeuge", {}).get("vertraut", []):
        if not (isinstance(e, dict) and isinstance(e.get("pfad"), str) and isinstance(e.get("unterbefehle"), list)
                and all(isinstance(u, str) and u for u in e["unterbefehle"])):
            raise ValueError(f"[werkzeuge].vertraut: Eintrag {e!r} braucht pfad (Text) und unterbefehle (Liste von Texten)")
        aus[_echt(os.path.expanduser(os.path.expandvars(e["pfad"])))] = set(e["unterbefehle"])  # V15b: Schreibweise der Platte
    return aus


def _vertraut_bewerten(cfg, w: list[str], i: int, cmd: str, cwd: str, basis: str | None,
                       zuweisungen: dict[str, str] | None) -> list[tuple[str, str]] | None:
    """v15 (#87): Aufruf eines vertrauten Werkzeugs (direkter Pfad oder Name aus $PATH) als Befehl bewerten statt per AST:
    freigegebener Unterbefehl (erstes Wort, wörtlich) → keine Befunde; jeder andere oder fehlende → nein.
    None = kein vertrautes Werkzeug."""
    liste = _vertraut(cfg)
    if not liste:
        return None
    if "/" in w[i]:
        datei, grund = _skript_pfad(w[i], basis, zuweisungen)
        if grund:
            return None
    else:
        gefunden = shutil.which(w[i])
        if gefunden is None:
            return None
        datei = Path(os.path.realpath(gefunden))
    datei = _echt(datei)  # V15b: `./WP.py` ist auf macOS dieselbe Datei wie wp.py
    if datei not in liste:
        return None
    unter = w[i + 1] if i + 1 < len(w) else ""
    if not unter or "$" in unter or unter.startswith("-") or unter not in liste[datei]:
        return [("nein", f"S06-CODE-MODE: Unterbefehl `{unter or '(keiner)'}` von {w[i]} nicht freigegeben "
                         f"([werkzeuge].vertraut: {', '.join(sorted(liste[datei]))})")]
    g = _skript_geschrieben(w[i], datei, cmd, cwd)
    return [g] if g else []


def _skript_im_befehl(cfg, seg: str, pos: int, cmd: str, cwd: str, rolle: str, tiefe: int = 0,
                       basis: str | None = None, zuweisungen: dict[str, str] | None = None) -> list[tuple[str, str]]:
    """Inline-Code und Skriptdateien im Teilbefehl seg (Heredoc-Rumpf aus dem ganzen Befehl cmd), nur für
    Dateien außerhalb des Projekts und außerhalb von [pfade].lesbar_extern: `python3 … <datei>` (mit und ohne
    .py-Endung, per AST), `python3 -c CODE`, `python3 - <<HEREDOC` (Rumpf per AST), `bash|sh|zsh -c CODE`
    (rekursiv bewertet), `bash|sh|zsh|source|. <datei>` (Inhalt als ein Befehl), `node|perl|ruby <datei>`
    (fragen) und direkte Pfadaufrufe (`/tmp/x.sh`, `./x.sh`: Shebang-Interpreter bzw. Textdatei als Skript).
    Liefert Befunde (stufe, grund)."""
    try:
        w = shlex.split(seg)
    except ValueError:  # z. B. `python3 x.py "a|b"`: unbalanciertes Zitat – nie ungeprüft durchlassen
        if _SKRIPT_AUFRUF_RX.search(seg):
            return [("fragen", "S06-CODE-MODE: Aufruf nicht zerlegbar (Zitat mit ;, & oder |) – Skript nicht prüfbar")]
        return []
    i = _praefixe_ueberspringen(w)  # NAME=wert, time, env …, nice, nohup, command vor dem Interpreter
    if i >= len(w):
        return []
    if _VAR_RX.search(w[i]) or "$(" in w[i]:  # v15 (#87): Befehl über Variable (`B=/x/werkzeug; $B …`) – auflösen wie geschrieben, sonst nicht prüfbar
        wort = _var_ersetzen(w[i], zuweisungen or {})
        if "$" in wort:
            return [("fragen", f"S06-CODE-MODE: Befehl über unaufgelöste Variable ({w[i]}) – nicht prüfbar")]
        w = w[:i] + [wort] + w[i + 1:]
    if (v := _vertraut_bewerten(cfg, w, i, cmd, cwd, basis, zuweisungen)) is not None:
        if rolle != "claude":  # V15b (Punkt 10, Entscheidung der Inhaberin 22.11.): Freigabe gilt nur Claude
            return [("nein", f"S06-CODE-MODE: vertrautes Werkzeug {w[i]} ist nur für die Rolle claude freigegeben")]
        return v
    prog = w[i].rsplit("/", 1)[-1]
    # Variablen im Inline-Code: Zuweisungen aus vorangehenden Teilbefehlen und Präfixen (`X=… python3 -c "$X"`), dann Umgebung
    zuw = dict(zuweisungen or {})
    zuw.update(t.split("=", 1) for t in w[:i] if _PRAEFIX_ZUWEISUNG.fullmatch(t))

    def variablen(code: str, ersatz: str | None) -> str:
        def wert(m) -> str:
            name = m.group(1) or m.group(2)
            if zuw.get(name) == _UNSICHER:  # mehrfach zugewiesen: wie unbekannt (nie Umgebung, nie Platzhalter in den Code)
                return ersatz or m.group(0)
            return zuw.get(name, os.environ.get(name, ersatz or m.group(0)))
        return _VAR_RX.sub(wert, code)
    rest = w[i + 1:]
    vorher = _maskiert(cmd)[:pos].rstrip()
    aus_pipe = (vorher.endswith("|") and not vorher.endswith("||")) or vorher.endswith("|&")  # auch zsh/bash `|&`

    def stdin(j: int) -> list[tuple[str, str]] | None:
        """Interpreter ohne Skriptdatei an Stelle j: Code aus Pipe, `<` oder /dev/stdin → fragen; None = Datei folgt."""
        if j < len(rest) and not (rest[j].startswith("<") or rest[j] in ("-", "/dev/stdin")):
            return None
        if aus_pipe or j < len(rest):
            return [("fragen", f"S06-CODE-MODE: {prog} liest Code von stdin (Pipe, < oder /dev/stdin) – nicht prüfbar")]
        return []

    if PYTHON.match(prog):
        def inline(code: str, art: str) -> list[tuple[str, str]]:
            ordner = _py_suchordner(basis, zuw)  # v16 (#71): Import einer Projektdatei wie `python3 projektdatei.py`
            stufe, gruende = code_pruefen(cfg, code, None, cwd, f"Inline-Code ({prog} {art})",
                                          ordner if isinstance(ordner, list) else None)
            aus = [] if stufe == "ja" else [(stufe, g) for g in gruende]
            try:
                koepfe = [n.split(".")[0] for k in ast.walk(ast.parse(code)) if isinstance(k, (ast.Import, ast.ImportFrom))
                          for n in ([a.name for a in k.names] if isinstance(k, ast.Import) else [k.module or ""]) if n]
            except (SyntaxError, ValueError):
                koepfe = []  # Syntaxfehler meldet code_pruefen („nein“)
            if not isinstance(ordner, list):  # V15b: ohne Suchpfad keine Schatten-Prüfung – wie bei -m nicht prüfbar
                if koepfe:
                    aus.append(("fragen", f"S06-CODE-MODE: {prog} {art} mit Import: {ordner} – nicht prüfbar"))
            elif g := _py_kandidat_geschrieben(cfg, koepfe, ordner, cmd, cwd):  # V15b (Nr. 1): im selben Befehl geschrieben
                aus.append(g)
            return aus

        def heredoc(art: str) -> list[tuple[str, str]]:
            rumpf = _heredoc_rumpf(cmd, pos)
            if rumpf is None:
                return [("fragen", "S06-CODE-MODE: Heredoc-Rumpf nicht eindeutig erkennbar – nicht prüfbar")]
            return inline(rumpf, art)

        j = 0
        while j < len(rest):
            a = rest[j]
            if a == "-":
                if not _heredocs(seg):
                    return [("fragen", "S06-CODE-MODE: `python3 -` liest Code von stdin – nicht prüfbar")]
                return heredoc("- <<Heredoc")
            if a.startswith("--") or not a.startswith("-"):
                if a.startswith("--"):
                    j += 1
                    continue
                break
            for k, c in enumerate(a[1:], 1):  # Optionsgruppe wie -Bc, -IXdev, -W error
                if c == "m":
                    modul = a[k + 1:] or (rest[j + 1] if j + 1 < len(rest) else "")
                    modul = variablen(modul, None)
                    if not re.fullmatch(r"[A-Za-z_][\w.]*", modul):
                        return [("fragen", f"S06-CODE-MODE: python3 -m mit unklarem Modulnamen ({modul or 'leer'}) – nicht prüfbar")]
                    return _python_m(cfg, modul, cmd, cwd, basis, zuw)
                if c == "c":
                    code = a[k + 1:] or (rest[j + 1] if j + 1 < len(rest) else None)
                    if code is None:
                        return [("fragen", "S06-CODE-MODE: python3 -c ohne Code – nicht prüfbar")]
                    code = variablen(code, "NORMENVAR")  # unbekannt: Platzhalter – in Strings harmlos, als Code nicht prüfbar
                    try:
                        baum = ast.parse(code)
                    except (SyntaxError, ValueError):
                        return inline(code, "-c")  # code_pruefen meldet den Syntaxfehler („nein“)
                    if any(isinstance(n, ast.Name) and n.id == "NORMENVAR" for n in ast.walk(baum)):
                        return [("fragen", "S06-CODE-MODE: python3 -c mit unbekannter Variable als Code – nicht prüfbar")]
                    return inline(code, "-c")
                if c in "XW":
                    j += 0 if a[k + 1:] else 1
                    break
            j += 1
        if (j >= len(rest) or rest[j].startswith("<") or rest[j] == "/dev/stdin") and _heredocs(seg):
            return heredoc("<<Heredoc")  # `python3 <<PY` / `python3 /dev/stdin <<PY`: Rumpf ist Code wie bei `-`
        if (b := stdin(j)) is not None:
            return b
        return _skript_datei_arg(cfg, rest[j], cmd, cwd, rolle, tiefe, basis, "python", zuw=zuweisungen)
    if prog in ("bash", "sh", "zsh"):
        j, mit_c = 0, False  # Optionen vor Code/Datei: -c, -lc, -e -c, -o name …
        while j < len(rest) and rest[j].startswith("-") and rest[j] not in ("-", "--"):
            mit_c = mit_c or (not rest[j].startswith("--") and "c" in rest[j][1:])
            j += 2 if rest[j] in ("-o", "-O") else 1
        if mit_c:  # -c: Inline-Code wie bisher (G4-A-Weg)
            if j >= len(rest):
                return [("fragen", f"S06-CODE-MODE: {prog} -c ohne Code – nicht prüfbar")]
            if tiefe >= 3:
                return [("fragen", "S06-CODE-MODE: -c-Verschachtelung zu tief – nicht prüfbar")]
            code = variablen(rest[j], None)
            if any(s.strip().startswith("$") for s in _segmente(code)):
                return [("fragen", f"S06-CODE-MODE: {prog} -c mit unbekannter Variable als Befehl – nicht prüfbar")]
            stufe, gruende = bewerten(cfg, rolle, "Bash", {"command": code}, cwd, _tiefe=tiefe + 1)
            return [] if stufe == "ja" else [(stufe, g) for g in gruende]
        if j < len(rest) and rest[j] == "--":
            j += 1
        if _heredocs(seg) and (j >= len(rest) or rest[j].startswith("<")):
            return []  # `bash <<EOF`: Rumpf bleibt im Befehl und wird zeilenweise geprüft
        if (b := stdin(j)) is not None:
            return b
        return _skript_datei_arg(cfg, rest[j], cmd, cwd, rolle, tiefe, basis, "shell", zuw=zuweisungen)
    if prog in ("source", "."):
        if rest and rest[0].startswith("-") and rest[0] != "-":
            return []
        if (b := stdin(0)) is not None:
            return b
        return _skript_datei_arg(cfg, rest[0], cmd, cwd, rolle, tiefe, basis, "shell", zuw=zuweisungen)
    if prog in ("node", "perl", "ruby"):
        j = 0  # Optionen; -e/-p CODE ist Inline-Code ohne Parser → fragen
        while j < len(rest) and rest[j].startswith("-") and rest[j] != "-":
            if rest[j] in ("-e", "-p", "-E", "--eval", "--print") or (rest[j][1:2] != "-" and "e" in rest[j][1:]):
                return [("fragen", f"S06-CODE-MODE: {prog} mit Inline-Code (-e) – nicht prüfbar")]
            j += 1
        b = stdin(j)
        if _heredocs(seg) or b:
            return [("fragen", f"S06-CODE-MODE: {prog} liest Code von stdin oder Heredoc – nicht prüfbar")]
        if b is not None:
            return []  # interaktiv ohne Eingabe
        return _skript_datei_arg(cfg, rest[j], cmd, cwd, rolle, tiefe, basis, "fragen", prog, zuw=zuweisungen)
    if "/" in w[i]:  # direkter Aufruf über einen Pfad: /tmp/x.sh, ./x.sh, $RUN/x …
        voll = os.path.expanduser(w[i])
        if os.path.isabs(voll) and os.path.dirname(os.path.normpath(voll)) in {
                os.path.normpath(d) for d in os.environ.get("PATH", "").split(os.pathsep) if os.path.isabs(d)}:
            return []  # installiertes Werkzeug aus $PATH (/opt/homebrew/bin/brew) – wie der Aufruf ohne Pfad
        datei, grund = _skript_pfad(w[i], basis, zuweisungen)
        if grund:
            return [("fragen", grund)]
        gate = _skript_gate(cfg, datei, w[i], cmd)
        if gate is not None:
            return gate
        g = _skript_geschrieben(w[i], datei, cmd, cwd)
        if g:
            return [g]
        try:
            with datei.open("rb") as f:
                kopf = f.read(4096)
        except OSError as e:
            return [("nein", f"S06-CODE-MODE: Skript nicht prüfbar ({type(e).__name__}: {e})")]
        if not kopf.startswith(b"#!"):
            if b"\x00" in kopf:
                return []  # Binärdatei (z. B. /usr/bin/git, /bin/ls) – wie bisher
            return _shell_datei_bewerten(cfg, datei, w[i], cmd, cwd, rolle, tiefe, basis)  # Text ohne Shebang: sh-Skript
        worte = kopf.split(b"\n", 1)[0][2:].decode("utf-8", "replace").split()
        if not worte:
            return _shell_datei_bewerten(cfg, datei, w[i], cmd, cwd, rolle, tiefe, basis)
        interp = worte[0].rsplit("/", 1)[-1]
        if interp == "env" and len(worte) > 1:  # #!/usr/bin/env python3 …: nächses Wort ist der Interpreter
            interp = worte[1].rsplit("/", 1)[-1]
        if PYTHON.match(interp):
            stufe, gruende = skript_pruefen(cfg, datei, cwd)
            return [] if stufe == "ja" else [(stufe, g) for g in gruende]
        if interp in ("bash", "sh", "zsh"):
            return _shell_datei_bewerten(cfg, datei, w[i], cmd, cwd, rolle, tiefe, basis)
        return [("fragen", f"S06-CODE-MODE: {interp}-Skript außerhalb des Projekts – nicht prüfbar")]
    return []


# ---------------------------------------------------------------- G5: Datenschutz vor vibe/agy (Prompt vor dem Start prüfen)
_TEAM_RX = re.compile(r"(^|[\s;&|(])(\S*/)?(vibe|agy)(\s|$)")
_CAT_PROMPT_RX = re.compile(r"^\$\(\s*cat\s+(\S+)\s*\)$")
_PFADWORT_RX = re.compile(r"[\w.~$-]*/[\w./~$*-]*")
_WORT_ENDE = '.,;:!?)]}"\'`'
_GEHEIM_INHALT = [
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "Private Key"),
    (re.compile(r"ghp_[A-Za-z0-9]{30,}"), "GitHub-Token ghp_…"),
    (re.compile(r"github_pat_\w{20,}"), "GitHub-PAT github_pat_…"),
    (re.compile(r"sk-[A-Za-z0-9_-]{20,}"), "API-Schlüssel sk-…"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS-Schlüssel AKIA…"),
    (re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"), "Slack-Token xox…"),
    (re.compile(r"AIza[0-9A-Za-z_-]{35}"), "Google-API-Schlüssel AIza…"),
]
_PFLICHT_ROLLEN = ("mistral-team", "gemini-analyst")


def _zuweisungen_aus_seg(seg: str) -> dict[str, str]:
    """Zuweisungen eines Teilbefehls, der ausschließlich aus Zuweisungen besteht (RUN=/x, RUN=\"/x\", export RUN=/x);
    Wert ohne Anführungszeichen (shlex.split)."""
    try:
        w = shlex.split(seg)
    except ValueError:
        return {}
    if w and w[0] == "export":
        w = w[1:]
    if not w or not all(_PRAEFIX_ZUWEISUNG.fullmatch(t) for t in w):
        return {}
    return {t.split("=", 1)[0]: t.split("=", 1)[1] for t in w}


def _var_ersetzen(text: str, zuweisungen: dict[str, str]) -> str:
    """$VAR/${VAR} ersetzen: zuerst Zuweisungen aus vorangehenden Teilbefehlen, dann os.environ (expandvars);
    Unbekannte bleiben als $VAR stehen."""

    def rep(m):
        return zuweisungen.get(m.group(1) or m.group(2), m.group(0))

    return os.path.expandvars(_VAR_RX.sub(rep, text))


def _prompt_wort(wort: str, basis: str | None) -> str:
    """Pfadartiges Wort für den Glob-Vergleich normalisieren: Satzzeichen am Ende weg, ./ weg,
    absolut unter ROOT/basis → relativ zum Projekt."""
    w = wort.rstrip(_WORT_ENDE)
    if w.startswith("./"):
        w = w[2:]
    if w.startswith("/"):
        p = _echt(w)  # V15b Nr. 20: Schreibweise wie auf der Platte (wie #74)
        for wurzel in [_echt(ROOT)] + ([_echt(basis)] if basis else []):
            try:
                return p.relative_to(wurzel).as_posix()
            except ValueError:
                continue
    return w


def _prompt_inhalt_pruefen(cfg: dict, werkzeug: str, text: str, basis: str | None) -> list[tuple[str, str]]:
    """G5: Prompt-Text prüfen – zuerst den Pflichtblock (auftrag_zeilen beider Team-Rollen) zeilenweise entfernen,
    dann im Rest Sperrpfade, Geheimnis-Inhalte, Geheimnis-Pfade (nur agy) und Forschungsdaten suchen."""
    pf = cfg["projekt"].get("pfade", {})
    pflicht: set[str] = set()
    for r in _PFLICHT_ROLLEN:
        if r in cfg["rollen"]:
            pflicht.update(z.strip() for z in auftrag_zeilen(cfg, r, []))
    rest = "\n".join(z for z in text.split("\n") if z.strip() not in pflicht)
    gesperrt = [s for s in pf.get("gesperrt", []) if s]
    geheimnisse = pf.get("geheimnisse", [])
    forsch = pf.get("forschungsdaten", [])
    team = "mistral-team" if werkzeug == "vibe" else "gemini-analyst"
    gruende: list[tuple[str, str]] = []
    for z in rest.split("\n"):
        for s in gesperrt:
            if re.search(r"(^|[\s`\"'(/])" + re.escape(s), z, re.IGNORECASE):
                gruende.append(("nein", f"N06-NUR-ERLAUBTE-PFADE: Auftrag nennt gesperrten Pfad {s}"))
        for rx, art in _GEHEIM_INHALT:
            if rx.search(z):
                gruende.append(("nein", f"N03-KEINE-GEHEIMNISSE: Auftrag enthält ein Geheimnis ({art})"))
        worte = [m.group(0) for m in _PFADWORT_RX.finditer(z)]
        for wort in worte:
            w = wort.rstrip(_WORT_ENDE)
            if not w:
                continue
            name = w.rsplit("/", 1)[-1]
            if werkzeug == "agy" and _geheim(name, pf):
                gruende.append(("nein", f"N03-KEINE-GEHEIMNISSE: Auftrag an agy nennt Geheimnis-Datei {w}"))
        for eintrag in forsch:
            if not eintrag:
                continue
            treffer = False
            if "/" in eintrag or "*" in eintrag:
                praefix = eintrag.split("*", 1)[0].rstrip("/")
                for wort in worte:
                    w = _prompt_wort(wort, basis).casefold()  # V15b Nr. 20: ohne Groß-/Kleinschreibung (sichere Richtung)
                    if fnmatch.fnmatchcase(w, eintrag.casefold()) or (praefix and w.rstrip("/") == praefix.casefold()):
                        treffer = True
                        break
            elif eintrag.lower() in rest.lower():
                treffer = True
            if treffer:
                stufe = "nein" if werkzeug == "agy" else "fragen"
                gruende.append((stufe, f"N06-NUR-ERLAUBTE-PFADE: Auftrag enthält Forschungsdaten ({eintrag})"
                                      f" – an {team} nur mit Freigabe"))
    return list(dict.fromkeys(gruende))


def _team_prompt(cfg: dict, seg: str, cmd: str, cwd: str, basis: str | None,
                 zuweisungen: dict[str, str]) -> list[tuple[str, str]]:
    """G5: vibe/agy im Teilbefehl seg – Prompt-Quelle finden (vibe: --prompt-file P bzw. -p/--prompt TEXT;
    agy: -p/--prompt TEXT, "$(cat P)" als Datei), Prompt-Datei samt *.md-Nebendateien bzw. Inline-Text auf
    Sperrpfade, Geheimnisse und Forschungsdaten prüfen. Liefert Befunde (stufe, grund)."""
    try:
        w = shlex.split(seg)
    except ValueError:
        if _TEAM_RX.search(_maskiert(seg)):
            return [("nein", "N06-NUR-ERLAUBTE-PFADE (Auftrag an Team): vibe/agy-Aufruf nicht zerlegbar (unbalanciertes Zitat) – Prompt nicht prüfbar")]
        return []
    i = _praefixe_ueberspringen(w)
    if i >= len(w):
        return []
    prog = w[i].rsplit("/", 1)[-1]
    if prog not in ("vibe", "agy"):
        return []
    rest = w[i + 1:]
    quellen: list[tuple[str, str]] = []
    for j, t in enumerate(rest):
        wert = t.split("=", 1)[1] if "=" in t and t.startswith("--") else (rest[j + 1] if j + 1 < len(rest) else None)
        if prog == "vibe" and (t == "--prompt-file" or t.startswith("--prompt-file=")):
            art = "datei"
        elif t in ("-p", "--prompt") or t.startswith("--prompt="):
            art = "text"
        else:
            continue
        if wert is None:
            return [("nein", f"N06-NUR-ERLAUBTE-PFADE (Auftrag an Team): {prog} {t} ohne Wert – nicht prüfbar")]
        quellen.append((art, wert))
    if len(quellen) > 1:  # welche Quelle das Werkzeug nimmt, ist nicht festgelegt – nie nur eine prüfen
        return [("nein", f"N06-NUR-ERLAUBTE-PFADE (Auftrag an Team): {prog} mit mehreren Prompt-Quellen – nicht prüfbar")]
    quelle = quellen[0] if quellen else None
    if quelle is None:
        if any(t in ("--version", "--help", "-h") for t in rest):
            return []
        # ohne Prompt: interaktiv oder Unterbefehl (vibe config …) – nichts geht ungeprüft an das Team, aber nachfragen
        return [("fragen", f"N06-NUR-ERLAUBTE-PFADE (Auftrag an Team): {prog} ohne Prompt-Quelle (interaktiv/Unterbefehl)")]
    art, wert = quelle
    if art == "text":
        m = _CAT_PROMPT_RX.match(wert)
        if m:
            art, wert = "datei", m.group(1)
        elif "$(" in wert or "`" in wert:
            return [("nein", f"N06-NUR-ERLAUBTE-PFADE (Auftrag an Team): Prompt-Quelle nicht prüfbar (Befehlsersetzung in -p: {wert[:80]})")]
        else:
            wert = _var_ersetzen(wert, zuweisungen)
            if _VAR_RX.search(wert):
                return [("nein", "N06-NUR-ERLAUBTE-PFADE (Auftrag an Team): Prompt-Text mit unaufgelöster Variable – nicht prüfbar")]
            return _prompt_inhalt_pruefen(cfg, prog, wert, basis)
    text = os.path.expanduser(_var_ersetzen(wert, zuweisungen))
    if "$" in text:
        return [("nein", f"N06-NUR-ERLAUBTE-PFADE (Auftrag an Team): Prompt-Datei mit unaufgelöster Variable ({wert})")]
    p = Path(text)
    if not p.is_absolute():
        if basis is None:
            return [("nein", f"N06-NUR-ERLAUBTE-PFADE (Auftrag an Team): Prompt-Datei {wert} relativ, aber Basisordner unbekannt (cd) – nicht prüfbar")]
        p = Path(basis) / p
    p = Path(os.path.realpath(p))
    if not p.is_file():
        return [("nein", f"N06-NUR-ERLAUBTE-PFADE (Auftrag an Team): Prompt-Datei nicht gefunden ({p})")]
    for z in _schreibziele(cmd, cwd):
        if z is None:
            return [("nein", "N06-NUR-ERLAUBTE-PFADE (Auftrag an Team): Prompt-Datei wird im selben Befehl geschrieben (Schreibziel nicht auflösbar)")]
        zr = Path(os.path.realpath(z))
        if zr == p or (zr.parent == p.parent and zr.suffix == ".md"):
            return [("nein", f"N06-NUR-ERLAUBTE-PFADE (Auftrag an Team): Prompt-Datei {p.name} wird im selben Befehl geschrieben – Inhalt nicht prüfbar")]
    try:
        texte = [p.read_text(encoding="utf-8")]
        for n in sorted(os.listdir(p.parent)):
            if n != p.name and n.endswith(".md"):
                texte.append((p.parent / n).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as e:
        return [("nein", f"N06-NUR-ERLAUBTE-PFADE (Auftrag an Team): Prompt-Datei nicht lesbar ({type(e).__name__}: {e})")]
    return _prompt_inhalt_pruefen(cfg, prog, "\n".join(texte), basis)


def cmd_skript(a) -> int:
    stufe, gruende = skript_pruefen(laden(), Path(a.pruefen), os.getcwd())
    print("\n".join([stufe] + [f"- {g}" for g in gruende]))
    return RANG[stufe]


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


# Assert-Zeile in Tests (N02/G9): assert, assertEqual(…, expect(, check(, XCTAssert…(, pytest.raises
# G9-Beleg (V15b Nr. 9): Importzeile am Zeilenanfang (Python, Swift, C) oder require( in JS/Ruby
_G9_IMPORT_RX = re.compile(r"^(import|from|@testable\s+import|#\s*include)\b|\brequire\s*\(")
_G9_KEIN_CODE = {".json", ".toml", ".yaml", ".yml", ".txt", ".md", ".csv"}
_ASSERT_RX = re.compile(r"\bassert\b|\bassert[A-Z]\w*\(|\bexpect\(|\bcheck\(|XCTAssert\w*\(|pytest\.raises")


def _diff_zeilen(basis: str | None, staged: bool) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """Entfernte und hinzugefügte Zeilentexte je Datei (git diff --unified=0; untracked = ganze Datei neu).
    --no-renames: eine aus den Test-Globs umbenannte Datei zählt als entfernt + neu (sonst fehlen die entfernten Zeilen)."""
    args = (["diff", "--unified=0", "--no-color", "--no-ext-diff", "--no-renames"]
            + (["--cached"] if staged else [basis or "HEAD"]))
    weg: dict[str, list[str]] = {}
    neu: dict[str, list[str]] = {}
    datei = None
    for z in _git(*args).splitlines():
        if z.startswith("--- a/"):
            datei = z[6:]
        elif z == "--- /dev/null":
            datei = None
        elif z.startswith("+++ b/"):
            datei = z[6:]
        elif z == "+++ /dev/null":
            pass  # gelöschte Datei: Dateiname bleibt der vom --- a/…
        elif datei and z.startswith("-"):
            weg.setdefault(datei, []).append(z[1:])
        elif datei and z.startswith("+"):
            neu.setdefault(datei, []).append(z[1:])
    if not staged:
        for f in _git("ls-files", "-o", "--exclude-standard").splitlines():
            if f:
                try:
                    neu[f] = (ROOT / f).read_text(encoding="utf-8").splitlines()
                except (OSError, UnicodeDecodeError):
                    pass  # unlesbar: überspringen (wie in _diff)
    return weg, neu


def erzeugt_kurz(cfg: dict, fuer_agents: bool = False) -> str:
    """kurz.md; fuer_agents=True: Block für AGENTS.md (Vibe/agy) ohne Normen mit nur_rollen."""
    meta, pj = cfg["meta"], cfg["projekt"]
    z = [f"# Agenten-Normen (Kurzfassung, v{meta['version']}, Stand {meta['stand']})", "",
         "Gilt für alle Agenten in diesem Projekt (Claude Code, Mistral Vibe, Antigravity/Gemini, lokale Modelle). "
         "Volltext mit Begründungen und Quellen: `normen/normen.toml`; Zuständigkeiten: `normen/rollen.toml`; "
         "Projektwerte: `normen/projekt.toml`. Bei Widerspruch gilt die strengere Regel.", ""]
    for stufe, titel in (("muss", "Muss (technisch durchgesetzt, soweit möglich)"), ("soll", "Soll")):
        z += [f"## {titel}"]
        for n in cfg["normen"]:
            if n["stufe"] != stufe or (fuer_agents and "nur_rollen" in n):
                continue
            zusatz = " _(nur Hauptsitzung/Orchestrator)_" if "nur_rollen" in n else ""
            z.append(f"- **{n['id']} – {n['titel']}:**{zusatz} {n['prompt']}")
        z.append("")
    z += ["## Rollen", ""]
    if meta.get("rollen_kette"):
        z += [f"**Rollenkette:** {meta['rollen_kette']}", ""]
    z += ["| Rolle | darf | nur mit Rückfrage | verantwortet |", "|---|---|---|---|"]
    for name, r in cfg["rollen"].items():
        if r.get("art") == "regelsatz":
            continue
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
    return f"{MARKE_ANFANG}\n{erzeugt_kurz(cfg, fuer_agents=True)}{MARKE_ENDE}\n"


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
        # G9: Asserts in Testdateien geändert oder ersatzlos entfernt? Vergleich über alle Testdateien des Diffs
        # gemeinsam – Verschiebungen (auch über Dateigrenzen) heben sich auf.
        weg_z, neu_z = _diff_zeilen(basis, staged)
        weg: Counter[str] = Counter()
        neu: Counter[str] = Counter()
        weg_datei: dict[str, list[str]] = {}
        # v16 (#61): Testdatei ganz gelöscht samt getestetem Altcode (N08) → Hinweis statt Fehler. Beleg: der Diff löscht
        # eine Nicht-Testdatei, deren Dateistamm als ganzes Wort in der gelöschten Testdatei vorkommt.
        geloescht = [z[2:] for z in _git(*(["diff", "--name-status", "--no-renames"]
                                           + (["--cached"] if staged else [basis or "HEAD"]))).splitlines()
                     if z.startswith("D\t")]
        # `__init__` steht in fast jeder Python-Testdatei – kein Beleg; Daten/Doku und Ausgeschlossenes auch nicht (V15b Nr. 9)
        ausgeschl = pj.get("pruefen", {}).get("ausschliessen", [])
        alt = [p for p in geloescht if not any(passt(p, g) for g in tests) and Path(p).stem != "__init__"
               and Path(p).suffix.lower() not in _G9_KEIN_CODE and not any(p.startswith(x) for x in ausgeschl)]
        for rel in geloescht:
            if rel not in weg_z or not any(passt(rel, g) for g in tests):
                continue
            # Beleg nur aus Importzeilen (Stamm als ganzes Wort in derselben Zeile); mehrzeilige Importe → kein Beleg
            importe = [z.strip() for z in weg_z[rel] if _G9_IMPORT_RX.search(z.strip())]
            code = next((p for p in alt if any(re.search(r"(?<!\w)" + re.escape(Path(p).stem) + r"(?!\w)", z)
                                               for z in importe)), None)
            if code is not None:
                anzahl = sum(1 for z in weg_z.pop(rel) if _ASSERT_RX.search(z.strip()))
                melde(rel, "N02-TESTS-SIND-TABU", "hinweis",
                      f"Testdatei gelöscht mit dem getesteten Code {code} ({anzahl} Asserts) – Review nötig "
                      f"(nur Orchestrator/{inhaberin(cfg)})")
        for rel, zeilen in weg_z.items():
            if any(passt(rel, g) for g in tests):
                for z in zeilen:
                    if _ASSERT_RX.search(z.strip()):
                        weg[z.strip()] += 1
                        weg_datei.setdefault(rel, []).append(z.strip())
        for rel, zeilen in neu_z.items():
            if any(passt(rel, g) for g in tests):
                for z in zeilen:
                    if _ASSERT_RX.search(z.strip()):
                        neu[z.strip()] += 1
        # nur als Kommentar (# … / // …) – erklärender Text in Doku/CHANGELOG ist keine Begründung
        begr_rx = re.compile(r"^\s*(#|//)\s*" + re.escape(f"{marker} N02-TESTS-SIND-TABU"))
        begruendet = sum(1 for zeilen in neu_z.values() for z in zeilen if begr_rx.search(z))
        ersatzlos = max(0, sum(weg.values()) - sum(neu.values()))
        rest = ersatzlos - begruendet
        if rest <= 0:
            ausnahmen += min(begruendet, ersatzlos)
        uebrig: list[tuple[str, str]] = []
        neu_rest = neu.copy()
        for rel in sorted(weg_datei):
            for z in weg_datei[rel]:
                if neu_rest[z] > 0:
                    neu_rest[z] -= 1
                else:
                    uebrig.append((rel, z))
        if rest > 0:
            for rel, z in uebrig[:rest]:
                melde(rel, "N02-TESTS-SIND-TABU", "fehler", f"Assert entfernt: {z[:100]}")
        else:
            je_datei: dict[str, list[str]] = {}
            for rel, z in uebrig:
                je_datei.setdefault(rel, []).append(z)
            for rel in sorted(je_datei):
                for z in je_datei[rel][:3]:
                    melde(rel, "N02-TESTS-SIND-TABU", "hinweis", f"Assert geändert: -{z[:100]}")
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
            if s and s.casefold() in z.casefold():
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
    labels = ["rueckmeldung", f"art:{a.art}"] + ([f"stufe:{a.stufe}"] if a.stufe else [])  # v16 (#75): Stufe als Label
    r = subprocess.run(basis + [x for lb in labels for x in ("--label", lb)], capture_output=True, text=True)
    if r.returncode != 0 and "label" in r.stderr.lower():
        r = subprocess.run(basis, capture_output=True, text=True)
        if r.returncode == 0:
            print(f"Hinweis: Labels fehlen im Ziel ({', '.join(labels)}; `gh label create` im Rückmelde-Repository) – "
                  "Issue ohne Labels angelegt.")
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
        _git("fetch", "-q", "origin")
        kopf = _git("rev-parse", "HEAD").strip()
        for versuch in range(4):  # direkt nach `git push` kennt GitHub den neuen PR-Kopf manchmal erst nach Sekunden
            pr = json.loads(subprocess.run(["gh", "pr", "view", str(a.pr), "--json", "state,baseRefName,headRefName,headRefOid"],
                                           cwd=ROOT, capture_output=True, text=True, check=True).stdout)
            if pr["headRefOid"] == kopf or pr["state"] != "OPEN" or versuch == 3:
                break
            time.sleep(5)
        basis = pr["baseRefName"]
        if pr["state"] != "OPEN" or basis not in ("main", "master"):
            return stopp(f"PR {a.pr} ist {pr['state']} bzw. zielt auf {basis}.")
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
    if (ROOT / "PLAN.md").exists() and not subprocess.run(
            ["git", "-C", str(ROOT), "diff", "--quiet", f"origin/{basis}...HEAD", "--", "PLAN.md"]).returncode:
        print("Hinweis: PLAN.md im PR unverändert – erledigte Aufgabe abhaken?", flush=True)
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


def auftrag_zeilen(cfg: dict, rolle: str, dateien: list[str]) -> list[str]:
    """Die Auftragszeilen (Pflichtblock) für eine Rolle – schreibt nichts (kein .normen-auftrag wird angelegt)."""
    globs = dateien or []
    pj = cfg["projekt"]
    z = [f"Normen für diesen Auftrag (Rolle {rolle}, Normen v{cfg['meta']['version']}) – verbindlich:",
         "- Außerhalb des Projektordners wird ohne ausdrückliche Erlaubnis nichts gelöscht oder geändert.",
         "- Lösche niemals Dateien, die du in diesem Lauf nicht selbst angelegt hast, auch keine unbekannten oder untracked "
         "Dateien. Kein rm, kein git clean, kein git restore auf fremde Dateien.",
         "- Du darfst NUR diese Pfade ändern: " + (", ".join(f"`{g}`" for g in globs) if globs else "keine (nur lesen)."),
         "- `.normen-auftrag` nie lesen, ändern oder erweitern – nur Claude vergibt Pfade. Brauchst du eine weitere Datei: "
         "anhalten und im Bericht nennen.",
         # v16 (#71): Vibe erreichte einen gesperrten `python -c`-Aufruf per `python -m` aus dem Lauf-Ordner
         "- Sperrt ein Normen-Hook einen Aufruf: denselben Zweck nicht auf anderem Weg erreichen (anderer Befehl, Skript, "
         "Ordner, `-m` statt `-c`), sondern anhalten und die Sperrmeldung wörtlich im Bericht nennen."]
    for n in cfg["normen"]:
        if rolle in n.get("nur_rollen", [rolle]):
            z.append(f"- {n['id']}: {n['prompt']}")
    gesperrt = pj.get("pfade", {}).get("gesperrt", [])
    if gesperrt and darf(cfg, rolle, "sperrpfade-lesen") != "ja":
        z.append("- Diese Pfade nicht lesen und nicht öffnen: " + ", ".join(f"`{s}`" for s in gesperrt))
    if cfg["rollen"][rolle].get("abnahme_durch_claude"):
        z.append("- Abnahme: Testbefehl und Normenprüfung führt Claude selbst aus. Führe keine Test-, Build- oder Prüfbefehle aus; "
                 "Dateien nur mit dem Lesewerkzeug lesen, nicht im Terminal; Shell nur ls, pwd, git status.")
    else:
        z.append(f"- Abnahme: `{pj['projekt']['testbefehl']}` grün und `python3 normen/normen.py pruefen --diff` ohne Fehler – "
                 "beide Befehle mit Ergebnis in den Bericht.")
    return z


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
    if a.rolle in KEINE_AUFTRAEGE:
        print(f"Rolle {a.rolle} bekommt keine Aufträge.", file=sys.stderr)
        return 64
    if a.dateien:  # v14: jedes Argument ist genau ein Pfad (auch mit Leerzeichen) – nie an Leerraum trennen
        AUFTRAG.write_text("# erlaubte Pfade (Globs) für den laufenden Auftrag – von normen.py auftrag geschrieben\n"
                           + "\n".join(a.dateien) + "\n", encoding="utf-8")
        _siegel().write_text(hashlib.sha256(AUFTRAG.read_bytes()).hexdigest() + "\n", encoding="utf-8")
    print("\n".join(auftrag_zeilen(cfg, a.rolle, _auftrag_globs() or [])))
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
    p = sub.add_parser("skript", help="Code-Mode-Skript prüfen wie der Hook (S06); Exit 0 ja, 1 fragen, 2 nein")
    p.add_argument("--pruefen", required=True, metavar="DATEI")
    p.set_defaults(f=cmd_skript)
    p = sub.add_parser("selbsttest", help="Hooks live prüfen (Köder-Befehl und Datei-Werkzeuge); Exit 0 nur wenn alle geprüften Wege sperren")
    p.add_argument("--werkzeug", choices=["claude", "vibe"], default=None, help="nur dieses Werkzeug prüfen (Standard: beide)")
    p.add_argument("--weg", choices=list(SELBSTTEST_TEXTE), default=None, help="nur dieser Weg prüfen (Standard: alle Wege des Werkzeugs)")
    p.add_argument("--sitzung", action="store_true",
                   help=f"laufende Claude-Sitzung prüfen: vorher `{KOEDER_BEFEHL}` in dieser Sitzung ausführen (muss gesperrt werden)")
    p.set_defaults(f=cmd_selbsttest)
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
