"""Gegenprobe: jeder Pfad im erzeugten Patch muss in der Vanilla-Datei
existieren, jeder Wert muss sich vom Vanilla-Wert unterscheiden, und nirgends
darf MoneyGenerator oder das Basis-Template [0] auftauchen."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VANILLA = str(ROOT / "vanilla" / "Stalker2" / "Content"
              / "GameLite" / "GameData")
from s2tweaker import cfgparse
from s2tweaker.emit import emit_patch
from s2tweaker.gamedata import GameData
from s2tweaker.tweaks import Settings, _loot_patch

VAN = VANILLA
gd = GameData(VAN)
vanilla = gd.itemgenerators

for pct in (25, 50, 75, 125, 150, 200, 275, 400):
    factor = pct / 100.0
    patches = _loot_patch(gd, Settings(loot_amount_factor=factor))
    text = emit_patch(patches)

    # 1) Text-Ebene: verbotene Namen
    assert "MoneyGenerator" not in text, f"{pct}%: MoneyGenerator im Patch!"
    assert not text.startswith("[0] :"), f"{pct}%: Template [0] gepatcht!"

    # 2) Re-parse: der Patch muss sich selbst wieder lesen lassen
    reparsed = cfgparse.parse(text)
    assert len(reparsed.children) == len(patches), (
        f"{pct}%: re-parse verliert Structs "
        f"({len(reparsed.children)} != {len(patches)})")

    n_values = 0
    for sid, gens in patches.items():
        assert sid != "[0]"
        vnode = vanilla.children.get(sid)
        assert vnode is not None, f"{pct}%: Struct {sid} existiert nicht in Vanilla"
        # bpatch-Attribut muss auf jeder Ebene stehen
        rnode = reparsed.children[sid]
        assert "bpatch" in rnode.attr_dict(), f"{pct}%: {sid} ohne bpatch"
        for gen_key, slots in gens.items():
            assert gen_key == "ItemGenerator", f"{pct}%: falscher Zweig {gen_key}"
            vgen = vnode.children.get(gen_key)
            assert vgen is not None, f"{pct}%: {sid}.{gen_key} fehlt in Vanilla"
            for slot_key, body in slots.items():
                vslot = vgen.children.get(slot_key)
                assert vslot is not None, \
                    f"{pct}%: {sid}.{gen_key}.{slot_key} fehlt in Vanilla"
                for pi_key, items in body.items():
                    assert pi_key == "PossibleItems"
                    vpi = vslot.children.get(pi_key)
                    assert vpi is not None, \
                        f"{pct}%: {sid}.{slot_key}.PossibleItems fehlt in Vanilla"
                    for item_key, cfg in items.items():
                        vitem = vpi.children.get(item_key)
                        assert vitem is not None, \
                            f"{pct}%: {sid}.{slot_key}.PossibleItems.{item_key} fehlt"
                        for key, value in cfg.items():
                            assert key in ("MinCount", "MaxCount"), key
                            # kein neuer Schluessel
                            assert key in vitem.values, \
                                f"{pct}%: {sid}.{item_key}.{key} gibt es in Vanilla nicht"
                            old = int(float(vitem.values[key].rstrip("fF").rstrip(".")))
                            new = int(value)
                            assert new != old, \
                                f"{pct}%: {sid}.{item_key}.{key} unveraendert ({old})"
                            assert new >= 1, f"{pct}%: {sid}.{item_key}.{key} = {new}"
                            n_values += 1
                        # Min <= Max nach dem Patch (Vanilla-Werte als Basis)
                        eff_min = int(cfg.get("MinCount", vitem.values.get("MinCount", "1")
                                              ).rstrip("fF").rstrip("."))
                        raw_max = cfg.get("MaxCount", vitem.values.get("MaxCount"))
                        if raw_max is not None:
                            eff_max = int(str(raw_max).rstrip("fF").rstrip("."))
                            assert eff_min <= eff_max, \
                                f"{pct}%: {sid}.{item_key} Min {eff_min} > Max {eff_max}"
    print(f"{pct:>4} %: {len(patches):>4} Structs, {n_values:>5} Werte, "
          f"{len(text.encode()):>9,} Bytes  OK")

print("\nALLE PFADE UND WERTE VERIFIZIERT")
