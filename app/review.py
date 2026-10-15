"""Review flags for one translated block. Nothing here edits the translation: it marks what a
human should check before the text goes to the client, and says where each rule came from.

- English acronym left in: an all-caps token from the English source that survives into the
  French. Acronyms that legitimately stay the same in both languages (PDF, T4) are learned
  from the training corpus: any acronym found in BOTH sides of one Open Government Licence
  pair is treated as bilingual. Built from data/train.jsonl only, never from the eval set.
- Termium: a French term the Translation Bureau labels avoid/anglicism for a concept whose
  English term appears in the source (see scripts/termium.py).
"""
import json
import re
import sys
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from termium import Checker  # noqa: E402

ACR = re.compile(r"\b[A-ZÀ-Ý][A-ZÀ-Ý0-9]{1,5}\b")


@lru_cache(maxsize=1)
def bilingual_acronyms() -> frozenset[str]:
    cache = ROOT / "data" / "bilingual_acronyms.json"
    if cache.exists():
        return frozenset(json.loads(cache.read_text(encoding="utf-8")))
    both: set[str] = set()
    for line in (ROOT / "data" / "train.jsonl").open(encoding="utf-8"):
        p = json.loads(line)
        both |= set(ACR.findall(p["en"])) & set(ACR.findall(p["fr"]))
    cache.write_text(json.dumps(sorted(both)), encoding="utf-8")
    return frozenset(both)


@lru_cache(maxsize=1)
def acronym_map() -> dict[str, dict]:
    """EN acronym -> the French acronym government translators use for it, learned from the
    training pairs: a pair with exactly one English-only and one French-only acronym is one
    vote. Kept when seen 3+ times and the top French form wins 70%+ of the votes."""
    cache = ROOT / "data" / "acronym_map.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    from collections import Counter, defaultdict
    votes: dict[str, Counter] = defaultdict(Counter)
    for line in (ROOT / "data" / "train.jsonl").open(encoding="utf-8"):
        p = json.loads(line)
        en, fr = set(ACR.findall(p["en"])), set(ACR.findall(p["fr"]))
        en_only, fr_only = en - fr, fr - en
        if len(en_only) == 1 and len(fr_only) == 1:
            votes[next(iter(en_only))][next(iter(fr_only))] += 1
    out = {}
    for a, c in votes.items():
        top, n = c.most_common(1)[0]
        total = sum(c.values())
        if n >= 3 and n / total >= 0.7:
            out[a] = {"fr": top, "pairs": n, "of": total}
    cache.write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding="utf-8")
    return out


@lru_cache(maxsize=1)
def checker() -> Checker:
    return Checker()


def review(en: str, fr: str) -> list[dict]:
    flags = []
    left = (set(ACR.findall(en)) & set(ACR.findall(fr))) - bilingual_acronyms()
    for a in sorted(left):
        flags.append({"kind": "acronym", "term": a,
                      "note": f"“{a}” is the English acronym. Government French usually has its own; check before sending.",
                      "source": "acronym rule learned from Open Government Portal pairs"})
    out_acr = set(ACR.findall(fr))
    known_fr = {v["fr"] for v in acronym_map().values()} | bilingual_acronyms()
    # what the model wrote instead: a capitalised token that is neither a known government
    # French acronym nor one that stays the same in both languages (RRCQ, NIS, RC)
    stray = sorted(out_acr - known_fr - set(ACR.findall(en)))
    for a in sorted(set(ACR.findall(en)) - left):
        m = acronym_map().get(a)
        if m and m["fr"] not in out_acr:
            flags.append({"kind": "acronym", "term": a, "expected": m["fr"], "wrote": stray,
                          "note": f"Expected “{m['fr']}” for “{a}”; government translators used it in "
                                  f"{m['pairs']} of {m['of']} pairs, and it is not in this translation.",
                          "source": "acronym pairs learned from Open Government Portal translations"})
    for h in checker().check(en, fr):
        flags.append({"kind": "termium", "term": h["used"], "preferred": h["preferred"],
                      "note": f"Termium labels “{h['used']}” as {h['label'].split(',')[0]} for “{h['en']}”.",
                      "source": "Termium Plus, Translation Bureau (Open Government Licence)"})
    return flags
