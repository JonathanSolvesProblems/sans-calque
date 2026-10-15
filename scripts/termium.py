"""Terminology check graded by the Translation Bureau's Termium Plus labels (Open Government Licence).

Termium labels are per concept: 'juridiction' is marked avoid as a rendering of 'authority'
and is correct in other senses. So a French term only counts against an output when the
English SOURCE contains that concept's English term. English terms are limited to two or
more words, because single words ('authority') are too ambiguous to match on.

build():  data/raw/termium/*/*.csv -> data/termium_index.json
check():  (en_source, fr_output) -> list of hits, each naming the concept and the label
"""
import csv
import glob
import json
import re
from pathlib import Path

INDEX = Path(__file__).resolve().parent.parent / "data" / "termium_index.json"
BAD_LABELS = ("avoid", "anglicism")


def _split(terms: str, params: str) -> list[tuple[str, str]]:
    ts = [t.strip() for t in (terms or "").split(";")]
    ps = [p.strip() for p in (params or "").split(";")]
    ps += [""] * (len(ts) - len(ps))
    return [(t, p) for t, p in zip(ts, ps) if t]


def build() -> dict:
    concepts = []
    for path in glob.glob(str(INDEX.parent / "raw" / "termium" / "*" / "*.csv")):
        for r in csv.DictReader(open(path, encoding="utf-8-sig", newline="")):  # some files carry a BOM
            fr = _split(r["TERME_FR"], r["TERME_FR_PARAMETRE"]) + _split(r["SYNONYMES_FR"], r["SYNONYMES_FR_PARAMETRE"])
            # 'see observation' means avoid only in some contexts, explained in a free-text note;
            # counting it flagged the government's own translators 21 times in 25, so it is excluded
            bad = [(t, p) for t, p in fr if any(b in p for b in BAD_LABELS) and "see observation" not in p]
            if not bad:
                continue
            good = [t for t, p in fr if "correct" in p or "standardized" in p or "officially approved" in p]
            en = [t for t, _ in _split(r["TERM_EN"], r["TERM_EN_PARAMETER"]) + _split(r["SYNONYMS_EN"], r["SYNONYMS_EN_PARAMETERS"])]
            en = [t for t in en if len(t.split()) >= 2]
            # a French term labelled correct for the same concept is never counted as bad
            bad = [(t, p) for t, p in bad if t not in good]
            if en and bad:
                concepts.append({"en": en, "avoid": [t for t, _ in bad],
                                 "labels": [p for _, p in bad], "preferred": good, "subject": r["SUBJECT_EN"]})
    INDEX.write_text(json.dumps(concepts, ensure_ascii=False), encoding="utf-8")
    return {"concepts": len(concepts)}


def _rx(term: str) -> re.Pattern:
    return re.compile(r"(?<!\w)" + re.escape(term.lower()) + r"(?!\w)")


class Checker:
    def __init__(self) -> None:
        self.concepts = json.loads(INDEX.read_text(encoding="utf-8"))
        for c in self.concepts:
            c["_en"] = [_rx(t) for t in c["en"]]
            c["_avoid"] = [(t, _rx(t)) for t in c["avoid"]]

    def check(self, en_source: str, fr_output: str) -> list[dict]:
        src, out = en_source.lower(), fr_output.lower()
        hits, used = [], set()
        for c in self.concepts:
            if any(rx.search(src) for rx in c["_en"]):
                for term, rx in c["_avoid"]:
                    # one avoided term counts once per sentence, even when several Termium
                    # concepts list it ('fiscal year' sits in three)
                    if term.lower() not in used and rx.search(out):
                        used.add(term.lower())
                        hits.append({"en": c["en"][0], "used": term, "preferred": c["preferred"][:2],
                                     "label": c["labels"][c["avoid"].index(term)]})
        return hits

    def triggered(self, en_source: str) -> bool:
        """True when the source contains at least one concept with a term to avoid."""
        src = en_source.lower()
        return any(rx.search(src) for c in self.concepts for rx in c["_en"])


if __name__ == "__main__":
    print(build())
