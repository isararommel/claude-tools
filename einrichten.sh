#!/usr/bin/env bash
# einrichten.sh – ein Einstieg für Agenten-Normen und Multi-KI-Ablauf (mehrfach ausführbar).
#   bash einrichten.sh <ziel-repository> --test "<testbefehl>" [--sperre <pfad>]… [--name <name>] [--inhaberin <Name>] [--benutzer-agents]
#   Beispiel: bash ~/Documents/Projekte/claude-tools/einrichten.sh ~/Projekte/mein-projekt --test "make test" --sperre "daten/"
# Ruft nacheinander agenten-normen/einrichten.sh (Normen, Hooks) und multi-ki/einrichten.sh (Ablauf, AGENTS.md …) auf.
set -euo pipefail
QUELLE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GEMEINSAM=(); NORMEN=(); MULTI=()
while [ $# -gt 0 ]; do case "$1" in
  --test|--sperre) GEMEINSAM+=("$1" "${2:?Wert fehlt für $1}"); shift 2 ;;
  --name|--inhaberin) NORMEN+=("$1" "${2:?Wert fehlt für $1}"); shift 2 ;;
  --benutzer-agents) MULTI+=("$1"); shift ;;
  -*) echo "Unbekannte Option: $1" >&2; exit 64 ;;
  *) GEMEINSAM=("$1" "${GEMEINSAM[@]+"${GEMEINSAM[@]}"}"); shift ;;
esac; done
[ "${#GEMEINSAM[@]}" -ge 3 ] || { sed -n '3,4p' "$0" >&2; exit 64; }
bash "$QUELLE/agenten-normen/einrichten.sh" "${GEMEINSAM[@]}" "${NORMEN[@]+"${NORMEN[@]}"}"
bash "$QUELLE/multi-ki/einrichten.sh" "${GEMEINSAM[@]}" "${MULTI[@]+"${MULTI[@]}"}"
