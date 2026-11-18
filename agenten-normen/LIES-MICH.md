# Vorlage: Agenten-Normen – Regeln, Zuständigkeiten und Durchsetzung für Coding-Agenten

**Für Claude: vor dem Ändern dieser Vorlage oder dem Einrichten in einem Projekt lesen.**

## Wozu
Ein festes, kopierbares Normensystem für alle Projekte, in denen Claude Code, Mistral Vibe, Antigravity/Gemini oder lokale
Modelle arbeiten. Grundsatz aus der Recherche vom 14.11.2026: Was nur in CLAUDE.md/AGENTS.md steht, ist ein Wunsch.
Die Muss-Normen werden deshalb **technisch** durchgesetzt (Hooks, Auftragsdatei, Prüfskript, pre-commit), der Text dient der Erklärung.

## Aufbau (im Projekt)
```text
normen/normen.toml      Regelwerk: Muss N01–N11, Soll S01–S08 – Text für Prompts, Begründung, Quellen, Prüfmuster   (gemeinsam)
normen/rollen.toml      Rollen und Fähigkeiten (ja / fragen / nein) + was jede Rolle verantwortet                      (gemeinsam)
normen/normen.py        ein Werkzeug für alles: pruefen · hook · stop · auftrag · kurz · sync                           (gemeinsam)
normen/projekt.toml     Testbefehl, gesperrte Pfade, Geheimnis-Muster, Forschungsdaten, MCP, Rollen-Abweichungen        (Projekt)
normen/kurz.md          Kurzfassung, erzeugt; per `@normen/kurz.md` in CLAUDE.md geladen                                (erzeugt)
AGENTS.md               Normen-Block zwischen <!-- normen:anfang --> und <!-- normen:ende --> (für vibe/agy)           (erzeugt)
.claude/settings.json   PreToolUse-Hook (Rolle claude), Stop-Hook (Test + Diff), SessionStart nach /compact (kurz.md)
.vibe/hooks.toml        pre_tool-Hooks (Rolle mistral-team), strict = true
.githooks/pre-commit    `normen.py pruefen --staged` (core.hooksPath = .githooks)
.normen-auftrag         nur während eines Auftrags: erlaubte Pfade für externe Teams (gitignored)
```
„Gemeinsam“ heißt: Quelle ist diese Vorlage, `einrichten.sh` ersetzt die Dateien im Projekt. Projektwerte gehören dem Projekt.

## Zuständigkeiten (Kurzform, verbindlich ist `rollen.toml`)
| Rolle | Aufgabe | Grenzen |
|---|---|---|
| Inhaberin | Ziele, Abnahme, Freigaben (Pakete, Löschen, Push/Merge, Einstellungen, Normänderungen), Serverläufe | – |
| claude (Orchestrator) | plant, schreibt Tests, erteilt Aufträge, prüft selbst nach, committet auf Zweigen | Löschen, Pakete, Push, außerhalb schreiben, Normen/Einstellungen ändern → Rückfrage bei der Inhaberin |
| mistral-team (vibe) | Umsetzung, neue Tests nach Auftrag, Review | nur Pfade aus `.normen-auftrag`; keine bestehenden Tests, kein git, keine Sperrpfade |
| gemini-analyst (agy) | Analyse, Doku | wie mistral-team; nie personenbezogene Daten oder Forschungsdaten |
| explore / lokal | Suche / künftige lokale Modelle | nur lesen bzw. wie mistral-team (Forschungsdaten erlaubt) |

## Ablauf eines Auftrags (Claude als Orchestrator)
1. `python3 normen/normen.py auftrag --rolle mistral-team --dateien src/a.py tests/test_neu.py` → schreibt `.normen-auftrag`
   und gibt die Pflichtsätze aus; diese wörtlich in den Prompt übernehmen.
2. Team arbeitet; Hooks sperren alles außerhalb der freigegebenen Pfade und alle Muss-Verstöße.
3. Claude führt selbst aus: Testbefehl und `python3 normen/normen.py pruefen --diff` (meldet auch Dateien außerhalb des Auftrags).
4. `python3 normen/normen.py auftrag --ende`, Diff lesen, committen.

## In ein Projekt bringen / aktualisieren
```bash
bash ~/Documents/Projekte/claude-tools/agenten-normen/einrichten.sh <projekt> --test "<testbefehl>" [--sperre <pfad>]… [--inhaberin <Name>]
```
- Mehrfach ausführbar; überschreibt nur die gemeinsamen Dateien, ergänzt sonst (Sicherungen `*.bak-<datum>`).
- Danach: `git diff` lesen, `python3 normen/normen.py pruefen --nur-melden` (Bestand ansehen), committen.
- Zusammen mit dem Multi-KI-Ablauf: `../multi-ki/einrichten.sh` zusätzlich ausführen (Reihenfolge egal).

## Prüfen
- `normen.py pruefen` – ganzer Bestand (Audit). Altbefunde zeigen, was nachzuziehen ist; sie blockieren nichts.
- `normen.py pruefen --diff [BASIS]` – nur neue/geänderte Zeilen; **das ist die Schranke** (Stop-Hook, Abnahme).
- `normen.py pruefen --staged` – pre-commit. Umgehen nur durch die Inhaberin: `git commit --no-verify`.
- `normen.py selbsttest [--werkzeug claude|vibe]` – prüft nach jedem Update von Claude Code oder Vibe mit einem Köder-Befehl durch das echte Werkzeug, ob die Normen-Hooks greifen (gesperrt / NICHT GESPERRT / unklar). Pflicht nach jedem Update.
- Begründete Ausnahme im Code: `normen-ausnahme: <ID> – Begründung` in derselben oder der Zeile davor. `<ID>` ist die volle ID
  (z. B. `N09-SICHERE-MUSTER`); die Kurzform `N09` wird nicht erkannt.

## Weniger Rückfragen (ab v3)
- `projekt.toml [pfade].loeschbar`: `rm` ohne Rückfrage, wenn **alle** Ziele dort liegen. Relativ zum Projekt (z. B. `.venv`, `build`):
  Ordner samt Inhalt; absolut (`${TMPDIR}`, `/tmp/claude-501` …): nur der Inhalt. Für Pfade im Projekt zählen nur relative Einträge.
  Globs, unbekannte Variablen, `sudo` und gemischte Ziele fragen weiterhin. Bestehende Projekte: Liste von Hand in `projekt.toml` ergänzen
  (`einrichten.sh` ändert `projekt.toml` nicht) – fehlt sie, gilt keine Ausnahme.
- N05: Installieren aus vorhandenen Manifesten (`pip install -r …requirements*.txt`, `npm ci`, `uv sync`) fragt nicht mehr (`ausser_regex`, je Teilbefehl).
- S05: Claude fragt nur bei echten Entscheidungen und bündelt Fragen; Branch, Tests, Commit, Push des Branches und PR ohne Rückfrage.
- Merge nach main automatisch: `python3 normen/normen.py merge <PR>` – mergt nur, wenn der Stand committet ist, dem PR-Kopf entspricht,
  origin/main enthält, der Testbefehl grün ist und `pruefen --diff origin/main` keine Fehler meldet; danach wird der lokale main aktualisiert.
- Weiterhin mit Rückfrage: direktes `git push … main` / `gh pr merge`, neue Pakete, andere destruktive Befehle, außerhalb des Projekts, Einstellungen/Normen.

## Neue Projektwerte in projekt.toml (v7)
- `[pfade].forschungsdaten`: Pfad-Globs relativ zum Projekt (enthalten `/` oder `*`, z. B. `daten/roh/**`) und Textmarker (z. B. `PROBAND-`). Wirkung: bei `gemini-analyst` (`agy`) gesperrt; bei `mistral-team` (`vibe`) wird nachgefragt (`fragen`).
- `[mcp]`: Steuert MCP-Werkzeuge (`mcp__.*`) über den vollen Werkzeugnamen:
  - `nein`: Globs gesperrter MCP-Werkzeuge.
  - `fragen`: Globs von MCP-Werkzeugen, die vor dem Aufruf fragen (z. B. `mcp__*__container_restart`).
  - `nein` hat Vorrang vor `fragen`. Unbekannte MCP-Werkzeuge sind standardmäßig erlaubt, Eingabefelder werden nicht als Befehle oder Pfade ausgewertet. In der Vorlage `.claude/settings.json` ist `enableAllProjectMcpServers: false` voreingestellt.

## Was technisch erzwungen wird – und was nicht
| Norm | Claude Code | Mistral Vibe | Antigravity (agy) | danach |
|---|---|---|---|---|
| N01 Zerstörung, N10 git/Einstellungen, N05 Pakete, N07 Auto-Modus | Hook (fragen/sperren) | Hook (sperren) | nur agy-Freigabeliste (`ALLOW` in gemini-analyst.md) | – |
| N03 Geheimnisse, N06 Sperrpfade | Hook + `permissions.deny` | Hook | `.geminiignore` (keine harte Grenze) | – |
| N06 nur Auftragspfade, N02 bestehende Tests | Hook (Tests dürfen) | Hook | **nicht** (agy hat keine Hooks) | `pruefen --diff` |
| N08, N09, S01, Syntax | – | – | – | `pruefen --diff`, pre-commit |
| N04 Beleg | Stop-Hook (Test + Diff) | – | – | Orchestrator prüft selbst |
| S02 minimal, S03 Schleifen, „wirklich repariert?“ | – | – | – | nur Review |

Grenzen (bewusst): Hooks prüfen Befehlstexte per Muster und lassen sich mit Tricks umgehen (z. B. Befehl in eine Datei schreiben und
ausführen). Deshalb zusätzlich: kein Auto-Modus, Teams nur im Projektordner, Snapshots/Time Machine, Diff-Prüfung danach.

## Pflege
- Normen ändern **nur hier** (`projekt/normen/*.toml`), `make test` in claude-tools (testet die Vorlage), dann in den Projekten
  `einrichten.sh` erneut ausführen. `meta.version` erhöhen, wenn sich Inhalte ändern. Änderungen bestätigt die Inhaberin.
- Nach jedem Update von Claude Code oder Vibe: `python3 normen/normen.py selbsttest` ausführen (prüft per Köder-Befehl durch die echten Werkzeuge, ob die Normen-Hooks greifen).
- Gemini CLI wurde für Gratisnutzer durch Antigravity ersetzt; falls doch Gemini CLI genutzt wird: `normen.py hook --werkzeug gemini`
  als BeforeTool-Hook eintragen (Exit 2 = sperren) und `context.fileName` auf `["AGENTS.md"]` setzen.
