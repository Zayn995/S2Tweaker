"""Compatibility reports distinguish editor intent, overlap and unknown runtime results."""
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from s2tweaker import gui, modscan
from s2tweaker.tweaks import Settings


def report(settings=Settings(), *, own="zzz_S2Tweaker_P.pak", workshop=False):
    pairs = {(f"A{i:02}", "ItemGridWidth") for i in range(20)}
    pairs |= {("GunArev_ST", "ItemGridWidth"), ("GunFora230_PP", "ItemGridHeight")}
    info = modscan.ModInfo(name="OXA_StandardA_P", path=Path("OXA_StandardA_P.pak"),
                           n_cfg=50, packed_assets=True, note=modscan.PACKED_NOTE,
                           source="workshop" if workshop else "mods")
    info.pairs = pairs
    stub = SimpleNamespace(
        _out_name=lambda: own, _game_fingerprint=lambda: 123,
        _collect=lambda: settings, avoid_conflicts=False, avoid_unlocked=set(),
        modscan_results=[info], _mods_after={info.name},
        _conflict_labels=lambda name: ["Inventory space per item"],
        mod_conflicts={"item_grid": [info.name]}, checks={},
        sliders={"item_grid": SimpleNamespace(label=SimpleNamespace(cget=lambda key: "Inventory space per item"))},
        _footprints={"item_grid": pairs},
    )
    return gui.App._build_compat_report(stub)


class CompatibilityReport(unittest.TestCase):
    def test_selection_and_every_overlap_are_visible_without_a_winner_claim(self):
        text = report(Settings(item_grid_factor=.5, repeatable_quest_factor=.5))
        self.assertIn("Selected changes in the current editor", text)
        self.assertIn("Inventory space per item", text.split("Scanned mods")[0])
        self.assertIn("Repeatable", text.split("Scanned mods")[0])
        self.assertIn("GunArev_ST.ItemGridWidth", text)
        self.assertIn("GunFora230_PP.ItemGridHeight", text)
        self.assertIn("A19.ItemGridWidth", text)
        self.assertNotIn(" more)", text)
        self.assertIn(modscan.PACKED_NOTE, text)
        self.assertIn("not a readback of the installed Pak", text)
        self.assertIn("not a verified winner", text)
        self.assertNotIn("values win", text)

    def test_name_change_does_not_reuse_stale_scan_order(self):
        self.assertIn("filename sorts before your pak", report())
        self.assertIn("filename sorts AFTER your pak", report(own="A_Custom.pak"))
        text = report(workshop=True)
        self.assertIn("Steam Workshop mod - activation and load order", text)
        self.assertNotIn("filename sorts", text)

    def test_neutral_controls_are_not_presented_as_active_changes(self):
        text = report()
        self.assertIn("None (all settings are neutral)", text)
        self.assertIn("Potential overlaps below include controls still at vanilla", text)


if __name__ == "__main__":
    unittest.main()
