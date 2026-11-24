# Review: Branch `paket-p-protokoll` (Normen v18, Normen-Protokoll) – 2026-11-24

Ablage nach `docs/review-bericht.md`. Rohausgaben der Teams liegen im Lauf-Ordner
`${TMPDIR}/review-runs/20261124-0901-paket-p-protokoll/`. Jeder Befund ist von Claude geprüft.

## Gegenstand
`git diff 75cc86b...ec3c043` (Basis main), vorbereitet mit `normen.py review`. Gruppen: **hook** =
`agenten-normen/projekt/normen/normen.py` (526 Diff-Zeilen) an Mistral, mit Leseauftrag auf drei Bereiche
(`_bash_schreibt_extern`, `cmd_hook`, Protokoll-Funktionen); **doku** = CHANGELOG, LIES-MICH, Ablauf, Vorlagen, Einstellungen
(410 Diff-Zeilen) an Gemini, dazu `normen.py` und der P-Abschnitt aus PLAN.md als Kopie im Lauf-Ordner; **tests** nur Claude.
Nicht doppelt geprüft: eingespielte Kopien (`normen/`, `docs/`, `AGENTS.md`, `.claude/settings.json`), per `cmp` gegen die
Quelle belegt. Nachträge nach ec3c043 (Korrekturen, `einrichten-hier.sh`) hat kein Team gesehen.

## Prüfer und Ablauf

| Prüfer | Modell | Lauf | Ergebnis |
|---|---|---|---|
| Claude | eigene Durchsicht der Diffs von mistral-team (Umsetzung) und eigener Teile | – | 2 Befunde |
| mistral-team | mistral-large-4-0-3, `--agent ask --add-dir`, `--time-limit 1200` | vollständig, 2 Runden, ≈ 11 min | 10 Befunde (1 positiv) |
| gemini-analyst | gemini-3.8-flash-high, Nur-Lesen, Material im Lauf-Ordner | `print timeout` nach 9 min, Antwort unvollständig (5 Befunde lesbar) | 5 Befunde |

Status: **bestätigt** = von Claude nachgestellt (Test oder Messung); **verworfen** = trifft nicht zu (Grund); **Grenze** =
bleibt, steht im CHANGELOG.

## Befunde

| Nr. | Ort | Befund | Fehlerszenario | Quelle | Status |
|---|---|---|---|---|---|
| 1 | Test `hook-nach groß` | erwartete den Ausgang in der vorletzten Zeile | Umsetzung korrekt, Test falsch | Mistral (Umsetzungsbericht) | **bestätigt**, Test korrigiert |
| 2 | `cmd_protokoll` | Gründe je Norm mehrfach gezählt | Eintrag mit zwei Normen → Grund doppelt | Claude | **bestätigt**, behoben |
| 3 | `_SCHREIB_VERB` | `dd of=`, `python3 -c` nicht als Schreiben erkannt | `dd if=/dev/zero of=<ext>/x` → durch | Mistral 1 | **bestätigt** (gemessen, auch auf main – keine Verschlechterung); `dd` ergänzt (N01 sperrt `dd` ohnehin); `python3 -c` prüft S06 (Inline-Code) |
| 4 | `_bash_schreibt_extern` | `cd` ohne Ordnernamen, `./`, Symlink | `cd sub && touch f` | Mistral 2 | **verworfen** (gemessen): aufgelöste Ziele aus `_schreibziele` (normpath, realpath) sperren alle drei |
| 5 | `_SCHREIB_VERB` | git-Langoptionen mit `=` | `git --git-dir=<ext>/.git add f` → durch | Mistral 3 | **bestätigt** (gemessen, auch auf main), behoben; Tests |
| 6 | `_bash_schreibt_extern` | zerlegtes Quoting | `touch '<ext>'/x` | Mistral 4 | **verworfen** (gemessen): gesperrt; Test ergänzt |
| 7 | `cmd_protokoll`, `hook-nach` | Team-`fragen`→`nein` zählte als „fragen, kein Beleg“ | vibe-Sperre erscheint als Rückfrage an die Inhaberin | Mistral 5, Gemini 3 | **bestätigt**, behoben: Zählung nach `entscheid`; Test |
| 8 | `_protokoll_marke` | Marke ohne Zeitzone → TypeError; kaputte Marke still als „keine Marke“ | Marke von Hand geschrieben | Mistral 6 | **bestätigt**, behoben: lokal annehmen; kaputte Marke wird gemeldet (Exit ≠ 0, `--faellig` Exit 0 mit stderr); Tests |
| 9 | `hook-nach` | Zeilengrenze bei parallelen Sitzungen | > 200 Zeilen / 64 KiB zwischen Pre und Post | Mistral 7, Gemini 5 | **Grenze**, CHANGELOG ergänzt (auch 64 KiB) |
| 10 | `cmd_hook` | `g.startswith` auf Nicht-String | `bewerten` liefert Zahl | Mistral 8 | **verworfen**: jede Stelle `gruende.append((…, …))` in `bewerten` hängt ein Zeichenketten-Literal oder einen f-String an (per `grep` geprüft); zudem bildet `cmd_hook` den Grund schon vor v18 mit `"; ".join(gruende)` |
| 11 | `_schwaerzen` | Geheimnis ohne Muster bleibt sichtbar | `mysql -pGeheim123` | Mistral 9 | **Grenze**, CHANGELOG ergänzt; Protokoll ist privat (600, außerhalb der Repos) |
| 12 | `hook-nach` | ohne Protokoll Fehlermeldung bei jedem Werkzeugaufruf | frische Umgebung → `FileNotFoundError` auf stderr | Gemini 1 | **bestätigt**, behoben; Test |
| 13 | `_protokoll_eintrag` | bei `mcp__*` leerer `inhalt` statt Tool-Name | Auswertung ohne Beispiel | Gemini 2 | **bestätigt**, behoben; Test mit gesperrtem MCP-Werkzeug |
| 14 | `_schwaerzen` | Globs in `[pfade].gesperrt` | `daten/intern/**` | Gemini 4 | **verworfen**: `gesperrt` sind laut Vorlage Präfixe (Hook vergleicht ebenso per Teilzeichenkette) |
| 15 | Testläufe | direkter Aufruf einer Testdatei schrieb ins echte Protokoll | `python3 tests/test_guardrails.py` → ≈ 235 Testeinträge | Claude (Advisor-Warnung vorab) | **bestätigt**, behoben: jede Testdatei setzt `NORMEN_PROTOKOLL` (gemessen: 240 → 240 Zeilen); Einträge bleiben stehen (Entscheidung der Inhaberin); alle Testdateien direkt gestartet: 245 → 245 Zeilen |
| 16 | `_bash_schreibt_extern` | `ln` und `cp -l`/`-s` galten als „nur Quelle“ (v17 sperrte) | `ln -s <ext> docs/l && touch docs/l/x` → durch | Advisor | **bestätigt** (Test rot), behoben: nur cp/install/rsync, cp ohne Link-Optionen; Tests |
| 17 | `_bash_schreibt_extern` | Ordner nur über Variable genannt (v17 sperrte) | `D=<ext>; git -C $D commit -m x` → durch | Advisor | **bestätigt** (Test rot), behoben: Zuweisung nennt den Ordner → ganze Kette streng; Tests. Vierte Fassung – danach nicht weiter gehärtet (S03) |
| 18 | `_schwaerzen` | nur das Präfix geschwärzt | `cat geheim/kunde-x.txt` → `[geschwärzt]kunde-x.txt` | Advisor | **bestätigt**, behoben: ganzes Pfadwort; Test |
| 19 | Hook | „Protokoll nie an Gemini“ nur als Anweisung | `cat ~/.config/claude-tools/normen-protokoll.jsonl` als Team → ja | Advisor | **bestätigt** (Test rot), behoben: Protokollordner für Teams gesperrt (N03); Tests für Shell und `read_file` |

## Nicht geprüft
- Korrekturen nach ec3c043 (Nr. 2, 5, 7, 8, 12, 13, 15–19) und `einrichten-hier.sh` hat kein Team gesehen; geprüft durch Tests
  bzw. einen Probelauf in einem Wegwerf-Ordner.
- Gemini: Antwort am Zeitlimit abgeschnitten; Teile der Prüffragen 2–4 (Auftrag gegen Umsetzung, veraltete Doku) offen.
- Ablehnung einer Rückfrage (kein Post-Ereignis erwartet) ist ungemessen – Grenze im CHANGELOG.

## Befunde zum Verfahren
- Erster Umsetzungslauf von Vibe endete ohne Änderung (`deadline`): Vibe wollte den 20 000-Zeilen-Test im Speicher
  nachstellen. Fortsetzung mit „nicht simulieren, Reihenfolge, Skizze für `seek`“ lieferte. Lehre: in Spezifikationen mit
  großen Testdaten ausdrücklich „Tests nur lesen, nicht nachbauen“.
- Vibes Smart-Approve lehnte das Ändern von `.claude/settings.json` (Vorlage in der Quelle) dreimal ab; Claude hat die drei
  geplanten Einträge selbst gesetzt.
- Mistral-Review mit Leseauftrag auf Zeilenbereiche: schnell (2 Runden), aber Befunde zu Hilfsfunktionen außerhalb blieben
  „vermutet“ – Messung per Skript klärte sie (2 von 4 verworfen).
- agy: 410 Diff-Zeilen plus Codebereiche überschreiten 9 min; nächstes Mal Doku-Gruppe teilen.

## Ergebnis
Mergereif: ja

Alle bestätigten Befunde (Nr. 1–3, 5, 7, 8, 12, 13, 15–19) sind auf dem Branch behoben, Code-Befunde mit Test. Grenzen (Nr. 9,
11, Ablehnung ungemessen) stehen im CHANGELOG v18. `make test` grün, `normen.py pruefen --diff` ohne Fehler.
