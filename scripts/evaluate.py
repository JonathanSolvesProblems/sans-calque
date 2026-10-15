"""Score a system against the held-out canada.ca pairs.

The reference French was written by Government of Canada translators, so every score here
is graded by text this project did not write. Outputs stay in data/eval_private/ (they are
translations of non-commercially licensed text); only the scores are committed, to
results/<name>.json.

Usage: python scripts/evaluate.py <name> <backend-spec> [n]
  e.g. python scripts/evaluate.py base tinker:Qwen/Qwen3.5-4B 300
       python scripts/evaluate.py gemma ollama:gemma3:4b 300
"""
import asyncio
import collections
import json
import random
import re
import sys
from pathlib import Path

import sacrebleu

sys.path.insert(0, str(Path(__file__).parent))
from termium import Checker  # noqa: E402
from translate import backend  # noqa: E402

PAIRS = Path("data/eval_private/pairs.jsonl")
NAV = re.compile(r"^(facebook|twitter|x|linkedin|youtube|instagram|flickr)\s*:", re.I)


def eval_set(n: int) -> list[dict]:
    """Fixed sample: real sentences only (no nav labels, no link lists), seed 0, deduped."""
    seen, rows = set(), []
    for line in PAIRS.open(encoding="utf-8"):
        p = json.loads(line)
        en = p["en"]
        if len(en) < 40 or len(en.split()) < 7 or NAV.match(en) or en in seen:
            continue
        seen.add(en)
        rows.append(p)
    random.Random(0).shuffle(rows)
    return rows[:n]


def scored_set(n: int, chk) -> tuple[list[dict], list[int], list[int]]:
    """n random sentences for the overall scores, plus EVERY sentence that touches a Termium
    avoid concept (a random 300 would hold only ~28, too few to say anything).
    Returns rows and the indices of each subset; the two subsets can overlap."""
    pool = eval_set(10**9)
    general = pool[:n]
    term = [p for p in pool if chk.triggered(p["en"])]
    rows, index = [], {}
    for p in general + term:
        if p["en"] not in index:
            index[p["en"]] = len(rows)
            rows.append(p)
    return rows, [index[p["en"]] for p in general], [index[p["en"]] for p in term]


async def run(name: str, spec: str, n: int, concurrency: int) -> None:
    chk = Checker()
    rows, general_idx, term_rows = scored_set(n, chk)
    if spec == "rescore":
        # re-score saved outputs after a scoring fix, without paying for new samples
        saved = {json.loads(l)["en"]: json.loads(l) for l in Path(f"data/eval_private/out_{name}.jsonl").open(encoding="utf-8")}
        outs = [saved[p["en"]]["out"] if not saved[p["en"]]["error"] else {"error": saved[p["en"]]["error"]} for p in rows]
        spec = json.loads(Path(f"results/{name}.json").read_text(encoding="utf-8"))["backend"]
    else:
        be = backend(spec)
        sem = asyncio.Semaphore(concurrency)

        async def one(p):
            async with sem:
                try:
                    return await be.translate(p["en"])
                except Exception as e:  # a failed call is recorded as a failure, never as an empty translation
                    return {"error": f"{type(e).__name__}: {e}"}

        outs = await asyncio.gather(*(one(p) for p in rows))
    failed = [i for i, o in enumerate(outs) if isinstance(o, dict)]
    hyp = [o if isinstance(o, str) else "" for o in outs]
    ref = [p["fr"] for p in rows]
    src = [p["en"] for p in rows]

    hits = {i: chk.check(src[i], hyp[i]) for i in term_rows}
    ref_hits = sum(len(chk.check(src[i], ref[i])) for i in term_rows)
    g_hyp, g_ref, g_src = [hyp[i] for i in general_idx], [ref[i] for i in general_idx], [src[i] for i in general_idx]

    scores = {
        "name": name, "backend": spec, "n_general": len(general_idx), "failed_calls": len(failed),
        "chrf++": round(sacrebleu.corpus_chrf(g_hyp, [g_ref], word_order=2).score, 2),
        "bleu": round(sacrebleu.corpus_bleu(g_hyp, [g_ref]).score, 2),
        "termium_sentences": len(term_rows),
        "termium_avoid_hits": sum(len(h) for h in hits.values()),
        "termium_sentences_with_avoid": sum(1 for h in hits.values() if h),
        "termium_avoid_hits_in_reference": ref_hits,
        "termium_terms_used": dict(collections.Counter(h["used"] for hs in hits.values() for h in hs).most_common()),
    }
    try:
        import torch
        from comet import download_model, load_from_checkpoint
        model = load_from_checkpoint(download_model("Unbabel/wmt22-comet-da"))
        out = model.predict([{"src": s, "mt": h, "ref": r} for s, h, r in zip(g_src, g_hyp, g_ref)],
                            batch_size=16, gpus=1 if torch.cuda.is_available() else 0, progress_bar=False)
        scores["comet"] = round(out.system_score, 4)
    except Exception as e:  # COMET is optional on a machine without the weights; say so instead of hiding it
        scores["comet"] = None
        scores["comet_error"] = f"{type(e).__name__}: {e}"

    Path("results").mkdir(exist_ok=True)
    Path(f"results/{name}.json").write_text(json.dumps(scores, indent=1, ensure_ascii=False), encoding="utf-8")
    with Path(f"data/eval_private/out_{name}.jsonl").open("w", encoding="utf-8") as f:
        for s, h, r, o in zip(src, hyp, ref, outs):
            f.write(json.dumps({"en": s, "out": h, "ref": r, "error": o.get("error") if isinstance(o, dict) else None},
                               ensure_ascii=False) + "\n")
    print(json.dumps({k: v for k, v in scores.items() if k != "termium_examples"}, indent=1))


if __name__ == "__main__":
    name, spec = sys.argv[1], sys.argv[2]
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 300
    asyncio.run(run(name, spec, n, concurrency=4 if spec.startswith("ollama") else 32))
