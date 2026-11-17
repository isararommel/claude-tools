# Worktree-Spike (Normen v8, Paket G11) – Messbericht

Stand: 2026-11-16 · git, Normen v8 · nur Messung im Wegwerf-Klon (getrackter Sperrpfad `daten/geheim/x.csv`, eingetragen in
`[pfade].gesperrt`; ungetrackte `.env` im Hauptordner). Das echte Repository wurde nicht angefasst.

Frage (Lücke L8): Teams arbeiten im Hauptordner und sehen parallele Arbeit der Inhaberin bzw. anderer Sitzungen. Hilft ein eigener
`git worktree` je Team-Lauf?

## Gemessen

| Punkt | Ergebnis |
|---|---|
| Inhalt des Worktrees | alle getrackten Dateien, **auch getrackte Sperrpfade** (`daten/geheim/x.csv`); ungetrackte Dateien fehlen (`.env`, `.normen-auftrag`, `.normen/`) |
| Hook-Aufruf mit dem `normen.py` des Worktrees | `ROOT` ist der Worktree (Hook-Entscheidungen gemessen; kein echter Vibe-/Claude-Lauf im Worktree) |
| Team schreibt im Worktree ohne eigenen Auftrag | gesperrt: „kein .normen-auftrag – Rolle mistral-team darf nichts schreiben“ → Claude muss `normen.py auftrag` **im Worktree** ausführen |
| Team aus dem Worktree in den Hauptordner | Hook sperrt: „außerhalb des Projekts“ (per Hook-Aufruf gemessen) |
| Claude: `cd <worktree> && python3 normen/normen.py auftrag …` bzw. `pruefen --diff` | Worktree **außerhalb**: **gesperrt** (G4-B: `normen.py` gilt als fremdes Skript) · Worktree **innerhalb** (`.worktrees/…`): ja |
| Worktree innerhalb des Projekts (`.worktrees/…`) | erscheint im Hauptordner als ungetracktes `.worktrees/` (gehört in `.gitignore`); `pruefen --diff` durchsucht ihn nicht |
| Worktree außerhalb (`../wt-…`) | taucht im Hauptordner nicht auf; für Claude „außerhalb des Projekts“ (in diesem Spike lag er unter `$TMPDIR` und war deshalb frei) |
| `make test` im Worktree | läuft (Ergebnis = Stand des Worktree-Branches) |
| `git worktree remove` mit ungesicherten Dateien | **verweigert** („contains modified or untracked files, use --force“) – getrackte Änderungen und ungetrackte Dateien bleiben erhalten; **git-ignorierte Dateien (z. B. `__pycache__/`) löscht ein normales `remove` ohne Rückmeldung** |
| Hook-Stufen Claude | `worktree add/list/remove/prune`, `branch -d`, `merge --ff-only`: ja · `branch -D`: fragen · **`worktree remove --force`: ja** (Stand v8; seit v9: `remove --force` fragt) |
| Hook-Stufen Teams | `worktree add/remove/prune`, `branch -d`: ja · `branch -D`, `merge`: nein · **`worktree remove --force`: ja** (Stand v8; seit v9: `add` und `remove --force` nein) |

## Nur dokumentiert / abgeleitet (nicht gemessen)

- Claude Code und Vibe laden im Worktree dessen Hook-Dateien (`.claude/settings.json` mit `$CLAUDE_PROJECT_DIR`, `.vibe/hooks.toml`,
  beide getrackt) und damit dessen `normen.py`.
- Ein Worktree teilt das Objekt-Archiv und die Branches mit dem Hauptordner; Commits im Team-Branch sind sofort im Hauptordner
  sichtbar (Übernahme per `git merge --ff-only` durch Claude).
- Getrackte Sperrpfade lassen sich im Worktree nicht ausblenden (kein sparse-checkout gemessen).

## Offen

- Vibe-Lauf im Worktree mit Auftrag (hier nur Hook-Entscheidungen gemessen, kein echter Lauf).
- sparse-checkout, um getrackte Sperrpfade im Team-Worktree wegzulassen.
- Wie Claude den Worktree-Pfad im Auftrag nennt, ohne dass G5 (Prompt-Prüfung) oder G4-B („außerhalb“) Fehlalarme auslöst.

## Vorschlag (Entscheidung der Inhaberin)

1. **Lücke schließen – umgesetzt in v9 (Entscheidung der Inhaberin 17.11.):** `git worktree remove --force|-f` als destruktiv werten (N01, wie `branch -D`);
   für Teams auch `git worktree add` sperren (Worktrees legt nur Claude an). Normänderung → vorher Advisor (S07 Punkt 5).
2. **Worktree je Team-Lauf als Option**, nicht als Standard: lohnt bei parallelen Sitzungen im selben Repository. Ablauf:
   Claude legt den Worktree **innerhalb** des Projekts an (`.worktrees/<lauf>`, in `.gitignore`; außerhalb sperrt G4-B die
   Normen-Befehle) mit Branch `team/<lauf>`, führt dort `normen.py auftrag` aus, startet das Team mit
   dem Worktree als Projektordner, prüft dort Diff und Tests, übernimmt per `git merge --ff-only`, räumt mit
   `git worktree remove` (ohne `--force`) und `git branch -d` auf. Getrackte Sperrpfade sind im Worktree vorhanden – für Projekte
   mit getrackten Sperrpfaden erst sparse-checkout klären.
