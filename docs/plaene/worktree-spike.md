# Worktree-Spike (Normen v8, Paket G11) – Messbericht

Stand: 2026-11-16 · git, Normen v8 · nur Messung im Wegwerf-Klon (getrackter Sperrpfad `daten/geheim/x.csv`, eingetragen in
`[pfade].gesperrt`; ungetrackte `.env` im Hauptordner). Das echte Repository wurde nicht angefasst.

Frage (Lücke L8): Teams arbeiten im Hauptordner und sehen parallele Arbeit der Inhaberin bzw. anderer Sitzungen. Hilft ein eigener
`git worktree` je Team-Lauf?

## Gemessen

| Punkt | Ergebnis |
|---|---|
| Inhalt des Worktrees | alle getrackten Dateien, **auch getrackte Sperrpfade** (`daten/geheim/x.csv`); ungetrackte Dateien fehlen (`.env`, `.normen-auftrag`, `.normen/`) |
| Hook im Worktree | Claude Code und Vibe nutzen das `normen.py` **des Worktrees** (getrackt, gleiche Version); `ROOT` ist der Worktree |
| Team schreibt im Worktree ohne eigenen Auftrag | gesperrt: „kein .normen-auftrag – Rolle mistral-team darf nichts schreiben“ → Claude muss `normen.py auftrag` **im Worktree** ausführen |
| Team aus dem Worktree in den Hauptordner | gesperrt: „außerhalb des Projekts“ – der Worktree trennt die Teams wirksam von paralleler Arbeit |
| Worktree innerhalb des Projekts (`.worktrees/…`) | erscheint im Hauptordner als ungetracktes `.worktrees/` (gehört in `.gitignore`); `pruefen --diff` durchsucht ihn nicht |
| Worktree außerhalb (`../wt-…`) | taucht im Hauptordner nicht auf; für Claude „außerhalb des Projekts“ (in diesem Spike lag er unter `$TMPDIR` und war deshalb frei) |
| `make test` im Worktree | läuft (Ergebnis = Stand des Worktree-Branches) |
| `git worktree remove` mit ungesicherten Dateien | **verweigert** („contains modified or untracked files, use --force“) – Team-Arbeit bleibt erhalten |
| Hook-Stufen Claude | `worktree add/list/remove/prune`, `branch -d`, `merge --ff-only`: ja · `branch -D`: fragen · **`worktree remove --force`: ja** |
| Hook-Stufen Teams | `worktree add/remove/prune`, `branch -d`: ja · `branch -D`, `merge`: nein · **`worktree remove --force`: ja** |

## Nur dokumentiert / abgeleitet (nicht gemessen)

- Ein Worktree teilt das Objekt-Archiv und die Branches mit dem Hauptordner; Commits im Team-Branch sind sofort im Hauptordner
  sichtbar (Übernahme per `git merge --ff-only` durch Claude).
- Getrackte Sperrpfade lassen sich im Worktree nicht ausblenden (kein sparse-checkout gemessen).

## Offen

- Vibe-Lauf im Worktree mit Auftrag (hier nur Hook-Entscheidungen gemessen, kein echter Lauf).
- sparse-checkout, um getrackte Sperrpfade im Team-Worktree wegzulassen.
- Wie Claude den Worktree-Pfad im Auftrag nennt, ohne dass G5 (Prompt-Prüfung) oder G4-B („außerhalb“) Fehlalarme auslöst.

## Vorschlag (Entscheidung der Inhaberin)

1. **Lücke schließen (unabhängig vom Worktree):** `git worktree remove --force|-f` als destruktiv werten (N01, wie `branch -D`);
   für Teams auch `git worktree add` sperren (Worktrees legt nur Claude an). Normänderung → vorher Advisor (S07 Punkt 5).
2. **Worktree je Team-Lauf als Option**, nicht als Standard: lohnt bei parallelen Sitzungen im selben Repository. Ablauf:
   Claude legt `../<projekt>-wt-<lauf>` mit Branch `team/<lauf>` an, führt dort `normen.py auftrag` aus, startet das Team mit
   dem Worktree als Projektordner, prüft dort Diff und Tests, übernimmt per `git merge --ff-only`, räumt mit
   `git worktree remove` (ohne `--force`) und `git branch -d` auf. Getrackte Sperrpfade sind im Worktree vorhanden – für Projekte
   mit getrackten Sperrpfaden erst sparse-checkout klären.
