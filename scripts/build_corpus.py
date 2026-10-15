"""Turn the raw catalogue pull into EN->FR training pairs.

Kept: records under the Open Government Licence - Canada whose French is human-written.
The portal marks machine-translated French with an 'fr-t-en' key (and English with
'en-t-fr'); any record carrying one is dropped, so no machine output is trained on.

Pairing is structural and never guessed: paragraphs are paired only when both sides have
the same number, then sentences inside a paragraph only when both sides have the same
number; otherwise the whole paragraph is kept as one pair if it is short enough.

Writes data/train.jsonl and data/corpus_stats.json.
"""
import html
import json
import random
import re
from pathlib import Path

RAW = Path("data/raw/ogp.jsonl")
OUT = Path("data/train.jsonl")
STATS = Path("data/corpus_stats.json")
MAX_CHARS = 600
SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-ZÀ-Ý«\"(])")


def paragraphs(text: str) -> list[str]:
    text = re.sub(r"</(p|li|h\d|div)>|<br\s*/?>", "\n", text, flags=re.I)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    text = re.sub(r"\*\*|__|^#+\s*", "", text, flags=re.M)  # markdown is common in notes
    return [re.sub(r"[ \t]+", " ", p).strip() for p in text.split("\n") if p.strip()]


def pair_field(en: str, fr: str) -> list[tuple[str, str]]:
    pe, pf = paragraphs(en), paragraphs(fr)
    if len(pe) != len(pf):
        return []
    out = []
    for a, b in zip(pe, pf):
        sa, sb = SENT_SPLIT.split(a), SENT_SPLIT.split(b)
        if len(sa) == len(sb) and len(sa) > 1:
            out += list(zip(sa, sb))
        elif len(a) <= MAX_CHARS and len(b) <= MAX_CHARS * 1.4:
            out.append((a, b))
    return out


def plausible(en: str, fr: str) -> bool:
    if len(en) < 15 or en == fr:
        return False
    ratio = len(fr) / len(en)
    return 0.8 <= ratio <= 1.8  # French typically runs 10-30% longer than English


def main() -> None:
    stats = {"records": 0, "dropped_licence": 0, "dropped_machine_translated": 0,
             "dropped_missing_language": 0, "pairs_before_dedupe": 0}
    pairs, seen = [], set()
    for line in RAW.open(encoding="utf-8"):
        rec = json.loads(line)
        stats["records"] += 1
        if rec.get("license_id") != "ca-ogl-lgo":
            stats["dropped_licence"] += 1
            continue
        fields = [rec.get("title_translated") or {}, rec.get("notes_translated") or {}]
        if any("-t-" in k for f in fields for k in f):
            stats["dropped_machine_translated"] += 1
            continue
        for f in fields:
            en, fr = f.get("en"), f.get("fr")
            if not en or not fr:
                stats["dropped_missing_language"] += 1
                continue
            for a, b in pair_field(en, fr):
                stats["pairs_before_dedupe"] += 1
                if plausible(a, b) and a not in seen:
                    seen.add(a)
                    pairs.append({"en": a, "fr": b, "source": f"open.canada.ca/data/dataset/{rec['id']}",
                                  "licence": "OGL-Canada-2.0"})
    random.Random(0).shuffle(pairs)
    OUT.write_text("".join(json.dumps(p, ensure_ascii=False) + "\n" for p in pairs), encoding="utf-8")
    stats["pairs"] = len(pairs)
    STATS.write_text(json.dumps(stats, indent=1), encoding="utf-8")
    print(json.dumps(stats, indent=1))


if __name__ == "__main__":
    main()
