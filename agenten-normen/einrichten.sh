#!/usr/bin/env bash
# einrichten.sh – bringt die Agenten-Normen in ein Projekt (oder aktualisiert sie). Läuft auf dem Mac oder unter Linux, Python >= 3.11.
#   bash einrichten.sh <ziel-repository> --test "<testbefehl>" [--sperre <pfad>]... [--name <name>] [--inhaberin <Name>]
#   Beispiel: bash einrichten.sh ~/Documents/Projekte/mein-projekt --test "make test" --sperre "daten/geheim.json"
#
# Gemeinsame Dateien (werden ersetzt – Quelle ist diese Vorlage): normen/normen.toml, normen/rollen.toml, normen/normen.py
# Projektdatei (nur wenn sie fehlt):                             normen/projekt.toml (Testbefehl, Sperrpfade, Prüfgrenzen)
# Erzeugt (normen.py sync):                                      normen/kurz.md, Normen-Block in AGENTS.md
# Ergänzt, ohne zu überschreiben:                                .claude/settings.json (Hooks + Lesesperren zusammengeführt),
#   .vibe/hooks.toml, .githooks/pre-commit (+ git core.hooksPath, falls nicht gesetzt), CLAUDE.md (Zeile @normen/kurz.md),
#   .gitignore (.normen-auftrag, .normen/)
# Schreibt:                                                        normen/herkunft.toml (Versionsverfolgung)
set -euo pipefail
QUELLE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ZIEL=""; TEST=""; NAME=""; SPERREN=(); INHABERIN=""
while [ $# -gt 0 ]; do case "$1" in
  --test) TEST="${2:?}"; shift 2 ;;
  --sperre) SPERREN+=("${2:?}"); shift 2 ;;
  --name) NAME="${2:?}"; shift 2 ;;
  --inhaberin) INHABERIN="${2:?}"; shift 2 ;;
  -*) echo "Unbekannte Option: $1" >&2; exit 64 ;;
  *) ZIEL="$1"; shift ;;
esac; done
[ -n "$ZIEL" ] && [ -n "$TEST" ] || { echo "Aufruf: bash einrichten.sh <ziel> --test \"<testbefehl>\" [--sperre pfad]... [--name name] [--inhaberin Name]" >&2; exit 64; }
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' || { echo "Python >= 3.11 nötig (tomllib). Es wurde nichts verändert." >&2; exit 1; }
ZIEL="$(cd "$ZIEL" && pwd)"; HEUTE="$(date +%F)"; NAME="${NAME:-$(basename "$ZIEL")}"
[ -d "$ZIEL/.git" ] || echo "Hinweis: $ZIEL ist kein Git-Repository (pruefen --diff und pre-commit brauchen Git)."
P="$QUELLE/projekt"
echo "Agenten-Normen → $ZIEL (Testbefehl: $TEST)"
mkdir -p "$ZIEL/normen"

ersetze() {  # gemeinsame Datei: $1 Quelle, $2 relativer Zielpfad
  local z="$ZIEL/$2"
  if [ ! -e "$z" ]; then cp "$1" "$z"; echo "  neu          $2"
  elif cmp -s "$1" "$z"; then echo "  gleich       $2"
  else cp "$1" "$z"; echo "  aktualisiert $2  (git diff zeigt die Änderung)"; fi
}
lege() {  # nur anlegen; abweichende Fassung als .vorlage daneben
  local z="$ZIEL/$2"; mkdir -p "$(dirname "$z")"
  if [ ! -e "$z" ]; then cp "$1" "$z"; echo "  neu          $2"
  elif cmp -s "$1" "$z"; then echo "  gleich       $2"
  else cp "$1" "$z.vorlage"; echo "  vorhanden    $2  → neue Fassung als $2.vorlage daneben (bitte zusammenführen)"; fi
}

# Gemeinsame Dateien kopieren
for f in normen.toml rollen.toml normen.py; do ersetze "$P/normen/$f" "normen/$f"; done
chmod +x "$ZIEL/normen/normen.py"

# projekt.toml nur anlegen, wenn sie fehlt
if [ ! -e "$ZIEL/normen/projekt.toml" ]; then
  python3 - "$P/normen/projekt.toml" "$ZIEL/normen/projekt.toml" "$NAME" "$TEST" "$INHABERIN" "${SPERREN[@]+"${SPERREN[@]}"}" <<'PY'
import json, sys
q, z, name, test, inhaberin, *sperren = sys.argv[1:]
s = open(q, encoding="utf-8").read()
liste = "".join(f"  {json.dumps(x, ensure_ascii=False)},\n" for x in sperren)
s = s.replace("@@NAME@@", name).replace("@@TESTBEFEHL@@", test.replace("\\", "\\\\").replace('"', '\\"'))
s = s.replace("@@SPERRLISTE@@]", liste + "]").replace('inhaberin = ""', "inhaberin = " + json.dumps(inhaberin, ensure_ascii=False))
open(z, "w", encoding="utf-8").write(s)
PY
  echo "  neu          normen/projekt.toml"
else
  echo "  vorhanden    normen/projekt.toml (unverändert – Projektwerte dort pflegen)"
fi

# Herkunft: Version, Commit der Quelle und Prüfsummen der gemeinsamen Dateien (normen.py aktualisieren/pruefen lesen sie).
# Kein Pfad der Quelle – die Datei landet auch in öffentlichen Repositories.
COMMIT="$(git -C "$QUELLE/.." rev-parse --short --verify -q HEAD)" || COMMIT=""  # Quelle ohne Git oder ohne Commit
python3 - "$ZIEL" "$COMMIT" "$HEUTE" <<'PY'
import hashlib, json, sys, tomllib
from pathlib import Path
ziel, commit, heute = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
version = tomllib.loads((ziel / "normen/normen.toml").read_text(encoding="utf-8"))["meta"]["version"]
z = ["# Von einrichten.sh geschrieben – nicht von Hand ändern.", "[quelle]", 'name = "claude-tools"',
     f"version = {version}", f"commit = {json.dumps(commit)}", f"eingespielt_am = {json.dumps(heute)}", "", "[dateien]"]
for rel in ("normen/normen.toml", "normen/rollen.toml", "normen/normen.py"):
    z.append(f'"{rel}" = "{hashlib.sha256((ziel / rel).read_bytes()).hexdigest()}"')
(ziel / "normen/herkunft.toml").write_text("\n".join(z) + "\n", encoding="utf-8")
PY
echo "  geschrieben  normen/herkunft.toml"

S="$ZIEL/.claude/settings.json"; mkdir -p "$ZIEL/.claude"
if [ ! -e "$S" ]; then cp "$P/.claude/settings.json" "$S"; echo "  neu          .claude/settings.json"
else
  cp -p "$S" "$S.bak-$HEUTE"
  python3 - "$S" "$P/.claude/settings.json" <<'PY'
import json, sys
z, v = sys.argv[1:3]
a, b = json.load(open(z)), json.load(open(v))
p = a.setdefault("permissions", {})
for k, werte in b.get("permissions", {}).items():
    alt = p.get(k, []); p[k] = alt + [x for x in werte if x not in alt]
h = a.setdefault("hooks", {})
for ereignis, eintraege in b.get("hooks", {}).items():
    for e in eintraege:
        befehle = {hk.get("command") for hk in e.get("hooks", [])}
        gleich = [x for x in h.get(ereignis, []) if any(hk.get("command") in befehle for hk in x.get("hooks", []))]
        if not gleich:
            h.setdefault(ereignis, []).append(e)
        for x in gleich:  # gleicher Hook-Befehl: fehlende Matcher-Teile der Vorlage ergänzen (z. B. mcp__.*)
            if "matcher" in e and "matcher" in x:
                teile = x["matcher"].split("|")
                x["matcher"] = "|".join(teile + [m for m in e["matcher"].split("|") if m not in teile])
for k, v in b.items():  # weitere Schlüssel (enableAllProjectMcpServers …) nur setzen, wenn sie fehlen
    if k not in ("permissions", "hooks"):
        a.setdefault(k, v)
if a != json.load(open(z)):
    json.dump(a, open(z, "w"), indent=2, ensure_ascii=False); open(z, "a").write("\n")
PY
  if cmp -s "$S" "$S.bak-$HEUTE"; then rm -f "${S:?}.bak-$HEUTE"; echo "  gleich       .claude/settings.json"
  else echo "  ergänzt      .claude/settings.json (Sicherung settings.json.bak-$HEUTE)"; fi
fi

H="$ZIEL/.vibe/hooks.toml"
if [ -e "$H" ] && ! cmp -s "$P/.vibe/hooks.toml" "$H" && grep -qE '^[[:space:]]*command[[:space:]]*=' "$H" \
   && ! grep -E '^[[:space:]]*command[[:space:]]*=' "$H" | grep -vqF 'normen/normen.py hook --rolle mistral-team --werkzeug vibe'; then
  # enthält nur Normen-Hooks → durch die aktuelle Fassung ersetzen (neue Werkzeugnamen wie `edit` kommen sonst nie an)
  cp -p "$H" "$H.bak-$HEUTE"; cp "$P/.vibe/hooks.toml" "$H"
  echo "  ersetzt      .vibe/hooks.toml (nur Normen-Hooks; Sicherung hooks.toml.bak-$HEUTE)"
else
  lege "$P/.vibe/hooks.toml" .vibe/hooks.toml
fi
lege "$P/.githooks/pre-commit" .githooks/pre-commit
chmod +x "$ZIEL/.githooks/pre-commit"
if [ -d "$ZIEL/.git" ]; then
  HP="$(git -C "$ZIEL" config --get core.hooksPath || true)"
  if [ -z "$HP" ]; then git -C "$ZIEL" config core.hooksPath .githooks; echo "  gesetzt      git core.hooksPath = .githooks"
  elif [ "$HP" = ".githooks" ]; then echo "  gleich       git core.hooksPath = .githooks"
  else echo "  Hinweis      core.hooksPath ist schon $HP – .githooks/pre-commit dort von Hand einbinden"; fi
fi

C="$ZIEL/CLAUDE.md"
if [ -e "$C" ] && grep -qxF "@normen/kurz.md" "$C"; then echo "  gleich       CLAUDE.md (@normen/kurz.md)"
else
  [ -e "$C" ] && cp -p "$C" "$C.bak-$HEUTE"
  python3 - "$C" <<'PY'
import sys, os
p = sys.argv[1]
s = open(p, encoding="utf-8").read() if os.path.exists(p) else ""
zeile = "@normen/kurz.md\n"
z = s.splitlines(keepends=True)
if z and z[0].startswith("# "):
    s = z[0] + "\n" + zeile + "".join(z[1:])
else:
    s = zeile + ("\n" + s if s else "")
open(p, "w", encoding="utf-8").write(s)
PY
  echo "  ergänzt      CLAUDE.md (Import @normen/kurz.md)"
fi

G="$ZIEL/.gitignore"; touch "$G"
for e in ".normen-auftrag" "*.bak-*" "*.vorlage" ".normen/"; do grep -qxF "$e" "$G" || { echo "$e" >> "$G"; echo "  ergänzt      .gitignore: $e"; }; done

(cd "$ZIEL" && python3 normen/normen.py sync | sed 's/^/  /')
echo "Fertig. Prüfen: cd \"$ZIEL\" && git diff && python3 normen/normen.py pruefen --nur-melden"
# v15 (#66): Claude Code lädt Projekt-Hooks nur in Sitzungen, die im Projekt-Stammverzeichnis gestartet wurden
echo "Hinweis: Claude-Sitzungen im Projekt-Stammverzeichnis ($ZIEL) erneut starten – Hooks wirken erst dann;"
echo "         Beleg: dort \`touch .normen/normen-koeder.txt\` (muss gesperrt werden), dann \`python3 normen/normen.py selbsttest --sitzung\`."
