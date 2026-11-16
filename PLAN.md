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
Köder-Muster, Live-Ausgabe, Gegenprobe). **G4-A fertig** (Inline-Code: `python3 -c`, `python3 [-|/dev/stdin] <<PY` per AST,
`bash|sh|zsh -c` rekursiv, Präfixe `FOO=1`/`time`/`env`/`nice`/`nohup`/`command`, Heredoc-Rümpfe mit Umleitung ohne Kette sind
Daten; umgesetzt von mistral-team, Ketten-Umgehung `cat <<EOF … | bash` und `python3 <<PY` ohne `-` von Opus nachgezogen).
**G4-B fertig** (Skriptdateien außerhalb des Projekts und außerhalb `lesbar_extern`: `bash|sh|zsh|source|.` und direkte
Pfadaufrufe – Inhalt als ein Befehl rekursiv durch `bewerten`; Python mit/ohne `.py` und Shebang per AST; `node|perl|ruby` und
unbekannte Shebangs → fragen; nicht vorhanden oder im selben Befehl geschrieben → fragen; `cd` im Befehl wird als Basis verfolgt;
Messung an 117 vorhandenen Skripten: Befunde stammen aus dem Inhalt, kaum Parser-Rauschen). Advisor- und Gemini-Review G4
eingearbeitet (pushd/`{ cd }`, Code über stdin, `nice -n`/`time -p`/`timeout`, `getattr`/Aliase, `node -e` fragt; G2-Fehlalarm bei
mehrzeiligen Commit-Nachrichten behoben). Gemini brach nach 4 von 10 Befunden mit Timeout ab – ein zweites Review vor dem Merge.
**G5 fertig** (mistral-team, 29 Schritte; Opus: `$(cat …)`/Variablen auch bei `vibe -p`; Trockenlauf über 71 alte Aufträge: 70 ja,
1 agy-Auftrag mit Geheimnis-Pfad gesperrt – gewollt): Prompt-Prüfung vor vibe/agy – Sperrpfade/Geheimnis-Inhalte nein, Geheimnis-Pfade nur agy nein,
`[pfade].forschungsdaten` (Globs + Textmarker) agy nein / vibe fragen; Messung: 4 von 75 alten Prompts nennen Geheimnis-*Pfade*.
Offen: ob ein „fragen“ aus einem Hintergrund-Subagenten die Inhaberin erreicht (sonst wirkt es wie „nein“ – in G8 dokumentieren).
Nächstes Paket: **G6** (MCP-Freigaben: Matcher `mcp__.*`, `[mcp].fragen`/`nein`, unbekannt → ja, `enableAllProjectMcpServers: false`). Erledigt: G2 (`--no-verify`/`core.hooksPath` sperren, Opus selbst, Normtext aus
Entwurf Abschnitt 6, Tests laut Abschnitt 5), dann G3 (inkl. Hook-Fehlalarm, Entscheidung 10) … G6. Nach dem Merge: alle anderen
Claude-Code-Sitzungen informieren (SendMessage) und `normen.py selbsttest` in den Projekten.

### 2. Nach v6 in den Projekten *(Rückfrage je Projekt)*

`normen.py aktualisieren` + `multi-ki/einrichten.sh` je Projekt (CLAUDE-Abschnitt wird nicht ersetzt: PLAN-Zeile, Fable-Zeile und
Regel 8 von Hand übernehmen; `docs/multi-ki-ablauf.md` kommt als `.vorlage`).

## Offene Fragen an die Inhaberin

- Advisor-Abrechnung: entschieden – Fable läuft; bei „Advisor unavailable“ gilt S07.
- v7: entschieden am 16.11. (Entwurf Abschnitt 8).
