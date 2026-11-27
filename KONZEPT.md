# claude-tools – Konzept (Stand 2026-11-15, Normen v4)

Öffentliches Repository mit allen Werkzeugen, mit denen Claude Code (als Orchestrator) und seine Teams arbeiten:
Agenten-Normen, Multi-KI-Ablauf (Claude + Mistral Vibe + Gemini/Antigravity), Agenten-Definitionen, Anleitung für neue
Repositories. Projektbezogenes (Testbefehl, gesperrte Pfade, Namen) liegt **nie** hier, sondern in `normen/projekt.toml`
des jeweiligen Projekts.

## 1. Grundsätze
- **Öffentlich:** keine Geheimnisse, keine personenbezogenen Daten, keine Server-, Pfad- oder Projektnamen aus privaten
  Repositories. Beispiele sind neutral (`daten/geheim.json`, `~/Projekte/mein-projekt`). Ein Test prüft das (Abschnitt 7).
- **Eine Quelle, eingespielte Kopien:** Projekte lesen von hier nur. Sie erhalten eine Kopie mit Versionsvermerk und
  aktualisieren bewusst. Kein Projekt-Hook ruft Code aus `claude-tools` live auf.
- **Nur lesend von außen:** `claude-tools` ist der einzige Ort außerhalb des eigenen Projektordners, den Agenten lesen
  dürfen. Schreiben dort nur in einer Sitzung, die in `claude-tools` selbst läuft (mit den Normen dieses Repositorys).
- **Neutrale Rolle:** Die Rolle der Besitzerin heißt `inhaberin`; der Anzeigename kommt aus `projekt.toml`
  (`[projekt].inhaberin = "…"`). Meldungen lauten z. B. „bitte <Anzeigename> fragen“.

## 2. Aufbau
```
claude-tools/
  LIES-MICH.md            Überblick, Schnellstart
  NEUES-REPOSITORY.md     Schritt-für-Schritt-Anleitung, die eine Claude-Instanz in einem neuen Repo abarbeitet
  KONZEPT.md              dieses Dokument
  (Version: [meta].version in agenten-normen/projekt/normen/normen.toml; steigt, wenn sich eine Muss-Norm ändert)
  CHANGELOG.md            was sich je Version ändert, mit Hinweis „Aktualisieren nötig: ja/nein“
  einrichten.sh           ein Einstieg für beides: ruft agenten-normen/ und multi-ki/einrichten.sh nacheinander auf
  agenten-normen/         QUELLE Normen: einrichten.sh, LIES-MICH.md, projekt/ (normen/*.toml, normen.py, Hooks)
  multi-ki/               QUELLE Multi-KI: einrichten.sh, multi-ki-ablauf.md, projekt/ (AGENTS.md, .geminiignore, …),
                          benutzer/agents/ (mistral-team.md, gemini-analyst.md für ~/.claude/agents/)
  qs/                     QUELLE Abteilung Qualitätssicherung: einrichten.sh (Gutachter-Büros in einem eigenen
                          QS-Projekt, gutachter-*.md für ~/.claude/agents/), rollen/, buero/, gutachten-format.md
  tests/                  make test
  Makefile, LICENSE (MIT)
  normen/, .claude/, .vibe/, .githooks/, AGENTS.md, docs/   eingespielte KOPIE für dieses Repository selbst
```
Diese Inhalte stammen aus den Vorlagen eines privaten Repositorys (Ordnerstruktur beibehalten, damit die Skripte unverändert laufen)
und werden bereinigt (keine Git-Geschichte, Herkunft im LIES-MICH vermerkt). Normen-Version wird 4 (Rollen-Umbenennung).

## 3. Einrichten und Aktualisieren
- `bash ~/…/claude-tools/einrichten.sh <projekt> --test "<befehl>" [--sperre <pfad>]… [--inhaberin <Name>]`
  - kopiert `normen/`, Hooks, `AGENTS.md`, `.geminiignore`, `docs/multi-ki-ablauf.md`, ergänzt den CLAUDE.md-Abschnitt;
  - schreibt `normen/herkunft.toml`: `quelle = "claude-tools"`, `version`, `commit`, `eingespielt_am`, Prüfsummen
    der kopierten Dateien;
  - `projekt.toml` wird nur beim ersten Mal angelegt, danach nie überschrieben.
- `python3 normen/normen.py aktualisieren [--quelle <pfad>]`
  - Quelle: Option, sonst `[quelle].pfad` aus `projekt.toml`, sonst `~/Documents/Projekte/claude-tools`;
  - zeigt CHANGELOG seit der eingespielten Version und den Diff, spielt dann ein (wie `einrichten.sh`);
  - bricht ab, wenn eingespielte Dateien im Projekt von Hand verändert wurden (Prüfsumme weicht ab) → erst melden;
  - Abnahme danach: Testbefehl + `pruefen --diff` grün.
- `pruefen` meldet als **Hinweis** (kein Fehler): Kopie älter als die Quelle; eingespielte Datei verändert.

## 4. Lese-Erlaubnis für claude-tools
- `projekt.toml`: `[pfade].lesbar_extern = ["~/Documents/Projekte/claude-tools"]` (Standard).
- N06 im Hook: Lesen (Read, Grep, `cat`, `ls`) unter diesen Pfaden erlaubt, jede schreibende Aktion dort gesperrt
  (Edit/Write, Umleitung `>`, `mv`, `cp` dorthin, `git` mit `-C` dorthin). Ausnahme: Sitzung läuft in `claude-tools` selbst.
- Für externe Teams (Vibe, agy) gilt dasselbe über ihre Hook-Konfiguration bzw. die Freigabeliste.

## 5. Rückmeldungen (`normen.py melden`)
Zweck: Erfahrungen aus allen Projekten fließen an einer Stelle zusammen, damit Normen und Abläufe besser werden.

Aufruf (durch Claude, nie durch externe Teams):
```
python3 normen/normen.py melden --art <art> --titel "…" --text-datei <pfad> [--agent <rolle>] [--norm <ID>] [--stufe niedrig|mittel|hoch]
```
- `art`: `agent-verhalten` (Sub-Agent hat sich merkwürdig verhalten), `zu-streng` (Hook/Freigabe sperrt unnötig),
  `zu-locker` (etwas ging durch, was gesperrt sein sollte), `ablauf` (Optimierungsidee), `fehler` (Fehler in normen.py/Vorlage).
- Ziel: GitHub-Issue im **privaten** Repository aus `[rueckmeldung].repo` (projekt.toml, z. B. das private Werkzeug-Repository der Inhaberin),
  Labels `rueckmeldung` + `art:<art>`. Kein Ziel konfiguriert → Abbruch mit Hinweis, nie Standard auf ein öffentliches Repo.
  Vor dem Anlegen prüft `melden` per `gh repo view --json visibility`, dass das Ziel privat ist.
- Inhalt (feste Vorlage, Markdown): Projekt (nur Repo-Name), Normen-Version, Agent/Rolle, Norm-ID, Was passierte, Was erwartet
  war, Vorschlag, Beleg (Befehl/Hook-Meldung, gekürzt). **Keine** Dateiinhalte, Logs mit Daten oder Pfade gesperrter Dateien.
- Datenschutz-Prüfung vor dem Senden: dieselben Muster wie N03 (Geheimnisse) plus E-Mail-Adressen, IBAN, Telefonnummern,
  Pfade aus `[pfade].gesperrt`; Treffer → Abbruch mit Fundstelle. Text wird zusätzlich lokal unter
  `.normen/rueckmeldungen/<zeit>-<art>.md` abgelegt (gitignored), damit nichts verloren geht, wenn `gh` scheitert.
- Senden ist nach außen gerichtet: Claude zeigt Titel und Text und fragt vor dem ersten Senden je Sitzung
  (Hook-Entscheid `fragen`). Mehrere Meldungen einer Sitzung möglichst bündeln.
- Wann melden (Regel in CLAUDE-abschnitt.md und `NEUES-REPOSITORY.md`): nach jedem Team-Lauf mit Auffälligkeit
  (eigenmächtige Änderungen, erfundene Ergebnisse, Verstoß gegen Pflichtsätze), wenn ein Hook nachweislich falsch sperrt
  oder etwas Gefährliches durchließ, wenn ein Ablauf wiederholt Rückfragen erzeugt.
- Auswertung: im privaten Ziel-Repository als Issues; Claude fasst sie auf Wunsch zusammen und schlägt Änderungen in
  `claude-tools` vor. Normänderungen nur mit Zustimmung der Inhaberin; neue Version + CHANGELOG.

## 6. NEUES-REPOSITORY.md (Inhalt)
Geschrieben als Arbeitsanweisung für eine Claude-Instanz, die in einem leeren oder frischen Repository startet:
1. Vorprüfung: Ist es ein Git-Repo? Sichtbarkeit (`gh repo view`)? Branch `main` geschützt? Gibt es schon CLAUDE.md/normen?
2. Fragen an die Inhaberin (gebündelt, eine Runde): Zweck, Sprache, Testbefehl, sensible Pfade (Geheimnisse,
   personenbezogene Daten, Forschungsdaten), privat/öffentlich, welche Teams erlaubt.
3. Grundgerüst: `.gitignore` (u. a. `.env*`, `.normen/`, `.venv`), `README`/`LIES-MICH.md`, Testbefehl, der sofort grün ist.
4. `einrichten.sh` ausführen, `projekt.toml` füllen (gesperrt, löschbar, lesbar_extern, rueckmeldung.repo, inhaberin).
5. CLAUDE.md: projektspezifische Regeln + Abschnitt Multi-KI; AGENTS.md und `.geminiignore` prüfen.
6. Agenten-Definitionen unter `~/.claude/agents/` mit `agenten/` abgleichen (Hinweis an die Inhaberin, falls abweichend).
7. Abnahme: Testbefehl, `normen.py pruefen --diff`, ein Probe-Auftrag (`normen.py auftrag --rolle mistral-team --dateien …`
   und `--ende`), Hook-Probe (ein gesperrter Befehl wird abgelehnt).
8. Erster Commit auf eigenem Branch, PR, `normen.py merge <PR>`.
9. Checkliste für öffentliche Repositories (zusätzlich): kein Name/Pfad aus privaten Projekten, Beispiele neutral,
   Lizenzdatei, Secret-Scanning auf GitHub einschalten.

## 7. Tests (`make test`)
- bisherige Tests der Vorlagen (`tests/test_normen.py`), angepasst an Rolle `inhaberin`;
- `einrichten.sh` in ein Temp-Repo, danach dort Testbefehl + `pruefen` grün; zweiter Lauf ändert nichts (idempotent);
- `aktualisieren`: Versionssprung, verweigert bei von Hand geänderter Datei;
- `melden`: lehnt öffentliches Ziel ab (gh durch Attrappe ersetzt), findet Geheimnis/E-Mail im Text, schreibt lokale Kopie;
- N06: Lesen in `lesbar_extern` erlaubt, Schreiben dort gesperrt;
- **Öffentlich-Prüfung:** grep über das ganze Repo auf eine Sperrliste privater Begriffe (liegt nicht im Repo, sondern wird
  per Umgebungsvariable/lokaler Datei `~/.config/claude-tools/privat-begriffe.txt` übergeben; fehlt sie → Test übersprungen
  mit Hinweis).

## 8. Umzug eines Projekts mit älteren Normen (v3, Vorlagen im Projekt)
1. `bash ~/Documents/Projekte/claude-tools/einrichten.sh <projekt> --test "<testbefehl>"` (bzw. später `normen.py aktualisieren`).
2. Alte Vorlagen-Kopie im Projekt entfernen (N08, keine zweite Fassung), Verweise in CLAUDE.md, AGENTS.md, docs/ anpassen.
3. `projekt.toml` ergänzen: `[projekt].inhaberin`, `[rueckmeldung].repo` (privat!), ggf. `[pfade].lesbar_extern`;
   im Ziel-Repository die Labels `rueckmeldung` und `art:<art>` anlegen.
4. `~/.claude/CLAUDE.md` auf `claude-tools/…` verweisen lassen (Einstellung – nur mit Zustimmung der Inhaberin).

## 9. Änderungen an den Normen in Version 4 (aus Rückmeldungen)
- **N10 „einstellungen“ zu streng** (Rückmeldung aus einem Projekt, 15.11.): Das Muster trifft jeden Bash-Befehl, der
  `~/.claude`, `~/.vibe`, `~/.gemini`, `~/.antigravity`, `~/.ssh` oder `~/.config/gh` nur erwähnt, auch reines Lesen. Für die
  Rolle claude folgt daraus jedes Mal eine Rückfrage an die Inhaberin. Neu:
  - Lesen (`ls`, `cat`, `head`, `grep`, `diff`, `find` ohne `-delete`/`-exec`) in `~/.claude`, `~/.vibe`, `~/.gemini` und
    `~/.antigravity` entscheidet Claude selbst (erlaubt).
  - Weiterhin gesperrt bzw. Rückfrage: jedes Schreiben dort; jedes Lesen von Schlüssel- und Zugangsdateien (`~/.ssh/`,
    `~/.config/gh/`, `*credentials*`, `*token*`, `*.key`, `.env*`) → N03.
  - Externe Teams: unverändert gesperrt (eigene Fähigkeit `einstellungen-lesen`).
- **Rückmeldungen** als eigene Fähigkeit `rueckmelden` (claude: fragen, Teams: nein).
- Lizenz: MIT.
