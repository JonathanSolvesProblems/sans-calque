"""Paired comparison of two scored systems on the identical held-out sentences.

1. Paired bootstrap on chrF++ (1,000 resamples of the 300 general sentences): how often
   system B beats system A. Below ~95% the difference is not claimed.
2. French acronyms: an all-caps token (2-6 letters) that appears in the human reference
   but not in the English source is one the government translators localised (BN -> NE).
   Measured: the share of those the system output reproduces. Graded by the reference.

Usage: python scripts/compare.py <name_a> <name_b>
"""
import json
import random
import re
import sys
from pathlib import Path

import sacrebleu

sys.path.insert(0, str(Path(__file__).parent))
from evaluate import scored_set  # noqa: E402
from termium import Checker  # noqa: E402

ACR = re.compile(r"\b[A-ZÀ-Ý]{2,6}\b")


def load(name: str) -> dict:
    return {json.loads(l)["en"]: json.loads(l) for l in Path(f"data/eval_private/out_{name}.jsonl").open(encoding="utf-8")}


def acronyms(rows: list[dict], outs: dict) -> dict:
    total = got = kept_english = 0
    for p in rows:
        src = set(ACR.findall(p["en"]))
        fr_only = set(ACR.findall(p["fr"])) - src
        if not fr_only:
            continue
        out = set(ACR.findall(outs[p["en"]]["out"]))
        total += len(fr_only)
        got += len(fr_only & out)
        kept_english += len((src - set(ACR.findall(p["fr"]))) & out)
    return {"french_acronyms_in_reference": total, "reproduced": got,
            "rate": round(got / total, 3) if total else None, "english_acronyms_left_in": kept_english}


def main() -> None:
    a, b = sys.argv[1], sys.argv[2]
    rows, general, _ = scored_set(300, Checker())
    oa, ob = load(a), load(b)
    g = [rows[i] for i in general]
    ref = [p["fr"] for p in g]
    ha, hb = [oa[p["en"]]["out"] for p in g], [ob[p["en"]]["out"] for p in g]
    rng, wins = random.Random(0), 0
    for _ in range(1000):
        idx = [rng.randrange(len(g)) for _ in g]
        sa = sacrebleu.corpus_chrf([ha[i] for i in idx], [[ref[i] for i in idx]], word_order=2).score
        sb = sacrebleu.corpus_chrf([hb[i] for i in idx], [[ref[i] for i in idx]], word_order=2).score
        wins += sb > sa
    report = {"a": a, "b": b, "chrf_b_beats_a_share": wins / 1000,
              "acronyms_all_rows": {a: acronyms(rows, oa), b: acronyms(rows, ob)}}
    Path("results").mkdir(exist_ok=True)
    Path(f"results/compare_{a}_vs_{b}.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
