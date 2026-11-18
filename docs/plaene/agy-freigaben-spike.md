# Spike: agy-Freigaben headless (Paket A, 18.11.2026)

Ziel: `gemini-analyst` soll headless (`agy -p`) zuverlässig lesen und neue Dateien anlegen, ohne
`--dangerously-skip-permissions` und ohne Auto-Freigaben.

## Aufbau

- agy **1.5.11**, Modell `gemini-3.8-flash-high`, je Lauf `--output-format stream-json` (zeigt jeden Werkzeugschritt mit
  Fehlermeldung) und bei Bedarf `--log-file` (zeigt die wirksamen Einstellungen: `CLI settings initialized: permissions=…`).
- Wegwerf-Repository unter dem **aufgelösten** Temp-Pfad (`/private/var/folders/<…>/T/agy-spike/repo`, getrackte Datei,
  gitignorte Datei), daneben ein Lauf-Ordner `…/agy-spike/lauf` mit `info.md`.
- Headless bricht der Zug nach der **ersten** Verweigerung ab (`jetski: no output produced — a tool required the "…"
  permission …`). Deshalb: erwartete Erlaubnisse gemeinsam in einem Lauf, erwartete Sperren je in einem eigenen Lauf.
- Vorhandene Transkripte (`~/.gemini/antigravity-cli/brain/*/.system_generated/logs/transcript_full.jsonl`) vorher
  ausgewertet: 26 verweigerte Befehle, darunter `wc -l docs/…`, `tail -n 3 .gitignore`, `cat build/…` – also Befehle,
  die laut ALLOW erlaubt sein sollten.

## Ergebnisse

| Fall | Regel(n) | Ergebnis |
|---|---|---|
| `cat a.txt` | `command(cat *)` (aus `--settings`) | **verweigert** |
| `cat a.txt` | ohne `--settings` (global `command(cat *)`) | **verweigert** |
| `cat a.txt` | `command(cat *)` + `trustedWorkspaces` | **verweigert** |
| `cat a.txt` | `command(cat *)` + `--sandbox` | **verweigert** |
| `cat a.txt` | `command(cat)` | ok |
| `cat <gitignorte Datei>` | `command(cat)` | ok |
| `cat a.txt \| wc -l` | `command(cat)`, `command(wc)` | ok |
| `wc -l <lauf>/*.md` (Glob außerhalb) | `command(wc)` | ok |
| `wc -l /var/…/lauf/info.md` | `command(wc)` | ok |
| `cat a.txt > kopie.txt` | `command(cat)` | verweigert (gut) |
| `cat a.txt; touch x` | `command(cat)` | verweigert (gut) |
| `lsof -h` | `command(ls)` | verweigert (gut: Präfix gilt nur wortweise) |
| `read_file` im Lauf-Ordner, beide Pfadformen | `read_file(/private/var/…/lauf)` | ok |
| `read_file` im Lauf-Ordner | `read_file(/var/…/lauf)` | **verweigert** |
| `read_file` im Lauf-Ordner, beide Pfadformen | `--add-dir /var/…/lauf` (ohne Regel) | ok (gibt aber auch Schreibrecht dort) |
| `read_file` gitignorte Datei im Workspace | – | ok |
| `write_file` neue Datei im Workspace | `--mode accept-edits` | ok |
| `write_file` außerhalb des Workspace | `--mode accept-edits` | verweigert (gut; Stream zeigt trotzdem `DONE`) |
| `lsof -h` **ohne `--mode`** | `command(cat)` | **ausgeführt** – Auto-Modus |
| `lsof -h` ohne `--mode`, `"agentMode": ""` | `command(cat)` | verweigert (gut) |
| `cat a.txt` | allow `command(cat)`, deny `command(cat *)` | ok – **deny mit `*` greift nicht** |

## Befunde

1. **`*` in Regeln wirkt nicht.** agy 1.5.11 vergleicht `command(<programm und unterbefehl>)` als Präfix auf
   Wortgrenze (eingebettete Doku: „`command(<binary_and_subcommand>)` e.g. `command(gh pr list)`“). `command(cat *)` und
   `command(cat*)` decken nichts ab – die bisherige ALLOW-Liste wirkte nur über die Formen ohne `*` (`ls`, `pwd`,
   `git status` …). Das erklärt die Rückmeldungen (`wc`, `tail`, `cat` gesperrt) und das Scheitern beim Anlegen
   (anschließendes `wc -l` auf die neue Datei). Gilt ebenso für `deny`.
2. **Pfadregeln brauchen den aufgelösten Pfad.** agy löst das Ziel auf (`/var` → `/private/var`), die Regel nicht.
   `read_file('"$RUN"')` mit `RUN=/var/folders/…` greift deshalb nie.
3. **Ohne `--mode` läuft `-p` im Auto-Modus** (Log: `SetCycleMode called: auto`, seit agy-Changelog „default Agent Mode
   … Auto“). Dort führte agy einen nicht freigegebenen Befehl aus. Für den Nur-Lesen-Aufruf ist das eine
   Auto-Freigabe (N07). `"agentMode": ""` in `--settings` stellt den Default-Modus her.
4. **„auto-denied“ betrifft den letzten verweigerten Schritt**, nicht unbedingt das Schreiben. Steht die Meldung am Ende,
   erst `git status` und die Zieldatei prüfen; die Datei kann vollständig geschrieben sein.
5. Stream-Status `DONE` heißt nicht „ausgeführt“: Bei verweigertem `write_file`/`run_command` meldet der Stream teils
   `DONE`, maßgeblich sind `denied_actions` im `result`-Ereignis und das Dateisystem.
6. `--settings` ersetzt `permissions.allow` und, wenn angegeben, `permissions.deny`; ohne `deny` bleibt die globale Liste.
   Globale Einträge `Edit`, `Write`, `MultiEdit` sind für agy ungültig (Log: `invalid grant string`), `command(rm *)`
   usw. greifen nach Befund 1 nicht. Die globale Datei liegt außerhalb des Projekts – Änderung nur durch die Inhaberin.
7. Nicht gefundene Schranke: gitignorte Dateien sind weder für `cat` noch für `read_file` gesperrt.
8. **Befehlsregeln kennen keine Pfadgrenze.** `command(cat)` liest jede Datei, auch außerhalb des Projekts (Abnahme:
   Gemini las per `cat` die Prompts anderer Lauf-Ordner). `read_file` ist dagegen auf Workspace und freigegebene Ordner
   begrenzt. Gleiches gilt für `head`, `tail`, `grep`, `wc`. Schutz vor dem Lesen von Geheimnissen außerhalb
   des Projekts geben nur der Prompt und die eingebaute „system protection boundary“ (sperrt z. B. `~/.gemini/…`).
9. `git log/diff/show --output=<pfad>` schreibt trotz reiner Präfixregel eine Datei, auch außerhalb des Projekts
   (gemessen mit `command(git log)`).
10. Ein ungelisteter Befehl oder ein Lesen außerhalb beendet den Lauf mit leerer Antwort. Gemini neigt dazu, sich in
    Nachbarordnern umzusehen; der Satz „Lies keine anderen Dateien und sieh dich nicht in anderen Ordnern um“ im
    Prompt hat das in der Abnahme verhindert.
11. Nicht gleichzeitig starten: Drei parallel gestartete agy-Läufe – einer scheiterte sofort mit „model … is not
    recognized“. Netzaussetzer zeigen sich als „stream was interrupted“ und verlängern den Lauf bis zum Zeitlimit.

## Folgerungen für die Agent-Definition

- ALLOW nur noch in Präfixform (`command(git diff)` statt `command(git diff)` + `command(git diff*)`).
- `"agentMode": ""` in jedes `--settings`, damit kein Aufruf im Auto-Modus landet.
- `RUN` wörtlich und **aufgelöst** angeben (`cd <lauf-ordner> && pwd -P`), `read_file('"$RUN"')` in ALLOW, damit
  Nebendateien im Lauf-Ordner lesbar sind.
- `rg` (`--pre <programm>` startet Programme) und `tree` (`-o` schreibt) gestrichen; `command(git branch --show-current)`
  aufgenommen (in alten Transkripten verweigert), nicht `command(git branch)` (deckt `-D`).
- Offen für die Inhaberin: `git log/diff/show --output` (Befund 9) und Lesen außerhalb per `cat` (Befund 8).

## Abnahme (18.11.2026)

Befehl wörtlich aus `multi-ki/benutzer/agents/gemini-analyst.md`, `RUN` in der echten Form `${TMPDIR}agy-runs/…`
(`/var/…`), Mini-Auftrag: Nebendatei im Lauf-Ordner lesen, `wc -l` im Projekt, neue Datei anlegen.

- **Umsetzung (`--mode accept-edits`), 3 Läufe:** erster Versuch 0 von 3 – keine Freigabe fehlte, aber Lauf 1 sah sich in
  Nachbarordnern um (Lesen außerhalb → korrekt verweigert → Lauf beendet), Lauf 2 ebenso, dann Netzausfall, Lauf 3
  scheiterte beim gleichzeitigen Start („model … is not recognized“). Nach dem Prompt-Satz „Lies keine anderen
  Dateien …“ und nacheinander gestartet: **3 von 3** ohne Verweigerung, Datei jeweils vollständig angelegt (ein Lauf
  hing nach getaner Arbeit bis zum Zeitlimit am abgebrochenen Stream).
- **Nur lesen (ohne `--mode`):** `read_file` im Lauf-Ordner, `git log --oneline -n 1`, `grep -n …` ok; `lsof -h`
  verweigert (kein Auto-Modus mehr). Schreiben im Nur-Lesen-Aufruf: verweigert (Einzelmessung oben).
- `make test` grün, `normen.py pruefen --diff` 0 Fehler.
