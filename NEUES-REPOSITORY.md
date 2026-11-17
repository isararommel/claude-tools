# Arbeitsanweisung: Neues Repository für Multi-KI und Agenten-Normen einrichten

Diese Anleitung führt eine Claude-Code-Instanz (als Chef-Architekt und Orchestrator) Schritt für Schritt durch das Einrichten eines neuen oder frischen Repositorys für den Multi-KI-Ablauf und das Agenten-Normensystem.

---

## Voraussetzungen auf dem Rechner

Vor dem Start müssen folgende Werkzeuge auf dem Entwicklungsrechner bereitstehen:

- **Python ≥ 3.11:** Erforderlich für `tomllib` in den Prüfskripten.
- **Git:** Für Versionsverwaltung und Hooks.
- **GitHub CLI (`gh`):** Installiert und angemeldet (`gh auth status`).
- **Lokale Vorlage:** `claude-tools` lokal vorhanden unter `~/Documents/Projekte/claude-tools`.
- **Benutzerweite Agenten:** Definitionen `~/.claude/agents/mistral-team.md` und `~/.claude/agents/gemini-analyst.md` vorhanden (können bei Bedarf über `einrichten.sh --benutzer-agents` angelegt werden).
- **Externe Werkzeuge (optional):** Mistral Vibe (`vibe`) und Google Antigravity (`agy`) im `PATH` verfügbar und angemeldet, sofern diese Teams genutzt werden sollen.

---

## Schritt 1: Vorprüfung des Repositorys

1. Prüfen, ob das Zielverzeichnis ein Git-Repository ist:
   ```bash
   git status
   ```
2. Sichtbarkeit und Zustand auf GitHub prüfen:
   ```bash
   gh repo view --json isPrivate,visibility,defaultBranchRef
   ```
3. Prüfen, ob der Hauptzweig (`main`) geschützt ist und ob bereits Konfigurationsdateien vorliegen (`CLAUDE.md`, `normen/`, `.githooks/`).

---

## Schritt 2: Fragen an die Inhaberin (gebündelte Runde)

Vor der Ausführung offene Parameter in **einer einzigen gebündelten Frage** an die Inhaberin klären. Standardvorschläge mitliefern:

1. **Zweck und Sprache:** Was ist das Ziel des Repositorys und welche Projektsprache gilt für Code und Dokumentation? *(Vorschlag: Deutsch für Doku, Englisch für Code).*
2. **Testbefehl:** Welcher Befehl führt die Testsuite aus? *(Vorschlag: `make test`, `pytest`, `swift test` oder `npm test` – muss sofort lauffähig und grün sein).*
3. **Sensible Pfade:** Welche Pfade enthalten vertrauliche Informationen, Geheimnisse, Kundendaten oder Forschungsdaten, und welche Textmarker kennzeichnen Forschungsdaten (z. B. `PROBAND-`)? *(Vorschlag: `daten/`, `secrets/`, `*.env`).*
4. **Sichtbarkeit:** Bleibt das Repository privat oder wird es öffentlich?
5. **Team-Freigaben:** Dürfen Mistral Vibe (`mistral-team`) und Google Antigravity (`gemini-analyst`) eingesetzt werden? *(Hinweis: Google Antigravity nie bei personenbezogenen Daten oder Forschungsdaten).*
6. **Rückmeldungs-Repository:** Welches private GitHub-Repository dient als Ziel für `normen.py melden`? *(Muss ein privates Repository der Inhaberin sein).*
7. **Anzeigename:** Wie soll die Inhaberin in Hinweisen genannt werden? *(Standard: „die Inhaberin“).*

---

## Schritt 3: Grundgerüst des Repositorys

1. Basis-`.gitignore` anlegen oder ergänzen (u. a. `.env*`, `.normen/`, `.normen-auftrag`, `.venv`, `__pycache__/`, `build/`).
2. Basis-Dokumentation (`LIES-MICH.md` oder `README.md`) anlegen.
3. Testbefehl vorbereiten, der sofort erfolgreich durchläuft (z. B. ein minimales `Makefile` mit Ziel `test` oder ein Dummy-Test).

---

## Schritt 4: Einrichtung ausführen und `projekt.toml` konfigurieren

Führe das zentrale Installationsskript aus:

```bash
bash ~/Documents/Projekte/claude-tools/einrichten.sh ~/Projekte/mein-projekt \
  --test "<testbefehl>" \
  --sperre "<pfad>" \
  --inhaberin "<Name>"
```

Danach die Datei `normen/projekt.toml` prüfen und anpassen:

- `[projekt].name`: Projektname.
- `[projekt].testbefehl`: Definierter Testbefehl.
- `[projekt].inhaberin`: Anzeigename der Inhaberin.
- `[pfade].gesperrt`: Vollständige Liste sensibler Pfade (Zugriff für externe Teams gesperrt).
- `[pfade].loeschbar`: Erlaubte Wegwerfpfade für schadlose `rm`-Befehle (z. B. `.venv`, `build`, `.pytest_cache`, `node_modules`, `${TMPDIR}`).
- `[pfade].lesbar_extern`: Standardmäßig `["~/Documents/Projekte/claude-tools"]` (Lesen gestattet, Schreiben strikt gesperrt).
- `[pfade].forschungsdaten`: Pfad-Globs (z. B. `daten/roh/**`) und Textmarker (z. B. `PROBAND-`) – für Antigravity gesperrt, Mistral Vibe fragt.
- `[mcp].fragen` / `[mcp].nein`: Globs über volle MCP-Werkzeugnamen (z. B. `mcp__*__container_restart`) für Rückfrage bzw. Sperrung; Unbekanntes erlaubt, `nein` vor `fragen`.
- `[rueckmeldung].repo`: Privates Ziel-Repository für Fehlermeldungen (z. B. `inhaberin/werkzeuge-privat`). **Muss ein privates Repository sein!**
- `[quelle].pfad`: Pfad zur lokalen Vorlage (`~/Documents/Projekte/claude-tools`).

---

## Schritt 5: Richtlinien und Ignorierlisten abgleichen

1. **`CLAUDE.md` prüfen:**
   - Am Anfang muss `@normen/kurz.md` importiert sein.
   - Der Abschnitt `<!-- multi-ki-abschnitt -->` enthält die Delegationsregeln.
   - Projektspezifische Anweisungen oberhalb des Multi-KI-Abschnitts einfügen.
2. **`AGENTS.md` prüfen:**
   - Enthält den synchronisierten Normen-Block (`normen:anfang` bis `normen:ende`) und die Verhaltensregeln für externe Agenten.
3. **`.geminiignore` prüfen:**
   - Stellt sicher, dass sensible und gesperrte Pfade für Antigravity ausgeblendet sind.
4. **`PLAN.md` anlegen:**
   - `einrichten.sh` legt die Vorlage an, wenn sie fehlt. Platzhalter füllen: *Stand*, Verweise, erste Aufgaben (so ausführlich,
     dass eine frische Sitzung ohne Rückfrage loslegt), offene Fragen an die Inhaberin. Jede Sitzung beginnt dort.

---

## Schritt 6: Agenten-Definitionen abgleichen

1. Prüfen, ob `~/.claude/agents/mistral-team.md`, `~/.claude/agents/gemini-analyst.md` und `~/.claude/agents/Explore.md` vorhanden sind (alle mit der Regel „Den Advisor nie aufrufen“).
2. Prüfen, ob die Freigabeliste (`ALLOW`) in `~/.claude/agents/gemini-analyst.md` den Test- und Buildbefehl des Projekts abdeckt (immer beide Formen, z. B. `command(make test)` und `command(make test*)`).
3. Bei Abweichungen die Inhaberin um Anpassung bitten (Änderungen an `~/.claude/` verantwortet die Inhaberin).

---

## Schritt 7: Abnahme-Checkliste

Vor dem ersten Commit folgende Punkte ausführen und prüfen:

- [ ] **Testbefehl:** Eigener Testbefehl läuft erfolgreich durch (`make test`).
- [ ] **Selbsttest:** `python3 normen/normen.py selbsttest` meldet „gesperrt“ für `claude` und `vibe` (beweist aktive Hooks).
- [ ] **Normen-Prüfung:** `python3 normen/normen.py pruefen --diff` meldet keine Fehler.
- [ ] **Auftrags-Simulation:**
  ```bash
  python3 normen/normen.py auftrag --rolle mistral-team --dateien datei.txt
  # Prüfen: .normen-auftrag wurde angelegt und Pflichtsätze ausgegeben
  python3 normen/normen.py auftrag --ende
  # Prüfen: .normen-auftrag wurde entfernt
  ```
- [ ] **Hook-Funktion:** Ein verbotener Befehl (z. B. `rm -r` außerhalb von `loeschbar`) wird vom PreToolUse-Hook gestoppt bzw. erfordert Freigabe.

---

## Schritt 8: Erster Arbeitszweig und PR

1. Nicht direkt auf `main` arbeiten:
   ```bash
   git checkout -b chore/projekt-einrichten
   ```
2. Änderungen prüfen und committen:
   ```bash
   git status
   git diff
   git add .
   git commit -m "chore: Agenten-Normen und Multi-KI-Ablauf einrichten"
   git push -u origin chore/projekt-einrichten
   ```
3. Pull Request anlegen und über das Prüftor mergen:
   ```bash
   gh pr create --title "chore: Agenten-Normen und Multi-KI-Ablauf" --body "Ersteinrichtung"
   python3 normen/normen.py merge <PR-Nummer>
   ```

---

## Schritt 9: Zusatz-Checkliste für öffentliche Repositories

Soll das Repository öffentlich zugänglich sein, sind folgende Zusatzpunkte zwingend:

- [ ] **Anonymität:** Keine Echtnamen von Personen, Servern oder internen Systemen in Code, Kommentaren oder Doku.
- [ ] **Neutrale Beispiele:** Nur neutrale Pfade und Beispieldaten verwenden (`~/Projekte/mein-projekt`, `daten/`).
- [ ] **Lizenz:** Eine gültige Open-Source-Lizenz (z. B. `LICENSE` mit MIT-Lizenz) ist vorhanden.
- [ ] **Secret Scanning:** Auf GitHub Secret Scanning und Push Protection aktivieren.
- [ ] **Rückmeldungen:** `[rueckmeldung].repo` verweist weiterhin auf ein **privates** Repository (niemals auf das öffentliche Repo!).

---

## Rückmeldungen an claude-tools (`normen.py melden`)

Erfahrungen aus dem laufenden Projektbetrieb fließen an einer zentralen Stelle zusammen, um Normen und Abläufe zu verbessern.

### Wann melden?
- Nach jedem externen Team-Lauf mit Auffälligkeiten (unerlaubte Dateiänderungen, erfundene Testergebnisse, Nichtbeachtung von Pflichtsätzen).
- Wenn ein Hook fälschlicherweise eine legitime Aktion blockiert (`zu-streng`).
- Wenn eine sicherheitskritische Aktion unbemerkt ausgeführt werden konnte (`zu-locker`).
- Wenn ein Ablauf wiederholt unnötige Rückfragen erzeugt.
- Bei Fehlern in `normen.py` oder Vorlagendateien.

### Meldung erfassen
```bash
# 1. Trockenlauf: Erzeugt lokale Kopie unter .normen/rueckmeldungen/, sendet nichts
python3 normen/normen.py melden --art <art> --titel "Kurzer Titel" --text-datei meldung.md --trocken

# 2. Übertragen an das private Ziel-Repository (nach Prüfung durch Claude und Freigabe durch die Inhaberin):
python3 normen/normen.py melden --art <art> --titel "Kurzer Titel" --text-datei meldung.md [--agent <rolle>] [--norm <ID>] [--stufe niedrig|mittel|hoch]
```

### Arten von Rückmeldungen (`--art`):
- `agent-verhalten`: Unerwartetes oder regelwidriges Verhalten eines Sub-Agenten.
- `zu-streng`: Hook sperrt eine harmlose oder notwendige Operation.
- `zu-locker`: Eine gefährliche Aktion wurde nicht verhindert.
- `ablauf`: Vorschlag zur Verbesserung des Multi-KI-Workflows.
- `fehler`: Fehlerhaftes Verhalten in Skripten oder Vorlagen.

### Was niemals in eine Meldung gehört:
- Keine Geheimnisse, Tokens, API-Schlüssel oder Passwörter.
- Keine personenbezogenen Daten (Namen, E-Mails, Telefonnummern, IBAN).
- Keine Dateiinhalte oder Pfade gesperrter Dateien.
- Keine ungefilterten Logs.
*(Das Skript führt vor dem Absenden eine automatische Prüfung auf sensible Muster durch und bricht bei Funden ab).*

---

## Aktualisieren (`normen.py aktualisieren`)

Aktualisierungen aus `claude-tools` werden kontrolliert ins Projekt übernommen:

```bash
python3 normen/normen.py aktualisieren [--quelle <pfad>]
```

- **Wird der Befehl für Claude abgelehnt** (in einem Projekt im Auto-Modus beobachtet – er ändert Einstellungen wie
  `.claude/settings.json`), bittet Claude die Inhaberin, `! python3 normen/normen.py aktualisieren` selbst einzugeben; danach
  `python3 normen/normen.py selbsttest` (bei „unklar“ wiederholt er einmal selbst; bleibt es „unklar“, der Inhaberin melden).

- **Bedeutung von `normen/herkunft.toml`:** Diese Datei dokumentiert den Versionsstand, den Quell-Commit, das Einspieldatum sowie SHA256-Prüfsummen der gemeinsamen Dateien (`normen.toml`, `rollen.toml`, `normen.py`).
- **Keine manuellen Änderungen:** Die gemeinsamen Vorlagendateien dürfen im Projekt nicht von Hand bearbeitet werden. Weicht eine Prüfsumme ab, verweigert `normen.py aktualisieren` das Überschreiben, um versehentlichen Datenverlust zu verhindern. Projektspezifische Anpassungen gehören ausschließlich in `normen/projekt.toml`.
- **Abnahme:** Nach jeder Aktualisierung müssen der Testbefehl und `python3 normen/normen.py pruefen --diff` fehlerfrei durchlaufen.
