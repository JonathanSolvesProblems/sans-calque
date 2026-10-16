# UI audit: deployed page (2026-10-16)

Audit of https://sans-calque.51-161-82-166.sslip.io as deployed. Nothing was changed. Captures are in `.design/shots/audit/`.

## Verdict

**Not at the bar.** The blind critic scores it 6/10, and the final gate wants 3 or lower. It has been 6 for four rounds in a row. What it remembers after three seconds is the circled **RRCQ** next to **66.9%**, and it calls that highlight "the one thing on the page that looks invented, not defaulted".

## Passing

- `lint_brand.py` with the charter: 0 errors, 0 warnings, 0 tracked-caps rules.
- Dark default plus a designed light theme. Motion runs (2 animations when results land) and stops under reduced motion (0).
- Icon served (`/static/icon.svg`, 200). One `h1`. No horizontal overflow at 1280 or 390. Tab order is logical.
- The deployed URL serves this build: the new sample and the provenance line were confirmed live.
- The cover test passes: with the wordmark hidden, the walnut, vellum and amber show-through are still recognisable.
- No seeded or stubbed data. The hero quotes recorded output, and the page says so.

## Failing or weak

| # | Finding | Source | Proposed fix | Cost |
|---|---|---|---|---|
| 1 | Error text on the table in dark mode is 4.42:1 | contrast script | `--pencil-ink` #a8281f to **#9c2219** (4.97 on table, 5.96 on vellum) | 1 value |
| 2 | Secondary text on the desk in light mode is 4.48:1, and the critic calls light-mode small text near illegible | contrast script and critic | light `--on-desk-2` #4a4037 to **#41372f** (5.14), and the smallest light-mode text from 14 to 15px | 2 values |
| 3 | The punch holes read as "carousel dots" (named in 3 of 4 rounds) | critic | Remove them. The metaphor survives without them | 1 rule |
| 4 | The 66.9% reads as the generic stat block (3 of 4 rounds), and at 1280 its caption is cut by the fold | critic | Drop the red rule and size the number down so caption and baselines sit above the fold. Keep the number visible: the hackathon guide wants it designed and on the first screen, so it should not move into the paragraph | small |
| 5 | Results repeat identical labelled bars. Flags in bold lettering read as UI | critic | Label "Untouched" and "Fine-tuned" on the first row only, and set flag notes in Spectral at body size so they read as margin notes | small |
| 6 | 390: the 66.9% appears only after a long scroll | critic | On phones, move the pinned figure above the specimen | 1 rule |
| 7 | Two type families "from different worlds" (named in all 4 rounds) | critic | Judgement call. Option: set the h1 and section headings in Spectral and keep Osifont for the wordmark, numbers and labels. Against: a large serif headline is close to the 2026 "Claude aesthetic" tell | medium |
| 8 | `.design/manifest.json` was never written | final gate | Write it from the built values | admin |

Recommended for before the video: 1, 2, 3, 5, 6, about an hour in all, every one a value or a rule. Items 4 and 7 change the look, so they are your call.
