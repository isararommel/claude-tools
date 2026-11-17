# Recherche-Spike – Messbericht

Stand: 2026-11-17 · Vibe 3.1.2 (Mistral Large 4), agy (gemini-3.8-flash-high), Claude Code 2.1.326 · nur Messung im Wegwerf-Ordner.
Gleiche öffentliche Testfrage an jeden Weg: „Welche ist die aktuelle stabile Version von Python 3 und wann erschien sie? Zwei
Quellen mit URL und Datum.“

## Gemessen

| Weg | Ergebnis | Beleg |
|---|---|---|
| **Vibe, Lese-Modus** (`--agent ask`) | Websuche **abgelehnt** (`Tool execution denied by approval callback`, `tool_denied`). Vibe antwortete trotzdem **aus dem eigenen Wissen** mit veralteter Version und plausibel klingenden, nicht abgerufenen Quellen. | 7 Schritte, `active_model` Large 4 |
| **Vibe, normal** (`--smart-approve`) | Recherche läuft ohne Rückfrage: 9 Aufrufe `web_search`, **kein Seitenabruf** (ohne Vorgabe; mit der Vorgabe „Seiten öffnen“ öffnet Vibe Seiten, siehe Abnahme-Probe). Antwort mit vier python.org-/endoflife-Quellen und „abgerufen“-Datum – die Angaben stammen aber aus Suchergebnissen, nicht aus geöffneten Seiten. | 6 Schritte, Large 4 |
| **agy** (Aufrufform von `gemini-analyst`, Freigabeliste nur Lesebefehle) | Google-Suche läuft **ohne zusätzliche Freigabe** (kein Shell-Befehl). Antwort mit zwei Quellen und Datum. | Exit 0 |
| **Gegenprüfung Vibe ↔ agy** | übereinstimmend (gleiche Version, gleiches Datum) | – |
| **Claude, Websuche** (`standard`) | Treffer aus einem älteren Suchindex, widersprüchliche Stände; für aktuelle Fakten die Primärquelle direkt abrufen (Webseitenabruf), nicht der Trefferliste trauen. | – |
| **Normen-Hook bei Vibes Websuche** | greift nicht: die Vibe-Hooks prüfen nur `bash`, `write_file`, `search_replace`, `read_file`. Suchanfragen selbst sieht der Hook nicht; geprüft wird nur der Auftrag vorab (G5). | `.vibe/hooks.toml` |

## Abnahme-Probe mit der Vorlage (zwei Anbieter parallel)

Frage: Ende des Supports für Python 3.10 und Empfehlung für neue Projekte; ausgefüllte `recherche-auftrag.md` an beide Teams.

| Anbieter | Ergebnis |
|---|---|
| Vibe (`--smart-approve`) | Format eingehalten; mit der Vorgabe „Seiten öffnen“ wurden Primärquellen tatsächlich abgerufen (Werkzeuge heißen in Vibe 3.1.2 `connector_web_search` und `open_url`, Suche über Brave) – 5 Befunde „Seite abgerufen“ |
| agy | Format eingehalten, Suchbegriffe genannt; alle Befunde „nur Suchtreffer“, aber als „belegt“ eingestuft → Regel „nur Suchtreffer ⇒ höchstens abgeleitet“ in die Auftragsvorlage aufgenommen |
| Vergleich | EOL-Datum übereinstimmend, Stichprobe durch Claude (Webseitenabruf) bestätigt; Empfehlung für neue Projekte abweichend – im Bericht unter „Widersprüche“ |

## Folgen für Vorlagen und Ablauf

1. Recherche-Aufträge an Vibe laufen **nicht** im Lese-Modus, sondern mit `--smart-approve` und „Ändere keine Dateien“ (ohne
   offenen Auftrag sperrt der Hook das Schreiben ohnehin).
2. Die Auftragsvorlage verlangt: **ohne funktionierende Websuche abbrechen und das melden – nicht aus dem Gedächtnis antworten.**
3. Die Berichtsvorlage unterscheidet je Befund **„Seite abgerufen“** und **„nur Suchtreffer“**; „abgerufen am“ nur bei geöffneter
   Seite.
4. Suchanfragen verlassen den Rechner ungeprüft: Datenschutz hängt am Auftragstext (G5) und an der Regel, keine privaten,
   Forschungs- oder Geheimdaten in Fragen zu schreiben.
5. Wichtige Fragen doppelt (Gemini + Mistral): die Gegenprüfung war hier billig und eindeutig.

## Offen

- Größere Recherche (viele Quellen, widersprüchliche Lage) – nur eine einfache Faktfrage gemessen.
- Ob agy Seiten tatsächlich öffnet oder nur Suchtreffer nutzt (Protokoll von agy nicht ausgewertet).
- `deep-research`-Skill von Claude (kostet Claude-Kontingent; nicht gemessen).
