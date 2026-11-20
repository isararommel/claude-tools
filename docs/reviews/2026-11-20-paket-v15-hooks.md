# Review: Branch `paket-v15-hooks` (Normen v15, PR #30) – 2026-11-20

Pilot von Paket R (eigenes Review-Verfahren). Rohausgaben der Teams bleiben im Lauf-Ordner; hier stehen nur geprüfte Ergebnisse.

## Gegenstand
`git diff origin/main...HEAD` nur Quelldateien: `agenten-normen/` (vor allem `projekt/normen/normen.py`), `tests/test_hook_luecken.py`,
`CHANGELOG.md`, `Makefile`, `NEUES-REPOSITORY.md`, `multi-ki/`. Die Kopien (`normen/`, `docs/multi-ki-ablauf.md`) sind per `cmp`
als identisch mit der Quelle belegt und wurden nicht doppelt geprüft. Eine Gruppe (rund 870 Diff-Zeilen); Mistral in drei
Themen geteilt (A Schreibweise, B `python -m`, C G9/Sitzungsprobe/Label).

## Prüfer und Ablauf

| Prüfer | Modell | Ergebnis |
|---|---|---|
| Claude | `/code-review medium` | 8 Befunde |
| mistral-team A, B, C | mistral-large-4-0-3, `--agent ask`, 540 s | alle drei am Zeitlimit **ohne Bericht**; Bericht erst per Fortsetzung (C mit `-c`, A und B mit `--resume <session_id>`, 1 Schritt); B auch dann abgeschnitten |
| gemini-analyst | gemini-3.8-flash-high, Nur-Lesen | Versuch 1 „auto-denied“; Versuch 2 Zeitlimit 9 min, Antwort partiell (2 Befunde) |

Status: **bestätigt** = von Claude am Hook bzw. an Python nachgestellt; **plausibel** = am Code gelesen, nicht nachgestellt;
**Grenze** = bleibt, wird im CHANGELOG genannt; **zurückgestellt** = nicht in v15.

## Befunde

| Nr. | Ort | Befund | Fehlerszenario | Quelle | Status |
|---|---|---|---|---|---|
| 1 | normen.py `_python_m` | `-m MOD` mit im selben Befehl geschriebener `MOD.py` erlaubt | `cd lauf && printf 'import os…' > neu.py && python3 -m neu` → ja (`python3 neu2.py` → nein) | Claude | bestätigt |
| 2 | normen.py `_skript_geschrieben` | Vergleich per `realpath`, Datei aus `_echt` | `> Evil.py && python3 -m evil` (evil.py harmlos vorhanden) → ja, geprüft wird der alte Inhalt | Claude | bestätigt |
| 3 | normen.py `_py_suchordner` | Regression: unauflösbarer PYTHONPATH/`cd` → fragen (vibe: nein) auch für installierte Module | `PYTHONPATH=$PWD/src python3 -m pytest` → nein; `cd "$(mktemp -d)" && python3 -m pytest` → nein (vor v15: ja) | Claude | bestätigt |
| 4 | normen.py `_py_modul_datei` | Eltern-`__init__.py` von `pkg.sub` nicht geprüft | `lauf/pk/__init__.py` mit `os.remove`, `python3 -m pk.sub` → ja | Advisor-Frage | bestätigt |
| 5 | normen.py `_py_modul_datei` | Reihenfolge falsch: Python nimmt Paket `pk/` vor `pk.py` | `pk.py` harmlos, `pk/__main__.py` böse → Hook prüft `pk.py`; Python führt `pk/__main__.py` aus (nachgestellt) | Mistral B | Python-Reihenfolge nachgestellt, Hook-Seite gelesen |
| 6 | normen.py `-c`-Importe | Schatten-Modul im Lauf-Ordner: Positivlisten-Import lädt fremde Datei | `cd lauf && printf … > json.py && python3 -c 'import json'` → ja | Advisor-Frage | bestätigt |
| 7 | normen.py `_python_m` | Code-Starter der Standardbibliothek ungeprüft | `python3 -m timeit "import os; os.remove(…)"` → ja; `-m cProfile <lauf>/x.py` → ja | Gemini | bestätigt |
| 8 | normen.py `_python_m` | Testläufer führen fremde Dateien aus | `cd lauf && python3 -m unittest pruef` → ja; `python3 -m pytest <lauf>/test_x.py` → ja | Advisor-Frage | bestätigt |
| 9 | normen.py `pruefen` (G9) | jeder gelöschte Nicht-Test mit häufigem Stamm (`utils`, `data`, `main`) entschuldigt eine ganze Testlöschung | `tests/test_api.py` + `data.json` löschen, `data` im Test → nur Hinweis, Exit 0 | Claude, Mistral C | plausibel (Code eindeutig) |
| 10 | normen.py `_sitzungsprobe` | Probe fälschbar: ID frei setzbar, `.normen/sitzungsprobe.txt` nicht geschützt | Sitzung ohne Hooks: `echo $CLAUDE_CODE_SESSION_ID >> .normen/sitzungsprobe.txt` → bestanden | Claude, Mistral C | plausibel; Grenze (Beleg gegen Versehen, nicht gegen Täuschung) |
| 11 | CHANGELOG.md v15 | `melden --stufe` unter „Bekannte Grenzen“ statt „Geändert“ | Leser übersieht die Neuerung | Claude, Gemini | bestätigt (CHANGELOG.md:43 steht im Abschnitt „Bekannte Grenzen“, Zeilen 37–45) |
| 12 | normen.py `_bash_schreibt_extern` | Text-Vorprüfung der `lesbar_extern`-Ordner mit Groß-/Kleinschreibung | `touch ~/…/CLAUDE-TOOLS/x` bei `lesbar_extern = ~/…/claude-tools` → nicht erkannt | Mistral A | plausibel |
| 13 | normen.py GESCHUETZT-Vergleiche | Literale `normen/`, `.claude/` mit Groß-/Kleinschreibung gegen Platten-Schreibweise | nur wenn der Ordner auf der Platte anders geschrieben ist (`NORMEN/`) | Mistral A | plausibel, geringe Bedeutung |
| 14 | normen.py `_echt` | `os.listdir`-Fehler → getippte Schreibweise (offen statt geschlossen) | Ordner ohne Leserecht (`chmod 111`) | Mistral A | plausibel, geringe Bedeutung |
| 15 | normen.py `_echt` | NFC/NFD nicht angeglichen | Namen mit Umlauten in zerlegter Form | Mistral A | plausibel, nicht nachgestellt |
| 16 | normen.py `_wie_platte` | Symlinks in `.normen-auftrag` aufgelöst → Fehlalarm in `pruefen --diff` | Auftrag nennt Link `docs/aktuell.md` | Claude | zurückgestellt (selten, sichere Richtung) |
| 17 | normen.py `_echt` | Leistung: `listdir` je Pfadteil | Hook-Zeit gemessen: 142 ms je Aufruf mit drei Schreibzielen (inkl. Prozessstart) | Claude | gemessen, unauffällig (ohne Vergleichswert von main) |
| 18 | normen.py `cmd_melden` | Label-Fallback legt Issue ohne alle Labels an (mit Hinweis) | Label fehlt im Ziel | Mistral C | zurückgestellt (vor v15, sichtbar) |
| 19 | normen.py Optionen `-E`/`-P`/`-I`, `PYTHONHOME` | nicht modelliert | `-E` → nur Fehlalarm; `PYTHONHOME=…` → fremde Standardbibliothek | Mistral B | plausibel; Grenze |
| 20 | normen.py `passt`, `_wie_platte`, `_prompt_wort`, Forschungsdaten-Prüfung im Prompt | Auftrags-Globs mit Platzhaltern und Forschungsdaten-Muster mit Groß-/Kleinschreibung; `_prompt_wort` mit `realpath` statt `_echt` | Globs: `Docs/*.md` sperrt `docs/x.md` (sichere Richtung); Forschungsdaten: Prompt nennt Pfad in anderer Schreibweise → geht an agy (gleiche Klasse wie #74) | Mistral A | plausibel |

Positivtests aus dem Nachstellen (müssen „ja“ bleiben): `python3 -m pytest -q > "$LOG"` → ja. Hinweis: `> out.txt` im Projekt
ohne `.normen-auftrag` ist für Teams wie bisher N06-gesperrt (kein v15-Thema).

## Nicht geprüft
- Gemini: Fragen 2–4 (Testabdeckung, Zusammenhänge, Vollständigkeit der Grenzen) – Antwort abgebrochen.
- Mistral B: Befund 5 zum Projekt-Import (abgeschnitten), Fragen ohne Befund.

## Befunde zum Verfahren (für Paket R)
- **Mistral liest bis zum Zeitlimit und berichtet nicht** (3 von 3 Läufen, je ≈ 500 000 Eingabe-Token in 14–17 Schritten).
  Bericht kommt erst in einer Fortsetzung („jetzt Bericht, keine Werkzeuge“, 1 Schritt). Für Paket R: Zweischritt fest einplanen
  oder Lesebudget (`--max-turns`) knapp setzen und den Bericht in einem zweiten Aufruf holen.
- **`-c` greift bei parallelen Vibe-Läufen im selben Projektordner die falsche Sitzung** („Session is already open“).
  `--resume <session_id>` (aus `out/export.json`) mit `--prompt-file` funktioniert headless.
- **`--agent ask` lehnt Bash-Aufrufe teils ab** („file_system.bash … needs approval“); versucht wurden `cd <projekt> && git diff …`,
  `grep -n …`, `sed -n …`, `wc -l` – welche genau abgelehnt wurden, ist nicht ausgewertet. Vorschlag: Diff als Datei bereitstellen.
- **agy `read_file` verlangt absolute Pfade**; relative Pfade im Prompt führen zu „auto-denied“ (Transkript: „must be an absolute
  path“), danach wurde `grep -n` verweigert. Versuch 2 endete an der 9-min-Grenze mit Teilantwort; ob Auszüge mit Zeilenbereichen
  schneller sind, ist nicht gemessen.
- Ertrag: Claude 8, Mistral (nach Fortsetzung) 14, Gemini 2 Befunde; neu und bestätigt durch die Teams: Nr. 5, 7.
  Die meisten bestätigten Lücken (Nr. 4, 6, 8) kamen aus den Prüffragen des Advisors.

## Ergebnis
Nicht mergereif: Nr. 1–8 sind bestätigte Lücken bzw. eine Regression im neuen `-m`-Code. Korrekturen im Paket V15b (PLAN.md).
