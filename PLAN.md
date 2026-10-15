# Week 2 "Side Hustle": plan

Due 2026-10-18, 11:59 PM PDT. Pre-submit gate on 2026-10-16 evening.

## Pitch

A bilingual freelancer can turn a small business's English website into Canadian French in minutes, on a model they own.

Genre in three seconds: a translation tool, fine-tuned on text that real government translators produced.

## Headline number (written before any code)

On N held-out sentence pairs translated professionally by the Government of Canada, the fine-tuned model compared with its own base model:

- chrF and COMET against the human reference
- Termium Plus term agreement: the share of known English terms rendered with the preferred French term
- cost per 1,000 words when run locally, against the per-word rate a client pays a human translator

Graded by: the federal translators' published French versions, which I did not write and cannot change. The ablation is built in: the same prompts with Tinker's fine-tune switched off.

All numbers are placeholders until measured. Every placeholder that the data contradicts goes in a correction log.

## Decisions from research (Oct 13)

- **Base model: Qwen3.5-4B on Tinker**, thinking off. It is small enough to run on a laptop after export (PEFT adapter or merged HF model). Qwen3-8B is the cheaper fallback for training. A run of about 3M tokens costs roughly $1.30 to $4.40. Gemma is not on Tinker.
- **Training data:** bilingual dataset titles and descriptions from the Open Government Portal (CKAN `package_search`, `title_translated` / `notes_translated`, licence `ca-ogl-lgo`). Open Government Licence, so the corpus can be published. Drop the machine-translated variants (`en-t-fr` / `fr-t-en` keys), strip the HTML, and align at sentence level.
- **Termium Plus** (Open Government Licence, CSV by subject, Administration and Economy ZIPs) provides the term check. Not yet verified: its columns, and whether it marks the preferred term.
- **Held-out eval:** professionally translated canada.ca small-business pages (CRA and canada.ca/business), paired through the language toggle. Their terms allow non-commercial use only, so they are used for grading and never redistributed. The repo ships the URLs and the scraper, not the text.
- **Metrics:** sacrebleu chrF++ and BLEU, plus COMET (Unbabel/wmt22-comet-da on CPU). The base model's own FLORES-200 eng->fra score is a sanity check. Published reference figures could not be verified, so none are quoted.
- **Gemma** runs locally as a third column in the comparison, which also qualifies the entry for the Gemma category.

## Sponsor surface (target 4 or more)

- Tinker: LoRA fine-tune (primary category)
- Gemma: local comparison column
- Render or DigitalOcean: host the demo
- Sentry Agent Tracing: trace each translation run
- .tech domain

## Demo script draft (60 to 90 s)

1. A real English page from a small business. Paste it in.
2. The base model's French appears next to the fine-tuned model's French. The Termium terms each one got wrong are highlighted.
3. The score card: chrF, COMET and term agreement on held-out government text, base model against fine-tune.
4. A refusal beat: a sentence where the model is unsure of a term, so it flags the term for the human instead of guessing.
5. The final shot: the finished French page, ready to send to the client.

## Schedule

- Oct 13: lock data sources, base model and metrics. Build the corpus split.
- Oct 14: baseline eval, then the first Tinker SFT run. Have one real number by end of day.
- Oct 15: iterate on the fine-tune, export the adapter, run it locally.
- Oct 16: web UI, hosting, Sentry. Write the post draft. Pre-submit gate in the evening.
- Oct 17: first real user, record the video, check claims against data.
- Oct 18: publish, then check logged out.

## Correction log (where the data overruled me)

- **Oct 14, Termium check too loose.** The first version counted French terms labelled "avoid, see observation". In Termium that means avoid only in some contexts, and those labels flagged the government's own reference translations 21 times out of 25. They are now excluded. The 4 hits left in the references are all "année fiscale", which Termium labels a calque (it prefers "exercice financier") and canada.ca still uses. Report this as a real disagreement between two federal sources. Do not tune it away.
- **Oct 14, one term counted several times.** "Fiscal year" sits in three Termium concepts, so a single "année fiscale" counted three times. The base model's 92 hits became 24 once each avoided term counted once per sentence. The reference's 4 became 1, so the human translators use "année fiscale" in only one held-out sentence.
- **Oct 14, random sample too thin for terminology.** A random 300 sentences holds only about 28 that touch an avoid concept. Scoring is now 300 random sentences for chrF++/BLEU/COMET plus every terminology sentence (147 after the fix), reported separately.
- **Oct 14, local runs are not perfectly deterministic.** Gemma 3 4B scored chrF++ 53.24, then 53.49, on the same 10 sentences at temperature 0. Report local scores as a range.

## First result (Oct 14, run 1: Qwen3.5-4B, LoRA rank 32, 8,000 OGL pairs, 2 epochs, est. $1.26, 13 min)

Same 447 held-out sentences for both. Files: `results/base_qwen35_4b.json`, `results/ft_qwen35_4b.json`, `results/compare_*.json`.

| | Base | Fine-tune |
|---|---|---|
| English acronyms left in the French | 41 | 6 |
| French acronyms reproduced (of 242 in the references) | 50.8% | 55.8% |
| Terminology sentences using a Termium term to avoid (of 147) | 24 | 7 |
| chrF++ / BLEU / COMET | 55.32 / 32.35 / 0.789 | 55.65 / 32.64 / 0.781 |

In a paired bootstrap the fine-tune beats the base on chrF++ in only 72.5% of resamples, so overall quality is unchanged and the post must say so. The gain is terminology and acronyms. That fits the training data: catalogue titles and descriptions, not running prose.

## Oct 14 evening: product and run 2

- The web app (`app/`) works locally against Tinker. Its review flags are (1) English acronyms left in, (2) an expected French acronym missing, and (3) Termium avoid terms. Each flag cites its source.
- **Live finding:** on "a business number (BN) from the CRA", the base model wrote "RRCQ" and run 1 wrote "RC". The government form is ARC, used in 31 of 31 OGL pairs. Neither was caught until I added the learned acronym map: 466 EN->FR acronyms, each seen at least 3 times with at least 70% agreement.
- **Run 2** oversamples acronym-bearing pairs: 2,000 of 8,000 drawn from 10,752 such pairs, est. $1.35. Both runs get reported on the same held-out set, and the one the app serves is chosen and disclosed.
- **Credit used so far (estimate):** run 1 $1.26, eval sampling about $0.30, run 2 $1.35. About $7 remains.

## Run 2 result and the choice (Oct 14 night)

| | Base | Run 1 | Run 2 (25% acronym pairs) |
|---|---|---|---|
| Government's French acronym written correctly (of 242) | 50.8% | 55.8% | **66.9%** |
| English acronyms left in | 41 | **6** | 10 |
| Termium avoid sentences (of 147) | 24 | **7** | 14 |
| chrF++ / BLEU / COMET | 55.32 / 32.35 / 0.789 | 55.65 / 32.64 / 0.781 | 56.09 / 33.57 / 0.785 |
| chrF++ beats base in bootstrap | | 72.5% | 92% (short of 95%) |

**The app serves run 2.** On the demo sentences it writes "(NE) de l'ARC" and "exercice financier", where run 1 wrote "de la RC" and mangled SIN into "N° de S de C". Run 2 writes "NIS" for SIN, but the government form is NAS, and the acronym map flags it. Run 1's better Termium count is reported, not hidden.

**Recorded demo outputs (`results/demo_outputs.json`) cut both ways. Say so in the post:**
- CRA: base "du RRCQ" (invented), run 1 "de la RC", run 2 **"de l'ARC"** (correct).
- Fiscal year: base "exercice fiscal", run 1 "exercice", run 2 **"exercice financier"** (Termium's preferred term).
- SIN: **the base model is right** ("numéro d'assurance sociale (NAS)"). Run 1 writes "N° de S de C" and run 2 "NIS". Run 2's error is caught by the acronym map.
- Run 2 writes "Conserver" (infinitive) where an instruction needs "Conservez". It's a grammar slip none of the checks catch.
- Run 1 against run 2 on chrF++: run 2 ahead in 77.4% of resamples, so they are level.

## Local runtime (the "model you own" claim)

- Tinker's archive download timed out the first time and worked on the retry. `train.py` now also calls `save_weights_external` while the session is alive.
- The Hugging Face cache needs symlinks, which Windows blocks, so the base model is downloaded into the plain `models/base` folder.
- Ollama 0.40 refuses LoRA adapters, and it can only quantise safetensors with MLX (Mac). Route: llama.cpp converts to an f16 GGUF, llama-quantize produces Q4_K_M, then `ollama create`. This is `scripts/make_local.py`.
- **Speed on an RTX 5060 laptop (8 GB):** Q8_0 ran at 0.8 tok/s (slow path), Q4_K_M at **20.8 tok/s**, and stock qwen3.5:4b at 16.5 tok/s. The Q4_K_M file is 2.59 GB.
- Run 2 is local too: `ollama:cafr-run2`, Q4_K_M. On the 4 demo sentences it matches cloud run 2 on 3. On the fourth it wrote "Si vous gagnez" for "If you expect to earn", where the cloud wrote "Si vous prévoyez gagner". The "expect" is lost, a small quantisation change in meaning.
- Local mode for the app: `FT_SPEC=ollama:cafr-run2 BASE_SPEC=ollama:qwen3.5:4b`.
- **Quantisation cost, measured on run 1:** local Q4 against cloud. chrF++ 54.96 against 55.65 (cloud ahead in 95.9% of resamples, a real drop). French acronyms 52.1% against 55.8%. English acronyms left in 10 against 6. Termium avoid sentences 5 against 7. Local trades about 0.7 chrF and a few acronyms for running offline.
- **Local run 2 (the model the app serves offline):**
  - chrF++ 56.43 against cloud 56.09, so the two are level: local ahead in 83.2% of resamples.
  - Acronyms: 67.8% correct (cloud 66.9%), 9 English left in (cloud 10).
  - Termium avoid sentences: 13 (cloud 14).
  - Against the base model it clears the 95% bar (98.2%); the cloud copy does not (92%). Reported as noise between two equal models, not as a win for local.
  - 32.5 tok/s, 2.59 GB.

## Early observation (5 sentences, superseded by the result above)

The base model keeps English acronyms where the government's French uses its own: "BN" where the reference says NE (numéro d'entreprise), "QFFP" where it says BAPA. If the fine-tune fixes this across the full set, it is the demo moment.
