"""Inhalt des eingebauten FAQ-Fensters (GUI: gui.App._show_faq).

Nur Daten, kein Code: eine Liste von Eintraegen mit Frage (q), Antwort (a)
und unsichtbaren Suchbegriffen (k) — Synonyme, Tippfehler-Varianten und
Spieler-Vokabular, damit die Suche auch "health pack" findet, wenn der
Regler "Consumable strength" heisst. Genau daraus ist das FAQ entstanden:
ein Nexus-Nutzer suchte die Medkit-Heilung und kam nicht auf den Namen.

Regeln fuer neue Eintraege:
- Englisch (alles Oeffentliche ist englisch), kurze Frage, ehrliche Antwort.
- Keine Vanilla-Zahlen versprechen, die das naechste Spiel-Update aendert —
  das Tool liest live; Zahlen nur als "currently/vanilla ~X" nennen.
- Nichts behaupten, was nicht implementiert oder getestet ist. Die
  "not play-tested"-Ehrlichkeit gilt auch hier.
"""

FAQ_ENTRIES = [
    # ------------------------------------------------------------ finding things
    {
        "q": "How do I heal more per medkit / health pack?",
        "a": "Two sliders in the World tab: 'Medkit & bandage healing' "
             "scales ONLY medical items (medkits and bandages), while "
             "'Consumable strength' scales all consumables - healing, "
             "bleeding/radiation removal, stamina from food and drink. "
             "They stack: both at 200 % means 4x medkit healing.",
        "k": "health pack heal hp medizin medikit first aid restore more "
             "healing medkit bandage army eco consumable strength",
    },
    {
        "q": "How do I get more loot from stashes, bodies and containers?",
        "a": "The game has TWO separate loot systems, so the World tab has "
             "two groups: 'Loot in stashes & on bodies' (three sliders: "
             "amount, find chance, ammo bonus - covers the smart-loot "
             "lists: ammo, medicine, food, grenades) and 'Loot amount "
             "(NPCs, containers, world)' for the big item generators "
             "behind dead stalkers, mutants and world stashes.",
        "k": "loot drops corpse body stash container crate more items "
             "farming scavenging generator amount",
    },
    {
        "q": "Why does the loot slider not give me more weapons or armor?",
        "a": "Weapons, armor, detectors, artifacts and grenades almost "
             "always come as a SINGLE item per loot slot, and amounts are "
             "whole numbers that never drop below 1. A single-item slot "
             "stays at 1 below 150 %, becomes 2 from 150 % and 3 from "
             "275 %. Only ammo and part of the food/medicine lists come "
             "as real stacks that scale smoothly. Money, quest items, "
             "unique weapons and trader stock are excluded on purpose.",
        "k": "loot amount weapons armor artifacts single item 150 percent "
             "not working why no effect money quest performance fps slow",
    },
    {
        "q": "Why do dead NPCs drop nothing on Hard/Stalker difficulty?",
        "a": "That is vanilla behavior: the game only puts smart loot "
             "(ammo, medicine, water) on bodies on Easy and Medium "
             "difficulty. On Hard and Stalker there is nothing on bodies "
             "for the stash/body sliders to scale - they still work on "
             "hidden stashes. The bigger 'Loot amount' slider affects NPC "
             "loadout drops on every difficulty.",
        "k": "corpse body empty hard stalker difficulty no loot bodies "
             "smart loot easy medium",
    },
    {
        "q": "Can I make ONE specific weapon stronger?",
        "a": "Yes - Weapons tab, 'Single weapon overrides': open a "
             "category, open the weapon, set its 9 factors (damage, "
             "spread, recoil, durability, fire rate, range, bleeding, ADS "
             "move speed, ADS aim-in speed). Unique named weapons are in "
             "there too - search e.g. 'Decider' or 'Sharpshooter' - and "
             "so are the Pre-order/Deluxe/Ultimate edition guns (Gabion, "
             "Veteran, the Monolith set ...). Edition guns patch the DLC "
             "config branch; that is harmless if you don't own the "
             "edition. A weapon's own factor beats its category factor, "
             "which beats the global sliders. Everything left at x1 "
             "(vanilla) falls through to the next level. The same idea "
             "works per ammo round in the Ammo tab and per armor piece "
             "in the Armor tab.",
        "k": "single weapon override individual gun buff nerf specific "
             "ak74 cascade category tree per weapon riemann lullaby "
             "gabion veteran monolith edition deluxe ultimate preorder",
    },
    {
        "q": "Can I tune ONE specific armor or helmet?",
        "a": "Yes - Armor tab, 'Single armor overrides': open Body armor "
             "(the Deluxe/Ultimate/Pre-order edition suits like the "
             "Monolith SEVA are in there too) "
             "or Helmets, open the piece, set its protection factors "
             "(physical, burn, shock, chemical, radiation, PSY - only "
             "types the piece actually has in vanilla get a slider). An "
             "armor's own factor REPLACES the global protection sliders "
             "above for that type. Durability and carry bonuses stay "
             "global - they work through different game systems.",
        "k": "armor helmet override individual specific exoskeleton seva "
             "protection suit tune single piece body",
    },
    {
        "q": "Do the ammo overrides stack with the global ammo sliders?",
        "a": "No - a round's own factor REPLACES the global slider for "
             "that factor on that round. Weapon damage is different: "
             "weapon damage factors stack with the global 'Player damage' "
             "slider in the Combat tab (that one is a difficulty "
             "multiplier, not a weapon value).",
        "k": "ammo override stack replace global caliber round damage "
             "player damage combine multiply",
    },
    {
        "q": "How do I play stealthy / make NPCs almost blind and deaf?",
        "a": "NPCs & AI tab: 'NPC vision range' and 'NPC hearing range' go "
             "down to 10 % - combine both for ghost-mode stealth. 'NPC "
             "reaction delay' controls how long they take to alert their "
             "squad. Only Korshunov and Scar keep vanilla vision (the Faust "
             "fight is affected); the hearing slider affects all human "
             "NPCs.",
        "k": "stealth sneak ghost invisible vision hearing blind deaf "
             "detection sniper spotted boss faust",
    },
    {
        "q": "Can NPCs stop throwing so many grenades?",
        "a": "Yes - NPCs & AI tab, 'NPC grenade usage'. 0 % = NPCs never "
             "throw grenades (scripted boss grenades stay).",
        "k": "grenade spam throw npc stop annoying frequency",
    },
    {
        "q": "Can I turn off hunger, sleepiness, radiation or bleeding?",
        "a": "Player/World tabs: 'Hunger rate' and 'Sleepiness rate' at "
             "0 % disable them completely. 'Radiation accumulation' 0 % "
             "stops radiation buildup; 'Bleeding intensity' 0 % stops "
             "bleed damage. 'Artifact radiation side-effect' 0 % makes "
             "artifacts radiation-free on your belt.",
        "k": "hunger sleep tired radiation bleeding disable survival "
             "needs eat food artifact radiation clean",
    },
    {
        "q": "Can NPCs carry better (or worse) weapons and armor?",
        "a": "Yes - NPCs & AI tab, 'NPC gear quality'. Every squad rolls "
             "its loadout from a faction- and rank-specific pool; the "
             "slider tilts those rolls toward the pricier gear in each "
             "pool (400 % = the best gun there is four times as likely, "
             "25 % = rust buckets everywhere). Honest limit: it never "
             "adds gear a faction or rank wouldn't carry in vanilla - a "
             "rookie bandit will not spawn with an exoskeleton. Their "
             "dropped loot changes accordingly.",
        "k": "npc gear weapons armor loadout quality better worse enemies "
             "equipment tier veteran carry drop harder richer",
    },
    {
        "q": "Can I get new repeatable jobs faster (or instantly)?",
        "a": "Yes - Economy tab, 'Repeatable quest cooldown'. Vanilla "
             "makes task givers wait 24 in-game hours before offering "
             "new repeatable jobs; the slider scales that from instant "
             "(0 %) to four days (400 %). Only the repeatable-job timers "
             "are touched - story and side quest timers stay vanilla. A "
             "cooldown already ticking in your save finishes at its old "
             "pace first.",
        "k": "repeatable quests jobs tasks side missions cooldown timer "
             "delay 24 hours barkeep warlock sidorovich grind reputation "
             "money farming instant",
    },
    {
        "q": "Can dropped weapons spawn in better (or exact) condition?",
        "a": "Yes - World tab, 'Dropped weapon condition'. The slider sets "
             "the AVERAGE (vanilla ~37.5 % for primary weapons); the game "
             "keeps rolling randomly around it exactly like vanilla, so "
             "80 % gives drops between roughly 67 and 93 %. Tick 'Exact "
             "condition' if you want every drop at precisely the set "
             "value. Armor, helmets, artifacts and trader stock stay "
             "vanilla. Fair warning: together with the loot slider this "
             "is the biggest patch the tool can build.",
        "k": "weapon condition durability dropped drops broken damaged "
             "pristine random spread exact fixed loot state repair",
    },
    {
        "q": "Can traders carry more stock, more variety or more money?",
        "a": "Yes - the Traders tab: 'Stock amount' scales the quantities "
             "on offer, 'Stock variety' raises each catalog item's chance "
             "to be in stock after a restock (capped at 100 %), 'Restock "
             "time' controls how often shelves refresh, and the wallet "
             "sliders handle their money (most traders already have "
             "unlimited money in vanilla - the checkbox converts the "
             "rest). Honest limit: the tool never ADDS items to a "
             "trader's catalog - what they can carry stays vanilla.",
        "k": "trader stock shop shelves inventory restock refresh money "
             "wallet coupons barkeep sell more items variety assortment",
    },
    {
        "q": "Can I get free repairs, upgrades or fast travel?",
        "a": "Economy tab: 'Repair cost' and 'Fast travel cost' at 0 % "
             "are completely free; 'Upgrade cost' scales down to 0 % as "
             "well. 'Traders buy gear from durability' at 0 % makes "
             "traders accept weapons and armor in any condition.",
        "k": "free repair guide fast travel cost upgrade money cheap "
             "trader durability broken sell",
    },
    {
        "q": "How do I carry more weight?",
        "a": "Weight & items tab: raise 'Max carry weight' (hard limit) "
             "and 'Overweight penalty starts at', or tick 'No overweight "
             "penalty at all'. You can also scale item weights per "
             "category down to 0 %. Known game issue since patch 2.0: "
             "changed carry-weight limits can break walking animations, "
             "especially combined with movement-speed changes - the tab "
             "shows the same warning.",
        "k": "carry weight overweight inventory heavy limit encumbrance "
             "kg backpack item weight more space penalty",
    },
    {
        "q": "Can weapons jam less - or never?",
        "a": "Combat tab, 'Weapon jamming': x0 = weapons never jam, up "
             "to x2 for a rusty-Zone experience. Weapon durability has "
             "its own sliders (weapons and armor separately).",
        "k": "jam jamming misfire reliability broken stuck weapon "
             "condition degrade",
    },
    {
        "q": "Can I tone down anomalies or emissions?",
        "a": "World tab: 'Anomaly damage' has one global slider plus one "
             "per element (electro, chemical, fire, gravity - they "
             "stack). 'Emission frequency' scales how often emissions "
             "build up, 'Emission duration' stretches the whole emission "
             "timeline together (warning siren, shockwave, deadly phase, "
             "aftermath - vanilla is roughly one minute of warning plus "
             "one minute active; story emissions keep their scripted "
             "timing), and 'Rain & storm frequency' the weather rotation. "
             "PSY anomalies drain psy energy, not health, so they have "
             "no damage slider. Emission DAMAGE itself lives in an "
             "engine curve asset - not tweakable by config, honestly.",
        "k": "anomaly anomalies emission storm blowout weather rain psy "
             "electro chemical fire gravity damage duration longer "
             "shorter warning time survive",
    },
    {
        "q": "Can I make the Zone busier or emptier (A-Life)?",
        "a": "NPCs & AI tab, two experimental sections. 'Max "
             "simultaneous NPCs & mutants' is only a cap (52 in vanilla) "
             "- on its own it barely changes anything. The real spawn "
             "controls are in 'A-Life spawns': LAIR population for "
             "mutants and humans (how many live in each place, per player "
             "rank), lair respawn speed, and the DIRECTOR's random "
             "encounters: frequency, mutant share, pack size and per-"
             "species weights. Raise the cap together with them. Existing "
             "saves re-roll lairs slowly (sleep or change region). Not "
             "play-tested yet - small steps and a backup save.",
        "k": "alife a-life spawn population busier more npcs encounters "
             "distance empty world performance fps lair director respawn "
             "more mutants spawn rate",
    },
    {
        "q": "Can I tune ONE mutant species - or stop mutants from "
             "healing?",
        "a": "Yes - the Mutants tab. Global sliders scale health, damage, "
             "speed, hearing and health regen for ALL species (mutants "
             "passively regenerate, just like human NPCs - 'Mutant health "
             "regen' at x0 is the mutant version of 'NPCs don't "
             "self-heal'). Below that, per-species overrides: open a size "
             "group, open the species, set its factors. Species only get "
             "sliders for things that really work - Poltergeist and rat "
             "swarms deal damage indirectly, so they have no damage "
             "slider. Mutant sight is engine logic, not config - no "
             "vision slider, honestly.",
        "k": "mutant species bloodsucker chimera pseudogiant controller "
             "burer boar flesh snork single one specific nerf buff "
             "regen heal regenerate tank spongy damage sponge",
    },
    {
        "q": "Can I change faction relations - make bandits friendly or "
             "start a faction war?",
        "a": "Yes - the Factions tab. 'You (Skif) <-> factions' sets your "
             "baseline standing with each major faction, the blocks below "
             "set faction-vs-faction pairs, all on the game's own scale "
             "(-800 = enemy/kill on sight, around -400 = wary but talking "
             "and trading still work, 0 = neutral, 600+ = friend). Story, "
             "boss and arena factions are deliberately not listed - "
             "changing them could break scripted fights. Quests can still "
             "override relations at any time; that is by design.",
        "k": "faction relations reputation bandits friendly hostile war "
             "peace duty freedom monolith mercenaries military ward "
             "loners mutants attack neutral standing diplomacy",
    },
    {
        "q": "Do faction relation changes work on my existing save?",
        "a": "Honest answer: not verified yet. The game copies relations "
             "into the save when a playthrough starts, so a plain config "
             "change would only affect NEW games. This tool additionally "
             "raises the game's internal RelationVersion counter - the "
             "mechanism built to push relation updates into existing "
             "saves - but treat that as untested until play-testing "
             "confirms it. New games start from the patched baseline. "
             "Keep a backup save. Also: local hostility still rolls back "
             "over time, scripted characters keep their fixed attitudes, "
             "and a save stamped with our raised counter may skip ONE "
             "future official relation update (rare - 7 versions in two "
             "years); remove the mod before big game patches to be safe.",
        "k": "faction relations existing save new game relationversion "
             "not working savegame old save version counter apply",
    },
    {
        "q": "Can I vault or climb over higher obstacles?",
        "a": "Yes - there is a whole Vaulting tab: seven sliders (max height, trigger "
             "distance, approach angle, min obstacle height, landing "
             "tolerance, vault-over thickness and landing distance), "
             "an experimental 'vault while sprinting' toggle, "
             "and the 'Improved vaulting (community preset)' checkbox that "
             "restores the tuned set of the pre-2.0 vault mod. The sliders "
             "stack on top of the preset. Player only - NPCs keep vanilla "
             "vaulting.",
        "k": "vault vaulting climb climbing mantle parkour jump over "
             "obstacle fence window ledge",
    },
    {
        "q": "Why is there no bullet time / slow motion tweak?",
        "a": "Bullet time is not possible through config files - it would "
             "need script injection (UE4SS), which is fragile after every "
             "game patch. This tool deliberately only does what the "
             "game's own config-patch system supports.",
        "k": "bullet time slow motion slomo slowmo matrix ue4ss missing feature",
    },
    {
        "q": "Why can't I reduce iron-sight sway, only scope sway?",
        "a": "Iron-sight sway is baked into animations, not into config "
             "values - no config tool can change it. Scoped sway is a "
             "real config value and has its own slider (Weapons tab); it "
             "is patched in a way that keeps offset-aiming (leaning past "
             "the scope) working.",
        "k": "sway iron sight wobble aim shake scope steady breath",
    },
    {
        "q": "Why don't the weapon stat bars in the inventory change?",
        "a": "Because those bars are hand-set numbers, not live values. "
             "Every weapon carries fixed DamageUI / AccuracyUI / "
             "RateOfFireUI / HandlingUI / RangeUI keys for the inventory "
             "display; the game never recomputes them from the real "
             "damage, spread or fire interval - only attachments and "
             "upgrades nudge them. Your tweaks change the real values "
             "(what happens when you shoot), the bars stay decorative. "
             "Verify in the field, not in the inventory screen.",
        "k": "stats display bars inventory ui not updating damage "
             "accuracy handling rate of fire range shown wrong same "
             "unchanged cosmetic",
    },
    {
        "q": "Can I remove recoil completely?",
        "a": "Two routes. 'Weapon recoil' at 0 % sets every weapon's "
             "RecoilRadius (the kick strength) to zero - the per-shot "
             "pattern is a game asset and keeps its shape, only its size "
             "follows the slider; not play-tested yet. 'Recoil reduction "
             "from upgrades' boosts the recoil upgrades and attachments "
             "instead (vanilla -5 % to -30 %, capped at -100 %): at 2000 % "
             "any recoil upgrade removes the kick entirely. That route "
             "only affects weapons with such an upgrade installed, but it "
             "is community-proven on patch 2.0. Iron-sight sway is "
             "animation-driven and stays either way.",
        "k": "no recoil zero recoil remove recoil kick climb upgrades "
             "attachments dead steady 100 percent laser steady",
    },
    {
        "q": "Can I set health higher than 1000?",
        "a": "Yes - the 'Max health' slider goes up to 100000 (GitHub "
             "request). It is logarithmic: the left part moves in small "
             "steps around vanilla 100, the right part jumps by "
             "thousands, and the value shown is what the pak writes. Keep "
             "in mind that medkits heal a fixed amount (a basic medkit "
             "70 HP), so with huge health also raise 'Medkit & bandage "
             "healing' or healing becomes meaningless. Reported to work "
             "by a user, not play-tested by me.",
        "k": "health hp higher than 1000 max 99999 100000 god mode "
             "invincible immortal unkillable huge",
    },
    {
        "q": "Can I change magazine size for ONE weapon or one weapon type?",
        "a": "Yes - since v1.16.1 'Magazine size' is the tenth factor of "
             "the weapon cascade: global slider (Weapons tab), per category "
             "(Weapon categories block) or per weapon (weapon tree). It "
             "scales the weapon's base capacity and the magazine "
             "attachments that weapon uses, read from the weapon's own "
             "reload table. Two honest limits: a magazine shared by a "
             "weapon family (the AK paired magazine, for example) follows "
             "the first weapon that overrides it, and a handful of unique "
             "guns list no magazine at all, so their magazines only follow "
             "the global slider.",
        "k": "magazine size per weapon individual capacity rounds clip mag "
             "category tree ammo capacity bigger mags",
    },
    {
        "q": "Can I install all weapon and armor upgrades at once?",
        "a": "Economy tab, 'Technician upgrades': three boxes. 'Take both "
             "of mutually exclusive upgrades' lets you install branches "
             "that normally exclude each other; 'Upgrades need no "
             "blueprint' drops the blueprint item requirement; 'No upgrade "
             "tiers' lets you skip the earlier tier. Each box clears the "
             "matching lock list on every upgrade that has one - the same "
             "route as the 'Take Both Upgrades' and 'Unrestricted "
             "Upgrades' Nexus mods (don't run those alongside, they patch "
             "the same lists). Which technician services which gear is "
             "not in these files and stays vanilla. Not play-tested yet.",
        "k": "upgrades technician blueprint tier unlock all both branches "
             "mutually exclusive unrestricted take both locked",
    },
    {
        "q": "Can I choose which mutants spawn?",
        "a": "Partly. The director's random encounters come from weighted "
             "scenarios - 'A-Life spawns' has a weight slider per pack "
             "kind (blind dogs, boars, fleshes, tushkans, chimeras, mixed "
             "mutant packs) on top of the overall mutant-share slider. "
             "Honest limits: bloodsuckers and the exotic mutants (controller, "
             "burer, poltergeist ...) are never rolled as random encounters "
             "in vanilla (weight 0 or forbidden), and the tool does not "
             "invent spawns the game never uses - those species come from "
             "their lairs, which the lair sliders scale.",
        "k": "mutant type species choose which spawn blind dog boar flesh "
             "tushkan chimera bloodsucker controller burer weights packs",
    },
    {
        "q": "Can I make the days longer (or shorter)?",
        "a": "Yes - World tab, 'Day length'. Vanilla runs one full game "
             "day per real hour; 200 % makes it two hours, 400 % four. "
             "The day/night ratio and everything timed in game hours "
             "(quest cooldowns, trader restocks, emissions) keep their "
             "in-game timing, they just take longer in real time. Same "
             "value the 'Longer Days' mods change.",
        "k": "day length longer days night cycle time scale real time "
             "hours slower clock",
    },
    {
        "q": "Can consumable effects last longer?",
        "a": "Yes - World tab, 'Consumable effect duration'. It scales the "
             "running effects (energy drink stamina, Hercules carry bonus "
             "and its comedown, cinnamon, vodka and psy-block protection "
             "...). Instant effects (healing, bleeding stop, anti-rad, 1-2 "
             "s) are not stretched on purpose - a medkit would heal "
             "slower, not longer. Stacks with 'Consumable strength'.",
        "k": "consumable duration longer effect energy drink hercules "
             "psy block anti rad last time seconds",
    },
    {
        "q": "Can anomaly fields spawn more artifacts?",
        "a": "Yes - World tab, Artifacts: 'Artifacts per anomaly field' "
             "(vanilla 1, up to 5 per spawn) and 'Artifact respawn speed' "
             "(how fast a field cools down before the next one). Which "
             "artifacts a field can produce stays its vanilla list, and "
             "the rarity roll has its own slider. Not play-tested yet.",
        "k": "more artifacts anomaly field count respawn cooldown farm "
             "hunting multiple per field",
    },
    {
        "q": "Can quest items weigh nothing?",
        "a": "Yes - Weight & items tab, 'Quest items weigh nothing'. Sets "
             "the weight of every quest item to 0 (most of the ~600 quest "
             "items weigh something, up to 25 kg). The per-category weight "
             "sliders leave quest items alone on purpose, so this is a "
             "separate box. Helps with quest items stuck in the inventory.",
        "k": "quest item weight zero stuck inventory pda key collar heavy "
             "weightless",
    },
    {
        "q": "Why do NPCs hit me from far away like an aimbot?",
        "a": "Two hidden things. Each NPC weapon profile has per-rank, "
             "per-distance 'guaranteed-hit shots' - the first shots of a "
             "burst ignore spread entirely (rifles 2-3 at long, 4-6 at "
             "short range in vanilla). And NPC bullet spread is its own "
             "value. NPCs & AI tab: 'NPC guaranteed-hit shots' (0 % = no "
             "free hits at all), 'NPC accuracy' (spread), plus burst "
             "length, fire pauses, engagement range and NPC weapon range. "
             "Same data the 'Grounded Combat' and 'Better Gunfights' mods "
             "edit - don't run those alongside these sliders. Not "
             "play-tested yet.",
        "k": "aimbot laser accurate npc hit far away unfair sniping "
             "opening fire guaranteed burst spread cheat",
    },
    {
        "q": "Can I sneak better - crouching, in the dark, in the rain?",
        "a": "NPCs & AI tab, 'Stealth: how NPCs notice you'. 'Crouch "
             "stealth' scales how much crouching hides you from eyes and "
             "ears, 'Movement noise' the footstep noise of walking, running "
             "and sprinting, 'Bad-weather stealth' how much fog, rain and "
             "thunder blind and deafen NPCs, and 'Flashlight gives you away' "
             "how strongly your own beam fills their vision. Darkness itself "
             "is driven by light curves the tool cannot touch - vision and "
             "hearing RANGE have their own sliders further up.",
        "k": "stealth sneak crouch invisible dark night rain fog storm "
             "flashlight noise footsteps hide detection axxii",
    },
    {
        "q": "Can I make NPCs less alert, or braver?",
        "a": "NPCs & AI tab, 'NPC awareness & nerve'. 'NPC alertness' "
             "moves the suspicion thresholds at which human NPCs turn their "
             "head, search, move in or call allies; 'NPC search time' is "
             "how long that suspicion lasts; 'NPC courage' shifts the "
             "confidence human squads need to attack or fall back; 'NPC "
             "stagger threshold' is the damage that makes them flinch. "
             "Bosses and mutants keep their own profiles. Not play-tested "
             "yet.",
        "k": "alert alertness search forget suspicion memory courage "
             "retreat flee brave flinch stagger cowards aggressive",
    },
    {
        "q": "Do mutants attack too fast?",
        "a": "Mutants tab, 'Mutant attack cooldown' - a difficulty "
             "multiplier on the pause between mutant attacks (vanilla 1.0 "
             "on every difficulty). 200 % = half as many attacks. The human "
             "counterpart 'NPC attack cooldown' sits in the NPCs & AI tab "
             "and is marked experimental because its exact scope is not "
             "verified.",
        "k": "mutant attack speed cooldown fast rate slower bloodsucker "
             "chimera swipe",
    },
    {
        "q": "What does the search box at the top find?",
        "a": "Slider names, weapon names and ammo rounds. Matches light "
             "up amber, everything else dims, and the status bar shows "
             "which tabs have hits. Weapon/ammo matches automatically "
             "open their category in the tree.",
        "k": "search find filter slider highlight where is",
    },
    # ------------------------------------------------------------ setup & files
    {
        "q": "How do I see only what I changed?",
        "a": "Click 'Changed only' in the header: everything still at "
             "(vanilla) is dimmed across all tabs, and the override trees "
             "highlight just your overridden weapons, rounds, armor "
             "pieces and changed faction pairs. Dimmed sliders stay "
             "usable. A search temporarily takes over; clearing it brings "
             "the view back. The 'Build pak' dialog also lists every "
             "active tweak.",
        "k": "changed only show my tweaks overview filter what did i "
             "change active editor view dim",
    },
    {
        "q": "Can I load the settings back from a built .pak?",
        "a": "Yes - every pak built with v1.10.0 or newer embeds a "
             "manifest (tool version, build date, game version and ALL "
             "settings). Click 'Load preset ...' and pick the .pak: your "
             "sliders, overrides and the mod name come back exactly. "
             "That also makes shared paks editable presets, and for bug "
             "reports the author can see what was set. Older or foreign "
             "paks carry no manifest and cannot be imported.",
        "k": "import pak load settings from pak manifest restore recover "
             "share preset which settings reproduce",
    },
    {
        "q": "Someone says my mod conflicts with theirs - how do I check?",
        "a": "Run 'Scan ~mods', then click 'Export report ...' in the "
             "results window: you get a plain-text compatibility report "
             "listing every scanned mod, the load order, which settings "
             "overlap (down to the exact game properties) and what the "
             "tool could not read. Perfect to attach to a Nexus comment.",
        "k": "compatibility report export txt conflict proof debug "
             "doesnt work with send report analyze",
    },
    {
        "q": "How do I install the mod I built?",
        "a": "Click 'Install to ~mods' - it builds the pak and copies it "
             "to <game>\\Stalker2\\Content\\Paks\\~mods\\ (creating the "
             "folder if needed). Or click 'Build pak -> output folder' "
             "and copy the zzz_<YourModName>_P.pak there yourself. Then "
             "just start the game - no load-order tool needed.",
        "k": "install setup mods folder pak copy where how to use start",
    },
    {
        "q": "How do I remove or change the mod?",
        "a": "Remove: click 'Remove from ~mods' or delete "
             "zzz_<YourModName>_P.pak from the ~mods folder. Change: move "
             "the sliders and build again - the new pak replaces the old "
             "one as long as the mod name stays the same. Note: movement "
             "speed values can persist inside an existing savegame until "
             "a refresh trigger (see the movement question).",
        "k": "uninstall remove delete disable revert vanilla back change "
             "update values",
    },
    {
        "q": "What do I do after a game update?",
        "a": "Start the tool, confirm the game folder again ('Reload game "
             "data') and REBUILD your pak. The tool detects the new game "
             "version automatically and re-reads all vanilla values, so "
             "your multipliers stay correct. A pak built against an older "
             "game version may point at outdated structures.",
        "k": "game update patch new version rebuild reload broken after "
             "steam",
    },
    {
        "q": "Why does the first start take 10-20 seconds?",
        "a": "On first start (and after every game update) the tool "
             "extracts the needed config files from the game's pakchunk0 "
             "archive and converts them to readable form. The result is "
             "cached next to the exe, so later starts are instant.",
        "k": "slow first start extracting loading cache stuck long",
    },
    {
        "q": "Where are my settings and presets stored? Is the tool portable?",
        "a": "Everything lives next to S2Tweaker.exe: settings.json "
             "(sliders, game folder), presets\\ (saved presets as JSON), "
             "cache\\ (extracted game data), output\\ (built paks), "
             "tools\\ (helper files). Deleting the folder removes the tool "
             "- with one exception: if the tool's folder is not writable "
             "(e.g. under Program Files), the downloaded Oodle DLL is "
             "kept in %LOCALAPPDATA%\\S2Tweaker instead.",
        "k": "settings presets save location portable appdata registry "
             "uninstall folder files",
    },
    {
        "q": "My antivirus flags S2Tweaker.exe - is it safe?",
        "a": "The exe is a PyInstaller one-file build of a Python app - a "
             "well-known false-positive pattern for many AV engines. The "
             "complete source code is public (github.com/Zayn995/"
             "S2Tweaker, MIT license) and every release states the exact "
             "commit it was built from, so anyone can reproduce the "
             "build. The only bundled binary is the open-source repak.",
        "k": "antivirus virus trojan flag warning defender false positive "
             "safe malware quarantine",
    },
    {
        "q": "Why does the tool download one file from the internet?",
        "a": "Reading the game's packed configs needs Oodle's "
             "oo2core_9_win64.dll, which is proprietary and may not be "
             "bundled. On first use the tool fetches it once from the "
             "public OodleUE mirror on GitHub, verifies its official "
             "SHA-256 checksum and keeps it in the tools folder - "
             "offline afterwards. If your network blocks GitHub, place "
             "that DLL next to S2Tweaker.exe yourself. There is no "
             "telemetry; nothing is uploaded.",
        "k": "internet network download dll oodle offline privacy "
             "telemetry connection firewall blocked",
    },
    {
        "q": "What does the Debug checkbox do?",
        "a": "It additionally exports the raw .cfg patch files to a "
             "<ModName>_cfg folder NEXT TO the built pak - in output\\ "
             "when you used 'Build pak', inside ~mods when you used "
             "'Install to ~mods'. Useful for bug reports and for checking "
             "conflicts with other mods by hand.",
        "k": "debug export cfg raw files inspect verify patch contents",
    },
    {
        "q": "What does 'nothing to patch' mean when building?",
        "a": "Every slider is at its (vanilla) position, so there is "
             "nothing to write - the tool only ever writes values you "
             "actually changed. Move at least one slider off vanilla and "
             "build again.",
        "k": "nothing to patch empty error build message vanilla",
    },
    # ------------------------------------------------------------ compatibility
    {
        "q": "Is this compatible with my other mods?",
        "a": "Usually yes: the pak contains ONLY the values you changed, "
             "and its zzz_ name loads after most mods, so your values win "
             "shared conflicts. Use 'Scan ~mods' to see which of your "
             "installed mods change the same settings - affected sliders "
             "get a colored dot. For a guaranteed hands-off setup, turn on "
             "'Avoid conflicts' in the scan results: it resets and locks "
             "every setting those mods change, and you can unlock single "
             "settings on purpose with their unlock button. Careful with "
             "mods whose pak name sorts AFTER zzz_<YourModName>_P.pak: "
             "those load later and win.",
        "k": "compatible conflict other mods load order zzz overwrite "
             "together combine priority avoid oxa lock locked compatibility "
             "mode",
    },
    {
        "q": "Are Steam Workshop mods covered by the mod scan?",
        "a": "Yes: the scan also lists the mods you subscribed to in the "
             "Steam Workshop (Steam stores them in its own workshop "
             "folder, not in ~mods). Honest limits: whether a subscribed "
             "mod is actually ACTIVE is decided in the game's own mods "
             "menu, its load order versus this tool's pak is managed by "
             "the game, and many Workshop mods use a packed format "
             "(IoStore) this tool cannot look inside - those are listed, "
             "but their exact changes stay unknown.",
        "k": "steam workshop subscribed subscribe abo mod scan covered "
             "in-game mods menu iostore active",
    },
    {
        "q": "What do the colored dots next to some sliders mean?",
        "a": "Results of the ~mods scan: blue = another installed mod "
             "changes this value while your slider is at (vanilla); "
             "violet = you changed it too, and the tooltip tells you "
             "whose value wins. Hover the dot for the mod name. The dots "
             "stay - even through 'Reset all to vanilla' - until you scan "
             "again, because the other mods are still installed.",
        "k": "dot blue violet purple marker conflict scan mods meaning "
             "color point",
    },
    {
        "q": "The mod scan says a mod 'contains data I can't read' - why?",
        "a": "That mod uses the IoStore format (.pak plus .ucas/.utoc "
             "files) or a protected archive, which this tool cannot look "
             "into. The mod still works in game - the scanner just can't "
             "tell you what it changes, so its conflicts stay unknown.",
        "k": "iostore ucas utoc unreadable scan can't read unknown "
             "encrypted",
    },
    {
        "q": "Do my weapon tweaks also affect NPCs?",
        "a": "Partly. Spread, recoil and fire rate live in game data "
             "shared with NPCs, so NPCs using those weapons change too. "
             "Weapon damage and durability resolve through "
             "player-specific data. Ammo modifiers live in shared item "
             "data - whether NPC shots use them is not verified yet. "
             "NPC combat strength has its own sliders in the NPCs & AI "
             "tab.",
        "k": "npc affected shared weapons enemies too both sides fair",
    },
    {
        "q": "Does this work on GOG / Game Pass / consoles?",
        "a": "It is built and tested against the Steam PC version. Other "
             "PC store versions should work if the tool can reach the "
             "game's Paks folder (use 'Browse ...' to select it) - the "
             "Game Pass/Microsoft Store version protects its files and "
             "is untested. Consoles: no, mods like this are PC-only.",
        "k": "gog game pass gamepass xbox microsoft store console "
             "playstation epic version support",
    },
    # ------------------------------------------------------------ known issues
    {
        "q": "Movement speed changes feel wrong or animations look broken",
        "a": "Known game limitation since patch 2.0: speed changes can "
             "desync from animations, and players report they sometimes "
             "only affect the animation instead of the real speed. Small "
             "changes (within ~10-20 % of vanilla) look best. Also note "
             "the game caches movement values inside the savegame - "
             "changes (and removals!) may only apply after a trigger "
             "like entering water or taking damage.",
        "k": "movement speed walk run sprint animation desync broken legs "
             "sliding not working savegame cached",
    },
    {
        "q": "Fire rate changes look or sound weird",
        "a": "Same engine limitation as movement speed (reported by the "
             "community): the firing animation and sound don't scale "
             "with the changed rate, so they can drift apart. The actual "
             "behavior is being verified in-game. Moderate factors show "
             "it less.",
        "k": "fire rate firerate rof animation sound desync weird rpm "
             "shooting faster slower",
    },
    {
        "q": "Has all of this been tested in the game?",
        "a": "Honest answer: every generated patch is cross-checked "
             "against the game's own config files, and the tool has an "
             "extensive automated test suite - but systematic in-game "
             "play-testing is still in progress. That's why the Nexus "
             "page says 'not play-tested yet'. If something misbehaves, "
             "a comment on Nexus with the affected slider helps a lot "
             "(the Debug checkbox shows exactly what your pak changes).",
        "k": "tested play tested safe trust quality verified beta stable "
             "savegame safe",
    },
    {
        "q": "Can this break my savegame or quests?",
        "a": "The tool is deliberately conservative: loot sliders skip "
             "quest items, story rewards, unique weapons and money by "
             "checking every item against the game's own quest markers; "
             "trader stock stays vanilla; only existing values are "
             "scaled, never new ones created. Removing the pak returns "
             "the game to vanilla - with the one known exception that "
             "movement values can persist in a savegame until a refresh "
             "trigger. Still: keep a backup save before big experiments, "
             "as in-game verification is ongoing.",
        "k": "savegame broken quest safe corrupt backup risk items "
             "progress stuck",
    },
    {
        "q": "The game updated and my mod stopped working or crashes",
        "a": "Rebuild the pak: start the tool, let it re-read the new "
             "game version, build again, replace the old pak. A pak from "
             "an older game version can point at moved structures. If it "
             "still misbehaves, remove the pak, verify game files in "
             "Steam, and rebuild with fewer tweaks to find the culprit "
             "(the Debug checkbox helps).",
        "k": "crash broken update not working startup freeze error "
             "bisect culprit",
    },
    {
        "q": "How do I update the tool? Is there an auto-update?",
        "a": "Click '⟳ Check for updates' (top right): the tool asks "
             "github.com once whether a newer release exists - it never "
             "checks in the background. If there is one, choose 'update "
             "now' and the bundled update.bat swaps S2Tweaker.exe for "
             "you (the old exe is kept as S2Tweaker.exe.bak), or open "
             "the download page and do it yourself. Settings, presets, "
             "output and cache always stay where they are. update.bat "
             "is plain text - read it if you like.",
        "k": "update autoupdate upgrade new version release download "
             "github check latest newer patch tool bat updater",
    },
    {
        "q": "Which values are 'vanilla'? Where do the numbers come from?",
        "a": "From YOUR installation: the tool extracts the game's real "
             "config files and reads every base value live, so sliders "
             "are multipliers on top of whatever your game version "
             "actually uses. That's also why sliders show '(vanilla)' "
             "instead of a fixed number - after a game patch the base "
             "may change, your multiplier stays.",
        "k": "vanilla values numbers base multiplier percent where from "
             "accurate",
    },
]
