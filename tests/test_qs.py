#!/usr/bin/env python3
"""Tests für qs/einrichten.sh: erzeugt aus den Quell-Vorlagen in qs/ ein QS-Projekt mit drei Gutachter-Büros
(und mit --benutzer-agents Sub-Agenten) in einem Temp-Ordner mit Temp-HOME – das echte ~/.claude bleibt unberührt.
Das Skript überschreibt nichts: unveränderte Zieldateien bleiben, abweichende landen als <datei>.vorlage daneben."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKRIPT = ROOT / "qs" / "einrichten.sh"
GUTACHTEN = (ROOT / "qs" / "gutachten-format.md").read_text(encoding="utf-8").strip()
SCHLUESSEL = ("name", "titel", "description", "tools-buero", "tools-gutachter")
OK = FAIL = 0
ENV = {}


def check(name, bedingung, info=""):
    global OK, FAIL
    if bedingung:
        OK += 1
    else:
        FAIL += 1
        print(f"FAIL {name} {info}")


def kopf(pfad):  # YAML-Kopf einer Rollen-Quelle per Text-Zerlegung (wie im Skript)
    zeilen = pfad.read_text(encoding="utf-8").split("\n")
    werte, rollentext = {}, ""
    if zeilen and zeilen[0].strip() == "---" and "---" in zeilen[1:]:
        ende = zeilen.index("---", 1)
        for zeile in zeilen[1:ende]:
            schluessel, _, wert = zeile.partition(":")
            werte[schluessel.strip()] = wert.strip()
        rollentext = "\n".join(zeilen[ende + 1:]).strip()
    return werte, rollentext


def agent_kopf(text):  # Kopf (zwischen ---) einer erzeugten Agent-Datei
    zeilen = text.split("\n")
    ende = zeilen.index("---", 1)
    werte = {}
    for zeile in zeilen[1:ende]:
        schluessel, _, wert = zeile.partition(":")
        werte[schluessel.strip()] = wert.strip()
    return werte


def lauf(*argumente):
    return subprocess.run(["bash", str(SKRIPT)] + [str(a) for a in argumente],
                          capture_output=True, text=True, env=ENV)


SANDBOX = Path(tempfile.mkdtemp())
try:
    HOME = SANDBOX / "home"  # Temp-HOME für den Skriptaufruf – nie das echte ~/.claude berühren
    ZIEL = SANDBOX / "qs-ziel"
    HOME.mkdir()
    ZIEL.mkdir()
    HEIM = os.path.realpath(HOME)  # physisch auflösen – das Skript löst Pfade ebenfalls physisch auf (pwd -P)
    Z = Path(os.path.realpath(ZIEL))
    ENV.update(dict(os.environ, HOME=HEIM))

    daten = []  # [(name, kopf-werte, rollentext)] alphabetisch nach Rollen-Datei
    for pfad in sorted((ROOT / "qs" / "rollen").glob("*.md")):
        werte, rollentext = kopf(pfad)
        check(f"Quell-Kopf vollständig ({pfad.name})", all(s in werte for s in SCHLUESSEL), str(werte))
        check(f"tools-buero ohne Bash/Agent ({pfad.name})",
              not {"Bash", "Agent"} & {t.strip() for t in werte.get("tools-buero", "").split(",")},
              werte.get("tools-buero", ""))
        if "name" in werte:
            daten.append((werte["name"], werte, rollentext))
    namen = [d[0] for d in daten]

    # 1. Lauf mit --benutzer-agents
    r1 = lauf(ZIEL, "--benutzer-agents")
    check("1. Lauf --benutzer-agents: Exit 0", r1.returncode == 0, r1.stdout + r1.stderr)
    for name, _, _ in daten:
        B = Z / f"buero-{name}"
        for pfad in (B / "eingang" / ".gitkeep", B / "ausgang" / ".gitkeep", B / "CLAUDE.md",
                     B / ".claude" / "settings.json", B / ".claude" / "agents" / f"{name}.md"):
            check(f"1. Lauf erzeugt {pfad.name} ({name})", pfad.is_file(), str(pfad))
        check(f"1. Lauf installiert Sub-Agent ({name})",
              (Path(HEIM) / ".claude" / "agents" / f"gutachter-{name}.md").is_file())

    # Büro-Einstellungen
    for name, _, _ in daten:
        pfad = Z / f"buero-{name}" / ".claude" / "settings.json"
        einstellungen = {}
        try:
            einstellungen = json.loads(pfad.read_text(encoding="utf-8"))
            check(f"settings.json ist JSON ({name})", True)
        except ValueError as fehler:
            check(f"settings.json ist JSON ({name})", False, str(fehler))
        check(f"autoMemoryEnabled false ({name})",
              einstellungen.get("autoMemoryEnabled") is False, str(einstellungen.get("autoMemoryEnabled")))
        check(f"blockWritesOutsideWorkingDirectories true ({name})",
              (einstellungen.get("permissions") or {}).get("blockWritesOutsideWorkingDirectories") is True,
              str(einstellungen.get("permissions")))
        ausschluss = einstellungen.get("claudeMdExcludes") or []
        for eintrag in (f"{HEIM}/.claude/CLAUDE.md", f"{Z}/CLAUDE.md", "/CLAUDE.md",
                        f"{Z}/buero-{name}/eingang/**/CLAUDE.md"):
            check(f"claudeMdExcludes enthält {eintrag}", eintrag in ausschluss, str(ausschluss))

    # Büro-Agent
    for name, werte, _ in daten:
        inhalt = (Z / f"buero-{name}" / ".claude" / "agents" / f"{name}.md").read_text(encoding="utf-8")
        k = agent_kopf(inhalt)
        check(f"Büro-Agent name ({name})", k.get("name") == name, str(k.get("name")))
        check(f"Büro-Agent tools ({name})", k.get("tools") == werte.get("tools-buero"), str(k.get("tools")))
        check(f"Büro-Agent ohne omitClaudeMd ({name})", "omitClaudeMd" not in k, str(k))
        check(f"Büro-Agent mit Gutachten-Format ({name})", GUTACHTEN in inhalt)

    # Sub-Agent im Temp-HOME
    for name, werte, rollentext in daten:
        inhalt = (Path(HEIM) / ".claude" / "agents" / f"gutachter-{name}.md").read_text(encoding="utf-8")
        k = agent_kopf(inhalt)
        check(f"Sub-Agent name ({name})", k.get("name") == f"gutachter-{name}", str(k.get("name")))
        check(f"Sub-Agent omitClaudeMd ({name})", k.get("omitClaudeMd") == "true", str(k.get("omitClaudeMd")))
        check(f"Sub-Agent tools ({name})", k.get("tools") == werte.get("tools-gutachter"), str(k.get("tools")))
        check(f"Sub-Agent ohne Write/Edit/Bash/Agent ({name})",
              not {"Write", "Edit", "Bash", "Agent"} & {t.strip() for t in k.get("tools", "").split(",")},
              str(k.get("tools")))
        einleitung = inhalt.split(rollentext, 1)[0] if rollentext else inhalt
        check(f"Sub-Agent Einleitung mit advisor ({name})", "advisor" in einleitung, einleitung[:80])
        check(f"Sub-Agent mit Gutachten-Format ({name})", GUTACHTEN in inhalt)

    # Keine Platzhalter in irgendeiner erzeugten Datei
    reste = [str(p) for p in list(Z.rglob("*")) + list(Path(HEIM).rglob("*"))
             if p.is_file() and "@@" in p.read_text(encoding="utf-8")]
    check("Kein @@ in erzeugten Dateien", not reste, str(reste))

    # 2. Lauf: alles vorhanden, keine .vorlage
    r2 = lauf(ZIEL, "--benutzer-agents")
    check("2. Lauf: Exit 0", r2.returncode == 0, r2.stdout + r2.stderr)
    check("2. Lauf: nur vorhanden-Zeilen",
          "  vorhanden  " in r2.stdout and "  neu        " not in r2.stdout and "  abweichend " not in r2.stdout,
          r2.stdout)
    vorlagen = list(Z.rglob("*.vorlage")) + list(Path(HEIM).rglob("*.vorlage"))
    check("2. Lauf: keine .vorlage", not vorlagen, str(vorlagen))

    # 3. Lauf nach Änderung einer Büro-CLAUDE.md
    if namen:
        geaendert = Z / f"buero-{namen[0]}" / "CLAUDE.md"
        soll = geaendert.read_text(encoding="utf-8")
        geaendert.write_text(soll + "\nFür den Test geändert.\n", encoding="utf-8")
        r3 = lauf(ZIEL, "--benutzer-agents")
        check("3. Lauf: Exit 0", r3.returncode == 0, r3.stdout + r3.stderr)
        check("3. Lauf: abweichend gemeldet", "  abweichend " in r3.stdout, r3.stdout)
        vorlage = Path(str(geaendert) + ".vorlage")
        check("3. Lauf: .vorlage entstanden", vorlage.is_file(), str(vorlage))
        check("3. Lauf: veränderte Datei unverändert",
              geaendert.read_text(encoding="utf-8") == soll + "\nFür den Test geändert.\n")
        check("3. Lauf: .vorlage mit erzeugter Fassung",
              vorlage.is_file() and vorlage.read_text(encoding="utf-8") == soll)

    # Aufruf ohne Ziel bzw. mit nicht vorhandenem Ziel
    check("Aufruf ohne Ziel: Exit 64", lauf().returncode == 64)
    check("Aufruf mit fehlendem Ziel: Exit 64", lauf(SANDBOX / "gibt-es-nicht").returncode == 64)
finally:
    shutil.rmtree(SANDBOX)

print(f"test_qs: {OK} ok, {FAIL} fehlgeschlagen")
sys.exit(1 if FAIL else 0)
