# Abteilung Qualitätssicherung (QS)

Die Abteilung Qualitätssicherung stellt drei kritische, unabhängige und möglichst kontextfreie Gutachter für Software-, Design- und UX-Arbeiten bereit. Jeder Gutachter arbeitet entweder in einem eigenen Büro (eine dedizierte Claude-Code-Sitzung mit Postfächern für Ein- und Ausgang) oder wird als Sub-Agent direkt aus einer anderen Sitzung heraus konsultiert.

## Aufbau der Quelle

- `rollen/`: Vorlagen der Rollen (`design.md`, `ux.md`, `architektur.md`) mit Metadaten im Kopf, Vorgehen, Prüfpunkten und Grenzen.
- `buero/`: Vorlage für ein Büro mit `CLAUDE.md` (Büroordnung für Eingang und Ausgang) und `.claude/settings.json` (`claudeMdExcludes`, Schreibsperre außerhalb des Büros).
- `gutachten-format.md`: Einheitlicher Gutachten-Aufbau (Kopfdaten, Gesamturteil, belegte Befundtabelle, „Nicht geprüft“); wird beim Einrichten automatisch an jeden Rollentext angehängt.
- `einrichten.sh`: Skript zum Erzeugen der Büros im QS-Projekt und optionalen Installieren der Sub-Agenten.

## Einrichten

Das QS-System wird mit folgendem Aufruf in einem separaten QS-Projekt eingerichtet:

```bash
bash qs/einrichten.sh <qs-ziel> [--benutzer-agents]
```

- Richtet im Zielverzeichnis für jede Rolle ein Büro `buero-<rolle>/` mit den Ordnern `eingang/` und `ausgang/`, lokaler `CLAUDE.md`, `.claude/settings.json` und `.claude/agents/<rolle>.md` ein.
- Mit dem Schalter `--benutzer-agents` werden die Sub-Agenten `gutachter-<rolle>.md` nach `~/.claude/agents/` installiert (erfordert Freigabe der Inhaberin).
- **Wichtig beim ersten Start:** Öffne das QS-Zielprojekt einmal interaktiv mit Claude Code und bestätige den Vertrauensdialog („Trust this folder?“). Ohne dieses Vertrauen an der git-Wurzel ignoriert Claude Code die Sicherheits- und Berechtigungseinstellungen aus den Büro-Dateien.

## Arbeit einreichen (Büro-Weg)

1. Lege einen neuen Auftragsordner an: `<qs-ziel>/buero-<rolle>/eingang/<JJJJ-MM-TT>-<titel>/auftrag.md`.
2. Beschreibe den Gegenstand als Verweis (Pfad und Commit) oder URL. Lege niemals eine Kopie des Projektordners im Eingang ab.
3. Starte die Sitzung im jeweiligen Büro-Ordner:
   ```bash
   claude --agent <rolle> --allowedTools "Read(//<pfad>/**)" "Grep(//<pfad>/**)" "Glob(//<pfad>/**)"
   ```
4. Der Gutachter wählt den neuesten unbearbeiteten Auftrag, analysiert den Gegenstand, schreibt das Gutachten nach `ausgang/<JJJJ-MM-TT>-<titel>/gutachten.md` (und eventuelle Anlagen nach `anlagen/`) und meldet den Speicherort.

## Sub-Agent-Weg

Ein Gutachter kann auch ohne Büro-Ordner direkt aus einer anderen Claude-Code-Sitzung heraus aufgerufen werden:
- Der Agent `gutachter-<rolle>` wird mit der Aufgabenstellung und dem Pfad/Verweis aufgerufen.
- Der Sub-Agent arbeitet mit `omitClaudeMd: true` ohne Schreibwerkzeuge (`Read`, `Grep`, `Glob`; UX zusätzlich die Chrome-Erweiterung – sie bedient den angemeldeten Browser der Inhaberin und ist aus jeder Sitzung aufrufbar).
- Das Gutachten wird nicht als Datei abgelegt, sondern direkt als formatierte Antwort im Gespräch zurückgegeben.

## Neue Rolle hinzufügen

1. Lege eine neue Rollendatei unter `qs/rollen/<name>.md` an.
2. Übernimm den standardisierten YAML-Kopf (`name`, `titel`, `description`, `tools-buero`, `tools-gutachter`).
3. Verfasse den Rollentext mit Vorgehen, Prüfpunkten und Grenzen (ohne das Gutachten-Format zu wiederholen).
4. Führe `bash qs/einrichten.sh <qs-ziel>` erneut aus. Das Skript erzeugt das neue Büro und den entsprechenden Sub-Agenten.

## Grenzen und bekannte Eigenheiten

- **Verschachtelte CLAUDE.md beim Sub-Agenten:** `omitClaudeMd: true` wirkt nur beim Start der Sitzung. Liest der Sub-Agent eine Datei in einem Unterordner eines fremden Projekts, lädt Claude Code eine dort liegende `CLAUDE.md` nachträglich ein (Probe-Befund n).
- **Keine Projektkopien in den Eingang legen:** Kopien fremder Projekte unter `eingang/` laden deren `CLAUDE.md` beim Lesen nach (Probe-Befund i). Die Büro-Einstellungen schließen `eingang/**/CLAUDE.md` zwar aus (Befund m), andere Steuerdateien einer Kopie (`.claude/`, `AGENTS.md`) aber nicht. Der Gegenstand wird daher nur als Verweis übergeben.
- **`advisor` nicht per Konfiguration sperrbar:** Die Einstellung `disallowedTools: advisor` wird von Claude Code nicht beachtet. Die Sperre erfolgt ausschließlich über explizite Anweisungen im Rollentext.
- **Commit-Angabe ohne Bash nicht prüfbar:** Da die Gutachter über kein Bash-Werkzeug verfügen, können sie den angegebenen Commit-Stand nicht verifizieren; die Angabe im Gutachten beruht auf den Daten des Auftrags.
- **Verifikationsstand:** Die Schutzmechanismen wurden in Probeläufen mit `claude -p` und Haiku nachgewiesen (Befunde a–o in `PLAN.md`, Abschnitt QS), die Sperren meist per Befehlszeilen-Schalter statt aus der Büro-`settings.json`; die interaktive Abnahme im Realbetrieb steht noch aus.
