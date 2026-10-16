# Sans calque

English to Canadian French for small-business pages, on a 4-billion-parameter open model I fine-tuned for about $1.35 and can run on a laptop. Every flag it raises cites where its rule came from.

Built for the DEV Hacktoberfest Open-Source AI Challenge, Week 2: Side Hustle.

## What it does

Paste English. You get the fine-tuned model's French next to the untouched base model's, a review list, and a "French, ready to send" box. The review list flags three things, each with its source:

- **An English acronym left in the French**, such as "CRA" in a French sentence.
- **A French acronym that is missing**, when the government uses a known one: ARC for CRA (31 of 31 government pairs), NAS for SIN (10 of 10). The map has 466 acronyms, learned from the training pairs.
- **A term the Translation Bureau says to avoid**, from Termium Plus. An example is "année fiscale", which Termium labels a calque of "fiscal year"; the preferred term is "exercice financier".

Two things came out of the first real use, on my own site:
- **Fetch the page.** Give a public page's address and its text is laid on the table. The fetcher refuses non-web schemes, unusual ports and private addresses, and it checks the address it actually connected to, so a rebinding DNS answer can't reach the server's neighbours.
- **Keep in English.** A per-client list of terms such as MCP or SDK that stay in English. They are exempt from the acronym checks only, and Termium checks still run. On my own "How I work" page this took 8 flags down to 1, and the one left was a real error.

Nothing is rewritten silently. A flagged sentence goes on the review list, and a failed block is shown as failed, never as an empty translation.

## Results

All systems were scored on the same held-out text: 300 random sentences from canada.ca small-business pages, plus all 147 that contain a Termium concept with a term to avoid. The French on those pages was written by Government of Canada translators, so every score here is graded by text I did not write.

| | Gemma 3 4B | Qwen3.5-4B base | Run 1 | **Run 2 (served)** |
|---|---|---|---|---|
| Government's French acronym written correctly (of 242) | 36.0% | 50.8% | 55.8% | **66.9%** |
| English acronyms left in the French | 47 | 41 | 6 | 10 |
| Sentences using a Termium "avoid" term (of 147) | 16 | 24 | 7 | 14 |
| chrF++ | 50.58 | 55.32 | 55.65 | 56.09 |
| COMET (wmt22-comet-da) | 0.759 | 0.789 | 0.781 | 0.785 |

What the table does and does not show:

- **The gain is in acronyms and terms.** Overall quality is not measurably better. In a paired bootstrap of 1,000 resamples, run 2 beats the base model on chrF++ in 92% of them, short of the 95% I set before looking. Run 1 beats it in 72.5%.
- **Run 2 is not better everywhere.** It writes the correct government acronym far more often, but it leaves more English acronyms in and uses more Termium "avoid" terms than run 1. I serve run 2 because it gets the acronyms a client would notice (ARC, not "RC"), and the checks catch what it still gets wrong.
- **On one demo sentence the base model wins.** For "your SIN", the base model writes "numéro d'assurance sociale (NAS)" and run 2 writes "NIS". The acronym check flags it.
- Gemma 3 4B ran locally through Ollama. 1 of its 447 calls failed with a server error and is scored as an empty translation.

## The fine-tune

- **Base model:** Qwen3.5-4B on [Tinker](https://thinkingmachines.ai/tinker/), LoRA rank 32, 2 epochs, learning rate 2e-4.
- **Data:** 8,000 English–French pairs from the titles and descriptions of datasets on the [Open Government Portal](https://open.canada.ca), all under the Open Government Licence – Canada. Records whose French the portal marks as machine-translated were dropped. Run 2 draws 2,000 of its 8,000 pairs from the 10,752 that contain a known acronym.
- **Cost:** run 1 cost an estimated $1.26 and run 2 $1.35, from Tinker's published per-token training price and the real token count.
- **No overlap with the test set:** no training sentence appears in the held-out set.

## Running it on your own machine

The point of an open model is that the weights are yours. The fine-tune exports from Tinker and runs in Ollama on an 8 GB laptop GPU (an RTX 5060) at 32.5 tokens per second, as a 2.59 GB 4-bit file.

Quantising to 4-bit can cost something, so I scored the laptop copies on the same held-out set instead of assuming. For run 1, the local copy scored chrF++ 54.96 against 55.65 in the cloud, a real drop in a paired bootstrap. For run 2 it did not drop: chrF++ 56.43 against 56.09 in the cloud, with the government's acronym written correctly 67.8% of the time against 66.9%. The two are level (the laptop copy is ahead in 83.2% of resamples). Against the base model, the laptop copy clears the 95% bar (98.2% of resamples) and the cloud copy does not (92%). Between two copies that score the same, I read that as noise, not as the laptop being better.

```
python scripts/export_model.py run2   # download adapter, merge into the base model
python scripts/make_local.py run2     # f16 GGUF -> Q4_K_M -> ollama create cafr-run2
FT_SPEC=ollama:cafr-run2 BASE_SPEC=ollama:qwen3.5:4b uvicorn app.server:app --port 8790
```

`make_local.py` documents three dead ends on Windows. Ollama 0.40 no longer accepts LoRA adapters. Its own quantiser needs MLX, which is Mac only. An 8-bit GGUF ran at 0.8 tokens per second, against 20.8 at 4-bit.

## Reproducing the numbers

```
python scripts/pull_ogp.py            # 48,116 catalogue records
python scripts/build_corpus.py        # 82,455 OGL pairs
python scripts/pull_eval.py 200       # held-out canada.ca pairs (kept local, see below)
python scripts/termium.py             # Termium avoid index
python scripts/train.py --n 8000 --epochs 2 --acronym-share 0.25 --name run2
python scripts/evaluate.py base_qwen35_4b tinker:Qwen/Qwen3.5-4B 300
python scripts/compare.py base_qwen35_4b ft2_qwen35_4b
python scripts/check_claims.py        # fails if a number in this README disagrees with results/
```

**Licences.**
- **Training data** is under the Open Government Licence – Canada and can be redistributed.
- **The held-out test text** comes from canada.ca, whose terms allow non-commercial reproduction only. The repository ships the scraper and the URL list (`data/eval_urls.json`), never the text, and model outputs on it stay local too.
- **Termium Plus** is under the Open Government Licence – Canada.

## Correction log

Every place where the data overruled my first version is in [PLAN.md](PLAN.md#correction-log-where-the-data-overruled-me). Three examples:

- My first Termium check flagged the government's own translators 21 times.
- One term was counted three times.
- The 8-bit local model ran 26 times slower than the 4-bit one.
