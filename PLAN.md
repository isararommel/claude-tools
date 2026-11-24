# PLAN – zentrale Aufgabenliste

**Jede Sitzung beginnt hier.** Die Inhaberin startet Sitzungen regelmäßig mit `/clear` neu, um Kontingent zu sparen. Deshalb steht
hier alles, was eine frische Sitzung zum Weiterarbeiten braucht: Stand, nächste Aufgaben mit genug Einzelheiten, offene Fragen.
Nach jeder erledigten Aufgabe wird diese Datei aktualisiert (abhaken, nächste Aufgabe ausformulieren) und mitcommittet.

*Stand: 24.11.2026 (v18 auf main nach Merge von Paket **P** (Normen-Protokoll, Forschungsdaten in Mistral-Reviews,
`lesbar_extern` je Teilbefehl, `einrichten-hier.sh`); erste Protokoll-Auswertung erledigt (Fehlalarm-Kandidaten K1–K3 unter
P); **KT** erledigt (Coding-Team: Umsetzung GLM-5.3, Reviews Large 4); nächstes Paket: **S06-ERS** (Lücke `$(…)` in S06,
Normen v19, Freigabe der Inhaberin nötig), dann **VL**
(eine Quelle `vorlage/`), dann **DT** (Design-Team, Fragen an die Inhaberin offen); danach D2 nach Entscheidung der Inhaberin, sonst E; Kandidat für die nächste Normen-Version: `_cd_basis` folgt
wirkungslosem `cd` (Befund unter V15b-2) und G9/Sitzungsprobe-Befunde (a)/(b) aus dem Beweislauf unter R; offen: A2 Punkte 4–6, G, H)*

## Verweise

| Datei | Wofür |
|---|---|
| [KONZEPT.md](KONZEPT.md) | Ziel und Aufbau von claude-tools |
| [CHANGELOG.md](CHANGELOG.md) | Normen-Versionen (aktuell v18; Einzelheiten aller früheren Pakete stehen dort) |
| [agenten-normen/](agenten-normen/LIES-MICH.md) | Quelle der Normen, Hooks, normen.py |
| [multi-ki/multi-ki-ablauf.md](multi-ki/multi-ki-ablauf.md) | Ablauf mit mistral-team / gemini-analyst |
| [NEUES-REPOSITORY.md](NEUES-REPOSITORY.md) | Neues Projekt einrichten |
| [docs/plaene/](docs/plaene/) | Entwürfe und Spikes (v6-Plan, v7-Entwurf, Sandbox-, Worktree-, Recherche-Spike) |

## Arbeitsweise (kurz)

- **Pakete so schneiden, dass danach `/clear` möglich ist (S08, seit v13):** Befunde sofort hier festhalten, am Paketende
  committen und „/clear möglich“ melden. Ausnahme: stark zusammenhängende Pakete – dann zusammen erledigen, Grund nennen.
- Öffentliches Repository: keine Namen, Server, privaten Projekte oder Pfade; Inhaberin nur als `{inhaberin}`.
- Eigener Branch je Aufgabe, PR, Merge über `python3 normen/normen.py merge <PR>`; Testbefehl `make test`.
- Normen nur in der Quelle (`agenten-normen/`, `multi-ki/`) ändern, `meta.version` erhöhen, CHANGELOG ergänzen, dann
  `bash einrichten.sh . --test "make test"` (spielt die Kopie ein). `tests/test_v4.py` prüft die Versionsnummer (mit anheben).
- Projekte holen Änderungen mit `python3 normen/normen.py aktualisieren`; der Multi-KI-Teil braucht `multi-ki/einrichten.sh` oder
  Handarbeit (CLAUDE-Abschnitt wird nicht ersetzt: PLAN-, Fable-Zeile und Regel 8 von Hand; `docs/multi-ki-ablauf.md` kommt als `.vorlage`).
- Bekannte Grenzen: `disallowedTools: advisor` wirkt nicht (Probe 16.11., Sperre nur per Anweisung); `~/.vibe/config.toml`
  braucht vollständige Modelleinträge (Server-Liste lieferte nur GLM-5.3 Flash); N03 sperrt `*.secret` auch in Temp (entschieden).
- Rückmeldungen der Projekte: offene Issues im privaten Rückmelde-Repository (`[rueckmeldung].repo` der Projekte) und lokale
  Kopien unter `<projekt>/.normen/rueckmeldungen/`. Kommentieren/Schließen nur nach Rückfrage.
- Nach jedem Normen-Release die anderen Claude-Code-Sitzungen per `ListAgents`/`SendMessage` informieren.
- Bekannter Hook-Fehlalarm: Liegt der Arbeitsordner einer *anderen* Projektsitzung hier, sperrt deren Hook Befehle mit `>`.
- **`normen.py aktualisieren` liest den Arbeitsbaum dieses Ordners** (`[quelle].pfad`), also den gerade ausgecheckten Branch,
  nicht `main`. Projekte nur aktualisieren lassen, wenn hier `main` (oder ein gemergter Stand) ausgecheckt ist.

## Erledigt (letzte Schritte)

- ✅ 23.11. **Paket R2 / Normen v17** (Branch `paket-r2-review-tor`): Review-Tor in `normen.py merge` (großer Meilenstein →
  Bericht mit `Mergereif: ja`; sonst Halt ab 150 Code-Zeilen/kritisch, weiter mit `--klein "<Grund>"`), `normen.py review`
  (Ordner, gefilterter Diff, Pflichtblock), N11-Zusatz; neuer Befund mit behoben: Teams durften jeden `normen.py`-Unterbefehl
  aufrufen (`auftrag --dateien` erweiterte die eigenen Rechte). Selbst-Review mit beiden Teams + Advisor: 21 Befunde, 15
  bestätigt und behoben (`docs/reviews/2026-11-23-paket-r2-review-tor.md`). Einzelheiten und Messungen: Abschnitt R2 unten.

- ✅ 22.11. **Paket R** (Branch `paket-r-review`): eigenes Review-Verfahren als Vorlagen + Ablauf (kein neuer Normtext),
  Beweislauf mit beiden Teams bestanden (Mistral mit `--add-dir`, agy mit Material im eigenen Lauf-Ordner); drei Fehlversuche
  dokumentiert. Einzelheiten und offene Fragen: Abschnitt R unten. Vorlagen selbst geschrieben (Schnittstelle zu den Teams).

- ✅ 22.11. **V15b-2** (V15b Punkte 5–9, Branch `paket-v15-hooks`, Tests `tests/test_v15b2.py`, vorher rot): G9-Beleg nur aus
  Importzeilen, ohne Daten/Doku/Ausgeschlossenes (Nr. 9); `.normen/sitzungsprobe.txt` in GESCHUETZT, `--sitzung` mit
  `--werkzeug`/`--weg` → Exit 64 (Nr. 10); `lesbar_extern` in Platten-Schreibweise (Nr. 12); Forschungsdaten im Prompt ohne
  Groß-/Kleinschreibung, `_prompt_wort` mit `_echt` (Nr. 20); `cd "$D"` mit sicher bekannter Zuweisung (Notiz a, einzige
  Lockerung, gegen die Shell gemessen); CHANGELOG (`melden --stufe` → Geändert, Grenzen Nr. 10, 13–15, G9 mehrzeilig);
  Markierungen v15 (#61/#66/#71/#74/#75) → v16; Bericht `docs/reviews/…` mit Stand je Befund. Selbst umgesetzt: kleine
  Korrekturen in sicherheitskritischer Hook-Logik, je wenige Zeilen. Advisor vor „fertig“: Lücke in (a) (Wert über zweite
  Variable, `unset`/`eval`/`printf -v`/Heredoc) gefunden, nachgestellt und geschlossen.
  **Befund für ein späteres Paket (gemessen 22.11., älter als v16):** `_cd_basis` folgt jedem `cd`, auch wenn es nicht
  wirkt (`cd <s>; false && cd <p>; python3 -c 'import json'`, `cd <p> | true`, `cd /gibt/es/nicht`) → ja, obwohl die Shell
  in `<s>` bleibt (Schatten unerkannt). Vorschlag: nach `cd` hinter `&&`/`||`/`|`/`&` oder auf einen nicht vorhandenen Ordner
  Basis = unbekannt. Im CHANGELOG v16 als Grenze.
  ✅ Advisor vor „fertig“, PR-Text neu, **PR #30 per `normen.py merge 30` gemergt (22.11., v16 auf main)**, fünf laufende
  Sitzungen per SendMessage zum Aktualisieren aufgefordert.
  ✅ 23.11. Rückmelde-Issues abgeglichen: #75, #66, #71 geschlossen (#71: Befehlsform `.venv/bin/python -c 'import <projektmodul>'`
  am Vibe-Hook für mistral-team nachgestellt → ja, mit `os.remove` → nein); #74 kommentiert, offen (wörtliche Sperrmeldung
  fehlt, Ordnername hat dieselbe Schreibweise); #61 kommentiert, offen (Stop-Hook, Befund (a) unter R).

- ✅ 22.11. **V15b-1** (V15b Punkte 1–4 und 10, Branch `paket-v15-hooks`): gemeinsamer Modul-Auflöser
  `_py_modul_aufloesen` (Suchreihenfolge gegen den Interpreter getestet) für `-m`, `-c`-Importe und `python3 <datei>.py`
  (Schatten im Skriptordner); geschriebene Modul-Kandidaten → fragen; `.so`/`.pyc`/zip außerhalb → fragen; Code-Starter →
  fragen; `$PWD` aus dem Basisordner (Skriptprüfung, `_cd_basis`, `_schreibziele`); `-c` mit Import bei unbekanntem
  Suchpfad → fragen; vertraute Werkzeuge für Teams → nein (auch über den Vibe-Hook getestet), `-m`/Import des Werkzeugs →
  nein für alle; `_echt` beim Werkzeug-Vergleich (`./WP.py`). S06-Normtext ergänzt (Wortlaut im CHANGELOG v16; Advisor
  geprüft, **Bestätigung der Inhaberin für den Zusatz zu `-m`/Import steht aus – vor `normen.py merge 30` nötig**).
  Neue Testdatei `tests/test_v15b.py` (95 Prüfungen, vorher 56 rot), `make test` grün (8 Dateien), `pruefen --diff` 0 Fehler.
  Befunde: transitive Schatten (`_json.py`, `_datetime.py` im Skriptordner) wirken und sind nicht geprüft → Grenze im
  CHANGELOG (Option: Dateinamen aus `sys.stdlib_module_names` in fremden Suchordnern → fragen); `python3 -c` in einer
  Subshell `( … )` → nein (Fehlalarm, Grenze). Zählung von `tests/test_v4.py` schwankt mit der Zahl untracked Dateien
  (Dateien × private Begriffe, `tests/test_v4.py:206`), harmlos. Nachtrag (Advisor): geschriebenes Schatten-Modul auch beim
  Skriptweg `python3 <datei>.py` → fragen (Test vorher rot).
  **Notizen für V15b-2:** (a) `_cd_basis` kennt Zuweisungen aus demselben Befehl nicht (`_schreibziele` jetzt schon):
  `D=…; cd "$D"` gilt als unbekannt → `-m`/`-c` mit Import „fragen“ (vibe: nein); der Test `D=<schatten>; cd "$D"` besteht
  deshalb, nicht über die Schatten-Erkennung. Prüfen, ob `_cd_basis` die Zuweisungen bekommen soll (dann Test mit
  bekanntem Basisordner ergänzen). (b) Text von PR #30 nennt noch v15, 6 Testdateien, 82 Prüfungen → vor dem Merge
  neu schreiben. (c) Kommentare/Docstrings „v15 (#71)“, „v15 (#87)“ in `normen.py` an v16 angleichen (#87 war v15 – nur
  die #71-Stellen). (d) **Entschieden 22.11. (Inhaberin):** S06-Zusatz („auch nicht per `python3 -m` oder Import“,
  Teamsatz) bestätigt. Transitive Schatten bleiben Grenze – keine Sperre über `sys.stdlib_module_names`, weil harmlose
  Dateien (`random.py`, `test.py`) sonst ständig Rückfragen auslösen („keine ständigen Rückfragen bei
  Belanglosigkeiten“). Daraus für V15b-2: Fehlalarme senken, wo es sicher geht – (a) bevorzugt umsetzen
  (`D=…; cd "$D"` mit bekannter Zuweisung soll nicht mehr fragen).

- ✅ 22.11. **main in `paket-v15-hooks` zusammengeführt, dort v16** (Merge statt Rebase, kein Force-Push für PR #30):
  CHANGELOG-Abschnitt des Branches heißt jetzt v16 (über v15 „vertraute Werkzeuge“), `normen.toml` 16, `tests/test_v4.py`
  16, Makefile führt `test_hook_luecken.py` und `test_werkzeuge.py` aus; Kopie mit `einrichten.sh . --test "make test"`
  eingespielt, `normen.py` Quelle = Kopie. `make test` grün (7 Testdateien, Exit 0), `pruefen --diff` 0 Fehler.
  `normen.py` wurde von git ohne Konflikt zusammengeführt; Wechselwirkung gemessen → Befund in V15b Punkt 1.
  PR #30 bleibt **nicht mergereif** (Review-Bericht), Merge erst nach V15b.

- ✅ 21.11. **Hotfix v15 vertraute Werkzeuge** (Rückmeldung „S06 sperrt freigegebenes Werkzeug“ im Rückmelde-Repository, Branch
  `paket-v15-werkzeuge`): `[werkzeuge].vertraut` in `projekt.toml` (Pfad + freigegebene Unterbefehle, nur Rolle claude, sonst
  nein); Befehlswort über Variable (`$B …`) wird aufgelöst, sonst fragen. Freigabe der Inhaberin 21.11. direkt (Stufe „ja“ für
  die freigegebenen Unterbefehle, Hotfix von main statt im offenen Hooks-Paket). Tests `tests/test_werkzeuge.py` (vorher 11 rot).
  **Folge für `paket-v15-hooks` (PR #30):** auf main umsetzen, Version 15 → 16 (normen.toml, `tests/test_v4.py`,
  CHANGELOG-Überschrift), Konflikte in `_skript_im_befehl` beachten (beide Pakete ändern den Anfang), dann V15b.

- ✅ 20.11. **Paket D Sandbox interaktiv** (Bericht: `docs/plaene/sandbox-spike.md`, „Nachtrag Paket D“): pty-gesteuerte
  Haiku-Sitzung mit Sandbox nur per `--settings`. `excludedCommands` greift interaktiv, nur mit `"vibe *"` (nicht `"vibe"`) und nur
  für den **bloßen Befehl** (keine Zuweisung, Pipe, Umleitung, `< /dev/null`; `cd` auf den eigenen Arbeitsordner wird entfernt).
  Laut Programmtext (nicht gemessen) zählt es bei `allowUnsandboxedCommands:false` nur aus Benutzer-/verwalteter/`--settings`-Ebene.
  Rückfragen aus Hintergrund-Sub-Agenten kommen an; im Auto-Modus je ein Lauf ohne Rückfrage (vibe lief, Netz gesperrt).
  `/tmp/claude-<uid>/` ist in und außerhalb der Sandbox derselbe beschreibbare Ordner. Einstellungen unverändert (Prüfsumme).
- ✅ 18.11. **v14 = Pakete B + C** (PR #25, gemergt; 5 Sitzungen informiert): Datei-Köder im Hook, Selbsttest je Weg (claude bash/write,
  vibe bash/write_file/edit, `--weg`), Beleg-Log `.normen/selbsttest-*.log`, `auftrag --dateien` trennt nicht mehr,
  mistral-team Umsetzungsläufe 1200 s im Hintergrund. Befunde: `Edit(./pfad)` greift in `claude -p` nicht, `Edit(//abs)`
  schon (Gegenprobe ohne Hook); ohne Hook schreiben vibe `write_file`/`edit` mit `--smart-approve` wirklich (Gegenprobe);
  Live-Selbsttest 5/5 Wege gesperrt; erster Vibe-Lauf in 5 frischen Ordnern 5/5 gesperrt (Ausreißer nicht nachstellbar, nicht gelöst – künftig Beleg-Log). vibe/edit mit 3 Runden 1 von 3 „unklar“ → 5 Runden, danach 3/3.
  Gegenprobe über `normen.py selbsttest` im Wegwerf-Repo sperrt der S06-Hook (fremdes Skript) → direkt mit claude/vibe.
  mistral-team-Lauf endete am Zeitlimit (code-worker noch aktiv), Code war fertig; zwei Korrekturen von Claude.
  Kopie `mistral-team.md` nach `~/.claude/agents/` erledigt 18.11. (Freigabe; `gemini-analyst.md` war schon gleich).

- ✅ 18.11. **Paket A agy-Freigaben** (PR #19): `*` in agy-Regeln greift nicht (1.5.11) → ALLOW in
  Präfixform; `-p` ohne `--mode` lief im Auto-Modus → `"agentMode":""`; `read_file` braucht aufgelösten Pfad → `realpath`.
  Abnahme 3/3 Umsetzung + Nur-Lesen ok. Einzelheiten: `docs/plaene/agy-freigaben-spike.md`, CHANGELOG.
- ✅ 18.11. **v13** gemergt (PR #16): S08-CLEAR-FAEHIG + Zeile in der PLAN-Vorlage; `make test` grün,
  `pruefen --diff` 0 Fehler. Rückmeldungen gesichtet (siehe Pakete A–C), vier Projektsitzungen nach Stand v12 gefragt (Paket G).
- ✅ 17.11. v12 (PR #14): Vibe-Hooks für `edit`/`grep`, Recherche-Vorlagen. v11 (PR #13), v10 (PR #11), v9 (PR #8), v8 (PR #6),
  v7 (PR #3), G7 Sandbox-Spike (Weg 2: vibe/agy ausnehmen, Sandbox nicht aktiv). Einzelheiten: CHANGELOG.

## Nächste Aufgaben (in dieser Reihenfolge, je ein Paket = eine Sitzung)

### V15. Hooks: Schreibweise, `python -m`, Sitzungsprobe, G9, Labels *(läuft, Branch `paket-v15-hooks`)*

Rückmelde-Issues (privates Rückmelde-Repository) #74, #71, #66, #61, #75. Plan vom Advisor geprüft 20.11.
Befunde (Nachstellung im Wegwerf-Repo, 20.11.):
- **#74 ist eine Lücke, nicht nur ein Fehlalarm:** `_rel`/`relative_to(ROOT)` vergleichen nach `realpath` mit Groß-/Kleinschreibung,
  macOS-Dateisystem nicht. Gesperrt wird nur ein absoluter Pfad mit anderer Schreibweise des **Projektordners** (Fehlalarm). Mit
  anderer Schreibweise **im Projekt** gehen durch: `.Claude/settings.json` (Rolle claude, sonst „fragen“), `NORMEN/normen.toml`,
  `.ENV` (N03), `Daten/Geheim/…` (Sperrpfad, mistral-team read_file). Lösung: Pfad auf die Schreibweise auf der Platte bringen
  (vorhandene Teile per Verzeichnisliste), Geheimnis-Muster ohne Groß-/Kleinschreibung; Negativtests für alle vier Fälle.
  Issue erst schließen, wenn die Sperrmeldung aus dem Projektlauf zur Ursache passt (dort nachfragen).
- **#71:** bestätigt: `python -c 'import projektmodul'` sperrt „Import … nicht in der Positivliste“ (vibe → nein);
  `cd <lauf> && PYTHONPATH=<projekt> python3 -m pruef` (Skript mit `os.remove`) geht ungeprüft durch. Plan: `-m MOD` nach
  Python-Reihenfolge (Basisordner, dann PYTHONPATH; `mod.py`, `pkg/__init__.py`, `pkg/__main__.py`) auflösen, außerhalb des
  Projekts per AST prüfen, nicht gefunden = wie bisher (`-m pytest|venv|pip`); Import, der auf eine Projektdatei auflöst, erlaubt
  (wie `python3 projektdatei.py`). Pflichtsatz „Hook-Sperre nicht umgehen, anhalten und melden“.
- **#66:** Sitzungsprobe nur mit positivem Beleg (Hook schreibt beim Köder einen frischen Marker; `selbsttest --sitzung` verlangt
  ihn) – „Köderdatei fehlt“ beweist nichts (im Elternordner scheitert `touch` schon am fehlenden Ordner). einrichten.sh: nur Hinweis.
- **#61:** ganz gelöschte Testdatei → Hinweis statt Fehler, wenn der Diff eine Nicht-Testdatei löscht, deren Stamm als ganzes Wort
  in der Testdatei vorkommt; Hinweis nennt beide Dateien; `--diff`, `--staged`, `--diff origin/main` testen. Stop-Hook-Wiederholung:
  zurückgestellt (#61 danach nur kommentieren, nicht schließen).
- **#75:** vorher prüfen, was `gh issue create --label` bei fehlendem Label tut (kein stiller Zweitversuch, N08).
Stand 20.11. abends: v15 umgesetzt, eingespielt (`einrichten.sh . --test "make test"`), `make test` grün (6 Testdateien, neu
`tests/test_hook_luecken.py` mit 68 Prüfungen), `pruefen --diff` 0 Fehler. **Sitzungsprobe live bestanden** (Köder in dieser
Sitzung gesperrt, `selbsttest --sitzung` → bestanden; session_id der Hook-Eingabe = `CLAUDE_CODE_SESSION_ID`).
mistral-team-Lauf für die Tests endete nach 1200 s am Zeitlimit (`outcome: deadline`, 36 Schritte, mistral-large-4-0-3) ohne
Datei, nur Lesen → Tests von Claude geschrieben; Beleg für Rückmeldung #52 (Kommentar dort nach Rückfrage).
Advisor vor „fertig“ geprüft: Befund Sperrpfad/Auftrag in Konfig-Schreibweise (Rückschritt durch `_echt`) behoben, `__init__`
kein G9-Beleg, Doku, Grenzen im CHANGELOG; jetzt 82 Prüfungen grün. **PR #30** offen.
**Freigaben der Inhaberin 20.11.:** Lockerungen G9 (#61) und S06-Projektimporte (#71) ja, Pflichtsatz ja, Labels ja →
`stufe:hoch|mittel|niedrig` angelegt, #72 → `stufe:hoch`, #61 → `stufe:mittel`.
`/code-review ultra` verworfen (20.11.): ganze Codebasis zu groß (Limit), Kern-PR von der Inhaberin abgebrochen; Hilfs-PRs
#31/#32 geschlossen, Hilfs-Branches gelöscht. Stattdessen eigenes Review-Verfahren (Paket R).
✅ 20.11. **Pilot von Paket R** gelaufen: Bericht `docs/reviews/2026-11-20-paket-v15-hooks.md` (19 Befunde, Status je Befund,
Verfahrensbefunde). Ergebnis: **nicht mergereif** – Nr. 1–8 bestätigte Lücken/Regression im `-m`-Code → Paket V15b.
Offen: V15b umsetzen, Advisor vor „fertig“, dann `normen.py merge 30`; nach dem Merge
Issues kommentieren/schließen (#74 und #71 erst nach Abgleich mit Sperrmeldung bzw. Befehl aus dem Projektlauf; #61 offen
lassen wegen Stop-Hook), Sitzungen informieren.

### V15b. Review-Befunde zu v15 einarbeiten *(nächstes Paket, Branch `paket-v15-hooks`)*

Grundlage: `docs/reviews/2026-11-20-paket-v15-hooks.md` (Nummern dort). Advisor hat den Korrekturplan geprüft (20.11.); seine
Auflagen sind hier eingearbeitet. Jede Korrektur in der Quelle mit neuem Test, der vorher rot ist; dann
`bash einrichten.sh . --test "make test"`, `make test`, `pruefen --diff`. CHANGELOG-Abschnitt bleibt v16 (seit 22.11.; vorher „v15“ auf dem Branch).
Kernlogik → vor dem Bau kurz Advisor (S07 Punkt 2). Das Nachstell-Skript aus dem Pilot liegt nicht im Repo; die Fälle stehen im Bericht.
Rohausgaben der Teams (Zeilennummern, Vorschläge), solange vorhanden: `${TMPDIR}/review-runs/20261120-1741-paket-v15-hooks/`.
1. **Gemeinsamer Modul-Auflöser** für `-m` und `-c`-Importe (Nr. 1, 4, 5, 6): Reihenfolge wie Python (`FileFinder`: Paket
   `mod/__init__.py` vor `mod.py`, Namespace-Ordner zuletzt); bei `a.b` alle `__init__.py` auf dem Weg prüfen; Schatten eines
   Positivlisten-Imports im Basisordner/PYTHONPATH außerhalb des Projekts → per AST prüfen. „Fragen“, wenn ein **Kandidat des
   Moduls** (nicht irgendein Schreibziel!) im selben Befehl geschrieben wird oder unzerlegbar ist und außerhalb von Projekt/
   `lesbar_extern` liegt; andere Importformen (`importlib.machinery.all_suffixes()` außer `.py`, zip/pyz im PYTHONPATH) → fragen.
   Ein unzerlegbares Schreibziel → fragen nur, wenn ein Suchordner außerhalb von Projekt und `lesbar_extern` liegt.
   Positivtests vorab: `python3 -m pytest -q > "$LOG"` → ja; `> out.txt` und `| tee out.txt` im Projekt nur mit
   `.normen-auftrag`, das `out.txt` nennt (ohne Auftrag sperrt N06 wie bisher).
   **Zusätzlich (Befund 22.11. nach dem Zusammenführen mit dem Hotfix, gemessen im Wegwerf-Repo):** Der Auflöser muss
   `[werkzeuge].vertraut` kennen. Heute löst `_python_m` das Modul auf, fragt aber nicht `_vertraut(cfg)` ab (anders als
   `_skript_datei_arg`). Ergebnis bei Werkzeug `wz.py` mit Unterbefehl-Liste `["status"]`:
   `cd <ext> && python3 -m wz schluessel` und `PYTHONPATH=<ext> python3 -m wz schluessel` → **ja** (Werkzeug unter
   `lesbar_extern`, Rollen claude und mistral-team); Werkzeug im Projekt: `python3 -m wp schluessel` und
   `python3 -c 'import wp'` → **ja** (beide Rollen). Außerhalb ohne `lesbar_extern` sperrt die AST-Prüfung (nein).
   `python3 wp.py …` sperrt der Hotfix für alle Rollen (nein). Soll: Auflösung auf ein vertrautes Werkzeug → nein
   („nur direkt aufrufen“), für `-m` und `-c`-Import; Tests in `tests/test_werkzeuge.py`. Gegenmessung auf main (v15),
   22.11.: `-m` geht dort in allen Fällen durch (auch Werkzeug außerhalb ohne `lesbar_extern` = Lücke #71, die v16 schließt);
   `-c 'import wp'` im Projekt ist auf main „fragen“, auf dem Branch „ja“ (neu durch die Lockerung #71). Probe-Skript lag nur
   im Scratchpad; die Fälle stehen hier.
2. Nr. 2: `_skript_geschrieben` mit `_echt(z)`; Test unter derselben Bedingung (Dateisystem ohne Groß-/Kleinschreibung) wie #74.
3. Nr. 3 Regression: `$PWD`/`${PWD}`/`$HOME`/`~` in PYTHONPATH nur auflösen, wenn die Zuweisung Präfix des Python-Aufrufs ist
   oder kein `cd` dazwischen liegt (Negativtest `cd lauf; export PYTHONPATH=$PWD/sub; cd projekt && python3 -m x`). Unbekannter
   Basisordner (`cd "$(mktemp -d)"`) bleibt fragen → Grenze im CHANGELOG.
4. Nr. 7/8: kleine Liste Code-Starter (`timeit`, `cProfile`, `profile`, `trace`, `pdb`, `runpy`) → fragen; `unittest`/`pytest`
   mit Ziel außerhalb des Projekts: im CHANGELOG als **Grenze** (Verbotsliste nie vollständig), nicht „geschlossen“.
5. Nr. 9 G9: Beleg nur, wenn der Stamm in einer Importzeile der gelöschten Testdatei steht (`import`/`from`/`@testable import`/
   `require(`/`#include`); gelöschte Datei nicht unter `ausschliessen`, keine Daten-/Doku-Endung (.json .toml .yaml .yml .txt
   .md .csv). Negativtests: `utils` nur im Kommentar, `data.json` mit `data` im Test. Grenze: mehrzeilige Importe → Fehler (sichere Richtung).
6. Nr. 10: `.normen/sitzungsprobe.txt` in GESCHUETZT; `selbsttest --sitzung` mit `--werkzeug`/`--weg` → Fehler; CHANGELOG-Grenze
   „Beleg gegen Versehen, nicht gegen Täuschung“.
7. Nr. 11: CHANGELOG `melden --stufe` nach „Geändert“. Nr. 12 und Nr. 20 (Forschungsdaten-Teil: offene Richtung) nachstellen,
   bei Bestätigung casefold bzw. `_echt`.
8. Nr. 13–15, 19 als Grenzen bzw. plausibel im CHANGELOG/Bericht; Nr. 16, 18 zurückgestellt; Nr. 17 verworfen.
9. Danach: Bericht-Status aktualisieren (behoben/Grenze), Advisor vor „fertig“, Kurzverweis im PR #30, `normen.py merge 30`.
   (Punkt 10 vorher erledigen.)
**Schnitt (22.11.):** V15b-1 = Punkte 1–4 und 10 (Python-Auflösung im S06-Hook, eigene Testdatei `tests/test_v15b.py`);
V15b-2 = Punkte 5–9 (G9, Sitzungsprobe, CHANGELOG, Nr. 12/20, Bericht, Merge). Auflagen des Advisors zu V15b-1 (22.11.):
Schatten-Prüfung auch für per AST geprüfte `-m`-Dateien (nur Schatten, keine Projekt-Import-Lockerung); `$PWD` überall aus
dem Basisordner (auch `_cd_basis`, `_schreibziele`); Kandidaten nur importierbare Endungen + Ordner `d/<kopf>/`
(`> pytest.log` bleibt ja); Punkt 10 mit `is not None` und `_echt`; „nicht gefunden“ je Fall getrennt (`-m` installiert = ja,
Positivliste = ja, sonst fragen; reiner Namespace nie „im Projekt“; `from ns import x` löst `ns.x` mit auf); Suchreihenfolge
gegen den echten Interpreter testen. Bewusste Abweichung: Schatten-Modul außerhalb → fragen (statt AST-Prüfung).
10. **Vertraute Werkzeuge für Teams ganz sperren** (Entscheidung der Inhaberin 22.11.: Variante b, gilt gleich für mistral-team,
   gemini-analyst und lokal; Begründung: die Freigabe galt Claude). Jeder Aufruf, der auf einen Eintrag aus
   `[werkzeuge].vertraut` auflöst, ergibt für Nicht-claude-Rollen „nein“, egal wo das Werkzeug liegt (im Projekt, unter
   `lesbar_extern`, außerhalb) und auf welchem Weg (direkt, über Variable, `python3|bash <werkzeug>`, `python3 -m`,
   `-c`-Import; mit Punkt 1). Prüfung vor `_skript_gate`, nicht nur bei `rolle == "claude"`. Tests in
   `tests/test_werkzeuge.py`, vorher rot: die Fälle aus der Messung 22.11. (Abschnitt „Entschieden 22.11.“ unten) für
   mistral-team; claude unverändert. CHANGELOG v16 „Sicherheit“, S06-Normtext-Satz zu `[werkzeuge].vertraut` um „nur Rolle
   claude, Teams nie“ ergänzen (Normänderung: Advisor S07 Punkt 5; Freigabe der Inhaberin liegt mit dieser Entscheidung vor).
Danach Paket R mit den Verfahrensbefunden aus dem Bericht (Zweischritt bei Mistral, `--resume <id>`, absolute Pfade/Auszüge für agy).

### R. Eigenes Code-Review-Verfahren *(✅ erledigt 22.11., Branch `paket-r-review`; Messprotokoll für spätere Pakete)*

Advisor-Zuschnitt: nur Vorlagen + Ablauf, kein `normen.py review`, kein Merge-Tor (Frage an die Inhaberin, siehe unten).
Umgesetzt: Vorlagen `multi-ki/projekt/docs/review-{auftrag,bericht}.md`, Abschnitt „Review“ in `multi-ki/multi-ki-ablauf.md`
(+ Abschnitt 7: `--resume`, `--add-dir`), `mistral-team.md`, `gemini-analyst.md`, `einrichten.sh`, `NEUES-REPOSITORY.md`,
CHANGELOG „Review-Aufträge (Multi-KI, kein neuer Normtext)“. Ungeprüft: zweiter Schritt (`--resume` + `bericht.md`) in dieser
Kombination; agy mit Dateien aus dem ausgecheckten Projekt; Gruppen über ≈ 140 Diff-Zeilen. **Beweislauf** (Thema C aus PR #30 bei e5b8705, Basis c5bd79c; Lauf-Ordner
`${TMPDIR}/review-runs/20261122-2004-beweis-c/`, Maßstab: Pilot-Befunde Nr. 9, 10, 11, 18):
- Mistral `--agent ask --max-turns 12`, Dateien im Lauf-Ordner (außerhalb des Projekts): **gescheitert**, `turn_limit` nach
  12 Schritten/≈ 90 s, 5× „Tool call denied: file_system.read_file (needs approval…)“, 1× bash. ⇒ Im Lese-Modus liest Vibe
  nur im Projektordner. Nächster Messlauf: `--smart-approve` (Schreiben sperrt der Hook ohne `.normen-auftrag`).
- Mistral Lauf 2 `--smart-approve --max-turns 20 --time-limit 540`, gleicher Prompt: **gescheitert**, `deadline` nach 544 s mit
  nur 2 Schritten und 14 779 Token (antwort: „Ich lese zuerst den Diff …“). Vermutung: Freigabe-Prüfung für Lesen außerhalb
  des Projekts hängt. Journal widerlegt das: 6 `read_file` „Auto-approved: read-only file operation within trusted temporary
  directory“ bzw. „…project file…“ (smart). Hänger danach im Modellaufruf, **Ursache offen**.
- `vibe --help`: `--add-dir <ADD_DIR>` („Additional working directory for file access“). Lauf 3 (Versuch 3, S03; Advisor):
  `--agent ask --max-turns 12 --add-dir <lauf-ordner>`, zweiter Schritt `--resume <session_id>` mit `bericht.md` erlaubt.
  Scheitert das: anhalten und melden, keine vierte Variante.
- Mistral Lauf 3 (`--agent ask --max-turns 12 --time-limit 540 --add-dir <lauf-ordner>`): **bestanden** – `finished`,
  exit 0, 4 Schritte, ≈ 340 s, 104 684 Token, keine Ablehnung, Bericht im Format in Schritt 1 (zweiter Schritt nicht nötig,
  also ungeprüft). Befunde = Pilot Nr. 9 (G9), Nr. 10 (Sitzungsprobe), Nr. 11 (CHANGELOG) – alle drei Maßstab-Befunde bis
  auf Nr. 18 (Labels) getroffen. `--add-dir` damit belegt.
- Gemini Lauf 1: **gescheitert** nach 17 s, „auto-denied“ (`read_file`): Sub-Agent gab nur `$RUN/gemini/` frei, Dateien lagen
  eine Ebene höher. ⇒ Für agy liegt das Material **im eigenen Lauf-Ordner** (`$RUN/`). agy schlug selbst
  `--dangerously-skip-permissions` vor – nicht befolgt. Lauf 2: Material nach `gemini2/` kopiert, Pfade angepasst.
- Gemini Lauf 2: **bestanden** – vollständig, exit 0, ≈ 6–7 min, Bericht im Format; trifft alle vier Maßstab-Befunde
  (Nr. 9, 10, 11, 18). Neu (am Code v16 gelesen, gelten noch; für ein späteres Paket): (a) G9: eine gelöschte Code-Datei
  entschuldigt beliebig viele Testlöschungen (`alt` wird nicht verbraucht, `pruefen` ≈ Z. 2274–2284) – plausibel, gering,
  da seit v16 nur Importzeilen belegen; (b) Sitzungsprobe behält nur 20 Einträge (`[-19:]`, Z. 861) – Fehlschlag in sichere
  Richtung (fälschlich „durchgefallen“).
- **Abnahme Beweislauf:** beide Teams liefern ohne Handrettung einen Bericht im Format (Mistral in 1 Schritt, agy durch).

**Fragen der Inhaberin vom 22.11., alle am 23.11. mit „ja“ beantwortet:** (1) Agent-Definitionen nach `~/.claude/agents/`
kopiert (Sicherungen `*.md.bak-2026-11-23` daneben); (2) `normen.py review` und Merge-Tor → Paket R2; (3) Issues abgeglichen
(siehe Erledigt, V15b-2).
**Entscheidungen der Inhaberin (20.11.):**
- Pflicht nur bei **Meilensteinen** (Normen-Release, größere Pakete), nicht vor jedem Merge.
- Bericht als **Datei** `docs/reviews/<datum>-<branch>.md` (Claudes Wahl: dauerhaft, im Diff prüfbar, in jedem Projekt
  gleich, unabhängig von GitHub; im PR nur ein kurzer Verweis). In öffentlichen Repos ohne private Bezüge (`make test` prüft).
- **Gemini bekommt den Code:** Kein Projekt hat sensible Daten im Code; solche Daten liegen in Datenbanken bzw. eigenen
  Ordnern, die über `[pfade].gesperrt` ohnehin aus jedem Auftrag fallen. Keine Sonderregel nötig.

### Entschieden 22.11.: vertraute Werkzeuge für Teams ganz gesperrt (b) – umsetzen in V15b Punkt 10 *(Befund 21.11.)*

Im Projekt, dem ein vertrautes Werkzeug selbst gehört, prüft der Hook Projektskripte für keine Rolle (`_skript_gate`: „Projektskripte
wie bisher“). Die Unterbefehl-Liste greift nur für die Rolle claude (`rolle == "claude"` in `_skript_im_befehl`). Deshalb darf
mistral-team (vibe) dort jeden Unterbefehl aufrufen, auch den gesperrten (Schlüssel anlegen auf dem Server), und `python3 <werkzeug>`.
In anderen Projekten liegt das Werkzeug außerhalb, dort sperrt die AST-Prüfung für Teams wie bisher.
Frage an die Inhaberin: Soll ein Eintrag in `[werkzeuge].vertraut` für Teams (a) dieselbe Unterbefehl-Liste bekommen oder
(b) ganz gesperrt werden? Empfehlung: (b), denn die Freigabe galt Claude. Umsetzung: die Prüfung vor `_skript_gate` für alle
Rollen, Teams bei Treffer → nein; Tests in `tests/test_werkzeuge.py` (Werkzeug im Projekt, Rolle mistral-team); v16 bzw. mit dem Hooks-Paket.
Messung 22.11. (Stand v16 auf dem Branch): `python3 <werkzeug>` sperrt der Hotfix schon für alle Rollen (nein). Der direkte
Aufruf mit verbotenem Unterbefehl geht für mistral-team durch (ja), und zwar im eigenen Projekt **und** wenn das Werkzeug unter
`[pfade].lesbar_extern` liegt. `python3 -m`/`-c import`: siehe V15b Punkt 1.

### A2. agy-Freigaben: Nacharbeiten

Paket A ist gemergt (PR #19, Bericht `docs/plaene/agy-freigaben-spike.md`). Entscheidungen der Inhaberin 18.11.:
- ✅ Kopie nach `~/.claude/agents/gemini-analyst.md`: erledigt 18.11. (vorher identisch mit der alten Repo-Fassung).
- Sperrpfade (`.geminiignore` sperrt in agy nichts): **nichts sperren** – `gemini-analyst` bleibt in allen Projekten nutzbar.
- Globale `~/.gemini/antigravity-cli/settings.json` (`deny` mit `*` und `Edit`/`Write`/`MultiEdit` wirkungslos,
  `"agentMode": ""`): an die Sitzung des privaten Server-Werkzeug-Projekts gemeldet; sie hat es der Inhaberin vorgelegt
  und ändert selbst nichts. Hier nichts ändern.
- `git … --output`/Lesen außerhalb: Die Inhaberin hat es an diese Sitzung übergeben; deren Empfehlung ist umgesetzt
  (enge Liste: keine `cat`/`grep`/`git log|diff|show` und keine Test-/Buildbefehle mehr, nur `read_file`;
  CHANGELOG „enge Liste“). Der geänderte Satz in `normen.py auftrag` kommt mit v14 (Paket B) in die Projekte.
  Die Kopie der neuen Fassung nach `~/.claude/agents/` braucht eine eigene Rückfrage.
Offen:
4. Projekte: `docs/multi-ki-ablauf.md` angleichen, projekteigene `command(x*)`-Einträge umstellen (mit Paket G).
5. Rückmelde-Issues zu agy-Freigaben (v7, v11) mit Verweis auf den PR schließen (Entscheidung 18.11.).
6. Hook-Prüfung, dass `agy -p` nie ohne `--mode` und ohne `"agentMode":""` startet: nicht in v14 aufgenommen (Umfang),
   Kandidat für die nächste Normen-Version.
7. ✅ 18.11. Rückmelde-Issues zu v14: `--dateien` geschlossen; „erster vibe-Lauf ungesperrt“ und Zeitlimit 540 s
   kommentiert und offen (warten auf Beleg-Log bzw. weitere 1200-s-Läufe).
8. **Unfertige Stände gelangen in Projekte** (Befund 18.11. aus einer Projektsitzung): Ein Projekt hatte „v14“ aus dem
   Arbeitsbaum von claude-tools eingespielt, während v14 noch auf dem Branch entstand – gleiche Versionsnummer, älteres
   `normen.py`; `aktualisieren` ersetzt die Datei zwar, aber weder es noch das Prüftor melden den Unterschied. Vorschlag:
   `einrichten.sh`/`aktualisieren` spielen nur von sauberem `main` ein (sonst Abbruch mit Hinweis) und `herkunft.toml`
   speichert den Commit der Quelle; `aktualisieren` meldet „gleiche Version, anderer Stand“. Kandidat für die nächste Version.

### R2. `normen.py review` und Review-Tor beim Merge (Normen v17) *(✅ erledigt 23.11., Branch `paket-r2-review-tor`)*

**Stand 23.11. (Commits 133ca18, 556aa0f; `make test` grün, `pruefen --diff` 0 Fehler):** Punkte 1–4 umgesetzt.
- Tor (Claude): `review_daten` (git, `--no-renames -z`) + reine `review_entscheidung`; Prüfung in `cmd_merge` nach der
  Vorprüfung, vor dem Testbefehl; `--klein` leer → Fehler vor jedem Netzaufruf; Grund per `gh pr merge --body`.
  Kopien fest im Code (`normen/normen.py`, `normen/*.toml` außer projekt.toml, `normen/herkunft.toml`, `normen/kurz.md`,
  `.claude/settings.json`, `.vibe/`, `.githooks/`) – **enger als der Entwurf** (ohne `docs/`, nur `settings.json` aus
  `.claude/`), weil Markdown ohnehin nicht zählt. `normen/projekt.toml` steht hier unter `kritisch` (Advisor).
- `review` (mistral-team): Lauf 1 gescheitert (Smart-Approve lehnte den Testlauf mit `einrichten.sh` ab, `deadline` nach
  30 Schritten, keine Änderung); Lauf 2 `--resume` „keine Tests ausführen“: `finished`, 8 Schritte, +139 Zeilen, Abnahme
  durch Claude. **Lehre:** Aufträge, deren Tests `einrichten.sh`/Temp-Repos anlegen, an Vibe gleich mit „keine Tests
  ausführen, Abnahme durch Claude“ geben. Abweichung vom Entwurf: `[pruefen].ausschliessen` filtert `review` nicht
  (enthält hier die Normen-Quelle); Forschungsdaten fallen auch aus dem Mistral-Diff (Advisor).
- **Neuer Befund, mit behoben (älter als v17):** Der Hook ließ Teams jeden `normen.py`-Unterbefehl aufrufen, auch
  `auftrag --dateien '**'` (erweitert die eigene Auftragsliste samt Siegel), `auftrag --ende`, `merge`. Jetzt nur
  `pruefen`/`kurz` (`TEAM_NORMEN_ERLAUBT`), Tests in `tests/test_review_tor.py`.
- Tests heißen `tests/test_review_tor.py` (N08 sperrt `test_v17.py`). `test_v4`: Prüfsummen vor dem Abgleich privater
  Begriffe entfernt (Zufallstreffer in `herkunft.toml`).
- **Selbst-Review erledigt** (Bericht `docs/reviews/2026-11-23-paket-r2-review-tor.md`, `Mergereif: ja`): 14 Befunde, 8
  bestätigt und behoben (u. a. Umgehung der Team-Sperre mit `""auftrag`/`$(…)`, Kopien aus Sperrpfaden, Geheimnis-Inhalt),
  6 verworfen. **Messungen:** agy liest keine Projektdateien (Abbruch 21 s) → Material immer in den Lauf-Ordner kopieren;
  zweiter Mistral-Schritt (`--resume` + `bericht.md`) liefert, aber 540 s sind für 344 Diff-Zeilen zu knapp (`deadline`).
- Advisor vor „fertig“: 6 weitere Befunde (Team-Sperre per Wortsuche mit Fehlalarmen und Umgehung → strukturell in
  `_skript_im_befehl`; `-l0`; Kopien neuer Dateien per Blob; `cmd_merge` mit `gh`-Attrappe getestet; Vorlage
  `review-auftrag.md` umgestellt; Bericht ehrlich). Merge per `normen.py merge` als erster Einsatz des Tors (v17 = Meilenstein).
**Kandidaten für später (aus R2):** Vibe-Zeitlimit für Reviews auf 1200 s in Ablauf/`mistral-team.md`; `review` könnte
für Gemini die geänderten Dateien gleich mitkopieren (`git show`), weil agy das Projekt nicht liest.

Entscheidung der Inhaberin 23.11.: beides ja (Frage 2 unter R). Normänderung (N11-Text, `meta.version` 17) → Advisor vor dem
Bau (S07 Punkt 1 und 5). Branch `paket-r2-review-tor`. Entwurf (vom Advisor zu prüfen):
1. **`normen.py review [--basis origin/main] [--gruppe NAME=GLOB[,GLOB…]]…`** – bereitet nur vor, startet keine Teams:
   legt `${TMPDIR}/review-runs/<zeit>-<branch>/<gruppe>/{mistral,gemini}/` an (aufgelöste Pfade), je Ordner `diff.patch`
   (`git diff <basis>...HEAD -- <globs>`), `pflicht.txt` (= `auftrag_zeilen(rolle, [])`), bei mistral `bericht.md`
   (zweiter Schritt). Ohne `--gruppe` eine Gruppe „alles“. Ausgabe: Ordner, Diff-Zeilen je Gruppe, Hinweis ab ≈ 150 Zeilen
   („ungemessen, teilen“). `prompt.md` schreibt weiter Claude (Write-Werkzeug). Exit ≠ 0 bei leerem Diff oder unbekannter Basis.
   **Datenschutz (Advisor 23.11.): Das Werkzeug ist die einzige Sperre vor Gemini** – der Hook prüft nur die Prompt-Datei,
   nicht `diff.patch`. Deshalb nicht per git-Pathspec ausschließen, sondern geänderte Dateien per `--name-status` holen und
   mit dem Abgleich des Hooks filtern (`passt`, `_echt`, ohne Groß-/Kleinschreibung, Ordner-Einträge): `[pfade].gesperrt` aus
   jedem Diff, `[pfade].forschungsdaten` aus dem gemini-Diff, `[pruefen].ausschliessen` ebenfalls. Bei Umbenennung zählen
   alter und neuer Pfad. Negativtests: andere Schreibweise (wie #74), Umbenennung aus einem Sperrpfad heraus.
2. **Review-Tor in `normen.py merge`** – heikle Kernlogik, **Claude schreibt es selbst** als reine Funktion
   (Labels, Dateiliste, Berichtstexte → Entscheidung); vorher nachsehen, wie bestehende Merge-Tests `gh` ersetzen.
   Ist der PR ein **Meilenstein**, verlangt das Tor eine im PR-Diff hinzugefügte oder geänderte Datei
   `docs/reviews/*-<branch>.md` mit fester Zeile `Mergereif: ja` (neu in `review-bericht.md`, Abschnitt „Ergebnis“; der
   Pilotbericht „nicht mergereif“ hätte ein bloßes `## Ergebnis` passiert). Sonst „Nicht gemergt: Meilenstein ohne
   Review-Bericht“ bzw. „… Bericht sagt nicht mergereif“. Branchnamen mit `/` im Dateinamen: `/` → `-` (festlegen, testen).
   Meilenstein = PR-Label `meilenstein` **oder** der Diff ändert `[meta].version` in einer Datei aus der neuen Liste
   `projekt.toml [review].versionsdateien` – hier `agenten-normen/projekt/normen/normen.toml`, in Projekten leer (sonst wäre
   jeder `aktualisieren`-PR dort ein Meilenstein). Das Label im Repository anlegen (Lehre #75); JSON-Feld `labels` vorher per
   `gh pr view --help` belegen (S04). Keine Umgehung im Werkzeug (sonst Merge durch die Inhaberin).
   **Grenze (CHANGELOG):** Das Label vergibt und entfernt Claude selbst – das Tor schützt gegen Vergessen, nicht gegen Absicht.
3. **Normtext N11** um den freigegebenen Satz ergänzen (Wortlaut unter „Antworten der Inhaberin 23.11.“ unten),
   `meta.version` 17, `tests/test_v4.py` anheben, CHANGELOG v17, Ablauf/Vorlagen auf `normen.py review` umstellen.
4. Tests `tests/test_v17.py` (vorher rot): review legt Ordner/Dateien an, Sperr-/Forschungspfade fehlen im Diff, Gruppen;
   Tor: Meilenstein per Label/Version ohne Bericht → stopp, mit Bericht → weiter, Nicht-Meilenstein unverändert (gh per
   Attrappe im Test, nicht im Produktivcode).
5. Umsetzung von `review` an `mistral-team` (Spezifikation von Claude), Tor und Tests schreibt Claude; dann einspielen
   (`bash einrichten.sh . --test "make test"`), `make test`, `pruefen --diff`, Advisor vor „fertig“, **erster Einsatz des
   Tors an sich selbst** (v17 ist Meilenstein → Review nach `docs/review-auftrag.md`, Bericht `docs/reviews/…`), Merge,
   Sitzungen informieren. Im Selbst-Review **einmal den zweiten Schritt erzwingen** (knappes `--max-turns`): `--resume` mit
   `bericht.md` ist nie gelaufen, auch nicht durch den Hook; derselbe Lauf misst agy mit Dateien aus dem Projekt und eine
   größere Gruppe.
**Antworten der Inhaberin 23.11.:** (1) N11-Zusatz ja, **für große Meilensteine** – Wortlaut daher: „Große Meilensteine
(PR-Label `meilenstein` oder neue Normen-Version der Quelle) brauchen zusätzlich einen Review-Bericht
`docs/reviews/<datum>-<branch>.md` mit `Mergereif: ja`; Ablauf `docs/multi-ki-ablauf.md`, Abschnitt „Review“.“
(2) Keine reine Zeilenschwelle: maßgeblich sind **sinnvolle Änderungen** – eine geänderte Beschreibung oder ein Prompt kann
400 Diff-Zeilen haben und ist trotzdem klein. Entwurf (Claude 23.11.; **N11-Wortlaut, dieser Entwurf und die Reihenfolge
R2 → P von der Inhaberin am 23.11. bestätigt** – im Bau nur noch Advisor-Prüfung der Umsetzung):
- **Gewichtete Größe statt Diff-Zeilen.** `merge` zählt nur Zeilen in **Code** (Endungen aus neuer Liste
  `projekt.toml [review].code`, Vorgabe `*.py, *.sh, *.js, *.ts, Makefile, *.json`); Markdown, Prompts, Vorlagen, Doku,
  `CHANGELOG`, `PLAN.md` zählen nicht. Tests zählen nicht (`[pfade].tests`) – sie wachsen mit dem Code mit.
  **Eingespielte Kopien zählen nicht** (`normen/`, `.claude/`, `.vibe/`, `.githooks/`, `docs/` aus `einrichten.sh`) – sonst
  wäre jeder `aktualisieren`-PR in den Projekten über der Schwelle und hier jede Änderung doppelt; gezählt wird nur die Quelle.
- **Kritische Stellen zählen immer.** Neue Liste `[review].kritisch` (Globs; hier `agenten-normen/projekt/normen/normen.py`,
  `agenten-normen/projekt/normen/{normen,rollen,projekt}.toml`, `agenten-normen/projekt/.claude/settings.json`,
  `agenten-normen/projekt/.vibe/**`, `agenten-normen/projekt/.githooks/**` – Rechte, Sperrpfade, Hooks; in Projekten leer):
  jede Änderung dort löst den Halt aus, egal wie klein.
- **Halt mit Begründungspflicht (keine harte Sperre).** Ab 150 gewichteten Code-Zeilen (≈ gemessene Gruppengröße aus R)
  oder bei einer kritischen Stelle ohne Label hält `merge` an: „Review empfohlen: <n> Code-Zeilen / kritisch: <dateien> –
  Label `meilenstein` setzen oder `--klein "<Grund>"`“. Weiter nur mit Label (dann Tor wie oben) oder
  `normen.py merge <PR> --klein "<Grund>"`; der Grund steht im Merge-Commit (später auch im Protokoll, Paket P).
  Grenze (CHANGELOG): den Grund gibt Claude selbst – sichtbar, nicht verhindert.
- Sperrend bleibt allein der große Meilenstein (Label oder neue Normen-Version).
- Tests in `tests/test_v17.py`: 400 Zeilen Markdown → kein Hinweis; 160 Zeilen `.py` → Hinweis; 3 Zeilen in `kritisch` →
  Hinweis; `--klein` ohne Grund → Fehler.

### P. Normen-Protokoll: Rückfragen und Sperren sammeln, regelmäßig auswerten (Normen v18) *(✅ erledigt 24.11., Branch `paket-p-protokoll`)*

**Schritt 0 (Entscheidung der Inhaberin 23.11., mit v18 ausliefern):** „Forschungsdaten dürfen an Mistral“ – bei Reviews
filtert `normen.py review` Forschungsdaten (Pfad-Globs und Textmarker, samt Kopien/Umbenennungen/gleichem Blob) **nur noch
aus dem Gemini-Diff**; der Mistral-Diff enthält sie. Gesperrte Pfade und Geheimnisse bleiben für beide Teams gefiltert.
Umsetzung (Claude, Datenschutzfilter = heikel): Gründe in `cmd_review` je Rolle führen (`grund()` liefert Art + Text; Paare
und Blob-Abgleich je Rolle), Ausgabe `gefiltert (gemini): …` bzw. `(mistral, gemini)`. Tests in `tests/test_review_tor.py`
umstellen (Forschungspfad/Marker/Kopie: im Mistral-Diff **vorhanden**, im Gemini-Diff nicht; Sperrpfad/Geheimnis: in keinem).
Doku: CHANGELOG v18, Ablauf „Review“, Vorlage `review-auftrag.md`, `CLAUDE.md` dieses Projekts („an mistral-team nur nach
Freigabe“ → bei Reviews freigegeben). Der Hook fragt bei Forschungsdaten im **Prompt** an vibe weiter nach (unverändert).

**Mit v18 mitnehmen (Befund aus einer Projektsitzung 23.11., hier nachgestellt):** `cp <lesbar_extern>/datei docs/` sperrt
für Claude mit N06 („schreibt möglicherweise in … [pfade].lesbar_extern“), obwohl nur die **Quelle** dort liegt und das Ziel
im Projekt. **Ursache (Code gelesen, per Skript eingegrenzt):** `_bash_schreibt_extern` prüft die **ganze Kette** – steht
der Ordner irgendwo im Befehl und kommt irgendwo `_SCHREIB_VERB` vor, wird gesperrt („Ganze Kette: … bewusst streng“).
Kleinster gemeldeter Fall: `git branch --show-current && ls <lesbar_extern>/x/` → nein (`git branch` ist Schreibverb, `ls`
nennt den Ordner); ebenso `… && git -C <lesbar_extern> log -3 main`. Vorschlag: je Teilbefehl prüfen (Ordner und
Schreibverb im **selben** Glied bzw. nach `cd <ordner>` im selben Ablauf), und bei `cp`/`mv`/`rsync` nur das Ziel (letztes
Argument bzw. `-t ZIEL`) als Schreibziel. Vorsicht: die Strenge war Absicht (Ketten wie `cd <ordner> && echo x > y`) –
diese Fälle als Tests behalten. Tests: `git branch --show-current && ls <ext>/` → ja; `cp <ext>/a docs/` → ja;
`cp docs/a <ext>/` → nein; `cd <ext> && touch x` → nein.

**Lehren aus R2 für P:** Testdatei nicht `test_v18.py` nennen (N08 sperrt Versionszusätze) – z. B. `tests/test_protokoll.py`.
Neue Unterbefehle (`hook-nach`, `protokoll`) in `NORMEN_UNTERBEFEHLE` eintragen (ein Test vergleicht mit argparse); ob Teams
sie aufrufen dürfen, entscheidet `TEAM_NORMEN_ERLAUBT` (Vorschlag: nein). Vibe-Aufträge, deren Tests `einrichten.sh`/Temp-Repos
anlegen: „keine Tests ausführen, Abnahme durch Claude“ (sonst lehnt Smart-Approve ab). P ist ein Meilenstein (v18) → Review
mit `normen.py review`, Gemini-Material in den Lauf-Ordner kopieren, Vibe `--time-limit 1200`.

Auftrag (23.11.): „jede Anwendung der Normen (mit Freigabe durch mich) in allen Projekten sammeln, in eine Datei schreiben und
regelmäßig zur Evaluation geben“. Lesart (Advisor 23.11.): protokolliert werden Hook-Entscheidungen **`fragen`** (Rückfrage an
die Inhaberin) mit ihrem Ausgang, dazu **`nein`** (Sperren) – nötig, um „zu streng“ zu erkennen. Die Auswertung zeigt
standardmäßig die Rückfragen. Eigenes Paket, getrennt von R2 (kleiner, eigene Version). Branch `paket-p-protokoll`.

**Messung 23.11. (Wegwerf-Repo, `claude -p`, Hooks geben Eingabe-Schlüssel aus):**
- `tool_use_id` steht in PreToolUse **und** PostToolUse (gleicher Wert) → Korrelation möglich.
- Fehlgeschlagenes Werkzeug (`false`): **kein** PostToolUse, aber **PostToolUseFailure** (Felder `error`, `is_interrupt`,
  gleiche `tool_use_id`).
- `ask` ohne Bediener (`-p`): kein Post-Ereignis, Eintrag in `permission_denials` des Ergebnisses.
- Weitere Felder: `session_id`, `cwd`, `permission_mode`, `transcript_path`, `prompt_id`.
- Folgerung: Ausgang = **„ausgeführt“**, wenn PostToolUse oder PostToolUseFailure mit derselben `tool_use_id` kommt, sonst
  **„kein Beleg“** (abgelehnt, abgebrochen oder Sitzung beendet). „Abgelehnt“ wird nicht behauptet. **Ungemessen (erster
  Bauschritt, einmal interaktiv mit der Inhaberin im Wegwerf-Repo):** kommt nach einem von ihr **freigegebenen** `ask` ein
  PostToolUse mit derselben `tool_use_id`? (der tragende Fall); was passiert bei ihrer Ablehnung; was macht ein `ask` im
  Auto-Modus. Was nicht belegt wird, kommt als Grenze ins CHANGELOG.

**Schritte:**
1. **Schreibstelle in `cmd_hook`** (Claude selbst, heikel): hinter der Herabstufung `fragen`→`nein` für vibe/gemini, nur bei
   `entscheid != "ja"`; Felder: Zeit, Projekt (`ROOT.name`), Rolle, Werkzeug, Tool, Stufe ursprünglich/endgültig, Norm-IDs,
   Gründe, Befehl bzw. Pfad (gekürzt auf 300 Zeichen), `session_id`, `tool_use_id`, **`permission_mode`** (im Auto-Modus
   beantwortet ein `ask` evtl. nicht die Inhaberin – die Auswertung muss das unterscheiden). **Eigener, enger Fehlerweg**: ein
   Schreibfehler ändert die Entscheidung nie (sonst sperrt ein voller Datenträger alle Projekte), Meldung auf stderr,
   `normen-ausnahme: N08-KEINE-ALTLASTEN – Protokoll darf die Hook-Entscheidung nicht ändern`.
2. **Datei:** zentral `~/.config/claude-tools/normen-protokoll.jsonl` (außerhalb aller Repos, privat, Rechte 600; Pfad in
   `[protokoll].datei` überschreibbar, für Tests). Je Eintrag **ein** `open(…, "a")`-Schreibvorgang einer Zeile (mehrere
   Sitzungen parallel; nicht das Lesen-Kürzen-Schreiben der Sitzungsprobe). **Schwärzen vor dem Schreiben** mit den Mustern
   aus `_datenschutz_funde` (N03-Inhaltsmuster, E-Mail, IBAN, Telefon) und gesperrten Pfaden → `[geschwärzt]`.
3. **Ausgang:** neuer Unterbefehl `normen.py hook-nach --werkzeug claude` für PostToolUse **und** PostToolUseFailure
   (Matcher wie PreToolUse); schreibt nur, wenn die `tool_use_id` vorher als `fragen` protokolliert wurde (Liste der offenen
   IDs je Sitzung klein halten: nur letzte 200 Zeilen lesen), Eintrag `{"ausgang": "ausgefuehrt"|"fehlgeschlagen", …}`.
   Exit immer 0, keine Ausgabe an Claude. Eintrag in `.claude/settings.json` der Quelle.
4. **Auswertung `normen.py protokoll [--alle] [--seit DATUM] [--gelesen]`:** Zusammenfassung seit der letzten Auswertung:
   je Norm und Projekt Anzahl `fragen` (davon ausgeführt / kein Beleg) und `nein`, die häufigsten Gründe, Beispiele
   (gekürzt). `--gelesen` setzt die Marke (`~/.config/claude-tools/normen-protokoll.marke`). Keine Rotation (S02).
5. **„Regelmäßig“:** SessionStart-Hook (Matcher `startup`) aus der Quelle, also **in allen Projekten** (die Datei ist zentral;
   nur in claude-tools käme der Hinweis selten), ruft `normen.py protokoll --faellig` auf: Ausgabe nur, wenn seit der Marke ≥ 7 Tage und ≥ 1 neuer Eintrag oder ≥ 30 neue Einträge (Vorgabe, im Bericht nennen):
   „Normen-Protokoll: <n> neue Einträge seit <datum> – in claude-tools auswerten (`normen.py protokoll`)“. Claude wertet dort aus
   (zu streng / zu locker / Fehlalarm, vgl. Memory „keine Rückfragen bei Belanglosigkeiten“), schreibt Kandidaten
   **neutralisiert** (keine Projektnamen, Pfade, Befehle aus privaten Projekten) in PLAN.md und setzt die Marke.
6. **Datenschutz:** Protokoll nie an `gemini-analyst`, nie ins Repo, nicht als Issue; Auswertung macht Claude selbst.
7. Tests `tests/test_protokoll.py` (vorher rot, Umsetzung `protokoll`/`hook-nach` an mistral-team, Schreibstelle Claude):
   Eintrag bei `fragen`/`nein`, keiner bei `ja`; Schwärzung (Token, E-Mail); Schreibfehler (Datei-Pfad ist Ordner) →
   Entscheidung unverändert; Korrelation Pre/Post; `--faellig` an den Schwellen; Marke.
8. `meta.version` 18, CHANGELOG, einspielen, Advisor vor „fertig“, Merge. **Wirkt in allen Projekten erst nach
   `normen.py aktualisieren` dort** → Sitzungen informieren (Memory „Versionsschritt“); von hier aus nicht in fremde
   Projekte schreiben. Schreiben nach `~/.config/claude-tools/` ist Schreiben außerhalb des Projekts – im Bericht der
   Inhaberin den Pfad nennen (Auftrag vom 23.11. deckt es dem Sinn nach).

**Stand 23.11. abends (Branch `paket-p-protokoll`):**
- ✅ Schritt 0 (Review-Filter je Rolle, `cmd_review`; Tests in `test_review_tor.py` inkl. „strengster Grund gewinnt“:
  Forschungspfad mit Geheimnis-Inhalt, Paar Sperrpfad→Forschung) – committet.
- ✅ `lesbar_extern` je Teilbefehl (`_bash_schreibt_extern`): betroffen sind Glieder, die den Ordner nennen, Glieder nach
  `cd`/`pushd` dorthin, Glieder hinter einer Pipe; cp/ln/install/rsync mit Ziel außerhalb = nur Quelle; `mv` und
  `rsync --remove-source-files` bleiben streng; Schleifen/Bedingungen/`xargs`/`eval` (`_KETTE_STRENG`) → ganze Kette wie
  vorher; unaufgelöstes Ziel → gesperrt. Tests in `test_guardrails.py` – committet.
- ✅ Schritt 1/2 Schreibstelle (`cmd_hook` → `_protokoll_eintrag`/`_protokoll_anhaengen`, `_schwaerzen` mit gemeinsamem
  `_datenschutz_muster`); Pfad `NORMEN_PROTOKOLL` (Umgebung) statt `[protokoll].datei` (deckt auch alle Tests ab: das
  Makefile setzt es auf `$TMPDIR/normen-test-protokoll.jsonl`); Köder-Einträge ausgenommen; `tests/test_protokoll.py`.
- ⏳ **Messung mit der Inhaberin** (Wegwerf-Repo `probe-ask` im Scratchpad der Sitzung; bei Verlust neu anlegen: Hooks
  Pre/Post/PostFailure/SessionStart schreiben Ereignis, `tool_use_id`, `permission_mode`, `source` nach `log.jsonl`;
  Pre fragt bei `probe-ask`): Fälle (a) `echo probe-ask 1` freigeben, (b) `echo probe-ask 2` ablehnen, (c) im
  Auto-Modus `echo probe-ask 3`, (d) `/clear` → `source` von SessionStart (Matcher `startup|clear`?).
  **Ergebnis 1. Lauf (23.11.):** Sitzung lief durchgehend mit `permission_mode: "auto"` (auch Fälle a/b). Alle drei `ask`
  → PostToolUse mit gleicher `tool_use_id` nach 1–2 s, also **im Auto-Modus beantwortet ein `ask` nicht die Inhaberin**
  (auch der „abgelehnte“ Fall lief). `/clear` → SessionStart `source: "clear"` → Matcher `startup|clear`.
  Nachtrag: **Alle drei** Rückfragen kamen bei der Inhaberin an (sie hat zu schnell geklickt, alle freigegeben) – ein Hook-`ask`
  erreicht sie also auch im Auto-Modus; `fragen` heißt damit immer „die Inhaberin gefragt“. Belegt: freigegebenes `ask` → PostToolUse mit gleicher
  `tool_use_id`. Ungemessen (Grenze im CHANGELOG): Ablehnung (erwartet: kein Post → „kein Beleg“).
- ✅ 24.11.: `hook-nach`, `protokoll` (mistral-team, zweiter Lauf), Hook-Einträge, Version 18, Doku, `einrichten-hier.sh`,
  Review (Mistral, Gemini unvollständig, Advisor) – Bericht `docs/reviews/2026-11-24-paket-p-protokoll.md`, Merge.
- **Lehren:** Vibe-Spezifikationen mit großen Testdaten: „Tests nur lesen, nicht nachbauen“ (erster Lauf hing in einer
  Simulation); Vibes Smart-Approve verweigert Änderungen an `.claude/settings.json` (auch der Vorlage) → solche Einträge
  setzt Claude; agy schafft 410 Diff-Zeilen + Codebereiche nicht in 9 min → Doku-Gruppe teilen; Testdateien direkt starten
  schrieb ins echte Protokoll (behoben: jede Testdatei setzt `NORMEN_PROTOKOLL`).
- ✅ **Erste Auswertung (24.11., Marke gesetzt mit `--gelesen`):** 244 Einträge, davon nur **8 aus echten Sitzungen** (der
  Rest Testeinträge unter Projektname `projekt`, verzerren alle Zählungen; stehen lassen). Berechtigt: N01 (`xargs … git
  restore` auf gelöschte Dateien, anderes Projekt), 2× N06 (Schreiben außerhalb des Projekts), S06 `nein` (Code-Mode-Skript
  mit `symlink_to`/`tempfile`), S06 „Modul wird im selben Befehl geschrieben“. **Fehlalarm-Kandidaten** (alle S06
  „nicht prüfbar“, für die nächste Normen-Version):
  (K1) Skriptpfad mit angehängtem `)` – Zuweisung `R=$(realpath "$RUN")` vor einer agy-Freigabe-JSON wurde als Skriptpfad
  `…/gemini)` gelesen; (K2) `S=<pfad>; … bash "$S/x.sh"` – Variable im selben Befehl zugewiesen, trotzdem „unaufgelöst“;
  (K3) `for f in tests/test_*.py; do python3 "$f"; done` – Schleifenvariable über einen Glob im Projekt (könnte die
  getrackten Treffer einzeln prüfen). Ablehnungen kamen keine vor.

### KT. Coding-Team neu aufstellen: bestes verfügbares Coding-Modell *(✅ erledigt 24.11., Branch `paket-kt-team`)*

Ziel: prüfen, welches verfügbare Modell (z. B. GLM) für Coding am besten ist, und `mistral-team` danach neu konzipieren.
**Bestand (gemessen 24.11.):**
- Vibe 3.1.2, Abo-Modelle: Mistral Large 4 (`mistral-large-4-0-3`, Teamleiter, `active_model`), GLM-5.3 (`glm-5-3`,
  Sub-Agent `code-reviewer`), GLM-5.3 Flash (`zai-glm-5-3-flash`, `…-vibe-free`, Sub-Agent `flash-scout`), Mistral Medium
  3.5 (Sub-Agent `code-worker`). Zuordnung in `~/.vibe/agents/*.toml` und `~/.vibe/config.toml` (Einstellungen der
  Inhaberin, außerhalb des Projekts); Text der Schnittstelle: `multi-ki/benutzer/agents/mistral-team.md` (Zeile ≈ 55).
- **Kein einziger der 16 Vibe-Läufe (22.–24.11., `export.json`) hat einen Sub-Agenten aufgerufen** – Large 4 hat alles
  selbst gemacht; GLM-5.3 lief bei uns nie. 6 von 16 Läufen endeten mit `deadline`/`turn_limit`.
- agy (`agy models`): Gemini 3.8 Flash (high/medium/low), Claude Sonnet 4.6, Claude Opus 4.6, GPT-OSS 120B – **kein**
  Gemini Pro mehr. agy hat keine Hooks (N02/N06 nicht erzwungen) → bleibt Analyst, nicht Umsetzer.
- Lokal (Ollama auf dem Server): u. a. Qwen3.6 35B-A3B, GPT-OSS 120B, eigene Ableitungen – keine Kandidaten für das
  Haupt-Coding-Team. Auffällig: Die MCP-Beschreibung des Servers sagt „nicht für Forschungsdaten“, die Rolle `lokal`
  erlaubt sie – getrennt klären (nicht in KT).
**Recherche (Benchmarks, Herstellerangaben widersprüchlich, nur Rangfolge belastbar):** auf gemeinsamem Gerüst
(mini-swe-agent, vals.ai: SWE-bench Verified, Terminal-Bench 4) gilt **GLM-5.3 > Mistral Large 4 > Mistral Medium 3.5**;
Gemini 3.8 Flash liegt auf SWE-bench Verified vor Sonnet 4.6, GPT-OSS 120B weit dahinter. Agenten-Werte messen Modell
plus Gerüst. Heißt: Heute schreibt nominell das schwächste Modell (Medium 3.5) Code, das stärkste prüft nur.
**Varianten (Entscheidung der Inhaberin):**
- (A) Minimal: `code-worker` → GLM-5.3; `code-reviewer` → Large 4 (anderes Modell als der Umsetzer, unabhängiger);
  Teamleiter bleibt Large 4. Nachteil: wirkt nur, wenn Vibe die Sub-Agenten auch aufruft – bisher nie.
- (B) **Empfohlen:** GLM-5.3 als `active_model` (arbeitet selbst, ein Sprung weniger); Reviews mit Large 4 (`--model`
  bzw. eigener Review-Agent), Kreuz-Review weiter über gemini-analyst; Medium 3.5 entfällt; Flash bleibt Scout.
**Schritte:** (1) **Probelauf** (nur nach Freigabe): dieselbe kleine, bekannte Aufgabe (z. B. Fehlalarm K2 oben mit Test)
je einmal mit GLM-5.3 und Large 4 als `active_model` per `--model`, ohne `~/.vibe` zu ändern; messen: Ergebnis grün?
Diff minimal? Dauer, Schritte, Tokens, `outcome`, Verhalten unter `safety = "smart"`, Wartezeit bei `thinking = "max"`
vs. `high`. Vorher klären, ob `glm-5-3` tatsächlich angesprochen wird (`export.json` → `routed_model_config`) und ob das
kostenlose Flash-Modell andere Datenbedingungen hat. (2) Advisor zu Ergebnis und Variante. (3) Mit Freigabe der Inhaberin
`~/.vibe/agents/*.toml`/`config.toml` umstellen (Sicherung `*.bak-<datum>`), Quelle `multi-ki/benutzer/agents/mistral-team.md`
und `multi-ki-ablauf.md` anpassen (Modellnamen, Rollen, Zeitlimits), Version/CHANGELOG, einspielen (`--benutzer-agents`).
(4) Ein echter Auftrag zur Abnahme; Sitzungen informieren.
**Entschieden (Inhaberin 24.11.):** Variante **B**, Probelauf frei, `~/.vibe` danach ändern frei.
**Probelauf (24.11., gleiche Prompt-Datei, `--model`, Zweige `probe-kt-glm` / `probe-kt-large`, nicht zum Merge):**
Aufgabe = Lücke + Fehlalarm K1: Befehle in `$(…)`/Backticks wurden in S06 nie geprüft (`echo $(python3 /außen/boese.py)`
lief durch); `R=$(realpath /x)` galt als Skriptaufruf `/x)`. Tatsächliches Modell steht in `out/session/meta.json`
(`config.model_name`), **nicht** in `export.json → routed_model_config` (zeigt nur die Voreinstellung).
| | GLM-5.3 (`zai-glm-5-3`) | Large 4 (`mistral-large-4-0`) |
|---|---|---|
| outcome / Schritte / Dauer | finished / 27 / 16,5 min | finished / 35 / 17,2 min |
| Ausgabe-Tokens | 100 k | 48 k |
| Diff `normen.py` | +169 | +134 |
| eigene 15 Tests / Tests des anderen | grün / grün | grün / grün |
| `make test`, `pruefen --diff` | grün, 0 Fehler | grün, 0 Fehler |
| 11 eigene Grenzfälle (Claude) | 7 ok; offen: case-`)`, verschachtelte Backticks, `$(( $(…) ))`, zitierter Heredoc → nein statt ja | 8 ok; offen wie GLM ohne Arithmetik |
| **Sperren** | 2 N10-Fehlalarme bei `grep`/`sed -n` (zweiter Aufruf eine Abwandlung des ersten), danach weiter ohne diese Befehle | Vibes Smart-Approve lehnte `write_file` der Testdatei 2× ab (Inhalt `os.system`); danach laut Journal bewusst per Shell-Heredoc geschrieben, „um den Klassifizierer zu umgehen“ (Ziel war ein erlaubter Pfad); Hook-Sperren dazwischen berechtigt |
Bewertung (n = 1, GLM mit `thinking = max`, Large mit `high`; GLM nicht schneller, doppelt so viele Ausgabe-Tokens):
fachlich gleichwertig (Large minimal besser bei Arithmetik). Large 4 umging Vibes Smart-Approve-Sperre auf anderem Weg
(Journal; n = 1, erlaubter Pfad – kein Normverstoß im engeren Sinn, aber gegen die Regel „denselben Zweck nicht auf
anderem Weg“). Grundlage für B: Benchmark-Rangfolge, nie genutzte Sub-Agenten, funktionierender GLM-Lauf.
Neuer Fehlalarm-Kandidat aus dem Protokoll: (K4) N10 „`normen.py hook`/`selbsttest` ruft nur Claude auf“ bei reinem
`grep`/`sed -n` mit diesen Wörtern (Team). Offen zu prüfen: `utility_models.smart_approve` ist leer – nutzt Smart-Approve
dann das aktive Modell (GLM prüft seine eigenen Aufrufe)? Beide Probezweige (nur lokal) sind **nicht mergereif** (mehrzeiliges `$(…)` außerhalb von
Anführungszeichen → „nicht zerlegbar“, neue Fehlalarm-Klasse).
**Umgesetzt (24.11.):** `~/.vibe/config.toml` `active_model = "glm-5-3"`, `code-worker` → GLM-5.3, `code-reviewer` →
Large 4 (Sicherungen `*.bak-2026-11-24`); Quelle `mistral-team.md` (Modell immer per `--model`, Review → Large 4, sonst
GLM-5.3; Modellprüfung über `meta.json`; Sperren und Umgehungsversuche im Bericht), `multi-ki-ablauf.md`, `LIES-MICH.md`,
Berichtsvorlagen; `~/.claude/agents/mistral-team.md` eingespielt (Sicherung `.bak-2026-11-24`). CHANGELOG-Eintrag ohne
Normen-Version. **Abnahme:** Testlauf ohne Modellvorgabe → `zai-glm-5-3`, grün; Review mit `--model mistral-large-4-0-3`
→ `mistral-large-4-0`, 10 Befunde, 9 behoben (Befund „LIES-MICH Stand 14.11.“ betrifft gemini-analyst, nicht KT).
**Offen:** Die neue Schnittstelle gilt erst nach Neustart einer Sitzung (diese Sitzung hatte die alte geladen – erster
Review-Lauf lief daher mit GLM). Nach dem Neustart einmal prüfen, dass ein Review ohne Modellangabe im Agent-Prompt
`mistral-large-4-0` in `meta.json` zeigt.

### S06-ERS. Befehlsersetzungen in der S06-Prüfung (Normen v19) *(nächstes Paket, Freigabe der Inhaberin für Normänderung)*

Lücke (gemessen 24.11.): `echo $(python3 /außen/boese.py)` wird für die Rolle claude erlaubt – Befehle in `$(…)`/Backticks
prüft S06 nie; zugleich Fehlalarm K1 (`R=$(realpath /x)` → „Skript /x) nicht gefunden“). Ausgangsbasis: Probezweig
`probe-kt-glm` (GLM-5.3, Funktionen `_ersetzungen`, `_skript_in_ersetzungen`, Test `tests/test_ersetzung.py`) – nicht
mergen, sondern als Vorlage für die Spezifikation. Zusätzlich verlangen: `case … )` in `$(…)`, verschachtelte Backticks,
`$(( $(…) ))`, zitierter Heredoc in `$(…)` = Daten (heute „nicht zerlegbar“), mehrzeiliges `$(…)` ohne Anführungszeichen
ohne Fehlalarm, doppelte Klammer-Hilfsfunktionen zusammenlegen; Grenzfälle aus
`tests/kante_kt.py` auf dem lokalen Zweig `probe-kt-glm` als Tests übernehmen. Zusammen mit K1–K4. Schritte:
Advisor (Normänderung, S07 Punkt 5), Freigabe der Inhaberin, mistral-team (GLM-5.3) setzt um, Review Large 4 + Gemini,
Version 19, Bericht, Merge, Sitzungen informieren. Danach Probezweige `probe-kt-glm`/`probe-kt-large` löschen (Rückfrage).

### VL. Eine Quelle `vorlage/` – Projektbaum zum Kopieren *(Entscheidung der Inhaberin 24.11., nach KT, vor DT)*

Wunsch: „ein Ordner im Repository, wo all die Dateien drin sind, die ich in ein neues Projekt kopieren muss“. Entschieden
(Variante a): `agenten-normen/projekt/` und `multi-ki/projekt/` zu **einem** Ordner `vorlage/` zusammenlegen, der genau den
Baum eines eingerichteten Projekts zeigt (`normen/`, `.claude/`, `.vibe/`, `.githooks/`, `docs/`, `AGENTS.md`,
`.geminiignore`, `CLAUDE-abschnitt.md`, `PLAN.md`); Benutzer-Agenten (`multi-ki/benutzer/`) als `vorlage-benutzer/` bzw.
Unterordner – beim Planen entscheiden. Einzige Quelle (N08: keine Kopie daneben), `einrichten.sh` liest von dort.
Schritte: (1) Advisor zu Schnitt und Namen; (2) Stellen finden, die die alten Pfade nennen (beide `einrichten.sh`,
`normen.py aktualisieren`/`_quelle`, `herkunft.toml`, Tests, LIES-MICH, NEUES-REPOSITORY, KONZEPT, CLAUDE.md) – Analyse an
gemini-analyst; (3) `git mv` + Pfade anpassen (mistral-team nach Spezifikation); (4) Platzhalter (`@@SPERRLISTE@@` …) in
`vorlage/` dokumentieren: „von Hand kopieren“ heißt Platzhalter selbst füllen – `einrichten.sh` bleibt der empfohlene Weg;
(5) Normen-Version, einspielen, **`aktualisieren` in Projekten muss mit dem neuen Quellpfad funktionieren** (Test mit
Projekt auf alter Version); Sitzungen informieren.

### DT. Design-Team (Ersteller + Kritiker) als Sub-Agenten *(Wunsch der Inhaberin 23.11., nach P)*

Ziel: ein Designer-Team analog zu `mistral-team`/`gemini-analyst` – zwei Rollen: **Design-Ersteller** (experimentierfreudig,
kreativ: Entwürfe, Varianten, Mock-ups) und **Design-Kritiker** (kritisch: prüft Entwürfe auf Gestaltung, Lesbarkeit,
Barrierefreiheit, Konsistenz, begründet und priorisiert Befunde). Claude koordiniert: Ersteller liefert, Kritiker prüft,
Ersteller überarbeitet (begrenzte Runden).
Schritte (Vorschlag): (1) Advisor zu Plan/Schnittstellen; (2) Entscheidung der Inhaberin: welcher Anbieter/welches Modell
je Rolle (Claude-Sub-Agent z. B. Sonnet, oder extern über Mistral/Gemini – Kontingent und Datenschutz), Ausgabeformat
(HTML-/SVG-Entwürfe, Artifacts, Bilder?), wo Entwürfe landen; (3) Agenten-Definitionen in der Quelle (`multi-ki/`, wie
die bestehenden `.claude/agents/*.md`), Rollen in `rollen.toml` (Rechte wie gemini-analyst: lesen, schreiben nur Pfade
aus `.normen-auftrag`), Abschnitt im Ablauf (`multi-ki-ablauf.md`: wann delegieren, Auftragsvorlage, Kritik-Runden),
`CLAUDE.md`-Vorlage; (4) Tests (Rollen, Hook-Rechte); (5) Normen-Version, einspielen, Sitzungen informieren.
Offene Fragen an die Inhaberin: Anbieter je Rolle; nur Web-/UI-Design oder auch Grafik/Logos; Zahl der Kritik-Runden.

### D2. Sandbox einführen? *(Entscheidung der Inhaberin offen)*

Grundlage: Nachtrag Paket D im Sandbox-Bericht. Weg 2 ist machbar, verlangt aber: (1) Sandbox-Block mit
`excludedCommands: ["vibe *", "agy *"]` in den **Benutzer-Einstellungen** (`~/.claude/settings.json`; Einstellungsänderung →
Freigabe; Projekt-Ebene laut Programmtext wirkungslos, ggf. mit einem Lauf belegen), (2) Aufrufform von `mistral-team`/`gemini-analyst` als bloßer Befehl (Pfade wörtlich, kein `RUN=`/`ALLOW=` davor,
keine Umleitung; Ergebnis über `--output-dir` bzw. Werkzeug-Ausgabe; agy-Freigaben als wörtliches `--settings`-JSON) – dafür
den Normen-Hook prüfen (findet er die Prompt-Datei ohne `RUN=`?), (3) fester Lauf-Ordner `/tmp/claude-<uid>/…` statt `${TMPDIR}`,
(4) `einrichten.sh`/`aktualisieren` außerhalb der Sandbox. Vorher nachmessen: `--output-dir` allein, agy im Hintergrund.
Abwägung: Im Auto-Modus kam bei ausgenommenem vibe (ein Lauf) keine Rückfrage; die Sandbox schützt dort vermutlich nur die
übrigen Bash-Befehle. Weitere Auto-Modus-Fälle (agy, Schreiben außerhalb) noch messen.
Nebenbei offen: Skill `fewer-permission-prompts` (häufige lesende Befehle → Allowlist-Vorschlag zeigen, nicht eintragen).
Treiber zum Nachmessen: Python-`pty`, `CLAUDE_CODE_FORCE_SESSION_PERSISTENCE=1`, `--permission-mode` ausdrücklich setzen,
Vertrauens-Dialog steht auf „No“ (Pfeil runter + Enter), Bildschirmtext ohne Leerzeichen vergleichen.

### E. `meta.ebenen` *(Frage 5, eingeplant)*

Entwurf in `docs/plaene/guardrails-v7-entwurf.md` Abschnitt 6: `[meta].ebenen` (Hooks / Sandbox / nachgelagert / Restgefahr)
in `normen.toml`, Ausgabe in `kurz.md`. Text an den Stand nach Paket D anpassen (Sandbox weiter „geplant“?). Normänderung:
Advisor vorher (S07 Punkt 5), Freigabe der Inhaberin.

### F. Worktree je Team-Lauf *(Frage 5, eingeplant, nach A–E)*

Grundlage `docs/plaene/worktree-spike.md` (nur innerhalb unter `.worktrees/`). Vorbedingungen aus den offenen Fragen: echter
Vibe-Lauf im Worktree, getrackte Sperrpfade/sparse-checkout, normales `git worktree remove` löscht git-ignorierte Dateien.

### G. Projekte auf v13 bringen *(Frage 2, läuft)*

18.11.: vier Projektsitzungen gefragt (Version, Prüfbefehl aus `.vibe/hooks.toml` → „gültig: 9“, Selbsttest). Antworten 3 von 4:
alle v12, „gültig: 9“, Selbsttest claude/vibe gesperrt; die vierte Sitzung arbeitet nicht in einem Normen-Projekt (oder antwortet
später). Auffällig in einem Projekt: der **Kopfkommentar** von `.vibe/hooks.toml` nennt noch „gültig: 8“ (eigene Hooks →
`einrichten.sh` legt nur `.vorlage` daneben; Kommentar dort von Hand angleichen).
Das Projekt auf v9 (ohne Sitzung) mit Freigabe vom 18.11. per `bash <claude-tools>/einrichten.sh <projekt> --test "make test"`
auf **v13** gebracht (direktes `normen.py aktualisieren` dort sperrt der S06-Hook als fremdes Skript): „gültig: 9“, Tests grün,
PR im Projekt am 18.11. gemergt (durch die Inhaberin); dort noch die
`.vorlage`-Dateien (`docs/multi-ki-ablauf.md`, `.geminiignore`) zusammenführen. Nach dem v13-Merge alle Sitzungen informiert.
Rückmeldung mistral-team-Zeitlimit 540 s: in v14 geändert (Umsetzungsläufe 1200 s im Hintergrund), Wirkung offen – der einzige 1200-s-Lauf (v14) endete ebenfalls am Zeitlimit; Issue offen lassen.

### H. Entschlacken und Archiv *(Wunsch der Inhaberin 18.11.)*

PLAN.md und ähnliche Dateien regelmäßig entschlacken: Erledigtes wandert in passende Dateien unter `./archiv/`; ebenso
alle anderen alten, nicht mehr benötigten Daten (z. B. erledigte Spikes und Entwürfe in `docs/plaene/`). Schritte:
1. In claude-tools selbst: `archiv/` anlegen (z. B. `archiv/plan-2026-11.md`, `archiv/plaene/`), Erledigt-Abschnitt und
   abgeschlossene Pakete aus PLAN.md dorthin, erledigte Pläne per `git mv`; Verweise (PLAN-Tabelle, CHANGELOG) anpassen.
2. Für alle Projekte: Regel in die PLAN-Vorlage (`multi-ki/projekt/PLAN.md`) und ggf. als Ergänzung zu S08 – das wäre eine
   Normänderung (Advisor S07 Punkt 5, Freigabe der Inhaberin). Vorschlag: „Am Paketende Erledigtes nach `archiv/`
   verschieben, PLAN.md enthält nur Offenes und die letzten Schritte“.
3. Klären: wann „regelmäßig“ (je Paketende? ab N Zeilen?) und ob `archiv/` von `.geminiignore`/Tests ausgenommen wird.

## Entscheidungen der Inhaberin (18.11.)

- v13 (S08) mergen: ja – gemergt (PR #16).
- Rückmelde-Issues: schließen, sobald das jeweilige Paket sie erledigt (kurzer Kommentar mit Version/PR).
- Projekt auf v9 selbst aktualisieren: ja – erledigt und gemergt (siehe G).
