# S2Tweaker 1.44.2 — Movement Animation & Sound Update: Walk, Run, Sprint & Sneak

**Movement speed, animations and movement sounds now follow the same selected
factors across walking, running, sprinting, crouched sneaking and low crouch.**
Low crouch refers to the game's existing deeply crouched movement, not a new
prone or crawling stance.

- **Ordinary walking and running now receive animation synchronization.**
  They use the same native body/shadow playback correction as crouching and
  sprinting. This closes the normal walk/run gap in the previous update.
- **Matching footsteps, backpack rattle and clothing sounds.** The movement
  sound option follows the same walk/crouch and run/sprint factors. Native
  animation events still trigger footsteps; sound duration changes without
  shifting pitch or replacing the game's recordings.
- **The existing sliders control the whole path.** Use **Walk & crouch speed**
  for walking, sneaking and low crouch, and **Run & sprint speed** for running
  and sprinting. Fine numeric-entry values remain supported.
- Active weapon-action montages keep their native timing, and the existing
  limping and overweight handling remains in place.

Enable both **Synchronize movement animations (experimental)** and
**Synchronize movement sounds (experimental)** on the Player page. Rebuild and
reinstall the companion and its numeric profile after updating. **Install to
~mods** handles these automatically; **Build pak** exports the matching
`*_AnimationSync.zip`. Debug export includes the same companion and settings.
Close the game before installation and restart after changing settings.

A brief Zone Kit gameplay check used actual generated CFGs at 80% walking and
140% running. It verified the selected body/shadow rates, changed foot-pose
cycles, and matching live sound-duration parameters for Step, Backpack and
Clothes. Earlier crouch/sprint checks support the shared implementation.

The companion remains experimental. Packaged campaign play, every crossed
extreme walk/run combination and arbitrary mod combinations remain unverified.
The update contains the small original controller and effect banks; no original
game animations, skeletons or sound media are included.

[Installation, behavior and limits](../docs/ANIMATION_SYNC.md).
