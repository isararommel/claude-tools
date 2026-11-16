# Changelog

Alle wesentlichen Änderungen an `claude-tools` (Agenten-Normen, Multi-KI-Ablauf und Skripte) werden in dieser Datei dokumentiert.

---

## v7 – in Arbeit

**Aktualisieren nötig:** ja (`normen.py aktualisieren`, dann `normen.py selbsttest`)

### Neu
- **Selbsttest (G1):** `normen.py selbsttest [--werkzeug claude|vibe]` prüft durch das echte Claude Code und Vibe, ob die Normen-Hooks greifen: ein Köder-Befehl, den nur der Hook sperrt (für alle Rollen, für Agenten unsichtbar). Ergebnis je Werkzeug gesperrt / NICHT GESPERRT / unklar. Pflicht nach jedem Update.
- **pre-commit nicht umgehen (G2):** N10 sperrt `--no-verify`, `git commit -n` und das Setzen von `core.hooksPath` (neue Fähigkeit `hooks-umgehen`, nur die Inhaberin); `git config --get core.hooksPath` bleibt frei.

---

## v6 – 2026-11-16

**Aktualisieren nötig:** ja (`normen.py aktualisieren`; zusätzlich `multi-ki/einrichten.sh` für CLAUDE-Abschnitt, Ablauf und PLAN.md;
Agent-Definitionen nach `~/.claude/agents/` kopieren – Rückfrage)

### Neu
- **S07-SUPERVISOR:** Fable als Advisor der Hauptsitzung; fünf Pflicht-Konsultationen; bei Ausfall ohne Fable weiter, Normänderungen zurückstellen.
- **S06-CODE-MODE:** mehrstufiges Auswerten als Skript; der Hook prüft Skripte außerhalb des Projekts per AST (`normen.py skript --pruefen`).
- **`nur_rollen`:** Normen nur für die Hauptsitzung erscheinen nicht in Team-Aufträgen und nicht im AGENTS-Block.
- **Rollen `fable` und `skript`:** `fable` (Advisor) und der Regelsatz `skript` für Befehle in Skripten bekommen keine Aufträge; `skript` steht nicht in der Rollentabelle. Rollenkette in `kurz.md`.
- **PLAN.md:** zentrale Aufgabenliste je Projekt; Sitzungen beginnen dort. `multi-ki/einrichten.sh` legt sie an, wenn sie fehlt; `normen.py merge` weist auf eine unveränderte PLAN.md hin.
- S03: Hauptsitzung fragt nach drei Fehlversuchen den Advisor, danach höchstens ein weiterer Versuch. S05: Auswerte-Skripte nach S06 ausgenommen.

### Agent-Definitionen
- `mistral-team.md`, `gemini-analyst.md`, neu `Explore.md`: Advisor nie aufrufen.

---

## v5 – 2026-11-16

**Aktualisieren nötig:** ja (`normen.py aktualisieren`; zusätzlich `.vibe/hooks.toml` übernehmen und die Agent-Definitionen nach `~/.claude/agents/` kopieren)

### Behoben
- **Vibe-Hooks waren wirkungslos (#25):** In `.vibe/hooks.toml` fehlte bei allen vier Einträgen das Pflichtfeld `name`; Vibe 3.x verwarf sie still, die Normen-Hooks griffen in Vibe nicht. Jetzt mit `name`, geprüft mit dem Lader der installierten Vibe-Version (Prüfbefehl steht in der Datei).
- **N10 zu streng (#23):** Reines Lesen aus `~/.gemini` usw. (`find … -newer`, `cp -n ~/.gemini/… docs/…`) löste eine Rückfrage aus. `find` zählt nur noch mit schreibenden Aktionen (`-delete`, `-exec`, `-execdir`, `-ok`, `-fprint` …), `cp`/`ln`/`install`/`rsync` nur mit dem Einstellungsordner als Ziel (auch `-t`/`--target-directory`). Neu erkannt: `>> "$HOME/…"` mit Anführungszeichen.
- **N06 zu locker:** `[pfade].lesbar_extern` galt nur für Edit/Write; Bash-Befehle (`cd … && sed -i …`, `cp … <ordner>/`, `git -C <ordner> commit`, Umleitung) gingen durch. Jetzt gesperrt.
- **agy-Schreibmodus (#22):** `normen.py auftrag --rolle gemini-analyst` verlangt keine Abnahmebefehle mehr (neues Rollenfeld `abnahme_durch_claude`); agy headless darf nur freigegebene Befehle ausführen.

### Agent-Definitionen (`multi-ki/benutzer/agents/`)
- `gemini-analyst.md`: Freigabeliste um Lesebefehle ergänzt (`--settings` ersetzt die globale agy-Liste), Bildmodus mit `read_file`-Freigabe für Lauf- und Bildordner, Bildgröße je Seitenverhältnis.
- `mistral-team.md`: Modell (`active_model`), `outcome` und `steps` aus `export.json` prüfen und berichten; „Model … not available“ und `hooks.toml`-Fehler nicht mehr als harmlos behandeln.

---

## v4 – 2026-11-15

**Aktualisieren nötig:** ja

### Änderungen und Neuerungen
- **Rolle `inhaberin`:** Die Rolle der Projektbesitzerin heißt nun einheitlich `inhaberin`. Der konfigurierbare Anzeigename wird in `normen/projekt.toml` über `[projekt].inhaberin` festgelegt (z. B. für Hinweise „bitte {inhaberin} fragen“).
- **N10 differenziert (Fähigkeit `einstellungen-lesen`):** Reines Lesen in den Konfigurationsordnern der Agenten (`~/.claude`, `~/.vibe`, `~/.gemini`, `~/.antigravity`) ist für Claude Code ohne Rückfrage erlaubt. Schreibzugriffe erfordern weiterhin eine ausdrückliche Rückfrage. Für externe Teams bleiben diese Verzeichnisse strikt gesperrt.
- **N03 geschärft:** Das Lesen und Schreiben von `~/.ssh` sowie `~/.config/gh` ist explizit unter N03 (Geheimnisse) verboten.
- **Externe Lesepfade (`[pfade].lesbar_extern`):** Einführung der Option `lesbar_extern` in `projekt.toml` (Standard: `["~/Documents/Projekte/claude-tools"]`). Ermöglicht Agenten das Lesen von Vorlagen außerhalb des Projektordners; Schreibzugriffe sind dort technisch unterbunden.
- **Versionsverfolgung (`normen/herkunft.toml`):** Protokolliert Version, Quell-Commit, Einspieldatum und SHA256-Prüfsummen der gemeinsamen Vorlagendateien.
- **Aktualisierungsbefehl (`normen.py aktualisieren`):** Neuer Befehl zum kontrollierten Nachziehen aktualisierter Vorlagendateien aus `claude-tools`. Prüft auf manuelle Änderungen im Zielprojekt und bricht bei Abweichungen ab. `normen.py pruefen` gibt entsprechende Hinweise aus.
- **Rückmeldesystem (`normen.py melden`):** Neuer Befehl zur strukturierten Übermittlung von Beobachtungen, Regelproblemen und Fehlern an ein privates GitHub-Repository der Inhaberin. Gesteuert über die neue Rollenfähigkeit `rueckmelden` (Claude fragt vor dem Absenden; externe Teams gesperrt) inklusive automatischer Prüfung auf sensible Muster.
- **Gemeinsames Einrichtungsskript (`einrichten.sh`):** Neues Skript im Wurzelverzeichnis, das `agenten-normen/einrichten.sh` und `multi-ki/einrichten.sh` in einem einzigen Aufruf bündelt.
- **Vereinheitlichte Marke in `CLAUDE.md`:** Der Multi-KI-Abschnitt wird nun über die Marke `<!-- multi-ki-abschnitt -->` eingebunden. Frühere Vorlagenmarken werden beim Einrichten automatisch umgestellt.
- **Ergänzung von `AGENTS.md`:** Multi-KI-Regeln für externe Modelle werden beim Einrichten sauber an den generierten Normen-Block angehängt, anstatt bestehende Konfigurationen zu überschreiben.

---

## v3 – 2026-11-14

**Aktualisieren nötig:** nicht zutreffend (Initialversion)

### Erste konsolidierte Fassung
- **Normensystem:** Einführung der Muss-Normen N01–N11 und Soll-Normen S01–S05 für alle Coding-Agenten im Projekt.
- **Technische Durchsetzung:**
  - PreToolUse- und Stop-Hooks für Claude Code (`.claude/settings.json`).
  - Pre-Tool-Hooks für Mistral Vibe (`.vibe/hooks.toml`).
  - Git-Pre-Commit-Hook (`.githooks/pre-commit`) basierend auf `normen.py pruefen --staged`.
- **Prüftor für den Hauptzweig:** Einführung von `python3 normen/normen.py merge <PR>` zur Absicherung von Merges nach `main` (automatischer Testlauf und Diff-Audit).
- **Auftragssteuerung:** Definition von Arbeitsbereichen für externe Agenten über `.normen-auftrag` und Befehle `normen.py auftrag` sowie `normen.py auftrag --ende`.
