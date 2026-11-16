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

- ✅ 16.11. v7 G1–G6 auf Branch `normen-v7` (Einzelheiten: CHANGELOG „v7 – in Arbeit“): Selbsttest, pre-commit nicht umgehen,
  Bash-Schreibziele, Inline-Code und fremde Skripte (Advisor- und Gemini-Review eingearbeitet), Datenschutz vor vibe/agy,
  MCP-Freigaben. G4-A/G4-B/G5 von mistral-team (Large 4), G1–G3/G6 und alle Review-Korrekturen von Opus. Trockenlauf G5 über 71 alte
  Aufträge: 70 ja, 1 agy-Auftrag mit Geheimnis-Pfad gesperrt (gewollt). Selbsttest nach jedem Paket bestanden.

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
Stand: **G1–G6 fertig** (siehe „Erledigt“ und CHANGELOG). **Ein Merge für v7**; bis dahin, in dieser Reihenfolge:
1. **Zweites Review** des Hooks (Diff `normen.py` gegen `origin/main`, Schwerpunkt G4–G6): an mistral-team (code-reviewer), da
   Gemini beim ersten Review nach 4 Befunden mit Timeout abbrach; Auftrag mit kleinerem Ausschnitt je Lauf. Befunde selbst probieren.
2. **G8 Doku** (gemini-analyst): `multi-ki/multi-ki-ablauf.md` und `agenten-normen` – drei Ebenen (Hook → Sandbox geplant →
   pre-commit/merge) mit Restgefahren; neue Projektwerte `[pfade].forschungsdaten` und `[mcp]`; `selbsttest` nach jedem Update;
   offen dokumentieren, dass ein „fragen“ aus einem Hintergrund-Subagenten die Inhaberin evtl. nicht erreicht und dann wie „nein“ wirkt.
3. Advisor-Konsultation 4/5 (Köder-Muster, Live-Selbsttest, Gegenprobe, Trockenlauf G5), CHANGELOG-Datum, PR, `normen.py merge`.
4. Nach dem Merge: alle anderen Claude-Code-Sitzungen informieren (SendMessage) und `normen.py selbsttest` in den Projekten.
Später (eigene Pakete): G7 Sandbox-Spike, G9, G10, G11 laut Entwurf.

### 2. Nach v6 in den Projekten *(Rückfrage je Projekt)*

`normen.py aktualisieren` + `multi-ki/einrichten.sh` je Projekt (CLAUDE-Abschnitt wird nicht ersetzt: PLAN-Zeile, Fable-Zeile und
Regel 8 von Hand übernehmen; `docs/multi-ki-ablauf.md` kommt als `.vorlage`).

## Offene Fragen an die Inhaberin

- Advisor-Abrechnung: entschieden – Fable läuft; bei „Advisor unavailable“ gilt S07.
- v7: entschieden am 16.11. (Entwurf Abschnitt 8).
