# Changelog

Alle wesentlichen Änderungen an `claude-tools` (Agenten-Normen, Multi-KI-Ablauf und Skripte) werden in dieser Datei dokumentiert.

---

## v19 – Befehlsersetzungen in der S06-Prüfung, Fehlalarme K1/K3/K4 – 2026-11-25

**Aktualisieren nötig:** `python3 normen/normen.py aktualisieren` (nur `normen.py` und `normen.toml`; kein neuer Normtext,
keine Änderung an Hooks oder Einstellungen).

### Behoben (Lücke)
- **Befehle in Ersetzungen und Gruppen werden geprüft (S06):** `$(…)`, Backticks (auch verschachtelt, wie in der Shell
  entschärft), Prozess-Ersetzungen `<(…)`/`>(…)`, zsh `=(…)`, Subshells `( … )` und Befehle hinter `case`-Mustern liefen
  bisher ungeprüft (`echo $(python3 /außen/boese.py)` → erlaubt). Neu zerlegt `_ersetzungen` (Zeichen-Scanner mit eigenem
  Zustand je Ebene: Anführungszeichen, `$'…'`, Escapes, Heredocs, `case`, `$((…))` nur als Arithmetik bei direkt folgendem
  `))`) den **ganzen Befehl** vor der Zerlegung in Teilbefehle und vor dem Entfernen von Text-/Heredoc-Daten; `_s06_text`
  prüft jede Ebene rekursiv mit Basisordner und Zuweisungen von unmittelbar vor dem Teilbefehl (Änderungen innen wirken
  nicht nach außen), ab der vierten Ebene `fragen`. Damit sind auch geprüft: `$(…)` in einer Commit-Nachricht
  (`-m "Text $(…)"`) und im Rumpf eines unzitierten Heredocs (`cat > f <<EOF`), `X=$(agy -p "$(cat P)")` (Prompt-Prüfung G5
  sieht den Originaltext). Zitierte Heredocs bleiben Daten; ein `cat`-Heredoc innerhalb einer Ersetzung ist Daten, solange
  er nicht in eine Pipe weitergibt. Nicht zerlegbar (unbalanciert, offenes Zitat) und Hunderte Ebenen → `fragen`.
  `time ( … )` und `coproc ( … )` gelten als Subshell.
- `_skript_im_befehl` trennt den Text der Ebene (Pipe davor, Heredoc-Rumpf) vom ganzen Befehl („im selben Befehl geschrieben“).

### Behoben (Fehlalarme aus dem Normen-Protokoll)
- **K1:** `R=$(realpath "$RUN")`, `D=$(dirname …)`, `` R=`…` `` galten als Skriptaufruf `…)` („nicht gefunden“) → erlaubt.
- **K3:** `for f in tests/test_*.py; do python3 "$f"; done` → je Wert geprüft statt „unaufgelöste Variable“. Nur wenn die
  Variable allein von dieser Schleife belegt wird, die Wörter schlicht sind (siehe Grenzen), vor der Schleife nur `cd` oder
  Zuweisungen stehen, der Befehl nichts außer `/dev/…` schreibt (der Glob gilt zur Hook-Zeit) und höchstens 50 Werte
  entstehen; sonst wie bisher `fragen`.
- **K4:** Teams: reines Lesen auf `normen.py` (`grep`, `egrep`, `fgrep`, `head`, `tail`, `cat`, `wc`, `ls`, `cd`,
  `sed -n 'N,Mp'`/`'$p'`/`'/Muster/p'`, ohne Präfixe, Umleitungen außer `/dev/null`, Heredocs oder Ersetzungen) löst den
  N10-Rückfall nicht mehr aus (bis v18 Grenze „`grep merge normen/normen.py` sperrt auch“). `rg` (`--pre`), `xargs`, `sh`,
  `awk`, `find`, `sed -i`/`e`/`w` bleiben im Rückfall.
- **K2** (`S=<pfad>; bash "$S/x.sh"`) ließ sich nicht nachstellen; Regressionstests ergänzt.

### Tests
- Neu `tests/test_ersetzung.py` (107 Fälle, vorher 41 von 79 rot; Abnahme vom Orchestrator, Review-Fälle ergänzt); `tests/test_review_tor.py`:
  `grep -n merge normen/normen.py` für Teams jetzt `ja` (K4). Vergleich alter gegen neuen Hook über 1500 echte Befehle:
  nur erwartete Änderungen (geschlossene Lücke, K1).

### Grenzen
- Kommentare erkennt der Zerleger nur bei der Ende-Suche einer Ersetzung oder Subshell (`#` nach Leerraum, `;`, `&`, `|`
  oder Zeilenanfang, nicht nach `\`-Zeilenfortsetzung): eine `)` darin schließt nichts, `$(…)`, Backticks und `<(…)` darin
  werden trotzdem geprüft; das Innere prüft S06 danach als eigene Ebene vollständig. Oben und in case-Zweigen gibt es keinen
  Kommentar-Modus. Ein case-Muster über mehrere Zeilen gilt als nicht zerlegbar (`fragen`).
- Mehr als 12 verschachtelte `$(`/`$((` → `fragen` („zu tief verschachtelt“): eine gescheiterte Arithmetik-Probe durchläuft
  den Inhalt zweimal, die Laufzeit verdoppelt sich je Ebene (gemessen: 16 Ebenen 0,7 s).
- K4 (`_nur_lesen`) nur ohne unzitierte Klammern, `$` oder Backticks (zsh-Glob-Qualifier `*(e:'…':)` führt Code aus).
- Älter als v19, nicht behoben: Funktionsdefinitionen `f() { …; }` und anonyme zsh-Funktionen `() { … }` prüft S06 nicht
  als Befehle; Schreiben eines Teams
  innerhalb von `"$(…)"` (Umleitung in Anführungszeichen) sieht die N06-Auftragsprüfung nicht (`pruefen --diff` nach dem Lauf
  findet Änderungen im Projekt).
- Schreiben über `tar -x`, `git checkout`, `curl -o`, `unzip` u. Ä. sieht die Prüfung „im selben Befehl geschrieben“ nicht
  (älter als v19). K3 gilt deshalb nur auf oberster Ebene und nur, wenn vor der Schleife lediglich `cd` oder Zuweisungen
  stehen; Wortlisten nur aus schlichten Wörtern (keine Shell-Klammerausdrücke `[…]`, kein `**`, keine zsh-Muster), Werte
  ohne Leerraum oder Glob-Zeichen.
- Arithmetik `$((…))` wird als Ersetzung herausgelöst und ihr Inhalt wie ein Befehl geprüft (nur Fehlalarm-Richtung).
- Array-Zuweisung `a=(…)` innerhalb von `$(…)` beendet die Ersetzung zu früh; der Rest wird außen geprüft (sichere Richtung).
- Älter als v19, nicht behoben: Der Hook braucht bei manchen sehr langen Befehlen über 60 s; ein überlanges Wort führt zu
  `OSError: File name too long` in der N03-Prüfung (Hook sperrt, fail-closed).

## Multi-KI: Coding-Team neu (Paket KT, ohne neue Normen-Version) – 2026-11-24

**Aktualisieren nötig:** `multi-ki/benutzer/agents/mistral-team.md` nach `~/.claude/agents/` kopieren (vorher sichern;
`einrichten.sh --benutzer-agents` überschreibt vorhandene Agenten nicht), danach Claude-Sitzung neu starten – erst dann
nutzt die Schnittstelle die neuen `--model`-Regeln. Vorlagen `docs/review-bericht.md`/`recherche-bericht.md` per
`multi-ki/einrichten.sh` (kommen als `.vorlage`). Vibe-Einstellungen (`~/.vibe`, je Rechner, Sicherungen `*.bak-2026-11-24`):
`active_model = "glm-5-3"`, Sub-Agent `code-worker` → `glm-5-3`, `code-reviewer` → `mistral-large-4-0-3`.

- **Geändert:** Umsetzung läuft mit GLM-5.3, Reviews mit Mistral Large 4 – beide ausdrücklich per `--model` im Aufruf
  (`mistral-team.md`, `multi-ki-ablauf.md`; Übersicht in `LIES-MICH.md`), nie dasselbe Modell für Code und Review. Mistral Medium 3.5
  entfällt. Der Hauptagent arbeitet selbst (in 16 Läufen vom 22.–24.11. hatte Vibe nie einen Sub-Agenten aufgerufen).
- **Modellprüfung:** das tatsächlich genutzte Modell steht in `out/session/meta.json` (`config.model_name`);
  `export.json → routed_model_config` zeigt nur die Voreinstellung.
- **Bericht der Schnittstelle:** jede Hook-/Smart-Approve-Sperre wörtlich und ob Vibe danach denselben Zweck auf anderem Weg
  versucht hat.
- **Grundlage:** öffentliche Benchmarks auf gemeinsamem Gerüst (Rangfolge GLM-5.3 > Large 4 > Medium 3.5) und ein
  Probelauf mit derselben Aufgabe (n = 1): beide Ergebnisse fachlich gleichwertig, GLM-5.3 läuft als schreibendes Modell
  zuverlässig; in 16 früheren Läufen rief Vibe nie einen Sub-Agenten auf. Einzelheiten: `PLAN.md`, Paket KT.

---

## v18 – Normen-Protokoll, Forschungsdaten in Mistral-Reviews, `lesbar_extern` je Teilbefehl – 2026-11-24

**Aktualisieren nötig:** `python3 normen/normen.py aktualisieren` (normen.py, normen.toml, `.claude/settings.json` mit neuen
Hooks). Vorlage `docs/review-auftrag.md` per `multi-ki/einrichten.sh` (kommt als `.vorlage`); in der eigenen `CLAUDE.md` die
Datenschutzzeile zu Forschungsdaten von Hand anpassen (siehe unten).

### Neu
- **Normen-Protokoll:** Der PreToolUse-Hook schreibt jede Entscheidung `fragen`/`nein` (aller Rollen, ohne Selbsttest-Köder)
  als JSON-Zeile nach `~/.config/claude-tools/normen-protokoll.jsonl` (zentral für alle Projekte, außerhalb aller Repos,
  Rechte 600; Umgebungsvariable `NORMEN_PROTOKOLL` lenkt um – `make test` in claude-tools setzt sie auf ein Testprotokoll).
  Felder: Zeit, Projekt, Rolle, Werkzeug, Tool, Stufe (vor der Herabstufung für Teams) und Entscheidung, Norm-IDs, Gründe,
  Bash-Befehl bzw. nur Pfad (Edit/Write) bzw. nur Tool-Name (`mcp__*`), `session_id`, `tool_use_id`, `permission_mode`.
  Vor dem Schreiben geschwärzt (N03-Inhaltsmuster, Token-Muster, E-Mail, IBAN, Telefon, gesperrte Pfade → `[geschwärzt]`),
  danach auf 300 Zeichen gekürzt. Ein Schreibfehler ändert die Hook-Entscheidung nie (Meldung auf stderr); ohne geladene
  Konfiguration entsteht kein Eintrag (kein Schwärzen möglich).
- **`normen.py hook-nach --werkzeug claude`** (Hooks PostToolUse und PostToolUseFailure, Matcher wie PreToolUse): trägt zu
  einem `fragen`-Eintrag den Ausgang `ausgefuehrt`/`fehlgeschlagen` nach (gleiche `tool_use_id`, nur die letzten 200 Zeilen
  bzw. 64 KiB der Datei). Immer Exit 0, keine Ausgabe.
- **`normen.py protokoll [--alle] [--seit JJJJ-MM-TT] [--gelesen]`:** Auswertung seit der letzten Marke – je Norm und Projekt
  `fragen` (ausgeführt / fehlgeschlagen / kein Beleg) und `nein`, häufigste Gründe, Beispiele. `--gelesen` setzt die Marke
  (`normen-protokoll.marke` neben dem Protokoll).
- **Regelmäßiger Hinweis:** SessionStart-Hook (Matcher `startup|clear`) ruft `protokoll --faellig` auf: eine Zeile mit Anzahl
  und Datum, wenn seit der Marke ≥ 7 Tage vergangen und ≥ 1 neuer Eintrag da ist, oder ≥ 30 neue Einträge. Ausgewertet wird in
  claude-tools durch Claude selbst (nie an `gemini-analyst`, nie ins Repository, nie als Issue); Kandidaten neutralisiert in
  `PLAN.md`.
- **Teams lesen das Protokoll nicht:** Für Rollen mit Auftragspflicht (mistral-team, gemini-analyst) sperrt der Hook jeden
  Befehl bzw. Pfad, der den Ordner des Protokolls nennt (`~/.config/claude-tools/`, auch als `$HOME/…`), mit N03.
- **`einrichten-hier.sh`:** einzelnes Skript zum Kopieren in ein neues Projekt; richtet den Ordner ein, in dem es liegt
  (ruft `einrichten.sh` aus `$CLAUDE_TOOLS` bzw. `~/Documents/Projekte/claude-tools` auf, fragt ohne `--test` nach Testbefehl
  und Sperrpfaden, bietet `git init` an).

### Geändert
- **`normen.py review`: Forschungsdaten nur noch aus dem Gemini-Diff** (Entscheidung der Inhaberin 23.11.). Sperrpfade und
  Geheimnisse bleiben für beide Teams gefiltert; der strengste Grund gewinnt, auch über Umbenennungspaare und den Blob-Abgleich
  (Paar Sperrpfad → Forschungspfad fällt für beide heraus). Ausgabe `gefiltert (gemini): …` bzw. `gefiltert (mistral, gemini): …`.
  Im Prompt an vibe fragt der Hook bei Forschungsdaten weiter nach (unverändert).
- **`[pfade].lesbar_extern` je Teilbefehl statt ganzer Kette:** `cp <ext>/datei docs/` und
  `git branch --show-current && ls <ext>/` sperren nicht mehr. Weiter gesperrt: Schreibziel im Ordner (aufgelöst), Glieder mit
  Schreibverb, die den Ordner nennen, alle Glieder nach `cd`/`pushd` dorthin und hinter einer Pipe aus einem solchen Glied,
  unaufgelöste Ziele, `mv` aus dem Ordner (löscht die Quelle), `ln` und `cp -l`/`-s` (Link in den Ordner),
  `rsync --remove-source-files`; Ketten mit Schleifen, Bedingungen, `xargs`, `eval`, `exec`, `source` oder einer Zuweisung,
  die den Ordner nennt (`D=<ext>; git -C $D …`), werden wie bisher als Ganzes geprüft. Neu erkannt: `dd` und git-Optionen
  mit `=` (`git --git-dir=<ext>/.git add`).
- **Schwärzen gesperrter Pfade:** das ganze Pfadwort, nicht nur das Präfix (`geheim/kunde.txt` → `[geschwärzt]`).

### Grenzen
- Gemessen (23.11., interaktiv): ein Hook-`ask` erreicht die Inhaberin auch im Auto-Modus; nach Freigabe folgt PostToolUse mit
  gleicher `tool_use_id`. **Ungemessen:** Ablehnung – erwartet kein Post-Ereignis, die Auswertung zeigt dann „kein Beleg“
  (abgelehnt, abgebrochen oder Sitzung beendet; „abgelehnt“ wird nicht behauptet).
- Ein `fragen`-Eintrag, auf den mehr als 200 Protokollzeilen oder mehr als 64 KiB folgen, bevor das Werkzeug fertig ist,
  bekommt keinen Ausgang.
- Geschwärzt wird nur, was ein Muster trifft (Token-Formen, `token = "…"`, E-Mail, IBAN, Telefon, gesperrte Pfade); ein
  Passwort in anderer Form (z. B. `-pGeheim`) bleibt sichtbar. Das Protokoll ist deshalb privat (Rechte 600, außerhalb der Repos).
- Keine Rotation des Protokolls.

---

## v17 – Review-Tor beim Merge, `normen.py review`, normen.py für Teams gesperrt – 2026-11-23

**Aktualisieren nötig:** `python3 normen/normen.py aktualisieren` (normen.py, normen.toml); in `normen/projekt.toml` den neuen
Abschnitt `[review]` aus der Vorlage übernehmen (fehlt er, gelten die Vorgaben: Code-Endungen wie unten, keine kritischen
Stellen, keine Versionsdateien). Vorlagen `docs/review-auftrag.md`, `docs/review-bericht.md` und `docs/multi-ki-ablauf.md` per
`multi-ki/einrichten.sh` (kommen als `.vorlage`). Je Repository einmal das Label anlegen:
`gh label create meilenstein --description "Großer Meilenstein: Review-Bericht nötig (N11)"` – sonst läuft der Hinweis des
Halts ins Leere.

### Neu
- **Review-Tor in `normen.py merge` (N11):** Große Meilensteine – PR-Label `meilenstein` oder neue `[meta].version` in einer
  Datei aus `[review].versionsdateien` – mergen nur, wenn der PR `docs/reviews/<JJJJ-MM-TT>-<branch>.md` hinzufügt oder ändert
  (jedes Zeichen außer `[A-Za-z0-9._-]` im Branch → `-`, Name exakt) und der Bericht genau eine Zeile `Mergereif: ja` hat. Versionsdatei an der Basis fehlend
  oder unlesbar zählt als neue Version.
- **Halt mit Begründungspflicht:** ab 150 Code-Zeilen (hinzugefügt + gelöscht in Dateien aus `[review].code`, Vorgabe
  `*.py, *.sh, *.js, *.ts, Makefile, *.json`; Tests aus `[pfade].tests` und eingespielte Kopien `normen/normen.py`,
  `normen/*.toml` außer `projekt.toml`, `.claude/settings.json`, `.vibe/`, `.githooks/` zählen nicht) oder bei jeder Änderung an
  `[review].kritisch` hält `merge` an. Weiter mit Label oder `normen.py merge <PR> --klein "<Grund>"` (Grund im Merge-Commit;
  ohne Grund Fehler, vor jedem Netzaufruf).
- **`normen.py review [--basis] [--gruppe NAME=GLOB,…]`:** bereitet Review-Läufe vor (Ordner je Gruppe und Team, `diff.patch`,
  `pflicht.txt`, bei Mistral `bericht.md`), startet keine Teams. Filtert aus jedem Diff `[pfade].gesperrt`, Geheimnis-Muster
  und Forschungsdaten (Pfad-Globs und Textmarker im Diff-Inhalt, ohne Groß-/Kleinschreibung); bei Umbenennungen und Kopien
  fallen beide Pfade heraus, wenn eine Seite gefiltert ist. Dateien mit Schlüsseln/Tokens im Diff-Inhalt (dieselben Muster wie
  die Prompt-Prüfung des Hooks) fallen ebenfalls heraus. `[pruefen].ausschliessen` gilt hier bewusst nicht. `bericht.md`
  enthält den Text für den zweiten Mistral-Schritt. Das Label zählt ohne Groß-/Kleinschreibung.
- Vorlage `review-bericht.md`: Abschnitt „Ergebnis“ mit `Mergereif: <ja|nein>`.

### Geändert
- **Teams rufen von `normen.py` nur `pruefen` und `kurz` auf (Hook):** Vorher ließ der Hook für mistral-team, gemini-analyst und
  lokal jeden Unterbefehl zu – auch `auftrag --dateien '**'`, das die eigene Auftragsliste samt Siegel erweiterte, und
  `auftrag --ende`, `merge`, `aktualisieren`, `melden`. Geprüft wird dort, wo S06 den Aufruf ohnehin auflöst
  (`python3 <skript>` samt Variablen, `python3 -m normen.normen`, `./normen/normen.py`): Skript `normen.py` → Unterbefehl muss
  lesbar sein und `pruefen` oder `kurz` heißen. Rückfall für Formen, die der Hook nicht zerlegt (Subshell, `case`, `xargs`,
  `$(…)`, `exec`): Steht `normen.py` als Pfadwort im Befehl, sperrt jedes Wort, das ein anderer Unterbefehl ist. Tests mit
  „normen“ im Namen (`test_normen.py`) bleiben frei.
- `review` steht in der Liste der in Code-Mode-Skripten verbotenen Unterbefehle.

### Bekannte Grenzen
- Das Label `meilenstein` vergibt und entfernt Claude selbst; `--klein` begründet Claude selbst. Das Tor schützt gegen Vergessen,
  nicht gegen Absicht.
- Das Tor liest `[review]` aus dem Stand, der gemergt wird: Eine Änderung an `normen/projekt.toml` kann die eigene Prüfung
  abschwächen. Deshalb steht `normen/projekt.toml` hier unter `kritisch` (Halt, sichtbar).
- Die Sperre für Teams erkennt normen.py am Dateinamen. Nicht erkannt: eine Kopie unter anderem Namen im Projekt (nur mit
  passendem `.normen-auftrag` schreibbar), ein Projektskript, das `normen` importiert, und ein zusammengesetzter Unterbefehl
  in einer Form, die der Hook nicht zerlegt. Kopien außerhalb des Projekts prüft S06 vor dem Lauf per AST. Rückhalt bleibt
  Claudes Vergleich von `git status`/Diff nach jedem Lauf. Preis der Wortprüfung: Ein Team darf `normen.py` nicht mit einem
  Unterbefehl als Suchwort durchsuchen (`grep merge normen/normen.py` → nein; Lesewerkzeug geht).
- `review` sucht Textmarker und Geheimnis-Muster im Diff **und** im ganzen Stand der Datei bei HEAD (Dateistände gehen als
  Kopie an agy). Folge: Testdateien mit Köder-Tokens fallen aus dem Review-Diff; die Ausgabe nennt sie unter „gefiltert“.
- `review` erkennt Kopien und Umbenennungen aus Sperr-/Forschungspfaden ab 30 % Ähnlichkeit (`-M30% -C30%
  --find-copies-harder -l0`) und Dateien mit gleichem Inhalt (Blob) wie eine gefilterte Datei, auch wenn beide neu im
  Branch sind. Ganz neu geschriebener oder teilweise kopierter Inhalt aus solchen Dateien unter neuem Pfad fällt nur über
  Textmarker heraus.
- Geheimnisse im Inhalt erkennt `review` nur an festen Mustern (private Schlüssel, GitHub-, AWS-, Slack-, Google-Tokens,
  `sk-…`); ein Passwort in Klartext ohne solches Muster gelangt in den Diff. Es ist kein vollständiger Geheimnis-Scanner.
- Mehrere passende Berichte im PR: Es gilt der neueste (Datum im Namen); ein früherer „nein“ vor der Nachbesserung ist
  der übliche Verlauf.

---

## Review-Aufträge (Multi-KI, kein neuer Normtext) – 2026-11-22

**Aktualisieren nötig:** nur für Reviews – `multi-ki/einrichten.sh <projekt> --test "<testbefehl>"` legt die neuen Vorlagen an
(vorhandene Dateien bleiben; `docs/multi-ki-ablauf.md` kommt als `.vorlage` und wird von Hand zusammengeführt);
Agent-Definitionen aus `multi-ki/benutzer/agents/` nach `~/.claude/agents/` kopieren (Rückfrage).

### Neu
- **Eigenes Review-Verfahren vor dem Merge von Meilensteinen** (ersetzt `/code-review ultra`, Größenlimit): Claude
  (`/code-review`), `mistral-team` und `gemini-analyst` prüfen denselben Branch-Diff in Gruppen; Claude prüft jeden Befund
  selbst und legt den Bericht unter `docs/reviews/<datum>-<branch>.md` ab. Vorlagen `docs/review-auftrag.md` (einheitliches
  Befundformat mit Fehlerszenario und Beleg, „Bericht vor Vollständigkeit“, zweiter Schritt für Mistral) und
  `docs/review-bericht.md` (Status bestätigt/plausibel/verworfen/Grenze/zurückgestellt). Ablauf: `docs/multi-ki-ablauf.md`,
  Abschnitt „Review“. Pflicht nur bei Meilensteinen, als Ablauf – kein Prüftor in `normen.py merge`.

### Geändert
- **Vibe-Fortsetzung mit `--resume <session_id>`** statt `-c` (Abschnitt 7, `mistral-team.md`): `-c` greift bei parallelen
  Läufen im selben Projekt die falsche Sitzung.
- **Vibe-Lese-Modus mit `--add-dir <lauf-ordner>`:** ohne die Option lehnt `--agent ask` `read_file` außerhalb des Projekts ab
  (gemessen 22.11.: 12 Runden ohne Bericht; mit `--add-dir`: 4 Schritte, Bericht im Format).
- `gemini-analyst.md`: Bei Review-Aufträgen liegt das Material im eigenen Lauf-Ordner; eine Ebene höher endet agy sofort
  mit „auto-denied“.

### Bekannte Grenzen
- Gemessen an einer Gruppe (141 Diff-Zeilen) aus dem Pilot. Wie groß eine Gruppe höchstens sein darf und ob der zweite
  Schritt bei Mistral trägt, ist nicht gemessen. Ein Lauf mit `--smart-approve` hing im Modellaufruf, die Ursache ist offen.
- Gemessen nur mit Kopien der Dateien im Lauf-Ordner. Der Normalfall der Vorlage (Dateien aus dem ausgecheckten Projekt) ist
  für agy in diesem Format nicht belegt.

---

## v16 – Schreibweise von Pfaden, `python -m`, Sitzungsprobe, Testlöschung samt Altcode – 2026-11-22

Entstanden als „v15“ auf dem Branch `paket-v15-hooks` (20.11.); nach dem Hotfix v15 (vertraute Werkzeuge) auf main
zusammengeführt und zu v16 umbenannt.

**Aktualisieren nötig:** ja – `python3 normen/normen.py aktualisieren` (bzw. `einrichten.sh`), danach die Claude-Sitzung
im Projekt-Stammverzeichnis erneut starten, `touch .normen/normen-koeder.txt` (muss gesperrt werden) und
`python3 normen/normen.py selbsttest --sitzung`.

### Sicherheit
- **Groß-/Kleinschreibung von Pfaden (Rückmeldung „N06 sperrt absoluten Pfad“):** macOS unterscheidet sie im Dateisystem
  nicht, der Hook schon. Dadurch gingen `.Claude/settings.json`, `NORMEN/normen.toml`, `.ENV` und Sperrpfade in anderer
  Schreibweise (`Daten/Geheim/…`) an den Sperrlisten vorbei. Ein absoluter Pfad mit anderer Schreibweise des
  Projektordners wurde dagegen fälschlich als „außerhalb“ gesperrt. Pfade werden jetzt auf die Schreibweise auf der Platte
  gebracht (`_echt`). Geheimnis-Muster und Sperrpfade werden ohne Groß-/Kleinschreibung verglichen, auch wenn die Schreibweise
  in `projekt.toml` von der Platte abweicht. Auftragseinträge ohne Platzhalter (`Modul.py`) werden auf die Schreibweise
  der Platte gebracht.
- **`python -m MODUL` (Rückmeldung „Vibe umgeht S06 per python -m“):** Das Modul wird wie bei Python aufgelöst (Basisordner,
  dann PYTHONPATH aus Präfix, Zuweisung, `export` oder Umgebung; `mod.py`, `pkg/__main__.py`). Liegt es außerhalb des
  Projekts, wird es per AST geprüft wie `python3 <datei>.py`. Installierte Module (`pytest`, `venv`, `pip`) bleiben erlaubt.
  Unaufgelöster PYTHONPATH → fragen.
- **Ein Modul-Auflöser für `-m` und Importe (Review-Befunde Nr. 1–8, `docs/reviews/2026-11-20-paket-v15-hooks.md`):**
  Suchreihenfolge wie Python (`FileFinder`; gegen den Interpreter getestet): Paket `mod/__init__.py` vor `mod.py`,
  Namespace-Ordner zuletzt, bei `a.b` alle `__init__.py` auf dem Weg, bei `-m` eines Pakets dazu `__main__.py`; jede
  ausgeführte Datei außerhalb von Projekt/`lesbar_extern` wird geprüft.
  - **Schatten-Module:** Löst ein Import einer Positivlisten-Bibliothek (`import json`) in `-c`, in per AST geprüften
    `-m`-Dateien oder in `python3 <datei>.py` (Skriptordner) auf eine Datei außerhalb von Projekt/`lesbar_extern` auf → fragen.
    Bewusst strenger als der Plan (dort: AST-Prüfung der Schatten-Datei).
  - **Geschriebene Module:** Wird im selben Befehl in einem Suchordner außerhalb des Projekts eine importierbare Datei
    (`.py`, `.so`, `.pyc` …) oder etwas im Paketordner geschrieben → fragen (auch in anderer Schreibweise: `> Evil.py`),
    bei `-m`, `-c` und `python3 <datei>.py` (Skriptordner).
    `> pytest.log` bleibt erlaubt.
  - **Andere Importformen** außerhalb des Projekts (`.so`/`.pyc` statt `.py`, zip/pyz im PYTHONPATH) → fragen.
  - **Code-Starter** `-m timeit|cProfile|profile|trace|pdb|runpy` → fragen.
  - **`$PWD`** gilt als Basisordner an der jeweiligen Stelle des Befehls (nach `cd`), in der Skriptprüfung, bei `cd` und bei
    Schreibzielen; vorher kam er aus der Umgebung des Hooks. `$OLDPWD` bleibt unaufgelöst. Behebt die Regression
    `PYTHONPATH=$PWD/src python3 -m pytest` → fragen (jetzt ja). Ein `cd` mit unaufgelöster Variable macht relative
    Schreibziele unbekannt (strenger).
- **Vertraute Werkzeuge nur für Claude (Entscheidung der Inhaberin 22.11.):** Ein Aufruf eines Werkzeugs aus
  `[werkzeuge].vertraut` ergibt für jede andere Rolle „nein“, auch im eigenen Projekt und unter `lesbar_extern` (vorher
  für Teams ungeprüft). `python3 -m <werkzeug>` und `python3 -c 'import <werkzeug>'` → nein für alle Rollen (nur direkt
  aufrufen). Pfadvergleich in der Schreibweise der Platte (`./WP.py` = `wp.py`). Folge: Im Projekt, dem das Werkzeug
  gehört, kann mistral-team es beim Entwickeln nicht mehr direkt starten.
  S06-Normtext ergänzt: „…, auch nicht per `python3 -m` oder Import. Die Freigabe gilt nur dir: Teams rufen vertraute
  Werkzeuge nie auf, Aufträge an Teams nennen sie nicht.“ (Der agy-Weg hat keinen Hook; dort gilt nur die Anweisung.)
- **`python3 -c` mit Import bei unbekanntem Suchpfad** (unaufgelöster PYTHONPATH, `cd "$(mktemp -d)"`) → fragen wie bei
  `-m`, weil die Schatten-Prüfung sonst entfiele. `python3 -c` ohne Import bleibt erlaubt.
- **`lesbar_extern` in anderer Schreibweise (Review Nr. 12):** `touch ~/…/CLAUDE-TOOLS/x` bei `lesbar_extern =
  ["~/…/claude-tools"]` wurde nicht als Schreiben in den Ordner erkannt. Aufgelöste Schreibziele werden jetzt immer in der
  Schreibweise der Platte verglichen, die Textsuche nach dem Ordner ohne Groß-/Kleinschreibung.
- **Forschungsdaten im Prompt (Review Nr. 20):** Ein Prompt an agy, der `Daten/Roh/p1.csv` oder den Projektpfad in anderer
  Schreibweise nennt, ging an `forschungsdaten = ["daten/roh/**"]` vorbei. Der Vergleich ist jetzt ohne
  Groß-/Kleinschreibung, absolute Pfade in der Schreibweise der Platte.
- **Sitzungsprobe geschützt (Review Nr. 10):** `.normen/sitzungsprobe.txt` gehört zu den geschützten Pfaden (Schreiben:
  Claude fragt, Teams nein). `selbsttest --sitzung` mit `--werkzeug`/`--weg` → Fehler (Exit 64) statt stiller Sitzungsprobe.

### Geändert
- **Projekt-Importe in `python3 -c`:** Ein Import, der (Suchreihenfolge wie Python) auf eine Datei im Projekt auflöst, gilt wie
  `python3 projektdatei.py` und wird nicht mehr als „nicht in der Positivliste“ gesperrt. Ein gleichnamiges Modul im
  Lauf-Ordner wird weiterhin gesperrt.
- **Pflichtsatz in `normen.py auftrag`:** „Sperrt ein Normen-Hook einen Aufruf: denselben Zweck nicht auf anderem Weg
  erreichen, sondern anhalten und die Sperrmeldung wörtlich im Bericht nennen.“
- **G9/N02 (Rückmeldung „N02 sperrt Löschen von Tests samt Altcode“):** Eine ganz gelöschte Testdatei ergibt einen Hinweis
  statt Fehlern, wenn derselbe Diff eine Nicht-Testdatei löscht, deren Dateistamm als ganzes Wort in einer **Importzeile**
  der Testdatei steht (`import`/`from`/`@testable import`/`#include` am Zeilenanfang, `require(`) – N08: Altcode samt Tests
  entfernen. Der Hinweis nennt beide Dateien. Kein Beleg: `__init__`, Daten-/Doku-Dateien (`.json .toml .yaml .yml .txt .md
  .csv`), Dateien unter `[pruefen].ausschliessen`, der Stamm nur im Kommentar oder Text (Review Nr. 9).
  Offen: Der Stop-Hook wiederholt bekannte Befunde.
- **`cd "$D"` mit bekannter Zuweisung:** `D=/x; cd "$D" && python3 -c 'import json'` kennt jetzt den Basisordner (vorher
  unbekannt → fragen). Gilt nur für Zuweisungen, die sicher laufen: eigener Teilbefehl am Anfang oder nach `;`/Zeilenumbruch,
  nicht in Pipeline oder Hintergrund, Wert nur aus ebenso sicheren Zuweisungen; im Befehl keine Steuerstrukturen, Subshells,
  Backticks, Heredocs und nichts, was Variablen ohne `NAME=` ändert (`unset`, `eval`, `source`/`.`, `read`, `printf -v` …).
  `D=/x cd "$D"`, `false && D=/x; cd "$D"`, `false && X=/x; D=$X; cd "$D"`, `(D=/x); cd "$D"` bleiben unbekannt (fragen),
  gegen die Shell gemessen.
- **`melden --stufe`** setzt zusätzlich das Label `stufe:<stufe>`. Fehlen Labels im Ziel, wird das Issue ohne Labels angelegt,
  und die Meldung nennt die fehlenden Labels.

### Bekannte Grenzen
- `python -m`: Geprüft wird nur, was im selben Befehl steht. Ein `cd` oder `export PYTHONPATH` aus einem früheren
  Werkzeugaufruf sieht der Hook nicht. Unbekannter Basisordner (`cd "$(mktemp -d)" && python3 -m pytest`) → fragen.
  Testläufer mit Ziel außerhalb des Projekts (`python3 -m unittest <modul>`, `python3 -m pytest <lauf>/test_x.py`) führen
  fremden Code aus, den der Hook nicht prüft; die Liste der Code-Starter ist nie vollständig. Nicht modelliert: Optionen
  `-E`/`-I`/`-P`, `PYTHONHOME`, `.pth`-Dateien, Bytecode in `__pycache__`, Schatten-Module über den PYTHONPATH bei
  `python3 <datei>.py` (geprüft wird nur der Skriptordner), geschriebene Module bei unbekanntem Basisordner.
  **Transitive Schatten** (gemessen 22.11.): Aufgelöst werden nur Importe, die im geprüften Code stehen. `import json`
  lädt intern `_json`, `import datetime` lädt `_datetime`; liegt `_json.py` bzw. `_datetime.py` im Skriptordner oder
  Suchpfad, führt Python sie aus, ohne dass der Hook sie prüft.
  `python3 -c` innerhalb einer Subshell `( … )` ist nicht zerlegbar → nein (Fehlalarm in der sicheren Richtung).
  **`cd`, das nicht wirkt** (gemessen 22.11., älter als v16): Der Basisordner folgt jedem `cd`, auch wenn die Shell es
  nicht ausführt oder es scheitert (`false && cd <p>`, `cd <p> | true`, `cd /gibt/es/nicht`). Danach prüft der Hook im
  falschen Ordner, ein Schatten-Modul im wirklichen Ordner bleibt unerkannt.
- G9: Mehrzeilige Importe (`from x import (\n utils)`) belegen nicht → Fehler „Assert entfernt“ (sichere Richtung).
  Ein Import mit häufigem Stamm (`import utils`) belegt weiter nur schwach, deshalb Hinweis zum Review statt stiller Freigabe.
- Sitzungsprobe: Beleg gegen Versehen (Sitzung ohne Hooks), nicht gegen Täuschung – wer Hooks umgeht, kann auch die Probe
  fälschen (Review Nr. 10).
- Schreibweise (Review Nr. 13–15): Feste Namen in den geschützten Pfaden (`normen/`, `.claude/`) gelten in der Schreibweise
  der Vorlage – nur relevant, wenn der Ordner auf der Platte anders heißt; `_echt` übernimmt bei Ordnern ohne Leserecht die
  getippte Schreibweise; Unicode-Normalform (NFC/NFD) wird nicht angeglichen. Auftrags-Globs mit Platzhaltern
  (`Docs/*.md`) bleiben schreibweisengenau (sichere Richtung: Fehlalarm).

### Neu
- **Sitzungsprobe (Rückmeldung „Hooks inaktiv, wenn die Sitzung nicht im Projekt-Stammverzeichnis läuft“):** Der Claude-Hook
  schreibt beim Köder die `session_id` nach `.normen/sitzungsprobe.txt`. `selbsttest --sitzung` verlangt einen Eintrag mit
  der eigenen `CLAUDE_CODE_SESSION_ID`, also einen positiven Beleg. „Köderdatei fehlt“ reicht nicht, weil `touch` außerhalb
  des Projekts schon am fehlenden Ordner scheitert. Der normale Selbsttest sagt jetzt dazu, dass er neu gestartete Läufe
  prüft und nicht die laufende Sitzung. `einrichten.sh` und `NEUES-REPOSITORY.md` (Schritt 7) verlangen, die Sitzung im
  Projekt erneut zu starten.

---

## v15 – Vertraute Werkzeuge im S06-Hook, Befehle über Variablen – 2026-11-21

**Aktualisieren nötig:** ja – `python3 normen/normen.py aktualisieren`. Wer ein Werkzeug freigeben will, trägt es
(nach Zustimmung der Inhaberin) in die eigene `normen/projekt.toml` ein; die Datei gehört dem Projekt und wird nicht ersetzt:

    [werkzeuge]
    vertraut = [{pfad = "~/Projekte/mein-werkzeug/bin/werkzeug", unterbefehle = ["status", "holen"]}]

### Neu
- **`[werkzeuge].vertraut` (Rückmeldung „S06 sperrt freigegebenes Werkzeug“):** Ein gepflegtes Werkzeug außerhalb des
  Projekts, das wie ein Wegwerf-Skript per AST geprüft und deshalb immer gesperrt wurde (Netz, Schlüsselbund, `os.replace`),
  wird für die Rolle claude als Befehl bewertet: direkter Aufruf (Pfad, auch relativ nach `cd`, Variable oder Name aus `$PATH`)
  mit einem freigegebenen Unterbefehl (erstes Wort, wörtlich) → erlaubt; jeder andere, fehlende, als Option (`-…`) oder über
  Variable angegebene Unterbefehl → nein, auch unter `lesbar_extern`. Übrige Teilbefehle und Schreibziele werden weiter geprüft;
  wird das Werkzeug im selben Befehl geschrieben → fragen. `python3|bash|source <werkzeug>` → nein (nur direkt aufrufen).
  Andere Rollen: wie bisher.
  Fehlerhafter Eintrag → der Hook sperrt mit Meldung. S06-Normtext um einen Satz ergänzt.

### Geändert
- **Befehl über Variable (`B=/x/werkzeug; $B …`):** Das Befehlswort wird aufgelöst (Zuweisungen davor, dann Umgebung) und
  wie geschrieben geprüft; vorher ging ein Aufruf ohne `/` im Befehlswort ungeprüft durch. Nicht auflösbar oder mehrfach
  zugewiesen → fragen (Verschärfung für alle Projekte).

### Grenzen
- Das „nein“ schützt vor Versehen, nicht vor Absicht. Nicht erkannt (gemessen 21.11., galt schon vorher für jedes Skript
  außerhalb des Projekts): Befehlsersetzung in Anführungszeichen (`echo "$(werkzeug …)"`), `exec werkzeug …`,
  `xargs werkzeug …`, Alias, Shell-Funktion, `eval`. Ein Name ohne Pfad wird über den `PATH` des Hooks aufgelöst, nicht den
  der Shell (`PATH=…:$PATH werkzeug` im selben Befehl wird nicht erkannt).
- Heredoc-Rümpfe, die keine reinen Daten sind (`cat <<EOF` ohne Umleitung), werden weiter zeilenweise geprüft: eine Zeile, die mit
  einer unbekannten `$NAME` beginnt, ergibt dort jetzt „fragen“ (`cat > datei <<EOF` und Text in `"$(cat <<EOF …)"` nicht).

---

## v14 – Selbsttest über Datei-Werkzeuge, `auftrag --dateien` mit Leerzeichen – 2026-11-18

**Aktualisieren nötig:** ja – `python3 normen/normen.py aktualisieren` (bzw. `einrichten.sh`), danach
`python3 normen/normen.py selbsttest`. `multi-ki/benutzer/agents/mistral-team.md` nach `~/.claude/agents/` kopieren
(Rückfrage); `docs/multi-ki-ablauf.md` kommt als `.vorlage` (Abschnitt Selbsttest, Grenzen).

### Neu
- **Datei-Köder im Hook:** Schreiben auf `.normen/normen-koeder.txt` über ein Datei-Werkzeug (Claude Write/Edit,
  Vibe `write_file`/`edit`/`search_replace`, Gemini) ist für alle Rollen gesperrt (Marke `SELBSTTEST-KOEDER`), gleich in
  welcher Schreibweise des Pfads. Lesen bleibt erlaubt.
- **Selbsttest je Weg:** claude `bash`/`write`, vibe `bash`/`write_file`/`edit` – jeder Vibe-Hook hängt an einem eigenen
  Werkzeugnamen, ein Bash-Köder belegt die anderen nicht (Befund 17.11.: ohne `edit`-Eintrag änderte Vibe eine Datei).
  Für `edit` liegt der Köder vorher mit bekanntem Inhalt bereit; „NICHT GESPERRT“ heißt dort: Inhalt geändert (5 Runden statt 3).
  Ausgabe `werkzeug/weg: …`, Eingrenzen mit `--werkzeug` und `--weg`.
- **Beleg bei „NICHT GESPERRT“:** Ausgabe und Vibe-Ausgabeordner landen in `.normen/selbsttest-<zeit>-<werkzeug>-<weg>.log`
  (vorher wurde der Ausgabeordner immer gelöscht; Rückmeldung).

### Geändert
- **`auftrag --dateien`:** jedes Argument ist genau ein Pfad, auch mit Leerzeichen; das Trennen an Leerraum entfällt
  (Rückmeldung, Paket C).
- **mistral-team Zeitlimit:** Umsetzungsläufe mit `--time-limit 1200` im Hintergrund; 540 s nur für kurze Läufe
  (Rückmeldung „540 s zu knapp“; Wirkung offen: der erste 1200-s-Lauf endete ebenfalls am Zeitlimit).
- Mit dieser Version kommt der angepasste Pflichtblock von `normen.py auftrag` für gemini-analyst (enge Liste) in die Projekte.

---

## agy-Freigaben, enge Liste (Multi-KI, kein neuer Normtext) – 2026-11-18

**Aktualisieren nötig:** ja – wie unten (Agent-Definition kopieren, `docs/multi-ki-ablauf.md` und
`docs/recherche-auftrag.md` angleichen).

### Geändert
- **Keine inhaltslesenden Befehle mehr für agy:** `cat`, `head`, `tail`, `wc`, `grep` und `git log/diff/show` gestrichen.
  Befehlsregeln haben keine Pfadgrenze (`cat ~/.ssh/…` ginge an Google, N03), `git … --output` schreibt Dateien. Gemini
  liest nur per `read_file` (Projekt + Lauf-Ordner); Diffs legt Claude als Datei in den Lauf-Ordner.
- **Auch keine Test-/Buildbefehle** (`make test`, `swift …`, `normen.py pruefen`): Im Umsetzungsaufruf kann Gemini das
  Makefile ändern, `make test` führt dann Beliebiges aus (gemessen). Die Liste ist damit projektunabhängig.
- **Prüfreihenfolge für Claude:** erst Diff lesen, dann Tests ausführen (Ablauf Schritt 6, Regel 3 in
  `multi-ki-ablauf.md` und `projekt/CLAUDE-abschnitt.md`): Ein Team-Lauf kann Makefile oder Testcode ändern, `make test`
  liefe sonst ungeprüft mit Claudes Rechten. Gemini bekommt keine Testbefehle; einen agy-Hook gibt es dafür nicht
  (Entscheidung der Inhaberin 18.11.). In Projekten Regel 3 im CLAUDE-Abschnitt von Hand angleichen.
- Prompt-Satz: „Lies Dateien nur mit dem Lesewerkzeug, nicht im Terminal …“; ebenso der Pflichtblock von
  `normen.py auftrag` für gemini-analyst (nannte noch `cat`, `grep`, `git diff/log/show` – jeder solche Aufruf hätte den
  Lauf beendet). Kommt mit der nächsten Normen-Version in die Projekte.

---

## agy-Freigaben (Multi-KI, kein neuer Normtext) – 2026-11-18

**Aktualisieren nötig:** ja – `multi-ki/benutzer/agents/gemini-analyst.md` nach `~/.claude/agents/` kopieren (Rückfrage);
`docs/multi-ki-ablauf.md` in den Projekten von Hand angleichen (`multi-ki/einrichten.sh` legt eine `.vorlage` daneben).
Projekteigene Ergänzungen der agy-Freigabeliste auf die Form ohne `*` umstellen.

### Geändert
- **agy-Freigabeliste in Präfixform** (`command(git diff)` statt `command(git diff*)`): In agy 1.5.11 greifen Regeln mit
  `*` nicht – weder in `allow` noch in `deny`. Das erklärt die gesperrten `cat`/`wc`/`tail`-Aufrufe aus den Rückmeldungen.
  `rg` und `tree` gestrichen (`--pre` startet Programme, `-o` schreibt), `git branch --show-current` aufgenommen.
- **`"agentMode":""` in jedem `--settings`:** Ohne `--mode` startete `agy -p` im Auto-Modus und führte auch nicht
  freigegebene Befehle aus (N07). Betraf den Nur-Lesen-Aufruf von `gemini-analyst`.
- **Lauf-Ordner als aufgelöster Pfad** (`R=$(realpath "$RUN")`, `read_file('"$R"')`): agy vergleicht `/private/var/…`, eine
  Regel mit `/var/…` greift nie. Jetzt auch im Analyse-Aufruf, damit Nebendateien im Lauf-Ordner lesbar sind.
- „auto-denied“ betrifft den letzten verweigerten Schritt: erst `git status` und Zieldateien prüfen; die Schnittstelle
  wiederholt nicht selbst, sondern meldet an Claude.
- Prompt-Pflichtsätze für agy (Agent-Definition, `docs/recherche-auftrag.md`): erlaubte Befehle nennen, „Lies keine
  anderen als die genannten Dateien …“ – jeder verweigerte Schritt beendet den Lauf.
- **Bekannte Lücke:** `.geminiignore`/`.antigravityignore` sperren in agy nichts; Sperrpfade schützt gegenüber agy nur die
  Hook-Prüfung der Prompt-Datei (PLAN A2).
- Bericht und Messungen: `docs/plaene/agy-freigaben-spike.md`.

---

## v13 – 2026-11-18

**Aktualisieren nötig:** ja – `normen.py aktualisieren` (nur neuer Normtext, keine Hook-Änderung).

### Neu
- **S08-CLEAR-FAEHIG** (Soll, nur Hauptsitzung): Pakete so schneiden, dass danach `/clear` möglich ist – Befunde sofort in
  `PLAN.md`, am Paketende committen, „/clear möglich“ melden; Ausnahme für stark zusammenhängende Pakete (Grund nennen).
  PLAN-Vorlage (`multi-ki/projekt/PLAN.md`) um eine Zeile ergänzt.

---

## v12 und Recherche-Aufträge – 2026-11-17

**Aktualisieren nötig:** ja – `normen.py aktualisieren` (wird es für Claude abgelehnt, gibt die Inhaberin
`! python3 normen/normen.py aktualisieren` ein), `normen.py selbsttest`; dazu `multi-ki/einrichten.sh <projekt> --test
"<testbefehl>"` für die Recherche-Vorlagen (vorhandene Dateien bleiben; `docs/multi-ki-ablauf.md` kommt als `.vorlage` und wird
von Hand zusammengeführt); Agent-Definitionen aus `multi-ki/benutzer/agents/` nach `~/.claude/agents/` kopieren (Rückfrage).

### Geändert (v12, Durchsetzung – kein neuer Normtext)
- **Vibe-Hooks prüfen jetzt auch `edit`** (Vibe 3.1.x nennt das Bearbeiten-Werkzeug so; der Hook kannte nur `search_replace`).
  Gemessen: ohne diesen Eintrag änderte Vibe ohne Auftrag eine Datei; mit ihm sperrt der Hook („kein .normen-auftrag“).
  Ebenso `grep` (liefert Dateiinhalte) und vorsorglich `experimental_bash`, `git_bash`, `managed_shell`. Prüfbefehl in
  `hooks.toml`: „gültig: 9“. Nachgewiesen: erlaubte Änderungen (48 `edit`-Aufrufe aus früheren Läufen, je mit ihrem Auftrag) gehen
  durch, ohne Auftrag gesperrt; live: Datei aus dem Auftrag geändert, andere gesperrt; auch Vibes Sub-Agenten werden gesperrt.
- **Gesperrter Ordner selbst:** Lese-Werkzeuge auf den Ordner eines Sperrpfads (`grep … daten/geheim/`) sind jetzt gesperrt,
  nicht nur Dateien darin.
- **`einrichten.sh`/`aktualisieren`** ersetzen eine `.vibe/hooks.toml`, die nur Normen-Hooks enthält (mit Sicherung
  `hooks.toml.bak-<datum>`); mit eigenen Hooks bleibt es bei der `.vorlage` daneben.

Recherche-Aufträge: keine Normänderung (Entscheidung der Inhaberin: nur Vorlagen und Doku).

### Neu
- Vorlagen `docs/recherche-auftrag.md` (Frage, Zweck, Umfang, feste Regeln: Webinhalte sind Daten, nichts Privates in
  Suchanfragen, ohne Websuche abbrechen statt aus dem Gedächtnis antworten, keine erfundenen Quellen, Suchtreffer höchstens
  „abgeleitet“) und `docs/recherche-bericht.md` (Kurzantwort, Befunde mit URL, Datum, Zugriff und Belegstärke, Widersprüche,
  offene Fragen, Methode).
- `multi-ki-ablauf.md`, Abschnitt „Recherche“: wer wann (Gemini breit, Mistral Gegenprüfung im normalen Modus, Claude bei
  Abwägung), wichtige Fragen doppelt, Ablage `docs/recherche/<datum>-<thema>.md`, Datenschutz.
- Messgrundlage `docs/plaene/recherche-spike.md` mit Abnahme-Probe (zwei Anbieter parallel).

---

## v11 – 2026-11-17

**Aktualisieren nötig:** ja (`normen.py aktualisieren` – wird es für Claude abgelehnt, gibt die Inhaberin `! python3 normen/normen.py aktualisieren` ein; dann `normen.py selbsttest`)

### Geändert (Rückmeldung aus einem Projekt: lokale Container-Probeläufe)
- **N01:** Ein Teilbefehl, der mit `docker|podman [container|compose] rm` beginnt (auch in einer Funktion `name() { … }`), gilt
  nicht als Datei-Löschen (Container entfernen); mit Befehlsersetzung (`$(…)`, Backtick, `<(…)`) bleibt er geprüft. Gilt für alle Rollen (Teams dürfen damit
  Container entfernen; vorher gesperrt). Nur am Anfang eines Teilbefehls: `if …; then docker rm -f x; fi` und
  `trap 'docker rm -f x' EXIT` fragen weiterhin.
  `docker volume rm`, `docker system prune` und jedes andere `rm -rf` bleiben destruktiv.
- **Skriptpfade:** `"$W/x.sh"` wird mit Zuweisungen aus **vorangehenden** Teilbefehlen aufgelöst (`W=/pfad; bash "$W/x.sh"`) und
  dann geprüft wie jedes Skript außerhalb des Projekts; Präfix-Zuweisungen (`W=… bash "$W/x"`) und `W="$(mktemp -d)"` bleiben
  „nicht prüfbar“.
- **Variablen nur bei eindeutiger Zuweisung:** Ist ein Name im Befehl mehrfach zugewiesen (auch in `if`/`for`/`read`/`local`) oder
  stammt sein Wert aus einer Befehlsersetzung (`` `…` ``, `$(…)`), löst der Hook ihn nicht auf – gilt für Skriptpfade, Prompt-Dateien
  (G5) und Bash-Schreibziele (G3/v8). Container-Ausnahme auch nicht bei Prozess-Substitution (`<(…)`, `>(…)`).
- **Shell-Schlüsselwörter:** Befehle hinter `do`, `then`, `else`, `if`, `while`, `until`, `!`, `{`, `(` werden geprüft wie jeder
  andere (vorher blieb z. B. `for …; do bash x.sh; done` ungeprüft). Folge: `for f in …; do python3 tests/$f.py; done` fragt jetzt
  nach (Schleifenvariable nicht auflösbar) – stattdessen `make test` oder die Dateien ausschreiben.
- Echter Fall aus dem Projekt (Skript mit Container-Probelauf) nachgespielt: `docker rm` wird nicht mehr beanstandet; weiter
  streng bleiben `rm -rf "${W:?}"` (fragen), `*.secret`-Dateien (gesperrt), Skriptpfade unter einem `mktemp`-Ordner.
- Unverändert (Entscheidung der Inhaberin): N03 sperrt Dateinamen wie `*.secret` auch in Temp-Ordnern – Testdateien anders benennen.

---

## v10 – 2026-11-17

**Aktualisieren nötig:** ja (`normen.py aktualisieren` – wird es für Claude abgelehnt, gibt die Inhaberin `! python3 normen/normen.py aktualisieren` ein; dann `normen.py selbsttest`)

### Geändert
- **N01-Text:** nennt `git worktree remove --force` (die Sperre gilt seit v9; Rückmeldung aus einem Projekt).
- **`normen.py selbsttest`:** lief ein Werkzeug, ohne den Köder zu versuchen („unklar“, keine Hook-Meldung), wird es einmal wiederholt (nicht bei fehlendem Werkzeug oder Zeitlimit); bleibt es „unklar“, der Inhaberin melden;
  „NICHT GESPERRT“ wird nie wiederholt.
- **`normen.py merge`:** kennt GitHub den gerade gepushten PR-Kopf noch nicht, wartet das Prüftor bis zu dreimal 5 Sekunden.
- **Doku:** Wird `aktualisieren` für Claude abgelehnt (in einem Projekt im Auto-Modus beobachtet), führt es die Inhaberin mit `!` aus.
- `normen.py merge`: der Wartepfad ist nicht durch Tests abgedeckt (Kopf-Prüfung danach unverändert).

---

## v9 – 2026-11-17

**Aktualisieren nötig:** ja (`normen.py aktualisieren`, dann `normen.py selbsttest`)

### Geändert
- **N01:** `git worktree remove --force|-f` gilt als destruktiv (Claude fragt nach, Teams gesperrt) – löscht ungesicherte Arbeit
  im Worktree. Normales `git worktree remove`, `prune` und `list` bleiben frei (Achtung: auch ein normales `remove` löscht
  git-ignorierte Dateien im Worktree).
- **N10:** `git worktree add` nur durch den Orchestrator (für Teams gesperrt).
- Grundlage: Worktree-Spike (G11, `docs/plaene/worktree-spike.md`), Entscheidung der Inhaberin vom 17.11.

### Hinweise
- `normen.py selbsttest` kann bei Vibe gelegentlich „unklar“ melden (Vibe versucht den Köder-Befehl nicht jedes Mal): einmal
  wiederholen; nur „NICHT GESPERRT“ ist ein Befund.

---

## v8 – 2026-11-17

**Aktualisieren nötig:** ja (`normen.py aktualisieren`, dann `normen.py selbsttest`; Agent-Definitionen aus
`multi-ki/benutzer/agents/` nach `~/.claude/agents/` kopieren – Rückfrage bei der Inhaberin)

### Neu
- **Teams schreiben auch per Bash nur Auftragspfade:** Bash-Schreibziele (Umleitung, `tee`, `sed -i`, `cp`, …) im Projekt sind für
  Rollen mit Auftragspflicht nur erlaubt, wenn sie in `.normen-auftrag` stehen; ohne Auftrag gesperrt,
  sowie außerhalb des Projekts nur Lauf-Ordner, Temp-Wurzeln aus `loeschbar` und `/dev/*`; relative `loeschbar`-Pfade (`build`,
  `.pytest_cache` …) bleiben frei. Nicht bestimmbare Ziele (`$(mktemp …)`) lässt der Hook durch – `pruefen --diff` prüft nach dem
  Lauf (bisher galt das alles nur für Datei-Werkzeuge – gefunden beim Messen von G10). Wiederholung von 75 echten Vibe-Befehlen:
  keine zusätzliche Sperre.
- **Lese-Modus und Lauf-Protokoll (G10):** reine Lese-Aufträge an Vibe mit `--agent ask` (Schreiben und nicht-lesende Befehle
  abgelehnt, auch bei Sub-Agenten; gemessen mit Vibe 3.1.2); Schnittstelle wartet auf die eigene PID statt `pgrep`, meldet nie
  „gescheitert“ bei laufendem Prozess, leere Statusdatei = sauber; `RUN` im selben Befehl wie `vibe`/`agy`. Nicht nachgewiesen:
  Normen-Hook bei lesenden Befehlen im Lese-Modus (in Projekten mit Sperrpfaden nur nach Rückfrage). Wirksam erst, wenn die
  Agent-Definitionen nach `~/.claude/agents/` kopiert sind.
- **Spikes:** `docs/plaene/sandbox-spike.md` (G7, Entscheidung: vibe/agy ausnehmen, Sandbox nicht aktiviert) und
  `docs/plaene/worktree-spike.md` (G11, Worktree je Team-Lauf als Option, nur innerhalb des Projekts).
- **Asserts in Tests (G9):** `pruefen --diff`/`--staged` vergleicht entfernte und neue Assert-Zeilen (`assert`, `assertX(`,
  `expect(`, `check(`, `XCTAssert…(`, `pytest.raises`) über alle Testdateien des Diffs: geänderte Asserts → Hinweis, ersatzlos
  entfernte → Fehler. Jede Zeile `normen-ausnahme: N02-TESTS-SIND-TABU – Begründung` im Diff entschuldigt genau ein entferntes Assert.
  Die Begründung zählt nur als Kommentar (`# …` / `// …`). Umbenennen aus den Test-Globs heraus zählt als Entfernen.
  Grenze: Erwartungswerte in Tabellenzeilen (z. B. `("befehl", "ja")`) sind keine Assert-Zeilen und werden nicht erkannt.

### Geändert
- G5: verschachtelte Zuweisungen werden aufgelöst (`G=/x; RUN="$G/lauf"; vibe … --prompt-file "$RUN/prompt.md"`).

### Hinweise
- Sperrt G9 einen Commit wegen eines bewusst entfernten Tests: Kommentar `# normen-ausnahme: N02-TESTS-SIND-TABU – Begründung`
  im selben Diff (je entferntem Assert eine Zeile).
- `git worktree remove --force` als destruktiv werten: entschieden, umgesetzt in v9.

---

## v7 – 2026-11-16

**Aktualisieren nötig:** ja (`normen.py aktualisieren`, dann `normen.py selbsttest`)

### Neu
- **Selbsttest (G1):** `normen.py selbsttest [--werkzeug claude|vibe]` prüft durch das echte Claude Code und Vibe, ob die Normen-Hooks greifen: ein Köder-Befehl, den nur der Hook sperrt (für alle Rollen, für Agenten unsichtbar). Ergebnis je Werkzeug gesperrt / NICHT GESPERRT / unklar. Pflicht nach jedem Update.
- **pre-commit nicht umgehen (G2):** N10 sperrt `--no-verify`, `git commit -n` und das Setzen von `core.hooksPath` (neue Fähigkeit `hooks-umgehen`, nur die Inhaberin); `git config --get core.hooksPath` bleibt frei.
- **Bash-Schreibziele (G3):** Umleitungen, `tee`, `sed -i`, `cp`/`mv`/`ln`/`rm` … auf Normen- und Agenten-Einstellungen (CLAUDE.md, AGENTS.md, `normen/`, `.claude/`, `.vibe/`, `.githooks/`) fragen bei Claude und sind für Teams gesperrt – wie Edit/Write. Fehlalarm bei `[pfade].lesbar_extern` (Lesen mit `>` im Text) behoben.
- **Inline-Code und fremde Skripte (G4):** `python3 -c`, `python3 [-] <<PY` per AST; `bash|sh|zsh -c` rekursiv; Skriptdateien außerhalb des Projekts (`bash x.sh`, `./x.sh`, `source`, Python ohne `.py`, Shebang) vor dem Lauf; Code über stdin, `node|perl|ruby -e` und fremde node/perl/ruby-Skripte fragen; Präfixe (`FOO=1`, `env`, `time -p`, `nice -n`, `timeout`) und `cd`/`pushd` werden berücksichtigt. Heredoc-Rümpfe von `cat > datei`/`tee` sind Daten (kein Fehlalarm mehr).
- **Datenschutz vor vibe/agy (G5):** Vor dem Start prüft der Hook Prompt-Datei (samt `*.md` daneben) bzw. `-p`-Text: Sperrpfade und Geheimnis-Inhalte → gesperrt; Geheimnis-Pfade → bei agy gesperrt; Forschungsdaten (neu `[pfade].forschungsdaten`, Pfad-Globs und Textmarker) → agy gesperrt, vibe fragt. Nicht prüfbare Prompt-Quelle → gesperrt. Der Pflichtblock aus `normen.py auftrag` zählt nicht.

- **MCP-Freigaben (G6):** Der Claude-Hook gilt auch für MCP-Werkzeuge (Matcher `mcp__.*`). Entscheidend sind nur die neuen
  Projektlisten `[mcp].nein` / `[mcp].fragen` (Globs über den vollen Werkzeugnamen, `nein` vor `fragen`); unbekannte MCP-Werkzeuge
  sind erlaubt, Eingabefelder werden nicht als Befehle oder Pfade gelesen. Vorlage: `enableAllProjectMcpServers: false`.
  `einrichten.sh` ergänzt in bestehenden Projekten fehlende Matcher-Teile und fehlende Schlüssel (eigene Werte bleiben).

### Geändert
- N06-Prompt: gesperrte Pfade auch in keinen Auftrag an externe Teams schreiben.
- Fehlalarm behoben: mehrzeilige `git commit -m "…"`-Nachrichten gelten als Text.
- `node -e` fragt (bisher frei).

### Hinweise
- Bestehende Projekte: `normen.py aktualisieren` ergänzt den Hook-Matcher `mcp__.*` in `.claude/settings.json`. Die Projektwerte
  `[mcp]` und `[pfade].forschungsdaten` legt die Inhaberin selbst in `normen/projekt.toml` an; bis dahin sind beide ohne Wirkung.
- Live geprüft: Selbsttest (claude, vibe), MCP-Sperre in Claude Code (Werkzeug in `[mcp].nein` → gesperrt). Die beiden Reviews
  (Gemini, Mistral) blieben unvollständig (Zeitlimit); Restgefahren stehen in `multi-ki-ablauf.md`.
- Zurückgestellt aus dem Entwurf: `meta.ebenen` in `normen.toml` (Inhalt steht in der Doku).

---

## v6 – 2026-11-16

**Aktualisieren nötig:** ja (`normen.py aktualisieren`; zusätzlich `multi-ki/einrichten.sh` für CLAUDE-Abschnitt, Ablauf und PLAN.md;
Agent-Definitionen nach `~/.claude/agents/` kopieren – Rückfrage)

### Neu
- **S07-SUPERVISOR:** Fable als Advisor der Hauptsitzung; fünf Pflicht-Konsultationen; bei Ausfall ohne Fable weiter, Normänderungen zurückstellen.
- **S06-CODE-MODE:** mehrstufiges Auswerten als Skript; der Hook prüft Skripte außerhalb des Projekts per AST (`normen.py skript --pruefen`).
- **`nur_rollen`:** Normen nur für die Hauptsitzung erscheinen nicht in Team-Aufträgen und nicht im AGENTS-Block.
- **Rollen `fable` und `skript`:** `fable` (Advisor) und der Regelsatz `skript` für Befehle in Skripten bekommen keine Aufträge; `skript` steht nicht in der Rollentabelle. Rollenkette in `kurz.md`.
- **PLAN.md:** zentrale Aufgabenliste je Projekt; Sitzungen beginnen dort. `multi-ki/einrichten.sh` legt sie an, wenn sie fehlt; `normen.py merge` weist auf eine unveränderte PLAN.md hin.
- S03: Hauptsitzung fragt nach drei Fehlversuchen den Advisor, danach höchstens ein weiterer Versuch. S05: Auswerte-Skripte nach S06 ausgenommen.

### Agent-Definitionen
- `mistral-team.md`, `gemini-analyst.md`, neu `Explore.md`: Advisor nie aufrufen.

---

## v5 – 2026-11-16

**Aktualisieren nötig:** ja (`normen.py aktualisieren`; zusätzlich `.vibe/hooks.toml` übernehmen und die Agent-Definitionen nach `~/.claude/agents/` kopieren)

### Behoben
- **Vibe-Hooks waren wirkungslos (#25):** In `.vibe/hooks.toml` fehlte bei allen vier Einträgen das Pflichtfeld `name`; Vibe 3.x verwarf sie still, die Normen-Hooks griffen in Vibe nicht. Jetzt mit `name`, geprüft mit dem Lader der installierten Vibe-Version (Prüfbefehl steht in der Datei).
- **N10 zu streng (#23):** Reines Lesen aus `~/.gemini` usw. (`find … -newer`, `cp -n ~/.gemini/… docs/…`) löste eine Rückfrage aus. `find` zählt nur noch mit schreibenden Aktionen (`-delete`, `-exec`, `-execdir`, `-ok`, `-fprint` …), `cp`/`ln`/`install`/`rsync` nur mit dem Einstellungsordner als Ziel (auch `-t`/`--target-directory`). Neu erkannt: `>> "$HOME/…"` mit Anführungszeichen.
- **N06 zu locker:** `[pfade].lesbar_extern` galt nur für Edit/Write; Bash-Befehle (`cd … && sed -i …`, `cp … <ordner>/`, `git -C <ordner> commit`, Umleitung) gingen durch. Jetzt gesperrt.
- **agy-Schreibmodus (#22):** `normen.py auftrag --rolle gemini-analyst` verlangt keine Abnahmebefehle mehr (neues Rollenfeld `abnahme_durch_claude`); agy headless darf nur freigegebene Befehle ausführen.

### Agent-Definitionen (`multi-ki/benutzer/agents/`)
- `gemini-analyst.md`: Freigabeliste um Lesebefehle ergänzt (`--settings` ersetzt die globale agy-Liste), Bildmodus mit `read_file`-Freigabe für Lauf- und Bildordner, Bildgröße je Seitenverhältnis.
- `mistral-team.md`: Modell (`active_model`), `outcome` und `steps` aus `export.json` prüfen und berichten; „Model … not available“ und `hooks.toml`-Fehler nicht mehr als harmlos behandeln.

---

## v4 – 2026-11-15

**Aktualisieren nötig:** ja

### Änderungen und Neuerungen
- **Rolle `inhaberin`:** Die Rolle der Projektbesitzerin heißt nun einheitlich `inhaberin`. Der konfigurierbare Anzeigename wird in `normen/projekt.toml` über `[projekt].inhaberin` festgelegt (z. B. für Hinweise „bitte {inhaberin} fragen“).
- **N10 differenziert (Fähigkeit `einstellungen-lesen`):** Reines Lesen in den Konfigurationsordnern der Agenten (`~/.claude`, `~/.vibe`, `~/.gemini`, `~/.antigravity`) ist für Claude Code ohne Rückfrage erlaubt. Schreibzugriffe erfordern weiterhin eine ausdrückliche Rückfrage. Für externe Teams bleiben diese Verzeichnisse strikt gesperrt.
- **N03 geschärft:** Das Lesen und Schreiben von `~/.ssh` sowie `~/.config/gh` ist explizit unter N03 (Geheimnisse) verboten.
- **Externe Lesepfade (`[pfade].lesbar_extern`):** Einführung der Option `lesbar_extern` in `projekt.toml` (Standard: `["~/Documents/Projekte/claude-tools"]`). Ermöglicht Agenten das Lesen von Vorlagen außerhalb des Projektordners; Schreibzugriffe sind dort technisch unterbunden.
- **Versionsverfolgung (`normen/herkunft.toml`):** Protokolliert Version, Quell-Commit, Einspieldatum und SHA256-Prüfsummen der gemeinsamen Vorlagendateien.
- **Aktualisierungsbefehl (`normen.py aktualisieren`):** Neuer Befehl zum kontrollierten Nachziehen aktualisierter Vorlagendateien aus `claude-tools`. Prüft auf manuelle Änderungen im Zielprojekt und bricht bei Abweichungen ab. `normen.py pruefen` gibt entsprechende Hinweise aus.
- **Rückmeldesystem (`normen.py melden`):** Neuer Befehl zur strukturierten Übermittlung von Beobachtungen, Regelproblemen und Fehlern an ein privates GitHub-Repository der Inhaberin. Gesteuert über die neue Rollenfähigkeit `rueckmelden` (Claude fragt vor dem Absenden; externe Teams gesperrt) inklusive automatischer Prüfung auf sensible Muster.
- **Gemeinsames Einrichtungsskript (`einrichten.sh`):** Neues Skript im Wurzelverzeichnis, das `agenten-normen/einrichten.sh` und `multi-ki/einrichten.sh` in einem einzigen Aufruf bündelt.
- **Vereinheitlichte Marke in `CLAUDE.md`:** Der Multi-KI-Abschnitt wird nun über die Marke `<!-- multi-ki-abschnitt -->` eingebunden. Frühere Vorlagenmarken werden beim Einrichten automatisch umgestellt.
- **Ergänzung von `AGENTS.md`:** Multi-KI-Regeln für externe Modelle werden beim Einrichten sauber an den generierten Normen-Block angehängt, anstatt bestehende Konfigurationen zu überschreiben.

---

## v3 – 2026-11-14

**Aktualisieren nötig:** nicht zutreffend (Initialversion)

### Erste konsolidierte Fassung
- **Normensystem:** Einführung der Muss-Normen N01–N11 und Soll-Normen S01–S05 für alle Coding-Agenten im Projekt.
- **Technische Durchsetzung:**
  - PreToolUse- und Stop-Hooks für Claude Code (`.claude/settings.json`).
  - Pre-Tool-Hooks für Mistral Vibe (`.vibe/hooks.toml`).
  - Git-Pre-Commit-Hook (`.githooks/pre-commit`) basierend auf `normen.py pruefen --staged`.
- **Prüftor für den Hauptzweig:** Einführung von `python3 normen/normen.py merge <PR>` zur Absicherung von Merges nach `main` (automatischer Testlauf und Diff-Audit).
- **Auftragssteuerung:** Definition von Arbeitsbereichen für externe Agenten über `.normen-auftrag` und Befehle `normen.py auftrag` sowie `normen.py auftrag --ende`.
