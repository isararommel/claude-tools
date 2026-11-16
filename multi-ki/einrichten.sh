#!/usr/bin/env bash
# einrichten.sh – richtet den Multi-KI-Ablauf (Claude + Mistral Vibe + Google Antigravity) in einem Projekt ein. Läuft auf dem Mac.
#   bash einrichten.sh <ziel-repository> --test "<testbefehl>" [--sperre <pfad>]… [--benutzer-agents]
#   Beispiel: bash einrichten.sh ~/Documents/Projekte/mein-projekt --test "make test" --sperre "daten/geheim.json" --sperre "daten/"
# Legt an bzw. ergänzt (überschreibt nichts; abweichende Fassungen landen als <datei>.vorlage daneben):
#   docs/multi-ki-ablauf.md, AGENTS.md, .geminiignore, docs/uebergabe-vorlage.md, .claude/settings.json (zusammengeführt),
#   CLAUDE.md (Abschnitt angehängt), PLAN.md (nur wenn sie fehlt), .gitignore (Lauf-Reste).
#   Die Agenten-Normen (normen/, Hooks) richtet ../agenten-normen/einrichten.sh ein – vorher oder danach ausführen.
# --benutzer-agents: kopiert mistral-team.md, gemini-analyst.md und Explore.md nach ~/.claude/agents/ – nur wenn dort noch keine liegen.
set -euo pipefail
QUELLE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ZIEL=""; TEST=""; SPERREN=(); BENUTZER=0
while [ $# -gt 0 ]; do case "$1" in
  --test) TEST="${2:?}"; shift 2 ;;
  --sperre) SPERREN+=("${2:?}"); shift 2 ;;
  --benutzer-agents) BENUTZER=1; shift ;;
  -*) echo "Unbekannte Option: $1" >&2; exit 64 ;;
  *) ZIEL="$1"; shift ;;
esac; done
[ -n "$ZIEL" ] && [ -n "$TEST" ] || { echo "Aufruf: bash einrichten.sh <ziel> --test \"<testbefehl>\" [--sperre pfad]… [--benutzer-agents]" >&2; exit 64; }
ZIEL="$(cd "$ZIEL" && pwd)"; HEUTE="$(date +%F)"
[ -d "$ZIEL/.git" ] || echo "Hinweis: $ZIEL ist kein Git-Repository."
SP_MD=""; SP_ROH=""
for s in "${SPERREN[@]+"${SPERREN[@]}"}"; do SP_MD="$SP_MD  - \`$s\`"$'\n'; SP_ROH="$SP_ROH$s"$'\n'; done
[ -n "$SP_MD" ] || SP_MD="  - (keine projektspezifischen Sperren)"$'\n'
TMP="$(mktemp -d)"; trap 'rm -rf "${TMP:?}"' EXIT
fuelle() {  # Platzhalter ersetzen: $1 Quelle, $2 Ziel
  python3 - "$1" "$2" "$TEST" "$SP_MD" "$SP_ROH" <<'PY'
import sys
q, z, test, md, roh = sys.argv[1:6]
s = open(q, encoding="utf-8").read()
s = s.replace("@@TESTBEFEHL@@", test).replace("@@SPERRLISTE@@\n", md).replace("@@SPERRLISTE_ROH@@\n", roh)
open(z, "w", encoding="utf-8").write(s)
PY
}
lege() {  # $1 fertige Datei, $2 relativer Zielpfad
  local z="$ZIEL/$2"; mkdir -p "$(dirname "$z")"
  if [ ! -e "$z" ]; then cp "$1" "$z"; echo "  neu        $2"
  elif cmp -s "$1" "$z"; then echo "  gleich     $2"
  else cp "$1" "$z.vorlage"; echo "  vorhanden  $2  → neue Fassung als $2.vorlage daneben (bitte zusammenführen)"; fi
}
echo "Multi-KI-Ablauf → $ZIEL (Testbefehl: $TEST)"
lege "$QUELLE/multi-ki-ablauf.md" docs/multi-ki-ablauf.md
fuelle "$QUELLE/projekt/AGENTS.md" "$TMP/AGENTS.md"
# AGENTS.md teilen sich Normen-Block (agenten-normen) und diese Regeln: fehlen sie, anhängen statt .vorlage daneben.
UEBERSCHRIFT="$(head -n 1 "$TMP/AGENTS.md")"
if [ ! -e "$ZIEL/AGENTS.md" ]; then lege "$TMP/AGENTS.md" AGENTS.md
elif grep -qxF "$UEBERSCHRIFT" "$ZIEL/AGENTS.md"; then echo "  gleich     AGENTS.md (Regeln schon vorhanden – bei Änderungen von Hand anpassen)"
else { echo; cat "$TMP/AGENTS.md"; } >> "$ZIEL/AGENTS.md"; echo "  ergänzt    AGENTS.md (Regeln für externe Agenten)"
fi
fuelle "$QUELLE/projekt/.geminiignore" "$TMP/.geminiignore";   lege "$TMP/.geminiignore" .geminiignore
lege "$QUELLE/projekt/docs/uebergabe-vorlage.md" docs/uebergabe-vorlage.md
S="$ZIEL/.claude/settings.json"; mkdir -p "$ZIEL/.claude"
if [ ! -e "$S" ]; then cp "$QUELLE/projekt/.claude/settings.json" "$S"; echo "  neu        .claude/settings.json"
else
  cp -p "$S" "$S.bak-$HEUTE"
  python3 - "$S" "$QUELLE/projekt/.claude/settings.json" <<'PY'
import json, sys
z, v = sys.argv[1:3]
a, b = json.load(open(z)), json.load(open(v))
p = a.setdefault("permissions", {})
for k in ("allow", "deny"):
    alt = p.get(k, []); p[k] = alt + [x for x in b["permissions"].get(k, []) if x not in alt]
json.dump(a, open(z, "w"), indent=2, ensure_ascii=False); open(z, "a").write("\n")
PY
  echo "  ergänzt    .claude/settings.json (Sicherung settings.json.bak-$HEUTE)"
fi
C="$ZIEL/CLAUDE.md"; MARKE='<!-- multi-ki-abschnitt -->'
# Einmalige Umstellung der früheren Marke (<!-- …-vorlage: multi-ki-claude-gemini-mistral -->) auf die neue
if [ -e "$C" ] && grep -qE '<!-- [a-z]+-vorlage: multi-ki-claude-gemini-mistral -->' "$C"; then
  sed -i.bak-"$HEUTE" -E "s/<!-- [a-z]+-vorlage: multi-ki-claude-gemini-mistral -->/$MARKE/" "$C"
  echo "  umgestellt CLAUDE.md (Marke des Multi-KI-Abschnitts)"
fi
if [ -e "$C" ] && grep -qF "$MARKE" "$C"; then echo "  gleich     CLAUDE.md (Abschnitt schon vorhanden – bei Änderungen von Hand anpassen)"
else
  fuelle "$QUELLE/projekt/CLAUDE-abschnitt.md" "$TMP/abschnitt.md"
  [ -e "$C" ] && cp -p "$C" "$C.bak-$HEUTE"
  { [ -e "$C" ] && echo; cat "$TMP/abschnitt.md"; } >> "$C"; echo "  ergänzt    CLAUDE.md (Abschnitt „Multi-KI-Orchestrierung“)"
fi
if [ -e "$ZIEL/PLAN.md" ]; then echo "  vorhanden  PLAN.md (unverändert)"
else cp "$QUELLE/projekt/PLAN.md" "$ZIEL/PLAN.md"; echo "  neu        PLAN.md (zentrale Aufgabenliste – ausfüllen)"; fi
G="$ZIEL/.gitignore"; touch "$G"
for e in ".claude/settings.local.json" "*.vorlage" "*.bak-*"; do grep -qxF "$e" "$G" || { echo "$e" >> "$G"; echo "  ergänzt    .gitignore: $e"; }; done
if [ "$BENUTZER" = 1 ]; then
  mkdir -p "$HOME/.claude/agents"
  for a in mistral-team gemini-analyst Explore; do
    q="$QUELLE/benutzer/agents/$a.md"; [ -f "$q" ] || { echo "  fehlt      Vorlage $a.md"; continue; }
    if [ -e "$HOME/.claude/agents/$a.md" ]; then echo "  vorhanden  ~/.claude/agents/$a.md (unverändert)"
    else cp "$q" "$HOME/.claude/agents/$a.md"; echo "  neu        ~/.claude/agents/$a.md (aus $(basename "$q"))"; fi
  done
fi
echo "Fertig. Prüfen: cd \"$ZIEL\" && git status && git diff"
