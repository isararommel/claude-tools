# Vorlage: Multi-KI-Ablauf – Claude als Chef-Architekt, Mistral und Gemini als Teams

**Für Claude (Claude Code in Zed, Cowork): lies das, bevor du die Vorlage benutzt, änderst oder in einem Projekt delegierst.**

## Was das ist
Der am 12.–14.11.2026 in einem Projekt erprobte Ablauf: Claude Opus plant, spezifiziert, prüft und committet;
die Arbeit läuft über zwei externe Teams, damit das Claude-Kontingent geschont wird:

| Agent (Claude Code) | Externes CLI | Wofür | Datenschutz |
|---|---|---|---|
| `mistral-team` | Mistral Vibe `vibe` (Mistral Large als Teamleiter, Sub-Agenten flash-scout, code-worker, code-reviewer) | Umsetzung nach Spezifikation, Unit-Tests, Testläufe, zweites Review | keine Geheimnisse; Forschungsdaten nur nach Freigabe (eigene Mistral-Lizenz) |
| `gemini-analyst` | Google Antigravity `agy --model gemini-3.8-flash-high` | Analyse vieler Dateien, Konzept-gegen-Code, Doku, Zweitmeinung | keine Geheimnisse, **keine personenbezogenen Daten, keine Forschungsdaten** |

Beide Agenten sind nur **Schnittstellen** (Modell Haiku, Werkzeuge nur `Bash, Read`): Prompt-Datei schreiben → CLI aufrufen →
Ergebnis zurückgeben. Sie erledigen nie selbst etwas. Die maßgebliche Beschreibung ist `multi-ki-ablauf.md` (eine Quelle für
alle Projekte) – vor jeder Delegation lesen, besonders Abschnitt 5 (Pflichtsätze nach dem Lösch-Vorfall vom 12.11.).

## Dateien
```text
multi-ki-ablauf.md                     Hauptanleitung (→ <projekt>/docs/multi-ki-ablauf.md)
projekt/CLAUDE-abschnitt.md            wird an CLAUDE.md angehängt (Platzhalter @@TESTBEFEHL@@, @@SPERRLISTE@@)
projekt/AGENTS.md                      Regeln, die vibe und agy im Projekt selbst lesen (Pflichtsätze, Sperrliste)
projekt/.geminiignore                  Pfade, die Gemini nicht lesen soll (Sperrliste + Geheimnis-Muster)
projekt/.claude/settings.json          Freigabe Bash(agy:*), Bash(vibe:*); Lesesperre für .env, *.secret, ~/.ssh
projekt/docs/uebergabe-vorlage.md      manueller Weg (Bilder, Deep Research im Browser; Ergebnis „von der Nutzerin erzeugt“)
projekt/PLAN.md                        zentrale Aufgabenliste je Projekt (nur angelegt, wenn sie fehlt)
benutzer/agents/                       mistral-team.md, gemini-analyst.md, Explore.md für ~/.claude/agents/ (gelten in allen Projekten)
einrichten.sh                          überträgt alles in ein Projekt, ohne zu überschreiben
```

## Normen
Regeln, Zuständigkeiten und deren Durchsetzung (Hooks, Auftragsdatei, Prüfung) stehen in `../agenten-normen/` und werden
dort eingerichtet. Diese Vorlage regelt nur den Ablauf der Delegation.

## In einem Projekt einrichten
```bash
bash ~/Documents/Projekte/claude-tools/multi-ki/einrichten.sh <projekt> \
     --test "<testbefehl>" [--sperre <pfad>]… [--benutzer-agents]
```
- `--test`: Testbefehl des Projekts (Abnahmekriterium in jedem Auftrag), z. B. `make test`, `swift test`, `pytest`.
- `--sperre`: Pfade mit Geheimnissen, personenbezogenen Daten oder Forschungsdaten – landen in CLAUDE.md, AGENTS.md und `.geminiignore`.
- `--benutzer-agents`: nur auf einem neuen Rechner (schreibt nach `~/.claude/agents/`, aber nur wenn dort nichts liegt).
- Danach: `git diff` lesen, committen. Die agy-Freigabeliste (`ALLOW`) in `~/.claude/agents/gemini-analyst.md` muss den
  Testbefehl des Projekts enthalten (Präfixform ohne `*`, z. B. `command(make test)`) – Änderung in `~/.claude`
  nur mit Zustimmung der Inhaberin.

## Stand der Agent-Dateien
- `benutzer/agents/*.md` sind Kopien der echten Fassungen aus `~/.claude/agents/` (Stand 14.11.2026, inkl. `command(make test)` in der
  agy-Freigabeliste). Abgleich mit `~/.claude/agents/`: Claude darf lesen (Normen v4), ändern nur mit Zustimmung der Inhaberin; siehe `benutzer/agents/LIES-MICH.md`.
- `gemini-analyst.md` enthält seit 14.11.2026 einen **Bildmodus**: agy erzeugt mit `generate_image` 3–5 Kandidaten (JPG, Größe je Seitenverhältnis, z. B. 1:1 → 1024 × 1024, 16:9 → 1376 × 768; seit agy 1.5.9 mit read_file-Freigabe),
  der Agent kopiert sie mit `cp -n` nach `docs/gemini/kandidaten/`.

- Seit 15.11.2026: **Claude schreibt die Prompt-Datei selbst** (Write-Werkzeug, Lauf-Ordner unter `$TMPDIR`), die Schnittstellen starten nur
  noch das CLI. Grund: Der Normen-Hook sperrte Heredocs, deren Text die Pflichtsätze (`rm`, `git restore` …) oder `*.secret` enthielt.
  Die Fassungen hier und in `~/.claude/agents/` sind seitdem gleich.

## Regeln beim Ändern dieser Vorlage
- Pflichtsätze (Abschnitt 5) nie kürzen oder umformulieren.
- Keine Freigaben für `--auto-approve`, `--yolo`, `--dangerously-skip-permissions`.
- Änderungen am Ablauf in `multi-ki-ablauf.md` nur hier pflegen; Projekte holen den neuen Stand mit `einrichten.sh` – eine Quelle.
- CLI-Optionen ändern sich schnell (Antigravity löst Gemini-CLI ab). Bei Fehlern zuerst `agy --help`, `vibe --help`.
