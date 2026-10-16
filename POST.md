---
title: A $1.35 fine-tune taught an open 4B model that CRA is ARC in French. It still writes NIS for SIN.
tags: devchallenge, hf26challenge, ai, opensource
cover_image: https://sans-calque.51-161-82-166.sslip.io/static/og.png
---

*This is a submission for the [Hacktoberfest Open-Source AI Challenge, Week 2: Side Hustle](https://dev.to/challenges/hacktoberfest-week2-2026-10-12)*

## What I Built

Every page on my site has a French twin. I build things on the side (send me a brief, get a working demo back in 48 hours), and the site ships in English and fr-CA, so every new page means a translation.

So I gave an open 4B model a line any Canadian small-business page would have: "you need a business number (BN) from the CRA". It wrote "auprès du RRCQ". There is no RRCQ. The Canada Revenue Agency is the ARC in French, and in Canada's open data the government's translators wrote ARC all 31 times the pair shows up.

Who pays: a small business pays a bilingual freelancer per page to put its site into French. The client won't read the French closely. They will notice CRA where it should say ARC. With an open model on the freelancer's own laptop there's no per-word bill, and the client's text never leaves the machine.

**Sans calque** is the tool for that freelancer. Paste English, get French from a model I fine-tuned for $1.35 on government text, next to the untouched base model, plus a review list. It flags three things, and each flag says where its rule came from:

- an English acronym left in the French
- a missing French acronym the government uses (ARC for CRA, NAS for SIN), from 466 pairs learned from open data
- a term the Translation Bureau's Termium Plus says to avoid, like "année fiscale" for fiscal year (it wants "exercice financier"). On "most small businesses use the calendar year as their fiscal year", the untouched model writes année fiscale and the fine-tune writes année financière. Both models write "comptes à payer" for accounts payable, which Termium also flags, and the check catches it on both

Nothing gets fixed silently. A flagged sentence lands on the review list, and the "French, ready to send" box tells you how many blocks to check first.

## Demo

Try it: **https://sans-calque.51-161-82-166.sslip.io** (it calls the fine-tune live on Tinker, with a daily word cap so the credit lasts). Click "Use the sample" for the sentences in this post.

[X: video]

## Code

{% github JonathanSolvesProblems/sans-calque %}

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

The gain is acronyms and terms, not overall quality. The acronym gain holds up: run 2 beats the base model in all 1,000 bootstrap resamples of the 146 held-out sentences that contain a government French acronym. Overall quality doesn't: run 2 beats the base model on chrF++ in 92% of 1,000 bootstrap resamples, and I had set 95% as the bar before running it, so I don't claim it. Run 2 isn't better everywhere either. It leaves more English acronyms and more Termium terms than run 1. I serve it anyway because it gets the acronyms a client notices.

**It's not always right, and the base model sometimes is.** On "you can apply for your SIN", the base model writes "numéro d'assurance sociale (NAS)", which is correct. Run 2 writes "NIS". The acronym check catches it: the government wrote NAS in 10 of 10 pairs. Run 2 also wrote "Conserver" where an instruction needs "Conservez", and none of my checks catch that one. That's why the box says to read it before you send it.

**The checks got checked too.** My first Termium check flagged the government's own translators 21 times out of 25. The label it was counting, "avoid, see observation", means avoid in *some* contexts, so I dropped it. What's left flags the human translation once, for "année fiscale", which Termium calls a calque and canada.ca still uses. I left that one in.

`check_claims.py` rebuilds every number in the README from the results files and fails if the prose and the data disagree. It also fails if a model output quoted in the docs isn't in the recorded outputs.

## Why Open Innovation Matters

The weights are mine. I exported the fine-tune from Tinker, converted it to a 2.59 GB 4-bit file and it runs in Ollama on my laptop's 8 GB GPU at 32.5 tokens a second. Client text never has to leave the machine, and there is no per-word bill. The same web page runs against it: I loaded it with every request outside my laptop blocked, and it still translated, fonts included, with zero requests out.

That took three dead ends: Ollama no longer accepts LoRA adapters, its own quantiser needs a Mac, and an 8-bit file ran at 0.8 tokens a second. Shrinking it to 4-bit can cost something, so I scored the laptop copies on the same test. For run 1 it did: chrF++ 54.96 against 55.65 in the cloud. For run 2 it didn't. The laptop copy scored 56.43 against 56.09 and got 67.8% of the government's acronyms right against 66.9%. Statistically those are the same model, so I'm not claiming the laptop is better, just that nothing was lost.

And the open data is the reason any of this works. The training pairs, the terminology bank and the acronym evidence all come from the Government of Canada's open data, and the test is the same government's translators. A closed model can't show you where its "ARC" came from. This one can, down to the 31 pairs.

## My First User

Me, on my own site. jonathanandrei.com ships in English and fr-CA, so I pasted the English "How I work" page into the live app: 41 blocks.

The fine-tune raised 8 flags. 7 were noise for this kind of text: MCP, LLM, RAG, FHIR, SDK and a NICE guideline code, all acronyms my own French page keeps in English. The acronym rule learned how the government writes, and tech jargon doesn't follow it.

The 8th was real. My sentence says the logs held data "the AI had already claimed was PHI-free". The French came back as "lesquels avaient déjà été déclarés exempts", which means "which had already been declared free". The AI is gone from the sentence, and it was the whole point of it. The flag fired because the expected "IA" was missing, and it was missing because the model dropped the subject.

So on my own page: one catch that mattered, seven to wave off. That told me what to build next, so I built it: a "keep in English" list per client, and a "Fetch the page" box so the page comes in by its address instead of by copy and paste. Same page, fetched by the app, with MCP, LLM, RAG, FHIR, SDK and the guideline code on the list: 8 flags became 1, and the one left is the real catch.

## Prize Categories

- Best Use of Tinker
