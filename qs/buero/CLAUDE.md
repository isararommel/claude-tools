# Büro @@TITEL@@

Dies ist das Arbeitsbüro für die Rolle @@TITEL@@. Hier werden eingereichte Arbeiten begutachtet.

## Büroordnung

- **Eingang:** Eingehende Prüfaufträge liegen unter `eingang/<JJJJ-MM-TT>-<titel>/auftrag.md`.
- **Ausgang:** Fertige Gutachten werden unter `ausgang/<JJJJ-MM-TT>-<titel>/gutachten.md` abgelegt, eventuelle Anlagen (Entwürfe, Screenshots) unter `ausgang/<JJJJ-MM-TT>-<titel>/anlagen/`.
- **Lesezugriff auf den Gegenstand:** Starte die Sitzung mit:
  `claude --agent @@ROLLE@@ --allowedTools "Read(//<pfad>/**)" "Grep(//<pfad>/**)" "Glob(//<pfad>/**)"`
  (doppelter Schrägstrich für absolute Pfade). Ohne diese Schalter fragt Claude beim Lesen außerhalb einmal nach.

## Arbeitsablauf

1. Finde den neuesten unbearbeiteten Auftrag im Ordner `eingang/` (unbearbeitet = es existiert noch kein gleichnamiger Ordner in `ausgang/`).
2. Lies `auftrag.md` und erfasse den Gegenstand über den angegebenen Verweispfad.
3. Führe die Begutachtung gemäß deiner Rollenbeschreibung durch.
4. Schreibe das Gutachten im verbindlichen Format nach `ausgang/<JJJJ-MM-TT>-<titel>/gutachten.md` (und Anlagen nach `anlagen/`).
5. Melde am Ende kurz und präzise, wo das fertige Gutachten liegt.

## Format eines Auftrags (`auftrag.md`)

Aufträge müssen folgenden Aufbau haben:

```markdown
# Titel: <Kurzer, aussagekräftiger Titel>

## Gegenstand
- Absoluter Pfad und Commit nur als Verweis (keine Kopie des Projekts in den Eingang!).
- Bei Weboberflächen: URL, Zugangs- oder Startanleitung sowie relevante Unterlagen.

## Fragestellung
<Konkrete Fragen an den Gutachter>

## Rahmen
- Zielgruppe: <Zielgruppe des Gegenstands>
- Grenzen: <Vorgaben, Einschränkungen, Nicht-Ziele>

## Einreicher
<Rolle oder Name des Einreichers>
```
