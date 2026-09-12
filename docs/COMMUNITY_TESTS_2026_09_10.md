# Community reports reviewed on 11–12 September 2026

12 September follow-up: [Molkerr reports](https://github.com/Zayn995/S2Tweaker/issues/9#issuecomment-5644157394) working quest translations and
the second return marker surviving a hand-in before/after save/load. Liquid Stone
resistances change at strength values 100, 500 and 1000. His message does not name
the exact tool version. This supersedes his earlier missing-text/marker result for
the tested case, while wider languages, givers, rewards and artifact combinations
remain unverified. The table below preserves the earlier observations.

These are player reports, not tests performed by the developer during this
session. Limited observations are kept separate from controlled measurements.

| Issue | Report | Interpretation |
| --- | --- | --- |
| [#9](https://github.com/Zayn995/S2Tweaker/issues/9#issuecomment-5635943100) | Molkerr reports separate hand-ins and the remaining journal surviving save/load in 1.39; the cancel line cancels both. | Partial player validation of independent journals. Missing title/objective localization is confirmed in his video. A completed sibling lost its marker in one report; an unfinished sibling retained its marker in a later clean-save test. Issue remains open. |
| [#9 artifacts](https://github.com/Zayn995/S2Tweaker/issues/9#issuecomment-5636395348) | Individual artifact edits work for Molkerr; weakened artifacts retain their old displayed strength. Requests extra bonus types and cosmetic controls. | Version 1.40.0 offers the optional tier display and nine extra-bonus families (518 available artifact/family choices). The new display, added effects and inherited-variant protection still need game tests. |
| [#10](https://github.com/Zayn995/S2Tweaker/issues/10) | craigduk76 confirms talk distance on 1.37.1 at 200%; prefers 180%. | Both minimum and maximum scale; standing too close can prevent interaction. No behavior change made here. |
| [#12](https://github.com/Zayn995/S2Tweaker/issues/12) | 1% sober-up speed tested through eventual sobriety. | Extends the earlier 25% confirmation. An emission briefly interrupts swaying. |
| [#13](https://github.com/Zayn995/S2Tweaker/issues/13) | 400% search time seems to work; requests 1000%. | Qualitative observation at 400%; new higher ceiling not play-tested. Empty RelationLevels and zero anomaly confidence time match local vanilla. |
| [#14](https://github.com/Zayn995/S2Tweaker/issues/14) | Aim punch at 300% makes returning fire difficult. | Reported confirmation at that setting. |
| [#15](https://github.com/Zayn995/S2Tweaker/issues/15) | At the same saved position, 300% weapon noise makes an unsuppressed AK alert NPCs; suppressed shots still pass. | Comparative evidence for weapon noise at 300%. |
| [#16](https://github.com/Zayn995/S2Tweaker/issues/16) | Guaranteed-hit shots at 0% seem to work; NPCs remain accurate. | Qualitative support; no measured hit probability. |
| [#17](https://github.com/Zayn995/S2Tweaker/issues/17) | Night light perception at 50% feels less bot-like. | Qualitative support; dawn/morning also scale. The proposed 0.2 safety threshold is the player's speculation, not a verified limit. |
| [#18](https://github.com/Zayn995/S2Tweaker/issues/18) | At 50% flashlight use, many Ward soldiers fight without lights. | Observational support, not a measured probability. |
| [#19](https://github.com/Zayn995/S2Tweaker/issues/19) | Respawn 25%, refill cooldown 400%, encounter frequency 25%, expansion 25% make the zone quieter. | Combined test, so no individual slider is independently confirmed. No conclusion about the performance or stability of a 1000-agent cap. |

The 1000% search-time option and the multi-job repair were introduced after
1.37.1. Later releases retained the journal repair. These observations do not
establish every giver, reward, hand-in order or long-term save behavior.
