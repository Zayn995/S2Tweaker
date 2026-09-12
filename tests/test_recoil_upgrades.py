"""Check beneficial upgrade/attachment recoil reductions against live data.

Preserve positive penalties and cap negative reductions at -100%."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VANILLA = str(ROOT / "vanilla" / "Stalker2" / "Content"
              / "GameLite" / "GameData")

from s2tweaker.gamedata import GameData
from s2tweaker.tweaks import Settings, build_patches, summarize

gd = GameData(VANILLA)
KEY = "EffectPrototypes/EffectPrototypes_patch_S2Tweaker.cfg"


def pct(raw: str) -> float:
    return float(raw.strip()[:-1])


# Inventory positive and negative recoil effects.
recoil = {sid: node for sid, node in gd.effects.children.items()
          if "#" not in sid
          and node.values.get("Type") == "EEffectType::Recoil"}
neg = {sid: pct(n.values["ValueMin"]) for sid, n in recoil.items()
       if pct(n.values["ValueMin"]) < 0}
pos = {sid: pct(n.values["ValueMin"]) for sid, n in recoil.items()
       if pct(n.values["ValueMin"]) >= 0}
assert len(neg) >= 10, neg
assert len(pos) >= 3, pos
assert "RecoilPos10Effect" in neg and "RecoilNeg20Effect" in pos
assert all(n.values["ValueMin"] == n.values["ValueMax"] for n in recoil.values())
print(f"Inventory: {len(neg)} reducing ({min(neg.values()):g} .. "
      f"{max(neg.values()):g} %), {len(pos)} increasing recoil effects  OK")


def patched_values(text: str) -> dict[str, tuple[float, float]]:
    out = {}
    for m in re.finditer(r"^(\S+) : struct.begin \{bpatch\}\n(.*?)^struct.end",
                         text, re.S | re.M):
        body = m.group(2)
        vmin = re.search(r"ValueMin = (\S+)", body)
        vmax = re.search(r"ValueMax = (\S+)", body)
        assert vmin and vmax, m.group(1)
        out[m.group(1)] = (pct(vmin.group(1)), pct(vmax.group(1)))
    return out


# --- 2) x2: double each decreasing effect, nothing else ---
p = build_patches(gd, Settings(recoil_upgrade_factor=2.0))
assert list(p) == [KEY], list(p)
got = patched_values(p[KEY])
assert set(got) == set(neg), set(got) ^ set(neg)
for sid, vanilla in neg.items():
    assert got[sid] == (vanilla * 2, vanilla * 2), (sid, vanilla, got[sid])
assert not (set(got) & set(pos)), "Increasing effects must remain unchanged"
print(f"x2: {len(got)} effects doubled (e.g. RecoilPos10Effect -> "
      f"{got['RecoilPos10Effect'][0]:g} %), positive values unchanged  OK")

# Large factors must respect the -100% cap.
for factor in (20.0, 100.0):
    got = patched_values(build_patches(
        gd, Settings(recoil_upgrade_factor=factor))[KEY])
    assert set(got) == set(neg)
    assert all(v == (-100.0, -100.0) for v in got.values()), got
print("x20 / x100: all decreasing effects capped at -100%  OK")

# Apply the cap only where the scaled value reaches it.
got = patched_values(build_patches(gd, Settings(recoil_upgrade_factor=4.0))[KEY])
for sid, vanilla in neg.items():
    assert got[sid][0] == max(-100.0, vanilla * 4), (sid, vanilla, got[sid])
print("x4: combination of scaled and capped values  OK")

# --- 5) Neutral, negative factor and summary ---
assert not build_patches(gd, Settings(recoil_upgrade_factor=1.0))
assert not build_patches(gd, Settings(recoil_upgrade_factor=-2.0))
assert any("Recoil reduction from upgrades" in line
           for line in summarize(Settings(recoil_upgrade_factor=20.0)))
assert not [line for line in summarize(Settings())
            if "Recoil reduction" in line]
# Compose correctly with artifact changes in the same file.
p = build_patches(gd, Settings(recoil_upgrade_factor=2.0,
                               artifact_effect_factor=2.0))
assert "RecoilPos10Effect" in p[KEY] and "Artifact" in p[KEY]
print("Neutral/negative = no patch, summary, coexistence with artifact slider  OK")

print("\nRECOIL-UPGRADES-TEST OK")
