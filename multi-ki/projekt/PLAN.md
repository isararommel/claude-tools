# PLAN – zentrale Aufgabenliste

**Jede Sitzung beginnt hier.** Sitzungen werden regelmäßig mit `/clear` neu gestartet, um Kontingent zu sparen. Deshalb steht
hier alles, was eine frische Sitzung zum Weiterarbeiten braucht: Stand, nächste Aufgaben mit genug Einzelheiten, offene Fragen.
Nach jeder erledigten Aufgabe wird diese Datei aktualisiert (abhaken, nächste Aufgabe ausformulieren) und mitcommittet.

*Stand: TT.MM.JJJJ*

## Verweise

| Datei | Wofür |
|---|---|
| [CLAUDE.md](CLAUDE.md) | Hinweise für Claude, Testbefehl, Datenschutz |
| [docs/multi-ki-ablauf.md](docs/multi-ki-ablauf.md) | Ablauf mit mistral-team / gemini-analyst |
| [normen/kurz.md](normen/kurz.md) | Agenten-Normen (Kurzfassung) |

## Arbeitsweise (kurz)

- Eigener Branch je Aufgabe, PR, Merge über `python3 normen/normen.py merge <PR>`; Testbefehl siehe `CLAUDE.md`.
- Pakete so schneiden, dass danach `/clear` möglich ist (S08): Befunde sofort hier festhalten, am Paketende committen und
  „/clear möglich“ melden. Ausnahme: stark zusammenhängende Pakete (Grund nennen).
- Projektbesonderheiten (gesperrte Pfade, Server, Abläufe) hier in Stichworten.

## Erledigt (letzte Schritte)

- ✅ TT.MM. Kurzbeschreibung – PR #N

## Nächste Aufgaben (in dieser Reihenfolge)

### 1. Titel der Aufgabe

Ziel: was am Ende anders ist.
Branch: `name`. Stand: noch nicht begonnen.
Schritte: 1. … 2. … (so ausführlich, dass eine frische Sitzung ohne Rückfrage loslegt: Dateien, Entscheidungen, Fallstricke).
Abnahme: Testbefehl, `normen.py pruefen --diff`, was sonst geprüft wird.

## Offene Fragen an die Inhaberin

- …
