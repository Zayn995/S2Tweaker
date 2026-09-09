"""Waisen-SID-Waechter (08.09.2026).

Die Idee stammt aus dem "Mod Validator" (Nexus 1285, DeadlyStr1ke). Seine
INI verraet, was er an fremden cfg-Dateien prueft, und einer der vier
Punkte ist fuer uns Gold wert:

  (a) `struct.begin` / `struct.end` paarweise ausgeglichen
  (b) Klammern paarweise
  (c) das Feld `SID` traegt denselben Namen wie sein Struct
  (d) **Waisen-SIDs: zeigt ein Patch auf eine SID, die es gar nicht gibt?**

Punkt (d) faengt genau die Sorte Fehler, die sonst NIEMAND bemerkt: ein
Spiel-Update benennt einen Knoten um, unser Patch schreibt weiter brav
seine Zeilen — nur eben ins Leere. Kein Absturz, keine Fehlermeldung, der
Regler tut nur nichts mehr. Molkerrs Bericht vom 07.09. war genau dieser
Fall, nur aus einem anderen Grund; die Suche danach hat einen ganzen Tag
gekostet.

Am empfindlichsten sind die Quest-Patches: der Mehrfach-Job-Schalter
haengt an acht namentlich genannten Knoten je Auftraggeber
(`RSQ01_SetTimer`, `RSQ01_If_LessThen3Tasks`, `RSQ01_Technical_GetQuest`
...) und an den Zaehlervariablen (`RSQ01_WarlockQuest`). Benennt GSC einen
davon um, ist der Schalter still tot.

METHODE: Es wird ein moeglichst breiter Patch-Satz gebaut (jedes
Bedienelement verstellt, dazu die zwei Baeume, die Referenzen erzeugen —
Fernrohre und Munitionswechsel). Dann wird jede erzeugte Datei gelesen und

  1. auf Struktur-Bilanz geprueft (a, b),
  2. auf `SID` == Struct-Name (c),
  3. Top-Level-Struct gegen die ZIELDATEI gehalten: mit `{bpatch}` muss er
     dort existieren, ohne `{bpatch}` darf er es NICHT (dann ist er als
     neuer Knoten gemeint), mit `{refkey=X}` muss X existieren,
  4. jede SID-REFERENZ (verschachteltes `SID`, `QuestSID`,
     `GlobalVariablePrototypeSID`, `ItemPrototypeSID`, `EffectSID` ...)
     gegen einen Index aller Struct-Namen und SID-Werte der Spieldaten
     gehalten (d).

Der Index kostet rund fuenf Sekunden ueber 490 Dateien; das ist der Preis
dafuer, keinen Namen zu erfinden.

⚠ Wird die Suite rot, ist das KEIN Testfehler: entweder hat ein
Spiel-Update etwas umbenannt (dann Builder nachziehen), oder ein neuer
Builder zeigt auf etwas, das es nicht gibt.
"""
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
GAMELITE = ROOT / "vanilla" / "Stalker2" / "Content" / "GameLite"
VANILLA = GAMELITE / "GameData"

from s2tweaker.gamedata import GameData
from s2tweaker.tweaks import Settings, build_patches, swappable_calibers
from s2tweaker.gui import SLIDER_FIELDS, CHECK_FIELDS

gd = GameData(str(VANILLA))
ok = 0


def check(cond, msg):
    global ok
    assert cond, msg
    ok += 1
    print(f"  OK  {msg}")


# --- 0) Ein moeglichst breiter Patch-Satz -------------------------------
# Sonden wie in test_wiring: Faktoren aufs Doppelte, Absolutwerte eine
# Stufe daneben, Schalter um. Die Regler, deren Vanilla-Wert 0 oder der
# Deckel selbst ist, brauchen eine eigene Sonde.
SPECIAL = {
    "fall_damage_pct": 50.0, "fast_travel_lock": 0.0, "slow_run_threshold_pct": 25.0,
    "evening_start_hour": 22.0, "armor_deflect_chance_pct": 50.0,
    "npc_weapon_rank_add": 2.0, "scope_sway_pct": 50.0,
    "trader_min_durability_pct": 0.0, "hud_compass": 2.0, "hud_crosshair": 2.0,
    "hud_body_markers": 2.0, "hud_stash_markers": 2.0, "pistol_slot_level": 3.0,
}

kw = {}
_default = Settings()
for field in sorted(set(SLIDER_FIELDS.values()) | set(CHECK_FIELDS.values())):
    value = getattr(_default, field)
    if isinstance(value, bool):
        kw[field] = not value
    elif field in SPECIAL:
        kw[field] = SPECIAL[field]
    elif isinstance(value, (int, float)):
        probe = value * 2 if value else 1.0
        kw[field] = (int(probe) or 1) if isinstance(value, int) else probe

# Die zwei Baeume, die REFERENZEN erzeugen statt nur Zahlen: der
# Fernrohr-Override legt abgeleitete Effekte an (`{refkey=<Effekt>}`), der
# Munitionswechsel tauscht eine Projektil-Liste aus. Beide werden aus den
# Spieldaten gewaehlt, nicht hardcodiert.
scope_sid = sorted(gd.scope_effects())[0]
kw["scope_overrides"] = {scope_sid: {"zoom": 1.5, "penalty": 0.5}}

_tables = swappable_calibers(gd)
_weapon = sorted(gd.player_weapons())[0]
_own = gd.weapon_caliber(_weapon)
_other = sorted(c for c in _tables if c != _own and _tables[c])[0]
kw["weapon_calibers"] = {_weapon: _other}

# Fraktionsbeziehungen: ein Paar mit dem Spieler und eines zwischen zwei
# Fraktionen - nur so entstehen die Laufzeit-Knoten (1.36.0) samt
# Startskript, und genau die haengen an Namen, die ein Spiel-Update
# umbenennen koennte.
kw["faction_relations"] = {k: v for k, v in (
    (gd.relation_pair_key("Duty", "Player"), 800),
    (gd.relation_pair_key("Duty", "Freedom"), -800)) if k}

# Der Mehrfach-Job-Schalter (dritter Entwurf 1.36.0) haengt an den
# empfindlichsten Namen im ganzen Werkzeug - die Sonde schaltet ihn ein
# (CHECK_FIELDS tut das ohnehin; hier steht es, damit es niemand entfernt).
kw["repeatable_jobs_multi"] = True

t0 = time.time()
PATCHES = build_patches(gd, Settings(mod_name="S2Tweaker", **kw))
build_s = time.time() - t0
check(len(PATCHES) > 50,
      f"breite Sonde erzeugt {len(PATCHES)} Patchdateien ({build_s:.1f}s)")


# --- 1) Struktur lesen --------------------------------------------------
BEGIN = re.compile(r"^(\S+)\s*:\s*struct\.begin\s*(\{[^}]*\})?\s*$")
LEAF = re.compile(r"^\s*([A-Za-z_\[][A-Za-z0-9_\]\[]*)\s*=\s*(.*?)\s*$")


def scan(text):
    """(Top-Level-Structs, Referenzen, Bilanzfehler).

    Top-Level-Struct = (Name, Attribute in {..}, Zeilennummer).
    Referenz = (Struct, Schluessel, Wert) fuer alles, was auf eine andere
    SID zeigt: verschachteltes `SID` und die *SID-Schluessel.
    """
    tops, refs, problems = [], [], []
    depth, current = 0, None
    for n, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        m = BEGIN.match(stripped)
        if m:
            if depth == 0:
                current = m.group(1)
                tops.append((current, m.group(2) or "", n))
            depth += 1
            continue
        if stripped == "struct.end":
            depth -= 1
            if depth < 0:
                problems.append(f"Zeile {n}: ein struct.end zu viel")
                depth = 0
            continue
        leaf = LEAF.match(line)
        if leaf and current:
            key, value = leaf.group(1), leaf.group(2)
            refs.append((current, key, value, depth, n))
    if depth != 0:
        problems.append(f"am Dateiende fehlen {depth} struct.end")
    return tops, refs, problems


# Schluessel, deren Wert auf eine andere SID zeigt. Bewusst als Liste statt
# "alles, was wie ein Bezeichner aussieht": `Title`/`Description` in
# MarkerPrototypes tragen LOKALISIERUNGS-Schluessel, die in keiner cfg als
# Struct stehen — die wuerden sonst jede Runde falschen Alarm schlagen.
REF_KEYS = {
    "ItemPrototypeSID", "AgentPrototypeSID", "QuestSID", "EffectSID",
    "FalseEffectSID", "WeatherSID", "GlobalVariablePrototypeSID",
    "StickinessAimAssistConeSID", "SnappingAimAssistConeSID",
    "MovingTrackingAimAssistConeSID", "StationaryTrackingAimAssistConeSID",
    "NextDialogSID",               # 1.36.0: der Menue-Boden in DialogPrototypes
}
# Listen, deren `[N] = <SID>`-Eintraege ebenfalls Referenzen sind.
REF_LISTS = {"NodesToCleanUpResults", "AmmoTypeProjectiles"}
NOT_A_SID = {"", "empty", "Empty", "None", "true", "false", "True", "False"}


def references(refs):
    """Aus dem Rohbestand die echten SID-Verweise herausfiltern."""
    out = []
    for struct, key, value, depth, line in refs:
        if "::" in value or value in NOT_A_SID:
            continue
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
            continue          # Zahlen, Literale, Pfade
        # `SID` auf Ebene 1 ist die eigene Kennung, tiefer ist es ein Verweis
        if key == "SID" and depth >= 2:
            out.append((struct, key, value, line))
        elif key in REF_KEYS:
            out.append((struct, key, value, line))
        elif key.startswith("[") and value:
            out.append((struct, key, value, line))
    return out


# Skriptzeilen in Scripts/OnGameLaunch sehen aus wie
# `[*] = XStartQuestNodeBySID <Knoten>` - der Verweis ist das LETZTE Wort.
# Ohne diese Sonderbehandlung faellt der Filter oben darauf herein (zwei
# Woerter sind kein Bezeichner) und genau der wichtigste Verweis der
# Laufzeit-Beziehungen bliebe ungeprueft.
SCRIPT_CMDS = ("XStartQuestNodeBySID", "XStartQuestBySID",
               "XExecuteAdditionalScript")


def script_references(text):
    out = []
    for n, line in enumerate(text.splitlines(), 1):
        m = re.match(r"^\s*\[[^\]]*\]\s*=\s*(\S+)\s+(\S+)\s*$", line)
        if m and m.group(1) in SCRIPT_CMDS:
            out.append(("ScriptsArray", m.group(1), m.group(2), n))
    return out


# --- 2) Index der Spieldaten -------------------------------------------
# ⚠ Der Name darf NICHT an Spaltenanfang verankert werden: die
# Wetterlagen (`Cloudy`, `Fogy`, `Thundery` ...), auf die AIGlobals per
# `WeatherSID` zeigt, stehen EINGERUECKT in WeatherSelectionPrototypes.
# Mit Anker meldete der erste Lauf sie als Waisen - falscher Alarm.
TOP_RE = re.compile(r"^\s*([A-Za-z_\[][^\s:]*)\s*:\s*struct\.begin", re.M)
SID_RE = re.compile(r"^\s*SID\s*=\s*([A-Za-z_][A-Za-z0-9_]*)\s*$", re.M)

# Die fuenf groessten Dateien machen 248 der 411 MB aus und deklarieren
# nichts, worauf ein Tweak zeigen koennte (Spawn-Platzierungen, Dialoge,
# Meshes, Frisuren). Sie bleiben aus dem Index — aber NICHT aus der
# Pruefung: taucht ein unbekannter Name auf, wird in ihnen nachgesehen,
# bevor der Test etwas beanstandet (siehe `resolve_late`).
INDEX_SKIP = {"SpawnActorPrototypes.cfg", "DialogPrototypes.cfg",
              "MeshGeneratorPrototypes.cfg", "BodyMeshPrototypes.cfg",
              "GroomGeneratorPrototypes.cfg"}

t0 = time.time()
KNOWN = set()
_files = 0
for f in GAMELITE.rglob("*.cfg"):
    if f.name in INDEX_SKIP:
        continue
    text = f.read_text(encoding="utf-8-sig", errors="replace")
    KNOWN.update(TOP_RE.findall(text))
    KNOWN.update(SID_RE.findall(text))
    _files += 1
index_s = time.time() - t0
check(len(KNOWN) > 100_000,
      f"Index ueber {_files} Spieldateien: {len(KNOWN)} bekannte Namen "
      f"({index_s:.1f}s)")


_big_texts: dict[Path, str] = {}


def resolve_late(name: str) -> bool:
    """Zweite Chance fuer einen Namen: in den uebersprungenen Riesen
    nachsehen. Laeuft nur, wenn der Index den Namen nicht kennt - seit
    1.36.0 regelmaessig fuer die acht Dialog-Ziele des Menue-Bodens, darum
    werden die Riesen beim ersten Mal gelesen und dann behalten."""
    needle = re.compile(rf"^\s*{re.escape(name)}\s*:\s*struct\.begin|"
                        rf"^\s*SID\s*=\s*{re.escape(name)}\s*$", re.M)
    for big in INDEX_SKIP:
        for f in GAMELITE.rglob(big):
            if f not in _big_texts:
                _big_texts[f] = f.read_text(encoding="utf-8-sig", errors="replace")
            if needle.search(_big_texts[f]):
                KNOWN.add(name)
                return True
    return False

_base_cache: dict[Path, set[str]] = {}


def base_names(path: Path) -> set[str] | None:
    """Top-Level-Struct-Namen der Zieldatei (seit Patch 1.6 haelt EINE
    Datei die ganze Prototypen-Familie, es gibt keinen Unterordner mehr)."""
    if path not in _base_cache:
        if not path.exists():
            return None
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        _base_cache[path] = {m.group(1) for m in
                             re.finditer(r"^([A-Za-z_\[][^\s:]*)\s*:\s*struct\.begin",
                                         text, re.M)}
    return _base_cache[path]


PATCH_NAME = re.compile(r"(.+?)(?:\.cfg)?_patch_[^.]+\.cfg$")


def base_file(patch_path: str) -> Path:
    """Aus dem Patch-Pfad die Vanilla-Datei ableiten, die er veraendert.

    Zwei Formen (docs/SPEC.md par. 0): `X.cfg_patch_<Mod>.cfg` neben der
    Basis (CoreVariables & Co.) und `X/X_patch_<Mod>.cfg` im Ordner des
    Prototyps. `//` am Anfang heisst DLC-Zweig (relativ zu Content/)."""
    if patch_path.startswith("//"):
        p = GAMELITE.parent / patch_path[2:]
    else:
        p = VANILLA / patch_path
    m = PATCH_NAME.match(p.name)
    if m is None:
        # Dritte Form (1.36.0, wie RSO): eine Datei mit FREIEM Namen im
        # Ordner des Prototyps, z.B. QuestNodePrototypes/<Mod>_Relations.cfg.
        # Der Ordner sagt, welche Familie sie erweitert.
        return p.parent.with_suffix(".cfg")
    stem = m.group(1)
    if p.parent.name == stem:
        return p.parent.with_suffix(".cfg")
    return p.parent / f"{stem}.cfg"


# --- 3) Die vier Pruefungen ---------------------------------------------
def audit(patches: dict[str, str]) -> list[str]:
    """Alle Beanstandungen ueber den ganzen Patch-Satz."""
    bad = []
    # Alles, was WIR selbst neu anlegen, gilt als vorhanden.
    own = set()
    for path, text in patches.items():
        for name, attrs, _line in scan(text)[0]:
            if "bpatch" not in attrs or "refkey=" in attrs:
                own.add(name)

    for path, text in sorted(patches.items()):
        tops, raw, problems = scan(text)
        bad += [f"{path}: {p}" for p in problems]
        if text.count("{") != text.count("}") or text.count("[") != text.count("]"):
            bad.append(f"{path}: Klammern nicht paarweise")

        base = base_file(path)
        names = base_names(base)
        if names is None:
            bad.append(f"{path}: Zieldatei {base.name} gibt es nicht")
            continue

        for name, attrs, line in tops:
            refkey = re.search(r"refkey=([^;}\s]+)", attrs)
            if refkey:
                if refkey.group(1) not in names and refkey.group(1) not in KNOWN:
                    bad.append(f"{path}:{line} refkey={refkey.group(1)} "
                               f"gibt es nicht")
            elif "bpatch" in attrs:
                if name not in names:
                    bad.append(f"{path}:{line} {name} steht nicht in "
                               f"{base.name} (umbenannt? Patch laeuft ins Leere)")
            elif name in names:
                bad.append(f"{path}:{line} {name} ist als NEUER Knoten "
                           f"geschrieben, existiert aber schon in {base.name}")

        # (c) SID == Struct-Name. ⚠ Nur bei BENANNTEN Structs: bei
        # index-adressierten Eintraegen traegt Vanilla selbst einen
        # anderen SID (`[1]` -> `DefaultNPC` in ThreatPrototypes,
        # `[100]` -> `sid_locations_..._name` in MarkerPrototypes).
        for struct, key, value, depth, line in raw:
            if (key == "SID" and depth == 1 and value
                    and not struct.startswith("[") and value != struct):
                bad.append(f"{path}:{line} SID = {value} in Struct {struct}")

        # (d) Waisen
        for struct, key, value, line in references(raw) + script_references(text):
            if value in KNOWN or value in own:
                continue
            if resolve_late(value):
                continue
            bad.append(f"{path}:{line} {struct}.{key} zeigt auf "
                       f"'{value}' - gibt es nirgends")
    return bad


t0 = time.time()
findings = audit(PATCHES)
audit_s = time.time() - t0
n_tops = sum(len(scan(t)[0]) for t in PATCHES.values())
n_refs = sum(len(references(scan(t)[1])) + len(script_references(t))
             for t in PATCHES.values())

check(not findings,
      f"{n_tops} Top-Level-Structs und {n_refs} SID-Verweise sind sauber"
      + ("\n      " + "\n      ".join(findings[:25]) if findings else ""))
print(f"      ({audit_s:.1f}s fuer {len(PATCHES)} Patchdateien)")


# --- 4) Die Anker, an denen der Mehrfach-Job-Schalter haengt ------------
# Diese acht Namen sind die empfindlichste Stelle im ganzen Werkzeug: sie
# stehen nicht in einer Liste, sondern werden datengetrieben gefunden -
# aber ein umbenannter Knoten wuerde sie stumm verschwinden lassen.
givers = gd.repeatable_quest_givers()
check(len(givers) == 8,
      "acht Auftraggeber gefunden ("
      + ", ".join(sorted(g["quest"] for g in givers)) + ")")

# Jeder Knotenname, den die Erkennung liefert, muss im Spiel stehen -
# sonst patcht der Schalter ins Leere, ohne dass irgendwer es merkt.
ANCHOR_KEYS = ("quest_sid", "cap_key", "dialog_key", "accept",
               "cleanup_sid", "end_sid")
lost = sorted({f"{g['quest']}.{k}={g[k]}" for g in givers for k in ANCHOR_KEYS
               if g.get(k) and g[k] not in KNOWN and not resolve_late(g[k])})
check(not lost,
      f"alle {len(givers) * len(ANCHOR_KEYS)} Quest-Anker der acht Geber "
      f"stehen in den Spieldaten" + (f" - FEHLT: {lost}" if lost else ""))

quest_patch = next((t for p, t in PATCHES.items()
                    if p.endswith("QuestNodePrototypes_patch_S2Tweaker.cfg")), "")
tops = scan(quest_patch)[0]
new_nodes = {n for n, attrs, _l in tops if "bpatch" not in attrs}
# Dritter Entwurf des Mehrfach-Job-Schalters (09.09.2026): KEIN neuer
# Knoten mehr in der {bpatch}-Datei - nur Aenderungen an vorhandenen.
check(not new_nodes and len(tops) >= 8 * 3,
      f"die Quest-Patchdatei traegt {len(tops)} vorhandene Knoten und keinen neuen")
# Die Laufzeit-Beziehungen (1.36.0) liegen in einer EIGENEN Datei ohne
# ein einziges {bpatch} - so, wie die zwei Mods es tun, deren neue Knoten
# nachweislich laufen.
rel_patch = next((t for p, t in PATCHES.items() if p.endswith("_Relations.cfg")), "")
rel_nodes = {n for n, attrs, _l in scan(rel_patch)[0]}
check(rel_nodes == {"S2T_Relations_Start", "S2T_Rel_01", "S2T_Rel_02"}
      and "{bpatch}" not in rel_patch,
      f"die Laufzeit-Beziehungen stehen fuer sich, ohne {{bpatch}} ({sorted(rel_nodes)})")
new_nodes |= rel_nodes
# Diese Knoten sind neu und duerfen darum NICHT schon im Spiel stehen -
# sonst wuerden wir einen Vanilla-Knoten komplett ersetzen.
collide = sorted(n for n in new_nodes if n in KNOWN)
check(not collide, "keiner der neuen Knoten kollidiert mit einem Vanilla-Knoten"
      + (f" - KOLLISION: {collide}" if collide else ""))


# --- 5) Der Test prueft sich selbst -------------------------------------
# Findet er die drei Fehlerbilder nicht mehr, ist die Regel kaputt.
sample = ("RSQ01_SetTimer : struct.begin {bpatch}\n"
          "   InGameHours = 48\n"
          "struct.end\n")
probe_path = "QuestNodePrototypes/QuestNodePrototypes_patch_S2Tweaker.cfg"

check(not audit({probe_path: sample}), "Selbsttest: sauberer Patch gilt als sauber")

check(any("laeuft ins Leere" in f for f in audit(
          {probe_path: sample.replace("RSQ01_SetTimer", "RSQ01_SetTimerXX")})),
      "Selbsttest: umbenannter Struct faellt auf")

broken = ("RSQ01_S2T_ClearAccept : struct.begin\n"
          "   SID = RSQ01_S2T_ClearAccept\n"
          "   NodesToCleanUpResults : struct.begin\n"
          "      [0] = RSQ01_Technical_GetQuestXX\n"
          "   struct.end\n"
          "struct.end\n")
check(any("gibt es nirgends" in f for f in audit({probe_path: broken})),
      "Selbsttest: Verweis auf eine erfundene SID faellt auf")

check(any("SID = " in f for f in audit(
          {probe_path: sample.replace("   InGameHours = 48",
                                      "   SID = SomethingElse")})),
      "Selbsttest: falsches SID-Feld faellt auf")

check(any("struct.end" in f for f in audit(
          {probe_path: sample.replace("struct.end\n", "")})),
      "Selbsttest: fehlendes struct.end faellt auf")

print(f"\n=== {ok} Pruefungen gruen "
      f"({n_tops} Structs, {n_refs} Verweise, {len(KNOWN)} bekannte Namen) ===")
