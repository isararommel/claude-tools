# PLAN – zentrale Aufgabenliste

**Jede Sitzung beginnt hier.** Die Inhaberin startet Sitzungen regelmäßig mit `/clear` neu, um Kontingent zu sparen. Deshalb steht
hier alles, was eine frische Sitzung zum Weiterarbeiten braucht: Stand, nächste Aufgaben mit genug Einzelheiten, offene Fragen.
Nach jeder erledigten Aufgabe wird diese Datei aktualisiert (abhaken, nächste Aufgabe ausformulieren) und mitcommittet.

*Stand: 16.11.2026 (nach v6)*

## Verweise

| Datei | Wofür |
|---|---|
| [KONZEPT.md](KONZEPT.md) | Ziel und Aufbau von claude-tools |
| [CHANGELOG.md](CHANGELOG.md) | Normen-Versionen (aktuell v5) |
| [agenten-normen/](agenten-normen/LIES-MICH.md) | Quelle der Normen, Hooks, normen.py |
| [multi-ki/multi-ki-ablauf.md](multi-ki/multi-ki-ablauf.md) | Ablauf mit mistral-team / gemini-analyst |
| [NEUES-REPOSITORY.md](NEUES-REPOSITORY.md) | Neues Projekt einrichten |
| [docs/plaene/normen-v6-plan.md](docs/plaene/normen-v6-plan.md) | Freigegebener Plan v6: Entscheidungen, wörtliche Texte, Spezifikation, Tests |

## Arbeitsweise (kurz)

- Öffentliches Repository: keine Namen, Server, privaten Projekte oder Pfade; Inhaberin nur als `{inhaberin}`.
- Eigener Branch je Aufgabe, PR, Merge über `python3 normen/normen.py merge <PR>`; Testbefehl `make test`.
- Normen nur in der Quelle (`agenten-normen/`, `multi-ki/`) ändern, `meta.version` erhöhen, CHANGELOG ergänzen, dann
  `bash einrichten.sh . --test "make test"` (spielt die Kopie in dieses Repository ein).
- Projekte holen Änderungen mit `python3 normen/normen.py aktualisieren`; der Multi-KI-Teil braucht `multi-ki/einrichten.sh` oder Handarbeit.
- Bekannter Hook-Fehlalarm: Liegt der Arbeitsordner einer *anderen* Projektsitzung hier, sperrt deren Hook Befehle mit `>`.

## Erledigt (letzte Schritte)

- ✅ 16.11. Agent-Definitionen (mit „Advisor nie aufrufen“, neu Explore.md) nach `~/.claude/agents/` übernommen; globale
  CLAUDE.md um Fable ergänzt. Probe `disallowedTools: advisor` (Claude Code 2.1.325): **wirkt nicht** – der Testagent listet
  `advisor` weiterhin (Selbstauskunft); Sperre bleibt Anweisung.
- ✅ 16.11. Vibe-Modelle repariert: `~/.vibe/config.toml` mit vollständigen Einträgen (Server-Liste lieferte nur noch
  GLM-5.3 Flash); Large 4, GLM-5.3, GLM-5.3 Flash getestet. CLAUDE.md dieses Repositorys um PLAN/Fable/Regel 8 ergänzt.
- ✅ 16.11. Normen v6 (S06 Code Mode mit AST-Prüfung im Hook, S07 Fable als Advisor, `nur_rollen`, Rollen fable/skript,
  PLAN.md-Vorlage, Agent-Definitionen „Advisor nie aufrufen“) – PR #2. `normen.py` schrieb Claude selbst (Vibe wich auf
  Mistral Medium 3.5 aus und änderte nichts).
- ✅ 16.11. Normen v5 (Vibe-Hooks wirksam, N10/N06 korrigiert) – PR #1
- ✅ 15.11. Erste Fassung: Normen v4, Multi-KI-Ablauf, Anleitung für neue Repositories

## Nächste Aufgaben (in dieser Reihenfolge)

### 1. Guardrail-Ausbau (Normen v7) *(Entscheidungen 16.11. getroffen, Branch `normen-v7`)*

Entwurf: `docs/plaene/guardrails-v7-entwurf.md` – Lücken L1–L10, Bewertung von 22 externen Repos, Ideen a–h, Pakete G1–G11,
Normtext-Diffs; Entscheidungen der Inhaberin in Abschnitt 8. Paketplan steht (Advisor-Konsultation 1 erledigt).
Stand: **G1, G2, G3 fertig** (G3: Bash-Schreibziele auf GESCHUETZT fragen/nein, lesbar_extern-Fehlalarm behoben). **G1:** (`normen.py selbsttest`: live gesperrt für claude und vibe, Gegenprobe ohne Hooks „NICHT GESPERRT“).
Version 7 und CHANGELOG-Abschnitt „v7 – in Arbeit“ sind angelegt; **ein Merge für v7** nach G6 (vorher Advisor-Konsultation 4/5 mit
Köder-Muster, Live-Ausgabe, Gegenprobe). Nächstes Paket: **G4** (danach G5, G6); erledigt: G2 (`--no-verify`/`core.hooksPath` sperren, Opus selbst, Normtext aus
Entwurf Abschnitt 6, Tests laut Abschnitt 5), dann G3 (inkl. Hook-Fehlalarm, Entscheidung 10) … G6. Nach dem Merge: alle anderen
Claude-Code-Sitzungen informieren (SendMessage) und `normen.py selbsttest` in den Projekten.

### 2. Nach v6 in den Projekten *(Rückfrage je Projekt)*

`normen.py aktualisieren` + `multi-ki/einrichten.sh` je Projekt (CLAUDE-Abschnitt wird nicht ersetzt: PLAN-Zeile, Fable-Zeile und
Regel 8 von Hand übernehmen; `docs/multi-ki-ablauf.md` kommt als `.vorlage`).

## Offene Fragen an die Inhaberin

- Advisor-Abrechnung: entschieden – Fable läuft; bei „Advisor unavailable“ gilt S07.
- v7: entschieden am 16.11. (Entwurf Abschnitt 8).
