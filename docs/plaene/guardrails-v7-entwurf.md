# Guardrail-Ausbau (Normen v7) – Entwurf, nicht geschrieben

Stand 16.11.2026. Entscheidungen fallen in diesem Repository. Repo-Angaben selbst geprüft: GitHub-API (Lizenz, letzter Push, Archiv, Release) für alle; READMEs nur
**nach Stichworten durchsucht**, nicht vollständig gelesen; vollständig gelesen: dcg-Lizenz, srt-Advisory, Claude-Code-Changelog,
offizielle Beispiel-Einstellungen, Sandbox-Doku. Code der Fremd-Repos nicht gelesen (Spalte „Prüftiefe“).
Recherche selbst statt gemini-analyst: agy darf headless weder `gh` noch `curl` (Freigabeliste), und die Behauptungen brauchten Primärquellen.

## 1. Lücken im heutigen System

| # | Lücke | Ebene | Status nach v6 |
|---|---|---|---|
| L1 | `bash/sh/node <datei>`, `python3 -c`, `bash -c`, Heredocs: Inhalt ungeprüft | Hook | v6 prüft nur `python3 <datei>` außerhalb des Projekts |
| L2 | Keine OS-Sandbox: Bash und alle Unterprozesse dürfen überall schreiben und ins Netz | Durchsetzung | offen |
| L3 | `GESCHUETZT` (`.claude/`, `normen/`, `CLAUDE.md`, `.githooks/`) gilt nur für Edit/Write, nicht für Bash (`sed -i`, `>`, `cp`) | Hook | offen |
| L4 | MCP-Werkzeuge laufen am Normen-Hook vorbei (Matcher ohne `mcp__.*`), auch ändernde Server-Werkzeuge | Hook | offen |
| L5 | Prompt-Dateien an vibe/agy werden inhaltlich nicht geprüft (Sperrpfade, Forschungsdaten, Geheimnisse) | Hook | offen |
| L6 | `git commit --no-verify` und `git -c core.hooksPath=…` umgehen pre-commit; kein Muster | Hook | offen (Prüftor `normen.py merge` prüft selbst nach → nachgelagert abgefangen) |
| L7 | Keine Liveness-Tests gegen das installierte Claude Code (Tests rufen normen.py direkt auf, nicht über den echten Hook) | Test | offen (Vibe-Lader-Check vorhanden) |
| L8 | Teams arbeiten im Hauptordner; parallele Arbeit von die Inhaberin/anderen Sitzungen sichtbar (16.11.: ein fremder Ordner mit über 400 Dateien tauchte während eines Laufs auf) | Ablauf | offen |
| L9 | N02 erkennt nur skip/xfail/`assert True`; geänderte Erwartungswerte und gelöschte Asserts nicht (betrifft Claude; Teams dürfen Tests nicht ändern) | nachgelagert | offen |
| L10 | Stop-Hook gibt nach 8 Blockaden auf (`CLAUDE_CODE_STOP_HOOK_BLOCK_CAP`, seit 2.1.143) | nachgelagert | unkritisch: `normen.py merge` führt Test und Prüfung selbst aus → nur dokumentieren |

## 2. Bewertung der Kandidaten

Prüftiefe: M = Metadaten (API), R = README/Doku, L = Lizenztext, C = Code gelesen.

| Kandidat | Prüftiefe | Lizenz · letzter Push | Urteil | Begründung |
|---|---|---|---|---|
| anthropics/claude-code `examples/settings` (strict, bash-sandbox) | M, C (JSON) | keine erkannte Lizenz · 15.11. | **Idee nachbauen** | Schlüssel `sandbox.*`, `disableBypassPermissionsMode`, `allowUnsandboxedCommands:false` übernehmen wir als eigene Einstellungen (keine Kopie nötig, Konfigurationswerte) |
| …`examples/hooks/bash_command_validator_example.py` | M, C (Gerüst) | s. o. | **verwerfen** | Regex-Liste wie unser Hook, nichts Neues |
| …`.devcontainer` (Firewall) | M | s. o. | **verwerfen (vorerst)** | Docker-Container für jede Sitzung; Vibe/agy/Schlüsselbund außerhalb – hoher Aufwand |
| eingebaute Sandbox (`/sandbox`, nutzt srt) | R (Doku) | in Claude Code enthalten | **übernehmen (Einstellung, kein Paket)** – nach Spike | wirkt auf Bash und alle Unterprozesse (schließt L1/L2 für Dateisystem/Netz); **nicht** auf Read/Edit/Write, MCP, Hooks; schützt `.claude`-Settings und `.git/hooks`, `.git/config` (L3 teilweise, L6 `core.hooksPath` per Config) |
| anthropics/sandbox-runtime (srt) eigenständig | M, R, Advisory | Apache-2.0 · v0.0.83 vom 13.11. | **verwerfen als Extra** | nur nötig, wenn wir Vibe/agy selbst einsperren wollen; GHSA-9gqj-5w7c-vx47 (Netz-Ausbruch < 0.0.16) zeigt: Version pinnen, falls doch |
| claude-plugins-official → security-guidance | M (Verzeichnis) | Apache-2.0 · 16.11. | **später prüfen** | Code nicht gelesen; Plugin = Installation → N05 |
| claude-code-security-review | M | MIT · 11.02. | **verwerfen** | GitHub Action für PRs fremder Beitragender; wir haben nur eigene PRs |
| destructive_command_guard (dcg) | M, R, L | MIT **mit Zusatz** · v0.16.0 | **verwerfen als Abhängigkeit, Ideen nachbauen** | Zusatz: „no rights are granted to any Restricted Party“ = Anthropic, OpenAI und „any … agent acting … on behalf of“ – Einsatz mit Claude Code rechtlich unklar; Standard fail-open; Rust-Binary (N05). Ideen: `python -c`/`bash -c`/Heredoc-Scan, fail-closed (haben wir), `scan` für pre-commit |
| trailofbits/claude-code-config | M, R | keine erkannte Lizenz · 24.08. | **Ideen nachbauen** | `enableAllProjectMcpServers:false`, Read/Edit-Deny für Geheimnisse; Hinweis „ohne Sandbox gelten Deny-Regeln nicht für Bash“ bestätigt L2. Nichts wörtlich kopieren (keine Lizenz) |
| trailofbits/claude-code-devcontainer | M | Apache-2.0 · 09.11. | **verwerfen (vorerst)** | wie Devcontainer oben |
| karanb192/claude-code-hooks | M, R | MIT · 16.11. | **Ideen nachbauen** | protect-tests (Löschen/Umbenennen von Tests), config-guard (CHAINDROP-Wurm in `.claude/settings.json`) → L3; Node-Abhängigkeit, viele Plugins – nicht übernehmen |
| liberzon/claude-hooks | M, R | MIT · 21.03. | **verwerfen** | Zerlegung verketteter Befehle haben wir (`SEGMENT`); Installation per `curl` nach `~/.claude/hooks`; 17 Sterne, seit März ruhig |
| eliferres/claude-code-guardrails | M, R | MIT · 12.10. | **Idee nachbauen** | Liveness-Harness („proves the four still block“) → L7; 0 Sterne → kein Code übernehmen |
| ccdwyer/assertion-guardian | M, R | MIT · 02.10. | **Idee nachbauen** | Erwartungswerte/Asserts gegen Commit vergleichen → L9; 0 Sterne, TypeScript |
| Arnav66692/testguard | M, R | MIT · 23.10. | **verwerfen** | gleiche Idee wie assertion-guardian, 0 Sterne |
| amElnagdy/delegate-skills (vibe-delegate) | M, R | MIT · 14.11. | **Idee nachbauen** | `--plan-only` (Plan-Agent) für Lese-Aufträge an Vibe statt nur Prompt-Satz „Ändere keine Dateien“ |
| CollinKasbergen/claude-to-mistral-delegation | M, R | keine erkannte Lizenz · 05.10. | **Idee nachbauen (Spike)** | Worktree je Lauf (Snapshot inkl. untracked) → L8; 0 Sterne, keine Lizenz → nichts kopieren |
| pcx-wave/vibe-skill | M, R | keine erkannte Lizenz · 11.11. | **Idee nachbauen** | Lauf-Protokoll (Modell, Tokens, Ergebnis) je Delegation – passt zu S06-Auswertung |
| abiswas97/gemini-plugin-cc | M, R (keine Treffer) | Apache-2.0 · 05.10. | **verwerfen** | für Gemini CLI, nicht agy; nichts Übertragbares gefunden |
| darjss/claude-code-codemode | M, R | MIT · 04.11. | **später testen (Installation = N05)** | Doku: „Nested calls go through Claude Code's own hooks“ – wäre ein Code Mode *mit* Hooks; 1 Stern |
| gabe4coding/claude-code-mode | M, R | MIT · 31.10. | **verwerfen** | für MCP-Aufrufe in Sandbox; unser Code Mode betrifft Shell-Auswertung |
| cisco-ai-defense/mcp-scanner | M, R | Apache-2.0 · 15.11. | **verwerfen (vorerst)** | genutzt werden nur eigene MCP-Server und Anthropic-Connectoren; YARA offline ginge, Nutzen gering |
| jarrodwatts/claude-delegator | M | MIT, **archiviert** | **verwerfen** | archiviert |
| Snyk agent-scan, ipybox | – | – | **verwerfen** | senden an Fremd-APIs bzw. Gemini (Vorgabe) |

## 3. Ideen a–h

- **a) Drei Ebenen:** ja. Normen/Hooks (Absicht, „fragen“) → Durchsetzung (eingebaute Sandbox, **geplant**, erst nach Spike) → nachgelagert
  (pre-commit, `normen.py merge`, Stop-Hook). Restgefahren dokumentieren: Skripte im Projektordner (Sandbox lässt Projekt beschreibbar),
  Read/Edit/Write und MCP außerhalb der Sandbox, `excludedCommands`.
- **b) Skriptprüfung im Live-Hook:** ja, als Ausbau von v6: `bash|sh <datei>` und `bash -c`/Heredoc zeilenweise durch `bewerten()`;
  `python3 -c` durch den AST-Prüfer; `node <datei>`/`node -e` → fragen (kein Parser in der Standardbibliothek); Projektskripte
  (`python3 skripte/x.py`) ebenfalls prüfen, nicht parsebar → fragen.
- **c) Datenschutz vor vibe/agy:** ja. Hook erkennt `vibe … --prompt-file P` und `agy … -p "$(cat P)"`.
  - Pfad P: Literal oder Zuweisung im selben Befehl (`RUN=…; … "$RUN/prompt.md"`) auflösen; nicht auflösbar → **nein**.
  - Der Pflichtblock aus `normen.py auftrag` nennt alle Sperrpfade („Diese Pfade nicht lesen …“) – diese Zeile wird vor der Prüfung
    herausgenommen (exakt der von `cmd_auftrag` erzeugte Text, sonst würde jeder Auftrag gesperrt).
  - Im Rest: Sperrpfad, Geheimnis-Muster oder Forschungsdaten-Marker → **nein**; bei agy (Google) zusätzlich jeder genannte Pfad unter einem Sperrpfad.
  - Abnahmefall „ja“: ein echter, mit `normen.py auftrag --rolle gemini-analyst` erzeugter Prompt.
- **d) Delegation im Worktree:** nur als später Spike. Befunde: Sperrpfade sind in einem Projekt teils **getrackt** (11 Dateien) → lägen auch im Worktree; Aufräumen braucht `git worktree remove`/`branch -D` (N01);
  `normen.py merge` ist PR→main, nicht Team-Branch→Arbeitsbranch → eigener Weg nötig (`git merge --ff-only` durch Opus).
- **e) Liveness-Tests:** ja – aber durch das **echte Werkzeug**, nicht nur JSON an normen.py (das wiederholt die Unit-Tests; der
  v5-Fehler war, dass Vibe den Hook gar nicht aufrief). Harmloser Köder: Befehl `true # normen-koeder` bzw. Schreiben nach
  `normen-koeder.txt`; ein Muster in normen.toml sperrt genau das. `normen.py selbsttest` startet `claude -p` (Werkzeug-Aufruf erbitten)
  und `vibe --prompt …` mit diesem Köder und erwartet in der Ausgabe die Hook-Sperre und keine angelegte Datei. Pflicht nach jedem
  Claude-Code- und Vibe-Update. (agy hat keine Hooks → nur Freigabeliste prüfen.)
- **f) Config-Selbstschutz:** zweistufig: Hook prüft Bash-Schreibziele gegen `GESCHUETZT` (L3); Sandbox ergänzt das für Bash.
  `permissions.deny` auf `.claude/settings.json` wäre ein hartes **nein** – widerspricht `rollen.claude.einstellungen = "fragen"`
  (heute fragt der Hook). **Entscheidung für dich**: hart sperren (Änderungen dann nur von dir) oder bei „fragen“ bleiben.
- **g) MCP-Gating:** ja, aber mit Regel: Matcher `mcp__.*`; neue Projektwerte `[mcp].fragen` / `[mcp].nein` (Werkzeugnamen, privat in
  projekt.toml); unbekannte MCP-Werkzeuge → ja (sonst jeder Lesezugriff eine Frage). `enableAllProjectMcpServers: false` in der Vorlage
  (heute ohne `.mcp.json` ohne Wirkung, schützt künftige).
- **h) Stop-Hook-Grenze:** Prüftor stützt sich nicht darauf (merge prüft selbst) → nur in Ebene 3 dokumentieren.

## 4. Öffentlich (claude-tools) vs. privat (Projekte)

- claude-tools: Hook-Code, Prüfer, `selbsttest`, Normtexte, Vorlage-Einstellungen (Sandbox-Grundgerüst ohne Domains), leere Schlüssel
  `[mcp]`, `[pfade].forschungsdaten` in der projekt.toml-**Vorlage**, Doku der drei Ebenen.
- Projekte (privat): Werte – Sperrpfade, `[mcp].fragen` mit den Werkzeugnamen ihrer MCP-Server, erlaubte Domains der Sandbox
  (z. B. API-Hosts von Mistral/Google, falls vibe/agy in der Sandbox laufen), Forschungsdaten-Marker.

## 5. Paketplan (nach v6; alle in claude-tools; Hook-Pakete nacheinander)

| # | Paket | Dateien (claude-tools) | Team | Abnahme |
|---|---|---|---|---|
| G1 | Liveness mit Köder durch echtes Claude Code und Vibe (`normen.py selbsttest`); Doku „nach jedem Update“ | `agenten-normen/projekt/normen/normen.py`, `normen.toml` (Köder-Muster), `tests/test_selbsttest.py`, `multi-ki/multi-ki-ablauf.md` | mistral-team (Code), Opus (Köder, Live-Lauf) | Live: Köder in Claude Code und Vibe gesperrt, `normen-koeder.txt` existiert nicht; Gegenprobe: Hook-Eintrag entfernt → selbsttest schlägt fehl |
| G2 | `--no-verify`/`core.hooksPath`-Umgehung sperren (L6) | `normen.toml`, `rollen.toml` | Opus selbst | Tests: `git commit --no-verify`, `git commit -an`, `git -c core.hooksPath=/x commit`, `git config core.hooksPath x` → nein für alle Rollen; `git commit -m "…"` weiter ja |
| G3 | Bash-Schreibziele gegen `GESCHUETZT` + Deny-Regeln in der Vorlage (L3, f) | `normen.py`, `agenten-normen/projekt/.claude/settings.json` | mistral-team | Tests: `sed -i … .claude/settings.json`, `> normen/x` → fragen (claude) / nein (Teams) |
| G4 | Skriptprüfung ausweiten (L1, b) – **erst Fehlalarm-Messung**: Prüfer im Trockenlauf über vorhandene Skripte (`einrichten.sh`, Test- und Einrichtungsskripte der Projekte), Stufen erst danach festlegen | `normen.py`, Tests | mistral-team; Review gemini-analyst (öffentlicher Code, keine Sperrpfade) | Messung: vorhandene Abläufe (auch der v6-Einspielschritt) ergeben nicht „nein“; Tests: `bash x.sh` mit `rm -rf` → nein; `python3 -c "…git push…"` → nein; `node x.js` → fragen |
| G5 | Datenschutz vor vibe/agy (L5, c) | `normen.py`, `projekt.toml`-Vorlage (`[pfade].forschungsdaten = []`), Tests | mistral-team (Code), Opus (Fälle) | Tests: echter `auftrag`-Prompt → ja; Prompt mit Sperrpfad außerhalb des Pflichtblocks → nein; `--prompt-file "$X"` unaufgelöst → nein |
| G6 | MCP-Gating (L4, g) | `normen.py`, Vorlage `settings.json` (Matcher, `enableAllProjectMcpServers`), `projekt.toml`-Vorlage `[mcp]` | mistral-team | Tests: Werkzeug aus `[mcp].fragen` → fragen; unbekannt → ja; **Live-Test**: Hook wird für die Connector-Werkzeuge (`mcp__claude_ai_…`) wirklich aufgerufen (Protokollzeile) |
| G7 | Sandbox-Spike (L2, a) – nur Messung, keine Einstellung | Bericht `docs/sandbox-spike.md` | Opus selbst (interaktiv) | Matrix vibe (Schlüsselbund, API), agy (`~/.gemini`), `gh` (Go-TLS unter Seatbelt laut Doku problematisch), `git push` (HTTPS), `make test`, Normen-Hook; Empfehlung `allowedDomains`/`excludedCommands` |
| G8 | Drei-Ebenen-Text + Restgefahren | `KONZEPT.md`, `normen.toml` `[meta].ebenen`, `erzeugt_kurz` | gemini-analyst (Doku-Entwurf), Opus (Normtext) | kurz.md zeigt drei Ebenen; Restgefahren genannt |
| G9 | N02 Erwartungswerte (L9) in `pruefen --diff` | `normen.py`, Tests | mistral-team | Test: `assertEqual(x, 3)`→`4` im Diff → Hinweis; gelöschtes `assert` → Fehler |
| G10 | Vibe `--plan-only` für Lese-Aufträge; Lauf-Protokoll je Delegation | `multi-ki/benutzer/agents/mistral-team.md`, `multi-ki-ablauf.md` | Opus selbst | Vibe-Version prüfen (S04), ein Leseauftrag läuft im Plan-Modus |
| G11 | Worktree-Spike (L8, d) | Bericht | Opus selbst | Ablauf mit getrackten Sperrpfaden, Aufräumen ohne N01-Verstoß |

Reihenfolge: G1 → G2 → G3 → G4 → G5 → G6 (Hook-Pakete seriell) · parallel möglich: G7 (Opus), G8 (gemini), G10 · später: G9, G11.
Danach in den Projekten: Projektwerte (`[mcp].fragen`, Forschungsdaten-Marker, ggf. Sandbox-Domains) – Rückfrage, Einstellungen.

## 6. Normänderungen v7 (Entwurf, wörtlich)

`normen.toml`:
```diff
 [meta]
-version = 6
+version = 7
+ebenen = [
+  "1 Normen (Hooks): prüfen Befehle, Pfade, Skripte, MCP-Werkzeuge und Prompt-Dateien vor der Ausführung – Absicht und Rückfrage.",
+  "2 Durchsetzung (Sandbox des Betriebssystems, geplant): begrenzt Dateisystem und Netz für Bash und alle Unterprozesse.",
+  "3 Nachgelagert: pre-commit, `normen.py merge` (Testbefehl + pruefen), Stop-Hook (gibt nach 8 Blockaden auf).",
+  "Restgefahr: Skripte im Projektordner und Read/Edit/Write/MCP liegen außerhalb der Sandbox; Hooks sind keine Sicherheitsgrenze.",
+]
```
N10, neues Muster:
```toml
  [[norm.muster]]
  ziel = "befehl"
  faehigkeit = "hooks-umgehen"
  regex = '\bgit\b[^;&|\n]*(\s--no-verify\b|\s-c\s+core\.hooksPath=|\sconfig\b[^;&|\n]*\bcore\.hooksPath\b)|\bgit\s+commit\b[^;&|\n]*\s-[a-zA-Z]*n[a-zA-Z]*\b'
  meldung = "pre-commit-Hook nicht umgehen."
```
N06, Prompt ergänzen:
```diff
-prompt = "Ändere nur die Dateien, die der Auftrag nennt (.normen-auftrag). Außerhalb des Projektordners wird ohne ausdrückliche Erlaubnis nichts gelöscht oder geändert. Gesperrte Pfade nicht lesen."
+prompt = "Ändere nur die Dateien, die der Auftrag nennt (.normen-auftrag). Außerhalb des Projektordners wird ohne ausdrückliche Erlaubnis nichts gelöscht oder geändert. Gesperrte Pfade nicht lesen und in keinen Auftrag an externe Teams schreiben (der Hook prüft Prompt-Dateien vor vibe/agy)."
```
`rollen.toml`: Fähigkeit `hooks-umgehen` (Kommentarliste) – niemand „ja“; `inhaberin` „ja“.
`projekt.toml`-Vorlage (öffentlich, leer):
```toml
[pfade]
forschungsdaten = []   # Marker/Pfade, die nie an gemini-analyst gehen (Dateinamen-Globs oder Textmarker)
[mcp]
fragen = []            # MCP-Werkzeuge (volle Namen), die vor dem Aufruf fragen
nein = []              # MCP-Werkzeuge, die gesperrt sind
```
Vorlage `.claude/settings.json`:
```diff
-        "matcher": "Bash|Edit|Write|MultiEdit|NotebookEdit|Read",
+        "matcher": "Bash|Edit|Write|MultiEdit|NotebookEdit|Read|mcp__.*",
+  "enableAllProjectMcpServers": false,
```
(Deny-Regeln für `.claude/settings.json` nur, wenn du dich in Frage 8 für „hart sperren“ entscheidest.)
(Sandbox-Block erst nach G7 und Freigabe.)

## 7. Offene Fragen (gebündelt)

1. Paketplan G1–G11 freigeben (Reihenfolge ok?).
2. dcg: einverstanden mit „verwerfen wegen Lizenzzusatz, Ideen nachbauen“?
3. Sandbox: Spike G7 erlauben (nur messen, keine Dauereinstellung)? Dürfen vibe/agy später in `excludedCommands` stehen (laufen dann ohne Sandbox)?
4. MCP: Unbekannte MCP-Werkzeuge → ja (Vorschlag), nur gelistete fragen/nein? (Die Liste je Projekt entscheidet die Inhaberin dort.)
5. Forschungsdaten: Schlüssel `[pfade].forschungsdaten` als Pfad-Globs **und** Textmarker – oder nur Pfade? (Werte je Projekt.)
6. Installationen zum Testen (darjss/claude-code-codemode, security-guidance) – später, einzeln freigeben?
7. Fable-Abrechnung (unverändert offen).
8. Config-Selbstschutz: `.claude/settings.json` hart sperren (deny) oder bei „fragen“ bleiben?
9. Erledigt: Entwurf liegt jetzt unter `docs/plaene/guardrails-v7-entwurf.md`.

10. Hook-Fehlalarm (Befehle mit `>` bzw. `=>` werden mit N06/lesbar_extern gesperrt, wenn der Arbeitsordner einer anderen
    Projektsitzung in claude-tools liegt; Variablen löst der Hook nicht auf) – in v7 mit beheben (Vorschlag) oder als Meldung?
11. „fragen“-Stufe: Erreichen die Rückfragen des Hooks die Inhaberin im Auto-Modus? (Am 16.11. liefen Änderungen an geschützten
    Dateien ohne sichtbare Rückfrage durch.) Falls nein: als Lücke L11 aufnehmen.

## 8. Entscheidungen der Inhaberin (16.11.2026)

| Frage | Entscheidung |
|---|---|
| 1 Paketplan | freigegeben wie Abschnitt 5: G1 → G2 → G3 → G4 → G5 → G6 seriell; G7, G8, G10 parallel; später G9, G11 |
| 2 dcg | verwerfen (Lizenzzusatz), Ideen nachbauen |
| 3 Sandbox | Spike G7 ja (nur Messung); vibe/agy dürfen in `excludedCommands` stehen (laufen ohne Sandbox) |
| 4 MCP | unbekannte MCP-Werkzeuge → ja; nur `[mcp].fragen`/`[mcp].nein` greifen |
| 5 Forschungsdaten | `[pfade].forschungsdaten` als Pfad-Globs **und** Textmarker |
| 6 Installationen | später, jeweils einzeln freigeben |
| 8 Config-Selbstschutz | bei „fragen“ bleiben (kein `permissions.deny`); G3 ergänzt Bash-Schreibziele |
| 10 Hook-Fehlalarm | in v7 mit beheben – Paket G3 (dort werden Umleitungsziele ohnehin angefasst) |
| 11 Rückfragen im Auto-Modus | für Bash belegt: Live-Probe 16.11. (Code-Mode-Skript mit `curl` → „fragen“) wurde vorgelegt und freigegeben. Für Edit/Write auf geschützte Dateien offen (16.11.: Edits an `CLAUDE.md` ohne erkennbare Rückfrage) – Rückfrage an die Inhaberin; je nach Antwort L11 in den Paketplan |
| 7 Fable-Abrechnung | entschieden: Fable läuft; bei „Advisor unavailable“ gilt S07 |

Nächster Schritt: Advisor-Konsultation 1 zum Paketplan, dann G1 (Liveness mit Köder).

Ergänzung zu G4 (offene Punkte aus v6): `FOO=1 python3 …`, `time python3 …`, Skripte ohne `.py`, „fragen“ bei `argparse`/`csv`
in Code-Mode-Skripten (Importliste prüfen), Heredoc-Edits (`python3 - <<EOF`).
Versionierung: ein Merge für v7 (alle Pakete), Version 7 und CHANGELOG mit dem ersten Normänderungs-Commit.
