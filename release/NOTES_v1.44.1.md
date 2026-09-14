# S2Tweaker 1.44.1 — Companion build and debug export fixes

Small follow-up to the Animation & Sound Update:

- **Native idle sway and firing-animation movement now work on their own.**
  Build pak and Install to ~mods no longer reject these settings with
  "nothing to patch" when no CFG slider has changed. The matching Pak carries
  the settings manifest; the companion and its profile provide the effect.
- **Debug export now includes the companion.** Look in
  `<mod_name>_cfg/AnimationSync` for its loose runtime files, installation README,
  numeric `.sav` profile, JSON parameters and a decoded `.txt` profile.
  Both build and install paths produce this output. A later successful debug
  export with the companion disabled clears its previous generated files.
- A debug-export error does not report a successful Pak build as failed.
  Failed Pak builds still roll back companion installation.

Extract the complete player ZIP and keep its runtime files together. Preserve
your settings and presets when moving folders. Enable the desired companion
options, then build or install again. Close the game before installing.

The two fixes passed 22 focused checks without opening the game or a GUI window.
The companion runtime is unchanged from 1.44.0; this patch changes tool-side
generation and export. All 19 signed desktop runtime binaries are unchanged.

The companion remains experimental: packaged campaign behavior and arbitrary
mod combinations are unverified. This patch does not resolve the earlier local
GUI startup delay observed with both 1.44.0 and unchanged 1.43.0; no new visual
recheck is claimed. [Behavior and limits](../docs/ANIMATION_SYNC.md).
