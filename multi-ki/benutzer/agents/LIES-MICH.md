# Benutzerweite Agent-Definitionen (gehören nach ~/.claude/agents/)

`mistral-team.md`, `gemini-analyst.md` und `Explore.md` liegen auf dem Mac der Inhaberin in `~/.claude/agents/` und gelten dort
für alle Projekte. Hier liegen Kopien, damit ein neuer Rechner sie bekommt (`einrichten.sh --benutzer-agents`).
Alle drei enthalten die Regel „Den Advisor nie aufrufen“ (S07): Subagenten erben den Advisor der Hauptsitzung, eine technische
Sperre je Agent ist nicht dokumentiert.

Abgleich vom Mac in diese Vorlage (wenn die Fassungen in ~/.claude/agents geändert wurden):

    cp ~/.claude/agents/mistral-team.md ~/.claude/agents/gemini-analyst.md ~/.claude/agents/Explore.md \
       ~/Documents/Projekte/claude-tools/multi-ki/benutzer/agents/
