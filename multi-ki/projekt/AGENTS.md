# Regeln für externe Agenten (Mistral Vibe `vibe`, Google Antigravity `agy`)

Beide Werkzeuge lesen diese Datei, wenn sie in diesem Projekt laufen. Den Auftrag erteilt Claude; es gilt der Auftrag plus diese Regeln.

- Außerhalb des Projektordners wird ohne ausdrückliche Erlaubnis nichts gelöscht oder geändert. Ausnahme nur: die eigenen Lauf-Ordner unter `${TMPDIR:-/tmp}/vibe-runs` bzw. `agy-runs`.
- Lösche niemals Dateien, die du in diesem Lauf nicht selbst angelegt hast, auch keine unbekannten, untracked oder scheinbar versehentlich entstandenen Dateien. Die Nutzerin arbeitet parallel im Projekt. Unerwartete Dateien nur im Bericht nennen. Kein `rm`, kein `git clean`, kein `git checkout --`/`git restore` auf fremde Dateien.
- Kein `git commit`, kein `git push`. Keine Änderungen an `~/.vibe`, `~/.gemini`, `~/.claude`, Homebrew oder anderen Einstellungen.
- Nur die im Auftrag genannten Dateien ändern. Zahlen und Behauptungen per Shell-Befehl prüfen.
- Nie Geheimnisse lesen, ausgeben oder anfordern (`.env`, `*.secret`, Schlüssel).
- Diese Pfade nicht lesen und nicht öffnen:
@@SPERRLISTE@@
- Sprache der Berichte: Deutsch, knapp, gegliedert.
