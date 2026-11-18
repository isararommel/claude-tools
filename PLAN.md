# PLAN – zentrale Aufgabenliste

**Jede Sitzung beginnt hier.** Die Inhaberin startet Sitzungen regelmäßig mit `/clear` neu, um Kontingent zu sparen. Deshalb steht
hier alles, was eine frische Sitzung zum Weiterarbeiten braucht: Stand, nächste Aufgaben mit genug Einzelheiten, offene Fragen.
Nach jeder erledigten Aufgabe wird diese Datei aktualisiert (abhaken, nächste Aufgabe ausformulieren) und mitcommittet.

*Stand: 18.11.2026 (v14 = Pakete B+C gemergt (PR #25), Sitzungen informiert; nächstes Paket: D, offen: A2 Punkte 4–6, G, H)*

## Verweise

| Datei | Wofür |
|---|---|
| [KONZEPT.md](KONZEPT.md) | Ziel und Aufbau von claude-tools |
| [CHANGELOG.md](CHANGELOG.md) | Normen-Versionen (aktuell v13; Einzelheiten aller früheren Pakete stehen dort) |
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

## Erledigt (letzte Schritte)

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

### D. Sandbox simulieren *(Frage 4, freigegeben 18.11.)*

Gemeint sind die offenen Punkte aus dem Sandbox-Spike (`docs/plaene/sandbox-spike.md`), nicht Rückfragen allgemein: greift
`excludedCommands` für vibe/agy interaktiv, kommen Sandbox-Rückfragen auch aus Hintergrund-Sub-Agenten an, fester Lauf-Ordner
statt umgeleitetem `$TMPDIR`. Der Spike lief nur mit `claude -p`; ein weiterer `-p`-Lauf belegt interaktives Verhalten nicht.
Messweg festlegen: interaktive Claude-Sitzung in einem Wegwerf-Repo mit Sandbox in `.claude/settings.local.json` (nur dort),
gesteuert über ein Pseudo-Terminal (tmux ist nicht installiert → `script`/Python `pty`, keine neuen Pakete ohne Freigabe).
Fälle: Bash-Befehl im Projekt, Schreiben außerhalb, vibe/agy-Aufruf, Hintergrund-Sub-Agent mit Bash. Bericht ergänzen.
Sandbox im echten Projekt einschalten = Einstellungsänderung → nur mit Freigabe. Nebenbei: Die Inhaberin bekommt viele
Rückfragen; der Skill `fewer-permission-prompts` kann häufige lesende Befehle aus den Transkripten in eine Allowlist übernehmen
(Vorschlag zeigen, nicht ohne Freigabe eintragen).

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
