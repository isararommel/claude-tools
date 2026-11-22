# Changelog

Alle wesentlichen Änderungen an `claude-tools` (Agenten-Normen, Multi-KI-Ablauf und Skripte) werden in dieser Datei dokumentiert.

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
    (`.py`, `.so`, `.pyc` …) oder etwas im Paketordner geschrieben → fragen (auch in anderer Schreibweise: `> Evil.py`).
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
- **`python3 -c` mit Import bei unbekanntem Suchpfad** (unaufgelöster PYTHONPATH, `cd "$D"`) → fragen wie bei `-m`, weil
  die Schatten-Prüfung sonst entfiele. `python3 -c` ohne Import bleibt erlaubt.

### Geändert
- **Projekt-Importe in `python3 -c`:** Ein Import, der (Suchreihenfolge wie Python) auf eine Datei im Projekt auflöst, gilt wie
  `python3 projektdatei.py` und wird nicht mehr als „nicht in der Positivliste“ gesperrt. Ein gleichnamiges Modul im
  Lauf-Ordner wird weiterhin gesperrt.
- **Pflichtsatz in `normen.py auftrag`:** „Sperrt ein Normen-Hook einen Aufruf: denselben Zweck nicht auf anderem Weg
  erreichen, sondern anhalten und die Sperrmeldung wörtlich im Bericht nennen.“
- **G9/N02 (Rückmeldung „N02 sperrt Löschen von Tests samt Altcode“):** Eine ganz gelöschte Testdatei ergibt einen Hinweis
  statt Fehlern, wenn derselbe Diff eine Nicht-Testdatei löscht, deren Dateistamm als ganzes Wort in der Testdatei vorkommt
  (N08: Altcode samt Tests entfernen). Der Hinweis nennt beide Dateien. `__init__` zählt nicht als Beleg.
  Offen: Der Stop-Hook wiederholt bekannte Befunde.

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
- G9: Jede gelöschte Nicht-Testdatei, deren Stamm in der Testdatei vorkommt, gilt als Beleg. Häufige Stämme (`utils`, `main`,
  `README`) belegen nur schwach, deshalb gibt es einen Hinweis zum Review statt einer stillen Freigabe.
- **`melden --stufe`** setzt zusätzlich das Label `stufe:<stufe>`. Fehlen Labels im Ziel, wird das Issue ohne Labels angelegt,
  und die Meldung nennt die fehlenden Labels.

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
