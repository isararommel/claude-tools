#!/usr/bin/env bash
# einrichten.sh – legt aus den Vorlagen in qs/ ein QS-Projekt mit einem Gutachter-Büro je Rolle an. Läuft auf dem Mac.
#   bash qs/einrichten.sh <qs-ziel> [--benutzer-agents]
#   Beispiel: bash qs/einrichten.sh ~/Projekte/qs --benutzer-agents
# Je Rolle aus qs/rollen/*.md: <qs-ziel>/buero-<name>/{eingang,ausgang}/.gitkeep, CLAUDE.md (Büroordnung),
#   .claude/settings.json (CLAUDE.md-Ausschlüsse, kein Auto-Memory, Schreibsperre außerhalb), .claude/agents/<name>.md.
# --benutzer-agents: zusätzlich ~/.claude/agents/gutachter-<name>.md (Sub-Agent ohne Schreibwerkzeuge, omitClaudeMd).
# Überschreibt nichts: gleiche Datei → unverändert; abweichende Fassung → <datei>.vorlage daneben.
set -euo pipefail
QUELLE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ZIEL=""; BENUTZER=0
while [ $# -gt 0 ]; do case "$1" in
  --benutzer-agents) BENUTZER=1; shift ;;
  -*) echo "Unbekannte Option: $1" >&2; exit 64 ;;
  *) ZIEL="$1"; shift ;;
esac; done
AUFRUF="Aufruf: bash qs/einrichten.sh <qs-ziel> [--benutzer-agents]"
[ -n "$ZIEL" ] || { echo "$AUFRUF" >&2; exit 64; }
[ -d "$ZIEL" ] || { echo "Ziel fehlt: $ZIEL" >&2; echo "$AUFRUF" >&2; exit 64; }
ZIEL="$(cd "$ZIEL" && pwd -P)"
[ -d "$ZIEL/.git" ] || echo "Hinweis: $ZIEL ist kein Git-Repository."

python3 - "$QUELLE" "$ZIEL" "$HOME" "$BENUTZER" <<'PY'
import json
import sys
from pathlib import Path

quelle, ziel, home, benutzer = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], sys.argv[4] == "1"
SCHLUESSEL = ("name", "titel", "description", "tools-buero", "tools-gutachter")
EINLEITUNG = ("Du arbeitest als Sub-Agent einer anderen Sitzung. Schreibe keine Dateien, rufe keine weiteren Agenten und nie das\n"
              "Werkzeug advisor auf. Gib das Gutachten vollständig als Antwort zurück.")


def abbruch(text):
    print(f"Fehler: {text}", file=sys.stderr)
    sys.exit(1)


def zerlege(pfad):  # Kopf zwischen den ersten beiden '---' (ohne YAML-Paket), Rest = Rollentext
    zeilen = pfad.read_text(encoding="utf-8").split("\n")
    if not zeilen or zeilen[0].strip() != "---" or "---" not in zeilen[1:]:
        abbruch(f"{pfad}: Kopf zwischen '---' fehlt")
    ende = zeilen.index("---", 1)
    werte = {}
    for zeile in zeilen[1:ende]:
        schluessel, trenner, wert = zeile.partition(":")
        if trenner:
            werte[schluessel.strip()] = wert.strip()
    for s in SCHLUESSEL:
        if not werte.get(s):
            abbruch(f"{pfad}: Kopf-Schlüssel '{s}' fehlt")
    return werte, "\n".join(zeilen[ende + 1:]).strip()


def roh(text):  # Wert für einen JSON-String ohne die äußeren Anführungszeichen
    return json.dumps(text, ensure_ascii=False)[1:-1]


format_text = (quelle / "gutachten-format.md").read_text(encoding="utf-8").strip()
buero_vorlage = (quelle / "buero" / "CLAUDE.md").read_text(encoding="utf-8")
settings_vorlage = (quelle / "buero" / "settings.json").read_text(encoding="utf-8")

eltern, ordner = [], ziel  # CLAUDE.md-Dateien von ZIEL aufwärts bis einschließlich '/'
while True:
    basis = "" if ordner == ordner.parent else str(ordner)
    for name in ("CLAUDE.md", ".claude/CLAUDE.md", "CLAUDE.local.md"):
        eltern.append(f'\n    "{roh(basis + "/" + name)}",')
    if ordner == ordner.parent:
        break
    ordner = ordner.parent

rollen = sorted((quelle / "rollen").glob("*.md"))
if not rollen:
    abbruch(f"keine Rollen in {quelle / 'rollen'}")
dateien, namen = {}, []
for pfad in rollen:
    w, rollentext = zerlege(pfad)
    name = w["name"]
    namen.append(name)
    buero = ziel / f"buero-{name}"
    dateien[buero / "eingang" / ".gitkeep"] = ""
    dateien[buero / "ausgang" / ".gitkeep"] = ""
    dateien[buero / "CLAUDE.md"] = buero_vorlage.replace("@@ROLLE@@", name).replace("@@TITEL@@", w["titel"])
    settings = (settings_vorlage.replace("@@ELTERN@@", "".join(eltern))
                .replace("@@HOME@@", roh(home)).replace("@@BUERO@@", roh(str(buero))))
    try:
        json.loads(settings)
    except ValueError as fehler:
        abbruch(f"settings.json für {name} ist kein gültiges JSON: {fehler}")
    dateien[buero / ".claude" / "settings.json"] = settings
    dateien[buero / ".claude" / "agents" / f"{name}.md"] = (
        f"---\nname: {name}\ndescription: QS-Büro {w['titel']}: {w['description']}\ntools: {w['tools-buero']}\n---\n"
        f"{rollentext}\n\n{format_text}\n")
    if benutzer:
        dateien[Path(home) / ".claude" / "agents" / f"gutachter-{name}.md"] = (
            f"---\nname: gutachter-{name}\n"
            f"description: QS-Gutachter ({w['titel']}), schreibt keine Dateien, liefert ein Gutachten als Antwort: {w['description']}\n"
            f"tools: {w['tools-gutachter']}\nomitClaudeMd: true\n---\n"
            f"{EINLEITUNG}\n\n{rollentext}\n\n{format_text}\n")

reste = [str(p) for p, inhalt in dateien.items() if "@@" in inhalt]
if reste:
    abbruch("Platzhalter '@@' übrig in: " + ", ".join(reste))

for pfad, inhalt in dateien.items():  # erst alles erzeugt und geprüft, jetzt schreiben – nie überschreiben
    if pfad.exists():
        if pfad.read_text(encoding="utf-8") == inhalt:
            print(f"  vorhanden  {pfad} (unverändert)")
        else:
            vorlage = Path(f"{pfad}.vorlage")
            vorlage.write_text(inhalt, encoding="utf-8")
            print(f"  abweichend {pfad} → {vorlage}")
    else:
        pfad.parent.mkdir(parents=True, exist_ok=True)
        pfad.write_text(inhalt, encoding="utf-8")
        print(f"  neu        {pfad}")

for name in namen:
    print(f'Fertig. Büro starten: cd "{ziel}/buero-{name}" && claude --agent {name}')
PY
