#!/usr/bin/env bash
# einrichten-hier.sh – richtet Agenten-Normen und Multi-KI-Ablauf in DEM Ordner ein, in dem dieses Skript liegt.
# Verwendung: Skript in das neue Projekt kopieren, dort ausführen:
#   bash einrichten-hier.sh                                   (fragt nach Testbefehl und Sperrpfaden)
#   bash einrichten-hier.sh --test "make test" --sperre "daten/" [--name …] [--inhaberin …] [--benutzer-agents]
# Quelle: $CLAUDE_TOOLS, sonst ~/Documents/Projekte/claude-tools. Mehrfach ausführbar; danach darf das Skript weg.
set -uo pipefail

ZIEL="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
QUELLE="${CLAUDE_TOOLS:-$HOME/Documents/Projekte/claude-tools}"

if [ ! -f "$QUELLE/einrichten.sh" ]; then
  echo "claude-tools nicht gefunden unter $QUELLE – Pfad mit CLAUDE_TOOLS=… angeben." >&2
  exit 1
fi
if [ "$ZIEL" = "$(cd "$QUELLE" && pwd)" ]; then
  echo "Das Skript liegt in claude-tools selbst – erst in das neue Projekt kopieren." >&2
  exit 1
fi

ARGS=("$@")
if [[ " $* " != *" --test "* ]]; then
  read -r -p "Testbefehl des Projekts (muss schon grün laufen, z. B. make test): " TEST
  [ -n "$TEST" ] || { echo "Ohne Testbefehl geht es nicht." >&2; exit 64; }
  ARGS+=(--test "$TEST")
  read -r -p "Gesperrte Pfade, nie an externe Teams (Leerzeichen-getrennt, leer = keine): " SPERREN
  for s in $SPERREN; do ARGS+=(--sperre "$s"); done
fi

if [ ! -d "$ZIEL/.git" ]; then
  read -r -p "$ZIEL ist kein Git-Repository. Jetzt mit 'git init -b main' anlegen? [j/N] " JA
  if [ "$JA" = "j" ]; then
    git -C "$ZIEL" init -b main || { echo "git init fehlgeschlagen." >&2; exit 1; }
  fi
fi

echo "Richte $ZIEL aus $QUELLE ein …"
bash "$QUELLE/einrichten.sh" "$ZIEL" "${ARGS[@]}"
status=$?
if [ "$status" -ne 0 ]; then
  echo "Einrichten fehlgeschlagen (Exit $status)." >&2
  exit "$status"
fi
echo
echo "Fertig. Nächste Schritte:"
echo "  1. git status und git diff in $ZIEL ansehen, dann committen (ohne dieses Skript)."
echo "  2. Claude Code im Projektordner neu starten – Hooks wirken erst dann."
echo "  3. Dieses Skript kann gelöscht werden: $ZIEL/einrichten-hier.sh"
