---
title: A $1.35 fine-tune taught an open 4B model that CRA is ARC in French. It still writes NIS for SIN.
tags: devchallenge, hf26challenge, ai, opensource
---

*This is a submission for the [Hacktoberfest Open-Source AI Challenge, Week 2: Side Hustle](https://dev.to/challenges/hacktoberfest-week2-2026-10-12)*

## What I Built

Ask an open 4B model to put "you need a business number (BN) from the CRA" into French and it writes "auprès du RRCQ". There is no RRCQ. The Canada Revenue Agency is the ARC in French, and in Canada's open data the government's translators wrote ARC all 31 times the pair shows up.

That one acronym is the whole side hustle in miniature. Mine is building things on the side: send me a brief and I send back a working demo in 48 hours. My own site ships in English and fr-CA, so every page I write needs a French twin, and a Canadian client who wants the same is trusting that the French is right. They won't read it closely. They will notice CRA where it should say ARC.

**Sans calque** is the tool for that freelancer. Paste English, get French from a model I fine-tuned for $1.35 on government text, next to the untouched base model, plus a review list. It flags three things, and each flag says where its rule came from:

- an English acronym left in the French
- a missing French acronym the government uses (ARC for CRA, NAS for SIN), from 466 pairs learned from open data
- a term the Translation Bureau's Termium Plus says to avoid, like "année fiscale" for fiscal year (it wants "exercice financier")

Nothing gets fixed silently. A flagged sentence lands on the review list, and the "French, ready to send" box tells you how many blocks to check first.

## Demo

[X: video or deployed link]

## Code

{% github [X: repo] %}

## How I Built It

**The data is all open.** Every dataset on Canada's Open Government Portal has its title and description in both languages, under the Open Government Licence. I pulled all 48,116 records, dropped the ones whose French the portal marks as machine-translated, and paired paragraphs and sentences only when both sides split the same way. That gave 82,455 pairs.

**The fine-tune is two runs on Tinker.** Qwen3.5-4B, LoRA rank 32, 8,000 pairs, 2 epochs, about 13 minutes each. Run 1 was a random sample. Run 2 drew 2,000 of its pairs from the 10,752 that contain a known acronym, because run 1 still wrote "de la RC" for CRA. Estimated cost: $1.26 and $1.35, from Tinker's per-token price and the real token count. The training script refuses to start if the estimate goes over budget, because the credit is a one-time $10.

**The grading is not mine.** I scored everything on canada.ca small-business pages, whose French was written by Government of Canada translators: 300 random sentences, plus all 147 that touch a Termium "avoid" concept. None of those sentences were in training.

| | Gemma 3 4B | Qwen3.5-4B base | Run 1 | Run 2 |
|---|---|---|---|---|
| Government's French acronym written correctly | 36.0% | 50.8% | 55.8% | **66.9%** |
| English acronyms left in the French | 47 | 41 | 6 | 10 |
| Sentences with a Termium "avoid" term (of 147) | 16 | 24 | 7 | 14 |
| chrF++ | 50.58 | 55.32 | 55.65 | 56.09 |

The gain is acronyms and terms, not overall quality. Run 2 beats the base model on chrF++ in 92% of 1,000 bootstrap resamples, and I had set 95% as the bar before running it, so I don't claim it. Run 2 isn't better everywhere either. It leaves more English acronyms and more Termium terms than run 1. I serve it anyway because it gets the acronyms a client notices.

**It's not always right, and the base model sometimes is.** On "you can apply for your SIN", the base model writes "numéro d'assurance sociale (NAS)", which is correct. Run 2 writes "NIS". The acronym check catches it: the government wrote NAS in 10 of 10 pairs. Run 2 also wrote "Conserver" where an instruction needs "Conservez", and none of my checks catch that one. That's why the box says to read it before you send it.

**The checks got checked too.** My first Termium check flagged the government's own translators 21 times out of 25. The label it was counting, "avoid, see observation", means avoid in *some* contexts, so I dropped it. What's left flags the human translation once, for "année fiscale", which Termium calls a calque and canada.ca still uses. I left that one in.

`check_claims.py` rebuilds every number in the README from the results files and fails if the prose and the data disagree. It also fails if a model output quoted in the docs isn't in the recorded outputs.

## Why Open Innovation Matters

The weights are mine. I exported the fine-tune from Tinker, converted it to a 2.59 GB 4-bit file and it runs in Ollama on my laptop's 8 GB GPU at 32.5 tokens a second. Client text never has to leave the machine, and there is no per-word bill.

That took three dead ends: Ollama no longer accepts LoRA adapters, its own quantiser needs a Mac, and an 8-bit file ran at 0.8 tokens a second. Shrinking it to 4-bit can cost something, so I scored the laptop copies on the same test. For run 1 it did: chrF++ 54.96 against 55.65 in the cloud. For run 2 it didn't. The laptop copy scored 56.43 against 56.09 and got 67.8% of the government's acronyms right against 66.9%. Statistically those are the same model, so I'm not claiming the laptop is better, just that nothing was lost.

And the open data is the reason any of this works. The training pairs, the terminology bank and the acronym evidence all come from the Government of Canada's open data, and the test is the same government's translators. A closed model can't show you where its "ARC" came from. This one can, down to the 31 pairs.

## My First User

[X: who tried it, what they pasted, what they said]

## Prize Categories

- Best Use of Tinker
- Best Use of Render [X: once deployed]
