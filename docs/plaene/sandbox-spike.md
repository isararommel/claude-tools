# Sandbox-Spike (Normen v7, Paket G7) – Messbericht

Stand: 2026-11-16 · Claude Code 2.1.325 · macOS (Seatbelt) · nur Messung, **keine Einstellung geändert**
(Prüfsummen der Benutzer- und Projekt-Einstellungen vorher = nachher).

## Aufbau

- Je Lauf ein `claude -p --model haiku --settings <datei>` mit der Sandbox als Einstellung nur für diesen Lauf
  (`sandbox.enabled`, `failIfUnavailable: true`, `allowUnsandboxedCommands: false`, `autoAllowBashIfSandboxed: false`),
  jede Probe einzeln per `--allowedTools` freigegeben; ausgewertet wurden die Roh-Ergebnisse der Werkzeugaufrufe (stream-json).
- Lauf A: leerer Wegwerf-Ordner unter `$TMPDIR` ohne Projekt-Hooks. Lauf B: Wegwerf-Klon von claude-tools mit lokalem Remote
  (Projekt-Hooks aktiv). Das echte Repository wurde nicht angefasst.

## Gemessen

| Probe | Ergebnis | Beleg / Bedingung |
|---|---|---|
| Schreiben im Arbeitsordner | geht | – |
| Schreiben im Home-Ordner (über `python3`, an der Freigabe-Ebene vorbei) | **gesperrt** | `PermissionError: [Errno 1] Operation not permitted` (Kernel) |
| Schreiben im Home-Ordner (über `touch`) | gesperrt | schon die Freigabe-Ebene: „needs approval … outside the working directories“ |
| Netz zu nicht freigegebener Domain | **gesperrt** | `sandbox_violations: deny network-outbound …:443` |
| Netz zu freigegebener Domain (`api.github.com`), `git ls-remote` über HTTPS | geht | `network.allowedDomains` |
| `gh api …` | geht nur mit `enableWeakerNetworkIsolation: true` | sonst `x509: OSStatus -26276` (dokumentiert) |
| `git push --dry-run` zu GitHub über HTTPS (Schlüsselbund) | geht | – |
| `git checkout -b`, `git commit` | geht | – |
| `git push` an ein lokales Remote außerhalb des Arbeitsordners | scheitert | „unable to create temporary object directory“ |
| `bash agenten-normen/einrichten.sh` / `normen.py aktualisieren` | scheitert am Ende | `.git/config` ist geschützt („could not lock config file“), `core.hooksPath` wird nicht gesetzt |
| `make test` (claude-tools) | 905 ok, **3 Fehler** | `mktemp` unter `$TMPDIR` außerhalb des Arbeitsordners: „Operation not permitted“ (laut Doku wäre `$TMPDIR` beschreibbar – hier nicht) |
| `normen.py pruefen --diff`, `auftrag`, `auftrag --ende` | geht | – |
| Normen-Hook (PreToolUse) | **greift weiter** | Köder des Selbsttests und G4-Prüfung gesperrt |
| `normen.py selbsttest` | scheitert | das verschachtelte `claude` kommt nicht zum Werkzeugaufruf („unklar“) |
| **vibe** (echter Aufruf mit `--prompt-file`) | geht, wenn freigegeben | `network.allowLocalBinding: true` (interner App-Server), `filesystem.allowWrite: ["~/.vibe"]`, Domain `api.mistral.ai`; Schlüsselbund funktioniert. Ohne: „initialize failed: app-server closed“ |
| **agy** (`-p`) | geht, wenn freigegeben | `allowLocalBinding: true` (sonst `bind: operation not permitted`), `allowWrite: ["~/.gemini"]`, Domain `*.googleapis.com` (Wildcard wirkt); gesperrt blieb nur ein Profilbild-Host, ohne Folgen |
| `excludedCommands: ["vibe *", "agy *"]`, `["vibe:*", "agy:*"]`, auch mit `allowUnsandboxedCommands: true` | **wirkungslos** | vibe/agy liefen in allen drei Varianten weiter in der Sandbox und scheiterten wie ohne Ausnahme |
| Verkettete Aufrufform `RUN=…; cd … && vibe … > "$RUN/…"` | nicht ausführbar im `-p`-Modus | Freigabe-Ebene: „cd + Ausgabe-Umleitung braucht ausdrückliche Freigabe“ |

## Nur dokumentiert (nicht selbst gemessen)

- Read/Edit/Write, WebFetch, MCP-Server und Hooks laufen **außerhalb** der Sandbox; die Sandbox wirkt nur auf Bash und dessen
  Unterprozesse. Lesen ist rechnerweit erlaubt (auch `~/.ssh`), außer Pfade unter `filesystem.denyRead` / `sandbox.credentials`.
- Geschützt auch im Arbeitsordner: `.claude`-Einstellungen, `.claude/{agents,hooks,skills,commands}`, `.mcp.json`, `.git/hooks`,
  `.git/config`. Sub-Agenten erben die Sandbox der Sitzung.
- Ohne `failIfUnavailable: true` läuft Claude Code bei fehlender Sandbox still ungeschützt weiter.

## Nicht gemessen (offen)

- Rückfragen im interaktiven Modus und im Auto-Modus (im `-p`-Modus gibt es keine Rückfrage).
- Ob ein Befehl, der eine Freigabe braucht, aus einem **Hintergrund-Sub-Agenten** die Inhaberin erreicht.
- Warum `excludedCommands` hier nicht wirkt (Version, `-p`-Modus oder Mustersyntax) – drei Varianten, dann nach S03 angehalten.

## Vorschlag (Entscheidung der Inhaberin)

Die Sandbox schließt L2 (Bash und Unterprozesse schreiben überall / gehen überall ins Netz) wirksam – belegt durch Kernel-Fehler
und Netz-Sperren. Für den Alltag in diesem Ablauf reicht sie aber **nicht ohne Anpassungen**:

1. **vibe und agy in der Sandbox laufen lassen** statt sie auszunehmen (Ausnahmen wirkten nicht): `allowLocalBinding: true`,
   `filesystem.allowWrite: ["~/.vibe", "~/.gemini"]`, `network.allowedDomains` mit `api.mistral.ai`, `*.googleapis.com`,
   `github.com`, `api.github.com`; `enableWeakerNetworkIsolation: true` nur, wenn `gh` gebraucht wird (schwächt die Isolation).
2. **Beschreibbar machen**, was der Ablauf braucht: `$TMPDIR` (Tests, Lauf-Ordner der Teams, Code-Mode-Skripte) und das
   Scratchpad der Sitzung.
3. **Außerhalb der Sandbox** bleiben (mit Rückfrage): `einrichten.sh`/`aktualisieren` (schreiben `.git/config`),
   `normen.py selbsttest`, vermutlich auch `git push -u` (setzt den Upstream in `.git/config`; gegen GitHub nicht gemessen).
   Da `excludedCommands` hier nicht wirkte, ginge das nur über `allowUnsandboxedCommands: true` (Claude wiederholt einen
   gesperrten Befehl ohne Sandbox – mit Rückfrage); das ist vor der Einführung interaktiv zu prüfen.
4. Erst einführen, wenn die offenen Punkte interaktiv geprüft sind; dann als Vorlage-Block (ohne private Domains) in
   `agenten-normen/projekt/.claude/settings.json` und Projektwerte je Repository.
