# claude-tools

Werkzeuge für die strukturierte und sichere Zusammenarbeit von **Claude Code** (als Chef-Architekt und Orchestrator) mit externen KI-Teams (**Mistral Vibe** und **Google Antigravity**).

Das Repository bündelt zwei Kernkomponenten:
1. **Agenten-Normen:** Ein verbindliches, technisch durchgesetztes Regelwerk (Muss N01–N11, Soll S01–S05) mit Hooks, Schranken und Rollenmodell.
2. **Multi-KI-Ablauf:** Ein bewährter Orchestrierungsablauf, der Kontingente schont, indem Implementierung und Analyse an externe Teams delegiert werden, während Planung, Testkontrolle und Commits bei Claude verbleiben.

---

## Repository-Inhalt

| Pfad | Zweck | Art |
|---|---|---|
| `agenten-normen/` | Regelwerk (`normen.toml`), Rollen (`rollen.toml`), Prüfskript (`normen.py`), Hooks für Claude Code und Vibe | Quelle |
| `multi-ki/` | Ablaufanleitung (`multi-ki-ablauf.md`), Vorlagen für `AGENTS.md`, `.geminiignore`, Agent-Definitionen | Quelle |
| `einrichten.sh` | Zentrales Einrichtungsskript, ruft die Installer von Normen und Multi-KI auf | Werkzeug |
| `NEUES-REPOSITORY.md` | Schritt-für-Schritt-Arbeitsanweisung für Claude Code in neuen Projekten | Dokumentation |
| `KONZEPT.md` | Detaillierte Architektur, Grundsätze und Sicherheitskonzept | Dokumentation |
| `CHANGELOG.md` | Versionshistorie mit Migrations- und Update-Hinweisen | Dokumentation |
| `tests/` | Testsuite für Vorlagen, Installer, Aktualisierung und Datenschutzprüfungen | Tests |
| `normen/` | Normenkonfiguration für dieses Repository selbst | Eingespielte Kopie |
| `.claude/`, `.vibe/`, `.githooks/` | PreToolUse-, Stop- und Git-Hooks für dieses Repository | Eingespielte Kopie |
| `AGENTS.md`, `docs/` | Externe Agentenregeln und Ablaufdoku für dieses Repository | Eingespielte Kopie |

---

## Schnellstart

In drei Schritten ein neues oder bestehendes Projekt ausstatten:

```bash
# 1. Repository lokal bereitstellen
git clone <repository-url> ~/Documents/Projekte/claude-tools

# 2. Im Zielprojekt einrichten (Normen, Hooks, Multi-KI-Konfiguration)
bash ~/Documents/Projekte/claude-tools/einrichten.sh ~/Projekte/mein-projekt --test "make test"

# 3. Einrichtung im Zielprojekt überprüfen
cd ~/Projekte/mein-projekt && python3 normen/normen.py pruefen --diff
```

---

## Weiterführende Dokumentation

- [NEUES-REPOSITORY.md](NEUES-REPOSITORY.md) – Detaillierte Arbeitsanweisung für Claude Code beim Einrichten frischer Repositories.
- [KONZEPT.md](KONZEPT.md) – Grundsätze, Funktionsweise von Schranken und Hooks sowie Sicherheitsmodell.
- [agenten-normen/LIES-MICH.md](agenten-normen/LIES-MICH.md) – Dokumentation des Normensystems und der technischen Durchsetzung.
- [multi-ki/LIES-MICH.md](multi-ki/LIES-MICH.md) – Ablauf und Rollenverteilung im Multi-KI-Betrieb.

---

## Tests

Die Funktionsfähigkeit der Werkzeuge, Skripte und Vorlagen wird automatisiert geprüft:

```bash
make test
```

Die Testsuite stellt u. a. sicher, dass Vorlagen konsistent sind, das Einrichten und Aktualisieren idempotent funktioniert und keine sensiblen Daten enthalten sind.

---

## Rückmeldungen

Erfahrungen, Regelverschärfungen oder Optimierungsideen aus Projekten werden **nicht** als öffentliche GitHub-Issues in diesem Repository erfasst. Die Rückmeldung erfolgt direkt aus den Projekten über ein privates Repository der Inhaberin:

```bash
python3 normen/normen.py melden --art <art> --titel "..." --text-datei meldung.md
```

Dies schützt projektspezifische Kontexte und gewährleistet eine vertrauliche Prüfung vor einer Übernahme in die öffentlichen Vorlagen.

---

## Lizenz

Dieses Projekt steht unter der **MIT-Lizenz** (siehe Datei `LICENSE`).
