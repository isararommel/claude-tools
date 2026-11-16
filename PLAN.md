# PLAN – zentrale Aufgabenliste

**Jede Sitzung beginnt hier.** Die Inhaberin startet Sitzungen regelmäßig mit `/clear` neu, um Kontingent zu sparen. Deshalb steht
hier alles, was eine frische Sitzung zum Weiterarbeiten braucht: Stand, nächste Aufgaben mit genug Einzelheiten, offene Fragen.
Nach jeder erledigten Aufgabe wird diese Datei aktualisiert (abhaken, nächste Aufgabe ausformulieren) und mitcommittet.

*Stand: 16.11.2026*

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

- ✅ 16.11. Normen v5 (Vibe-Hooks wirksam, N10/N06 korrigiert) – PR #1
- ✅ 15.11. Erste Fassung: Normen v4, Multi-KI-Ablauf, Anleitung für neue Repositories

## Nächste Aufgaben (in dieser Reihenfolge)

### 1. Normen v6 *(freigegeben 16.11.)*

Ziel: S07-SUPERVISOR (Fable als Advisor der Hauptsitzung, fünf Pflicht-Konsultationen), S06-CODE-MODE (Auswerte-Skripte, AST-Prüfung
im Hook), Feld `nur_rollen`, Rollen `fable`/`skript`, Agent-Definitionen „Advisor nie aufrufen“, PLAN-Vorlage (Aufgabe 2).
Branch `normen-v6`. Alle Einzelheiten (wörtliche Texte, Spezifikation für `normen.py`, Tests, Abnahmefälle, Ablauf) in `docs/plaene/normen-v6-plan.md`.
Abnahme: `make test`, `normen.py pruefen --diff`, Hooks live mit den Abnahmefällen, Advisor-Prüfung vor dem Merge.

### 2. PLAN.md als Vorlage *(freigegeben 16.11.)*

`multi-ki/projekt/PLAN.md` (neutral, Abschnitte wie diese Datei), `multi-ki/einrichten.sh` legt sie an, wenn sie fehlt; CLAUDE-Abschnitt:
„Zu Beginn jeder Sitzung `PLAN.md` lesen. Nach jeder erledigten Aufgabe `PLAN.md` aktualisieren und mitcommitten.“; Hinweis in
`normen.py merge`, wenn PLAN.md im PR unverändert ist; Schritt in `NEUES-REPOSITORY.md`. Kann im selben Branch wie v6 laufen.

### 3. Guardrail-Ausbau (Normen v7) *(Entwurf fertig, wartet auf Entscheidungen)*

Entwurf: `docs/plaene/guardrails-v7-entwurf.md` – Lücken L1–L10, Bewertung von 22 externen Repos, Ideen a–h, Pakete G1–G11,
Normtext-Diffs, offene Fragen (Abschnitt 7). Erst die Fragen mit der Inhaberin klären, dann Paketplan festlegen
(Advisor-Konsultation 1 und 5), dann Pakete nacheinander (Hook-Pakete seriell). Nach v6 umsetzen.

## Offene Fragen an die Inhaberin

- Abrechnung des Advisors (Doku: Fable-Advisor wird über Usage Credits abgerechnet).
- v7: Fragen 1–11 in `docs/plaene/guardrails-v7-entwurf.md` Abschnitt 7 (Paketplan, dcg, Sandbox-Spike, MCP-Regel,
  Forschungsdaten-Schlüssel, Config-Selbstschutz, Hook-Fehlalarm, Rückfragen im Auto-Modus).
