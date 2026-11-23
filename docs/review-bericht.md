# Review: Branch `<branch>` (<Anlass, z. B. Normen v17, PR #nn>) – <JJJJ-MM-TT>

Ablage: `docs/reviews/<JJJJ-MM-TT>-<branch>.md`. Claude schreibt den Bericht aus den Antworten der Teams und dem eigenen Review
(Rohausgaben bleiben im Lauf-Ordner), prüft jeden Befund selbst und committet den Bericht auf dem Branch. Im PR nur ein Verweis.
In öffentlichen Repositories ohne private Bezüge (Namen, Server, private Pfade).

## Gegenstand
<`git diff <basis>...<commit>`; welche Dateien; was nicht doppelt geprüft wurde (z. B. eingespielte Kopien, per `cmp` belegt);
Gruppen mit Thema und Größe>

## Prüfer und Ablauf

| Prüfer | Modell | Lauf | Ergebnis |
|---|---|---|---|
| Claude | `/code-review <stufe>` | – | <n> Befunde |
| mistral-team | <active_model aus export.json>, `--agent ask` | <Schritte, Zeit, outcome; zweiter Schritt ja/nein> | <n> Befunde |
| gemini-analyst | <Modell>, Nur-Lesen | <Zeit, vollständig/abgebrochen> | <n> Befunde |

Status: **bestätigt** = von Claude nachgestellt (Test, Befehl, Interpreter); **plausibel** = am Code gelesen, nicht
nachgestellt; **verworfen** = trifft nicht zu (Grund); **Grenze** = bleibt, steht im CHANGELOG; **zurückgestellt** = nicht in
diesem Paket.

## Befunde

| Nr. | Ort | Befund | Fehlerszenario | Quelle | Status |
|---|---|---|---|---|---|
| 1 | <datei `funktion`> | <was falsch ist> | <Eingabe → falsches Ergebnis> | <Claude \| Mistral \| Gemini \| Advisor-Frage> | <Status, bei „verworfen“ mit Grund> |

Doppelte Befunde stehen einmal, mit allen Quellen.

## Nicht geprüft
<Prüffragen oder Gruppen, die kein Prüfer abgedeckt hat>

## Befunde zum Verfahren
<was am Ablauf hakte (Zeitlimit, Freigaben, Format); gemessene Werte für spätere Läufe>

## Ergebnis
Mergereif: <ja|nein>

<welche bestätigten Befunde vor dem Merge behoben werden (mit Test) und wo (Paket, PLAN.md)>

Die Zeile `Mergereif: ja` (genau so, eigene Zeile, nur einmal) prüft `normen.py merge` bei großen Meilensteinen (N11, v17);
erst setzen, wenn alle bestätigten Befunde behoben sind.
