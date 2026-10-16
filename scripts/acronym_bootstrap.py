"""Is the acronym gain real? Paired bootstrap over held-out sentences.

For every held-out sentence, count the French acronyms in the government reference that
are not in the English source, and how many of them each system reproduced. Resample
sentences 1,000 times and report how often system B's rate beats system A's.
Writes results/acronym_bootstrap_<a>_vs_<b>.json.
"""
import json
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from evaluate import scored_set  # noqa: E402
from termium import Checker  # noqa: E402

ACR = re.compile(r"\b[A-ZÀ-Ý]{2,6}\b")


def per_sentence(rows, outs):
    out = []
    for p in rows:
        fr_only = set(ACR.findall(p["fr"])) - set(ACR.findall(p["en"]))
        if fr_only:
            got = len(fr_only & set(ACR.findall(outs[p["en"]]["out"])))
            out.append((got, len(fr_only)))
    return out


a, b = sys.argv[1], sys.argv[2]
rows, _, _ = scored_set(300, Checker())
load = lambda n: {json.loads(l)["en"]: json.loads(l) for l in Path(f"data/eval_private/out_{n}.jsonl").open(encoding="utf-8")}
pa, pb = per_sentence(rows, load(a)), per_sentence(rows, load(b))
idx = list(range(len(pa)))
rng, wins = random.Random(0), 0
for _ in range(1000):
    s = [rng.choice(idx) for _ in idx]
    ra = sum(pa[i][0] for i in s) / sum(pa[i][1] for i in s)
    rb = sum(pb[i][0] for i in s) / sum(pb[i][1] for i in s)
    wins += rb > ra
res = {"a": a, "b": b, "sentences_with_french_acronyms": len(pa),
       "rate_a": round(sum(x for x, _ in pa) / sum(y for _, y in pa), 3),
       "rate_b": round(sum(x for x, _ in pb) / sum(y for _, y in pb), 3),
       "b_beats_a_share": wins / 1000}
Path(f"results/acronym_bootstrap_{a}_vs_{b}.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
print(json.dumps(res, indent=1))
