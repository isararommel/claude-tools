# Changelog

Alle wesentlichen Änderungen an `claude-tools` (Agenten-Normen, Multi-KI-Ablauf und Skripte) werden in dieser Datei dokumentiert.

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
