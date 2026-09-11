# S2Tweaker 1.40.0 — extra artifact bonuses, job texts and NPC equipment

**Add missing bonuses to ordinary artifacts**, including fire protection on
Liquid Stone, in **World → Artifact editor & related settings**. Nine supported
bonus families offer 518 additional item/bonus choices on the audited 2.0.5 data,
bringing this editor to 871 controls. New **Add ...** settings use 0 for off and
100% for the installed native Low bonus, adjustable up to 1000%. Global artifact
strength also applies; existing bonus types keep their individual controls.
Carry capacity includes its matching hidden weight-penalty adjustment.

The optional **Artifact bonus labels follow your changes** checkbox selects the
nearest native strength tier after global and individual changes, with the lower
tier at a midpoint, and hides zero-strength bonus rows. Labels remain approximate.
Radiation shielding tiers and unusual artifact mechanics remain separate.

**Experimental multi-job exports now include journal translations automatically.**
The tool reads the installed translations and adds the missing title/objective
keys: 208 aliases in each of the 18 installed languages checked locally. Original
resources are preserved, and no game translations ship inside the tool ZIP.
Existing isolated journal and stage identifiers are unchanged. The first export
after a game-data change may need Oodle to read the compressed source resources;
the tool's Oodle help explains setup. No UE4SS is required.

**NPC equipment by faction & player progression** is available in World. Choose
among 12 factions, 50 ordinary role profiles and 370 native equipment groups,
with 1,028 controls for existing weapon, pistol and body-armor choices. Values
change relative selection weights, not drop chances. Rank means player
progression; native combined rank and difficulty groups remain linked.
Individual settings use private generator branches and compose with global
quality, condition, loaded ammo and variety settings. Fractional native weights
retain their precision. Equipped NPC-only armor does not become lootable.

Profiles, favorites, undo/redo, reset, conflict scans and Pak manifests are
supported. Neutral settings produce no additional patch. All values come from
the loaded game installation.

**Validation:** 55 local headless suites; targeted portable GUI editing,
save/load, undo/redo, reset and export; binary Pak readback, including the
18-language job export. The published artifacts are checked against the release
tag and GitHub Actions build. The existing 19 signed runtime binaries remain
unchanged. No new VirusTotal result is claimed for this ZIP.

**Not play-tested:** added bonuses, adjusted labels, protection of inherited
fake/quest variants, supplementary localization loading (including English), and
new NPC equipment generators. Many simultaneous bonus rows have no verified
engine limit. Re-equip edited artifacts; existing NPC inventories may not refresh.
Generic mission NPCs can share edited ordinary profiles.

Molkerr's 1.39 reports support separate job hand-ins and remaining journals after
save/load in the cases tested. The completed sibling's marker case remains open;
this release does not change marker logic. **#9 and #19 stay open** for gameplay
observations. Use a save from before accepting experimental jobs and retain their
Pak while they are active; removing a Pak does not roll back saved quest state.

[Artifact guide](https://github.com/Zayn995/S2Tweaker/blob/v1.40.0/docs/ARTIFACT_EDITOR.md) ·
[NPC equipment guide](https://github.com/Zayn995/S2Tweaker/blob/v1.40.0/docs/NPC_EQUIPMENT.md) ·
[Job repair and game checks](https://github.com/Zayn995/S2Tweaker/blob/v1.40.0/docs/REPEATABLE_JOBS_REPAIR.md).

Extract the entire player ZIP and keep the executable, DLLs and `_internal`
together. Rebuild your personal Pak to use these changes. Includes all 1.39.0
features and game patch 2.0.5 data-loading fixes. Bullet Time remains deferred;
no UE4SS or slow-motion add-on is included.

Source: tag `v1.40.0`; build with `.github/workflows/build.yml` and
`tools/refresh_portable.py` using the existing hash-pinned runtime.
