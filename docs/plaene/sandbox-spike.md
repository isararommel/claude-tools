# Sandbox-Spike (Normen v7, Paket G7) – Messbericht

Stand: 2026-11-16 · Claude Code 2.1.325 · macOS (Seatbelt) · nur Messung, **keine Einstellung geändert**
(Prüfsummen der Benutzer- und Projekt-Einstellungen vorher = nachher).

## Aufbau

- Je Lauf ein `claude -p --model haiku --settings <datei>` mit der Sandbox als Einstellung nur für diesen Lauf
  (`sandbox.enabled`, `failIfUnavailable: true`, `allowUnsandboxedCommands: false`, `autoAllowBashIfSandboxed: false`),
  jede Probe einzeln per `--allowedTools` freigegeben; ausgewertet wurden die Roh-Ergebnisse der Werkzeugaufrufe (stream-json).
- Lauf A: leerer Wegwerf-Ordner unter `$TMPDIR` ohne Projekt-Hooks. Lauf B: Wegwerf-Klon von claude-tools mit lokalem Remote
  (Projekt-Hooks aktiv). Das echte Repository wurde nicht angefasst.
- Alle Messungen im `-p`-Modus; Aussagen gelten für diesen Modus.

## Gemessen

| Probe | Ergebnis | Beleg / Bedingung |
|---|---|---|
| Schreiben im Arbeitsordner | geht | – |
| Schreiben im Home-Ordner (über `python3`, an der Freigabe-Ebene vorbei) | **gesperrt** | `PermissionError: [Errno 1] Operation not permitted` (Kernel) |
| Schreiben im Home-Ordner (über `touch`) | gesperrt | schon die Freigabe-Ebene: „needs approval … outside the working directories“ |
| Netz zu nicht freigegebener Domain | **gesperrt** | `sandbox_violations: deny network-outbound …:443` |
| Netz zu freigegebener Domain (`api.github.com`), `git ls-remote` über HTTPS | geht | `network.allowedDomains` |
| `gh api …` | ohne Zusatz: TLS-Fehler `x509: OSStatus -26276` (dokumentiert) | lief mit `enableWeakerNetworkIsolation` + weiteren Freigaben (Kombination, s. u.) |
| `git push --dry-run` zu GitHub über HTTPS (Schlüsselbund) | geht | – |
| `git checkout -b`, `git commit` | geht | – |
| `git push` an ein lokales Remote außerhalb des Arbeitsordners | scheitert | „unable to create temporary object directory“ |
| `bash agenten-normen/einrichten.sh` / `normen.py aktualisieren` | scheitert am Ende | `.git/config` ist geschützt („could not lock config file“), `core.hooksPath` wird nicht gesetzt |
| **Temp-Ordner** | **umgeleitet** | In der Sandbox ist `$TMPDIR` ein eigener Ordner (`/tmp/claude-<uid>`); Python (`tempfile`) nutzt ihn und kann schreiben. `mktemp -d` von macOS nutzt den System-Temp-Ordner und scheitert: „Operation not permitted“. |
| `make test` (claude-tools) | 905 ok, 3 Fehler | die drei Fälle von `einrichten.sh` mit `mktemp -d` (siehe Temp-Ordner) |
| `normen.py pruefen --diff`, `auftrag`, `auftrag --ende` | geht | – |
| Normen-Hook (PreToolUse) | **greift weiter** | Köder des Selbsttests und G4-Prüfung gesperrt |
| `normen.py selbsttest` | scheitert, Ursache: kein Netz | `deny network-outbound api.anthropic.com:443` – Domain stand nicht in der Freigabeliste; mit Freigabe nicht gemessen |
| **vibe** (echter Aufruf mit `--prompt-file`) | ohne Freigaben: „initialize failed: app-server closed“ | lief („OK“, Schlüsselbund funktioniert) mit der Kombination `network.allowLocalBinding: true`, `filesystem.allowWrite: ["~/.vibe", "~/.gemini"]`, `enableWeakerNetworkIsolation: true`, Domain `api.mistral.ai`. **Mindestmenge nicht ermittelt.** |
| **agy** (`-p`) | ohne Freigaben: `listen tcp 127.0.0.1:0: bind: operation not permitted` | lief („OK“) mit derselben Kombination und Domain `*.googleapis.com` (Wildcard wirkt). **Mindestmenge nicht ermittelt.** |
| `excludedCommands: ["vibe *", "agy *"]`, `["vibe:*", "agy:*"]`, auch mit `allowUnsandboxedCommands: true` | im `-p`-Modus keine Ausnahme | vibe/agy scheiterten in allen drei Varianten mit denselben Fehlern wie ohne Ausnahme |
| Verkettete Aufrufform `RUN=…; cd … && vibe … > "$RUN/…"` | im `-p`-Modus nicht ausführbar | Freigabe-Ebene: „cd + Ausgabe-Umleitung braucht ausdrückliche Freigabe“ |

## Nur dokumentiert (nicht selbst gemessen)

- Read/Edit/Write, WebFetch, MCP-Server und Hooks laufen **außerhalb** der Sandbox; die Sandbox wirkt nur auf Bash und dessen
  Unterprozesse. Lesen ist rechnerweit erlaubt (auch `~/.ssh`), außer Pfade unter `filesystem.denyRead` / `sandbox.credentials`.
- Geschützt auch im Arbeitsordner: `.claude`-Einstellungen, `.claude/{agents,hooks,skills,commands}`, `.mcp.json`, `.git/hooks`,
  `.git/config`. Sub-Agenten erben die Sandbox der Sitzung.
- Ohne `failIfUnavailable: true` läuft Claude Code bei fehlender Sandbox still ungeschützt weiter.
- Freigaben wie `allowLocalBinding`, `allowWrite` und `allowedDomains` gelten für **jeden** Bash-Befehl in der Sandbox, nicht nur
  für vibe/agy.

## Nachtrag Paket D: interaktiv gemessen (20.11.2026, Claude Code 2.1.328)

Aufbau: interaktive Sitzung `claude --model haiku --permission-mode default|auto --settings <datei>` in einem Wegwerf-Repo im
Lauf-Ordner, gesteuert über ein Pseudo-Terminal (Python `pty`, kein neues Paket). Sandbox-Werte nur in der `--settings`-Datei:
`enabled`, `failIfUnavailable: true`, `allowUnsandboxedCommands: false`, `autoAllowBashIfSandboxed: true`, je Lauf mit oder ohne
`excludedCommands`. Beleg: Sitzungs-Transkript (rohe Werkzeug-Ergebnisse), Rückfragen aus dem Bildschirmtext. Haiku bekam
wörtliche Befehle; was wirklich lief, steht im Transkript. Prüfsumme der Benutzer-Einstellungen vorher = nachher; geändert haben
sich nur Vertrauens-Eintrag und Transkripte (`~/.claude.json`, `~/.claude/projects/`).

Vorab im Programm nachgesehen (S04, Zeichenketten der installierten Version):
- **`excludedCommands` zählt nur aus Benutzer-, verwalteten oder `--settings`-Einstellungen, sobald `allowUnsandboxedCommands: false`
  gilt** (Meldung „excludedCommands restricted to trusted settings tiers: ignoring …“). Ein Eintrag in `.claude/settings.json`
  oder `settings.local.json` des Projekts wird dann still ignoriert.
- Eine Ausnahme gilt nur, „wo eine Rückfrage den Lauf ohne Sandbox freigeben kann“ – das erklärt den `-p`-Befund oben.
- Verschachtelte Sitzungen erben `CLAUDE_CODE_CHILD_SESSION` und speichern dann kein Transkript;
  `CLAUDE_CODE_FORCE_SESSION_PERSISTENCE=1` schaltet es wieder ein. Ohne `--permission-mode` startete die Probe im Auto-Modus.

| Fall | Ergebnis |
|---|---|
| Sandbox aktiv? `echo $TMPDIR`, `mktemp -d`, `python3` schreibt außerhalb | `TMPDIR=/tmp/claude-<uid>`; `mktemp -d` und `python3` scheitern mit „Operation not permitted“ – **ohne Rückfrage** (Kernel) |
| Netz zu nicht freigegebener Domain (`curl https://example.com`), Vordergrund | Rückfrage „Network request outside of sandbox · Host … Do you want to allow this connection?“; Option 2 trägt die Domain dauerhaft in die **Benutzer-Einstellungen** ein |
| Derselbe Befehl aus einem **Hintergrund-Sub-Agenten** | Rückfrage erreicht die Hauptoberfläche; nach „Nein“ erhält der Sub-Agent `deny network-outbound … (user denied)` |
| vibe / agy ohne Ausnahme | scheitern wie im `-p`-Modus („app-server closed“, `bind: operation not permitted`) |
| `excludedCommands: ["vibe *", "agy *"]`, **bloßer Befehl** | Rückfrage „Bash command (unsandboxed) … This command requires approval“ (Option „don't ask again for: vibe *“); nach „Ja“ laufen beide außerhalb der Sandbox („OK“) |
| `excludedCommands: ["vibe", "agy"]` (bloßer Name) | **keine** Ausnahme – Befehle mit Argumenten laufen in der Sandbox und scheitern |
| `vibe … \| tail -5` | keine Ausnahme, keine Rückfrage, läuft in der Sandbox und scheitert |
| `vibe … < /dev/null` | keine Ausnahme (scheitert) |
| `vibe … > datei 2>&1` | keine Ausnahme (scheitert) |
| `RUN=…; cd <projekt> && vibe … > "$RUN/…" 2>&1` (Aufrufform von `mistral-team`) | normale Freigabe-Rückfrage, danach **in** der Sandbox → scheitert |
| `cd <eigener Arbeitsordner> && vibe …` | Claude Code entfernt das `cd` auf den eigenen Arbeitsordner; Ausnahme greift („OK“) |
| ausgenommenes vibe aus **Hintergrund-Sub-Agent** | Rückfrage „Bash command (unsandboxed) · from the general-purpose agent“ in der Hauptoberfläche; nach „Ja“ läuft vibe („OK“) |
| ausgenommenes vibe im **Auto-Modus** | **keine Rückfrage**: der Auto-Modus gibt frei, vibe läuft außerhalb der Sandbox („OK“) |
| Fester Lauf-Ordner `/tmp/claude-<uid>/vibe-runs/…` | Write-Werkzeug schreibt hinein; Bash in der Sandbox schreibt hinein (`antwort.txt`, `--output-dir`); vibe außerhalb liest die Prompt-Datei; Lesen mit dem Read-Werkzeug braucht eine Freigabe (außerhalb des Arbeitsordners) |

Folgen:
- **Weg 2 (vibe/agy ausnehmen) ist machbar**, aber nur mit `excludedCommands` in den Benutzer-Einstellungen (oder `--settings`) und
  einer Aufrufform als **bloßer Befehl**: keine Variablenzuweisung davor, kein `cd` in einen anderen Ordner, keine Umleitung, keine
  Pipe. Die heutigen Aufrufe von `mistral-team` (`RUN=…; cd … && vibe … < /dev/null > "$RUN/antwort.txt" 2>&1`) und
  `gemini-analyst` (`RUN=…; R=…; ALLOW=…; agy …`) müssten umgestellt werden: Pfade wörtlich, Ergebnis über `--output-dir` bzw.
  die Werkzeug-Ausgabe statt `> antwort.txt`. vibe lief im Bash-Werkzeug ohne `< /dev/null`, ohne zu hängen (drei Läufe).
- Fester Lauf-Ordner: `/tmp/claude-<uid>/` ist in beiden Welten derselbe und beschreibbar – Kandidat für `vibe-runs`,
  `agy-runs`, `code-mode-runs` statt `${TMPDIR}`.
- Rückfragen aus Hintergrund-Sub-Agenten kommen an; im Auto-Modus entfallen sie für ausgenommene Befehle ganz. Die Sandbox ändert
  am Auto-Modus also nichts für vibe/agy; sie wirkt auf alle übrigen Bash-Befehle.

Nicht gemessen: ob `--output-dir` allein die Ausnahme verhindert (nur zusammen mit Umleitungen geprüft); agy aus einem
Hintergrund-Sub-Agenten und in der verketteten Form (nach dem vibe-Befund zu erwarten: keine Ausnahme); ob der Normen-Hook
die Prompt-Datei auch ohne `RUN=`-Zuweisung findet; Mindestmenge der Freigaben; `Bash(vibe:*)`-Schreibweise.

## Nicht gemessen (offen, Stand 16.11.; interaktive Punkte siehe Nachtrag Paket D)

- Mindestmenge der Freigaben für vibe, agy und `gh` (die Läufe änderten mehrere Werte zugleich).
- Schreiben ins Scratchpad der Sitzung (die Probe stoppte schon der Normen-Hook, vor der Sandbox).
- `normen.py selbsttest` mit freigegebener Anthropic-Domain; `git push -u` gegen GitHub.

## Folge für den Ablauf (gemessen)

`${TMPDIR}/vibe-runs` zeigt in der Sandbox auf einen **anderen Ordner** als außerhalb. Claude schreibt Prompt-Dateien mit dem
Write-Werkzeug (außerhalb der Sandbox) in den System-Temp-Ordner; Bash in der Sandbox sucht sie unter dem umgeleiteten `$TMPDIR`
und darf den System-Temp-Ordner nicht beschreiben. Vor einer Einführung müssen Lauf-Ordner und Code-Mode-Ordner einen festen Pfad
bekommen, der in beiden Welten gleich und beschreibbar ist.

## Zwei Wege (Entscheidung der Inhaberin)

**Entschieden am 16.11.2026: Weg 2 (vibe/agy ausnehmen), fürs Erste. Die Sandbox ist nicht aktiviert;** vor dem Einschalten
`excludedCommands` interaktiv prüfen. (20.11.: interaktiv geprüft – greift unter Bedingungen, siehe Nachtrag Paket D.)

Die Sandbox schließt L2 (Bash und Unterprozesse schreiben überall / gehen überall ins Netz) wirksam – belegt durch Kernel-Fehler und
Netz-Sperren. Ohne Anpassungen bricht sie aber den Ablauf (Teams, Temp-Ordner, `einrichten.sh`).

1. **vibe und agy in der Sandbox** mit Freigaben (`allowLocalBinding`, `allowWrite` für `~/.vibe` und `~/.gemini`, Domains
   `api.mistral.ai`, `*.googleapis.com`). Kosten: Die Freigaben gelten für alle Bash-Befehle – jeder Unterprozess darf dann in
   `~/.vibe`/`~/.gemini` schreiben (genau die Ordner, die N10 schützt) und jeden Google-API-Host erreichen (schwächt G5).
2. **vibe und agy ausnehmen** (Entscheidung 3 im Entwurf) – im `-p`-Modus hier nicht bestätigt; vor der Wahl interaktiv prüfen.

In beiden Fällen: fester Lauf-Ordner (s. o.), `einrichten.sh`/`aktualisieren` außerhalb der Sandbox (mit Rückfrage), Anthropic-Domain
für `selbsttest`, `enableWeakerNetworkIsolation` nur bei Bedarf für `gh`. Erst nach interaktiver Prüfung der offenen Punkte als
Vorlage-Block (ohne private Domains) in `agenten-normen/projekt/.claude/settings.json`.
