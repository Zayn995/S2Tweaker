"""Check live indexed patches against unchanged vanilla baselines.

Apply the documented recursive bpatch contract locally, without executing
Unreal. Unmodified leaves must survive every tested patch order.
"""
import itertools
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from s2tweaker import cfgparse
from s2tweaker.gamedata import GameData
from s2tweaker.tweaks import Settings, build_patches, _resolved_struct
from test_npc_patch_compatibility import apply_bpatch, leaves

gd = GameData(ROOT / "vanilla/Stalker2/Content/GameLite/GameData")
for tree, settings in (
    (gd.threats, [Settings(npc_search_time_factor=10), Settings(npc_alertness_factor=2)]),
    (gd.weatherselection, [Settings(rain_factor=2), Settings(emission_factor=2),
                           Settings(weather_duration_factor=2)]),
):
    baseline = leaves(tree)
    patches = [cfgparse.parse(next(iter(build_patches(gd, s).values()))) for s in settings]
    expected = dict(baseline)
    for patch in patches:
        changed = leaves(patch)
        assert changed
        assert set(changed) <= set(baseline)
        assert all(cfgparse.parse_number(v) != cfgparse.parse_number(baseline[k]) for k, v in changed.items())
        assert all(n.attrs == "bpatch" for top in patch.children.values() for n in top.walk())
        expected.update(changed)
    for a, b in itertools.combinations(patches, 2):
        assert not (leaves(a).keys() & leaves(b).keys())
    for order in itertools.permutations(patches):
        applied = tree
        for patch in order:
            applied = apply_bpatch(applied, patch)
        assert leaves(applied) == expected
    print(f"{tree.name}: {len(patches)} disjoint patches, all orders preserve unrelated values OK")

fixture = cfgparse.parse("""
[0] : struct.begin
Keep = 9
Nested : struct.begin
Value = 3
struct.end
struct.end
[1] : struct.begin {refkey=[0]}
Nested : struct.begin
Other = 4
struct.end
struct.end
""")
assert _resolved_struct(fixture, fixture.children["[1]"]) == {
    "Keep": "9", "Nested": {"Value": "3", "Other": "4"}}
assert not build_patches(gd, Settings())
print("INDEX-ENTRIES-TEST OK")
