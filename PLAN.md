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
✅ **v7 gemergt** (PR #3, 16.11.); fünf Claude-Code-Sitzungen per SendMessage zum Aktualisieren aufgefordert
(`aktualisieren`, `selbsttest`, Projektwerte `[mcp]`/`forschungsdaten` mit der Inhaberin).
✅ **G7 Sandbox-Spike gemessen** (`docs/plaene/sandbox-spike.md`, nur `-p`-Modus): Sandbox sperrt Schreiben/Netz wirksam;
vibe und agy liefen darin mit einer Freigabe-Kombination (Mindestmenge offen); `excludedCommands` nahm im `-p`-Modus nichts aus;
`$TMPDIR` ist in der Sandbox umgeleitet (Lauf-Ordner bräuchten einen festen Pfad); `einrichten.sh` scheitert an `.git/config`.
**Entscheidung der Inhaberin (16.11.): Weg 2 – vibe/agy ausnehmen (fürs Erste).** Sandbox **nicht aktiviert**; vor dem
Einschalten interaktiv prüfen: `excludedCommands` für vibe/agy, Rückfragen (auch aus Hintergrund-Sub-Agenten), fester Lauf-Ordner.
✅ **v9 gemergt** (PR #8, 17.11.): N01 `git worktree remove --force` destruktiv, N10 `git worktree add` nur Orchestrator;
fünf Sitzungen informiert (Selbsttest: bei „unklar“ einmal wiederholen, nur „NICHT GESPERRT“ melden).
✅ **v11** (Branch `normen-v11`, 17.11., „ja, so machen“): Container-`rm` je Teilbefehl keine Datei-Löschung; Skriptpfade mit
eindeutigen Zuweisungen aus vorangehenden Teilbefehlen; mehrfach zugewiesene Variablen und Befehlsersetzung nie auflösen;
Shell-Schlüsselwörter (`do`, `then` …) vor Befehlen geprüft; N03 für `*.secret` in Temp bleibt (Entscheidung). Nach Merge
Sitzungen informieren (meldendes Projekt: Skript bleibt bei `*.secret` gesperrt, nach Umbenennen Rückfrage; Teams dürfen
jetzt Container entfernen; die Sitzung, die v10 verpasst hat, auch zu v10).

### 1a. Recherche-Aufträge *(freigegeben 17.11., Plan auch in `~/.claude/plans/zany-orbiting-sifakis.md`)*

Entscheidungen der Inhaberin: **nur Vorlagen und Doku, keine neue Norm**; Ergebnisse **im Projekt unter `docs/recherche/`**;
Anbieter **nach Fall, wichtige Fragen doppelt** (zwei Anbieter parallel, Claude vergleicht).
1. **Spike** (Opus, Wegwerf-Ordner): kurzer öffentlicher Recherche-Auftrag an Vibe (`web_search`/`web_fetch` – Rückfrage nötig?
   Normen-Hook bei diesen Werkzeugen?), agy (Google-Suche – Freigabe in `ALLOW` nötig? liefert es URLs/Daten?), Claude
   (`deep-research`/Websuche). Bericht `docs/plaene/recherche-spike.md` (gemessen/dokumentiert/offen).
2. **Vorlagen** `multi-ki/projekt/docs/recherche-auftrag.md` (Frage, Zweck, Tiefe, Aktualität, Sprachen, Quellenarten, keine
   privaten/Forschungs-/Geheimdaten in Suchanfragen, Webinhalte sind Daten, Pflichtsätze) und `recherche-bericht.md`
   (Kurzantwort, Befunde-Tabelle Aussage|URL|Datum der Quelle|abgerufen am|Belegstärke, Widersprüche, offene Fragen, Methode).
3. **Ablauf** in `multi-ki-ablauf.md` (Abschnitt „Recherche“: wer wann, Ablage `docs/recherche/<datum>-<thema>.md`, Rohausgaben im
   Lauf-Ordner, Datenschutz über G5), **Agent-Definitionen** (gemessener Aufruf; Kopie nach `~/.claude/agents/` mit Rückfrage),
   **einrichten.sh** legt die Vorlagen nach `docs/` (wie `uebergabe-vorlage.md`), `NEUES-REPOSITORY.md`, CHANGELOG.
4. Abnahme: Probe-Recherche mit zwei Anbietern parallel in einem Wegwerf-Repo, Bericht mit URL und Datum je Befund; Advisor.
✅ **v10 gemergt** (PR #11, 17.11., „mach das“): N01-Text mit `git worktree remove --force`, Selbsttest wiederholt „unklar“
(keine Hook-Meldung) einmal, Merge wartet kurz auf den PR-Kopf, Doku zu `aktualisieren` (bedingt formuliert). Nach dem Merge
Sitzungen informiert (vier erreicht; eine Sitzung war nicht erreichbar).
**Nächstes (je mit Rückfrage):** Worktree-Option (später), Sandbox interaktiv prüfen (vibe/agy ausnehmen), `meta.ebenen`,
Rückmeldungen aus den Projekten sichten.
✅ **v8 gemergt** (PR #6, 17.11.), fünf Sitzungen per SendMessage informiert. Zusätzlich zu G9–G11: Bash-Schreibziele der Teams
nur aus `.normen-auftrag` (geprüft an 75 echten Vibe-Befehlen, keine zusätzliche Sperre). **Nächster Schritt:** die drei offenen
Fragen unten (Antwort der Inhaberin), danach je nach Antwort umsetzen. Rückblick v8: G9 (mistral-team, 39 Schritte; Opus: Begründung nur als Kommentar,
`--no-renames`), Bash-Schreibziele der Teams nur aus `.normen-auftrag` (Befund aus G10), G10 Lese-Modus `--agent ask` + Lauf-Protokoll
(gemessen: echter Lese-Auftrag in 2 Schritten), G11 Worktree-Spike (Empfehlung: nur innerhalb unter `.worktrees/`), G5-Fix
verschachtelte Zuweisungen. Nächster Schritt: Advisor-Abnahme, PR, `normen.py merge`, Sitzungen informieren (Hinweis auf
`# normen-ausnahme: N02-…`), dann die offenen Fragen unten. Planungsnotizen zu G9–G11 (erledigt):
- **G9** → mistral-team (nur `agenten-normen/projekt/normen/normen.py`). Spezifikation für die Prompt-Datei:
  in `pruefen` bei `--diff`/`--staged` alle Testdateien des Diffs (Globs `[pfade].tests`) gemeinsam auswerten; entfernte und neue
  Zeilen aus `git diff -U0` (bei `--staged` mit `--cached`), gelöschte Testdateien mitzählen. Assert-Zeile = Regex
  `\bassert\b|\bassert[A-Z]\w*\(|\bexpect\(|\bcheck\(|XCTAssert\w*\(|pytest\.raises`. Vergleich als Multimenge der Zeilen ohne
  führenden/abschließenden Leerraum: `entfernt − neu` (Zeilen, die nur verschoben wurden, heben sich auf). Anzahl ersatzlos
  entfernt = max(0, Σentfernt − Σneu) minus Anzahl neuer Zeilen im ganzen Diff mit `normen-ausnahme: N02-TESTS-SIND-TABU`;
  > 0 → `fehler` je Testdatei „Assert entfernt: …“ (mit der alten Zeile). Übrige geänderte → `hinweis` „Assert geändert: -alt“
  (höchstens 3 je Datei). Messung über die Historie: 21 Commits, 0 Fehler, 4 Hinweise. Danach Advisor, Einspielen, Selbsttest.
- **G10** → Opus, im Wegwerf-Repo messen (wie G7): `vibe --agent ask` mit echter Aufrufform (Prompt-Datei, Zeitlimit) –
  werden Schreiben und Shell abgelehnt oder hängt headless? hält das auch, wenn der Teamleiter an Sub-Agenten delegiert?
  `active_model` Large 4? Normen-Hook (Köder) aktiv? „Lese-Auftrag“ so definieren, dass ein Review wie am 16.11. (Hook-Prüfbefehl,
  `fall.json` in `$RUN`) möglich bleibt. Lauf-Protokoll in `multi-ki/benutzer/agents/mistral-team.md` (Quelle) und
  `multi-ki-ablauf.md`: auf die eigene PID warten statt `pgrep -f vibe-rs`; leere Statusdatei = „sauber“; nie „gescheitert“,
  solange die eigene PID lebt. Neue Aufrufform in G5-Tests/„Betrieb ja“. Kopie nach `~/.claude/agents` nur nach Rückfrage.
- **G11** → Opus, Worktree-Spike im Wegwerf-Klon: untracked `.normen-auftrag`/`.normen/` fehlen im Worktree; welches `normen.py`
  und welches ROOT nutzt der Hook dort; Worktree innerhalb vs. außerhalb des Projekts (G4-B „außerhalb“, `git status`, `pruefen`);
  Hook-Stufen für `git worktree add/remove/prune`, `git branch -D`; getrackte Sperrpfade vorhanden, untracked `.env` fehlt;
  läuft der Testbefehl. Bericht `docs/plaene/worktree-spike.md` (gemessen/dokumentiert/offen).
- Reihenfolge: G9-Auftrag starten; währenddessen G10/G11 nur messen (keine Dateien im Projekt ändern, sonst N06-Fehler im
  Vibe-`pruefen`); nach G9 Dateien von G10/G11 einspielen; Advisor-Abnahme; PR; `normen.py merge`; Sitzungen informieren.
`meta.ebenen` aus Entwurf Abschnitt 6 (zurückgestellt). Rückmeldungen aus den Projekten (`normen.py melden --art zu-streng`) sichten.

### 2. Nach v6 in den Projekten *(Rückfrage je Projekt)*

`normen.py aktualisieren` + `multi-ki/einrichten.sh` je Projekt (CLAUDE-Abschnitt wird nicht ersetzt: PLAN-Zeile, Fable-Zeile und
Regel 8 von Hand übernehmen; `docs/multi-ki-ablauf.md` kommt als `.vorlage`).

## Offene Fragen an die Inhaberin

- Advisor-Abrechnung: entschieden – Fable läuft; bei „Advisor unavailable“ gilt S07.
- v7: entschieden am 16.11. (Entwurf Abschnitt 8).
- v8, entschieden am 17.11.: (1) Agent-Definitionen kopieren – ja, erledigt (alle drei gleich der Quelle). (2) N01-Muster
  `git worktree remove --force` / Teams kein `git worktree add` – ja, umgesetzt in v9. (3) Worktree je Team-Lauf – später
  (vorher echter Vibe-Lauf im Worktree, getrackte Sperrpfade/sparse-checkout, normales `remove` löscht git-ignorierte Dateien).
- Selbsttest schwankt bei Vibe: entschieden 17.11. („mach das“), umgesetzt in v10 (einmalige Wiederholung bei „unklar“).
