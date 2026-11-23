# Review: Branch `paket-r2-review-tor` (Normen v17, Review-Tor und `normen.py review`) – 2026-11-23

Ablage nach `docs/review-bericht.md`. Rohausgaben der Teams liegen im Lauf-Ordner
`${TMPDIR}/review-runs/20261123-1207-paket-r2-review-tor-120743/`. Jeder Befund ist von Claude geprüft.

## Gegenstand
`git diff d522956...46e515c` (Basis origin/main), vorbereitet mit `normen.py review` – erster Einsatz des neuen Werkzeugs.
Gruppen: **tor** = `agenten-normen/projekt/normen/normen.py` (344 Diff-Zeilen) an beide Teams; **doku** = CHANGELOG,
`multi-ki/**`, `agenten-normen/projekt/normen/*.toml`, `normen/projekt.toml` (186 Diff-Zeilen) zusätzlich an Gemini;
**tests** (`tests/*.py`, `Makefile`, 440 Diff-Zeilen) nur Claude. Nicht doppelt geprüft: eingespielte Kopien (`normen/`,
`docs/multi-ki-ablauf.md`, `docs/review-bericht.md`, `AGENTS.md`), per `einrichten.sh` aus der Quelle erzeugt und von
`make test` (`test_v4`, Herkunft) abgeglichen.

## Prüfer und Ablauf

| Prüfer | Modell | Lauf | Ergebnis |
|---|---|---|---|
| Claude | eigene Durchsicht des Diffs (kein `/code-review`, Kontingent) | – | 2 Befunde |
| mistral-team | mistral-large-4-0-3, `--agent ask --add-dir`, `--max-turns 5` (bewusst knapp) | Schritt 1: `deadline` nach 540 s, 3 Schritte, kein Bericht; Schritt 2 `--resume` + `bericht.md`: Bericht (bricht nach Nr. 4 am Zeitlimit ab) | 4 Befunde |
| gemini-analyst | gemini-3.8-flash-high, Nur-Lesen | Lauf 1 mit Datei aus dem Projekt: abgebrochen nach 21 s („auto-denied“ `read_file`); Lauf 2 mit Kopie im Lauf-Ordner: vollständig, 428 s | 7 Befunde |

Status: **bestätigt** = von Claude nachgestellt (Test); **verworfen** = trifft nicht zu (Grund); **Grenze** = bleibt, steht
im CHANGELOG.

## Befunde

| Nr. | Ort | Befund | Fehlerszenario | Quelle | Status |
|---|---|---|---|---|---|
| 1 | normen.py Hook, `_NORMEN_UNTER_RX` | Sperre von normen.py für Teams umgehbar | `normen.py ""auftrag --ende`, `python3 $(echo normen/normen.py) auftrag`, `exec(open(…))` → ja | Mistral 1 | **bestätigt**, behoben: ohne Anführungszeichen prüfen + jedes Wort, das ein gesperrter Unterbefehl ist; Tests |
| 2 | `cmd_review` | Kopien und stark umgebaute Umbenennungen aus Sperr-/Forschungspfaden landen im Diff | `cp daten/roh/x.csv kopie.csv` (nur `-M`, keine Kopie-Erkennung) bzw. Umbenennung mit > 50 % Umbau → Inhalt an Gemini | Mistral 2 (Kopie: Claude) | **bestätigt**, behoben: `-M30% -C30% --find-copies-harder`; Tests; Rest als Grenze |
| 3 | `review_daten`/`review_entscheidung` | Pfade nicht relativ zum Projekt | – | Mistral 3 | **verworfen**: git liefert Pfade relativ zur Wurzel des Repositorys, `docs/reviews/` liegt dort (`test_sammeln`) |
| 4 | `review_entscheidung` | bei mehreren Berichten zählt nur der neueste | erster Bericht „nein“, zweiter „ja“ | Mistral 4 | **verworfen**: gewollt – Nachbesserung nach einem „nein“ ist der übliche Verlauf; als Grenze dokumentiert |
| 5 | `review_entscheidung` | Label `Meilenstein` (Großbuchstabe) zählt nicht | Label „Meilenstein“ → kein Meilenstein (offene Richtung) | Claude | **bestätigt**, behoben (casefold); Test |
| 6 | `cmd_review` | `bericht.md` leer statt Text für den zweiten Schritt | Fehler in der Spezifikation | Claude | **bestätigt**, behoben; Test |
| 7 | `cmd_review` | Geheimnisse im Inhalt harmlos benannter Dateien gehen an Gemini | `src/client.py` mit privatem Schlüssel → im `diff.patch` | Gemini 7 | **bestätigt**, behoben: Muster `_GEHEIM_INHALT` des Prompt-Hooks; Test; Klartext-Passwörter als Grenze |
| 8 | `review_entscheidung` | Branchname anders abgebildet als im Ordner von `review` | Branch `feat#42` → Bericht `…-feat-42.md` nicht gefunden | Gemini 1 | **bestätigt**, behoben (`_review_branch` für beide); Test |
| 9 | `projekt.toml` (Vorlage) | Kommentar nennt pauschal `normen/` als Kopie, Code nur feste Dateien | `normen/werkzeug.py` zählt doch | Gemini 3 | **bestätigt**, Kommentar mit genauer Liste |
| 10 | Ablauf „Review“ | 150 Diff-Zeilen (`review`) ≠ 150 Code-Zeilen (`merge`) | Verwechslung beim Lesen | Gemini 4 | **bestätigt**, Ablauf klargestellt |
| 11 | `review_daten` | `_geheim` prüft nur Dateinamen | `geheimnisse = ["secrets/*"]` | Gemini 2 | **verworfen**: `[pfade].geheimnisse` sind laut Vorlage Dateinamen-Globs; Ordner gehören in `gesperrt` |
| 12 | Hook | `normen.py` ohne Unterbefehl nicht gesperrt | `python3 normen/normen.py` | Gemini 5 | **verworfen**: argparse bricht ohne Unterbefehl ab (`required=True`), keine Wirkung |
| 13 | `review_daten` | mehrere Merge-Basen | Criss-Cross-Merge | Gemini 6 | **verworfen**: `git merge-base` ohne `--all` gibt genau eine Basis aus |
| 14 | Hook | Glob im Programmpfad | `python3 normen/norme?.py auftrag`, `python3 n*/n*.py auftrag` | Claude | **verworfen** (gemessen): ersten sperrt die Wortprüfung, zweiten S06 („Skript nicht gefunden – nicht prüfbar“) |

## Nicht geprüft
- Tests (`tests/test_review_tor.py`) prüfte nur Claude; kein Team.
- Mistral: Bericht nach Nr. 4 abgebrochen, „Nicht geprüft“ fehlt (Zeitlimit).
- Laufzeitverhalten mit echtem `gh pr view`/`gh pr merge` – das prüft der Merge dieses PR selbst (erster Einsatz des Tors).

## Befunde zum Verfahren
- `normen.py review` trägt: Ordner, Filter, „ohne Gruppe“ und Hinweis ab 150 Zeilen wie beschrieben; die erste Gruppe (784
  Zeilen) war zu groß, neu geschnitten in tor/tests/doku.
- **agy liest keine Dateien aus dem Projekt** (Freigabe nur Lauf-Ordner): Abbruch nach 21 s. Material immer in den
  Lauf-Ordner kopieren (`git show <commit>:<pfad>`). Damit ist die offene Frage aus Paket R beantwortet.
- **Zweiter Mistral-Schritt** erstmals gelaufen: `--resume` + `bericht.md` liefert einen Bericht, aber `--time-limit 540` ist
  für 344 Diff-Zeilen plus Dateibereiche zu knapp (beide Schritte `deadline`, nicht `turn_limit`). Für Gruppen dieser Größe
  Zeitlimit 1200 s oder kleinere Gruppen.
- Ohne `--trust` ignoriert Vibe `AGENTS.md` („project configuration will be ignored“) – für Reviews unerheblich, notiert.
- Gemini fand die meisten bestätigten Befunde zum Konzept gegen den Code, Mistral die beiden schwersten Sicherheitslücken.

## Ergebnis
Mergereif: ja

Alle bestätigten Befunde (Nr. 1, 2, 5–10) sind auf dem Branch behoben, jeweils mit Test in `tests/test_review_tor.py`
(135 Prüfungen grün, `make test` grün). Grenzen (Nr. 2 Rest, 7 Rest, Label/`--klein` durch Claude) stehen im
CHANGELOG v17.
