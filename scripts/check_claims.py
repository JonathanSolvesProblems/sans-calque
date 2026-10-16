"""Fail if the prose and the data disagree.

Each claim is the exact text a document must contain, rebuilt from the committed results
files rather than typed by hand. If a run is re-scored and a number moves, the document
that still quotes the old number fails here. Quoted model outputs ("de l'ARC", "NIS") must
appear in results/demo_outputs.json. 'TBD' anywhere in a checked document is a failure.

Usage: python scripts/check_claims.py      (exit code 1 on any failure)
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
R = ROOT / "results"
DOCS = [p for p in [ROOT / "README.md", ROOT / "app" / "static" / "index.html", ROOT / "POST.md"] if p.exists()]


def res(name: str) -> dict:
    return json.loads((R / f"{name}.json").read_text(encoding="utf-8"))


def pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def acr(a: str, b: str, side: str) -> dict:
    return res(f"compare_{a}_vs_{b}")["acronyms_all_rows"][side]


def claims() -> list[tuple[str, str, str]]:
    """(document, what it is, exact text expected in the document)."""
    g, base, r1, r2 = (res(n) for n in ("gemma3_4b", "base_qwen35_4b", "ft_qwen35_4b", "ft2_qwen35_4b"))
    a_base = acr("base_qwen35_4b", "ft2_qwen35_4b", "base_qwen35_4b")
    a_r1 = acr("base_qwen35_4b", "ft_qwen35_4b", "ft_qwen35_4b")
    a_r2 = acr("base_qwen35_4b", "ft2_qwen35_4b", "ft2_qwen35_4b")
    a_g = acr("gemma3_4b", "ft_qwen35_4b", "gemma3_4b")
    boot_r2 = res("compare_base_qwen35_4b_vs_ft2_qwen35_4b")["chrf_b_beats_a_share"]
    boot_r1 = res("compare_base_qwen35_4b_vs_ft_qwen35_4b")["chrf_b_beats_a_share"]
    t1, t2 = res("train_run1"), res("train_run2")
    stats = json.loads((ROOT / "data" / "corpus_stats.json").read_text(encoding="utf-8"))
    amap = json.loads((ROOT / "data" / "acronym_map.json").read_text(encoding="utf-8"))
    readme = "README.md"
    c = [
        (readme, "acronym row", f"| {pct(a_g['rate'])} | {pct(a_base['rate'])} | {pct(a_r1['rate'])} | **{pct(a_r2['rate'])}** |"),
        (readme, "English-left row", f"| {a_g['english_acronyms_left_in']} | {a_base['english_acronyms_left_in']} | "
                                     f"{a_r1['english_acronyms_left_in']} | {a_r2['english_acronyms_left_in']} |"),
        (readme, "Termium row", f"(of {base['termium_sentences']}) | {g['termium_sentences_with_avoid']} | "
                                f"{base['termium_sentences_with_avoid']} | {r1['termium_sentences_with_avoid']} | "
                                f"{r2['termium_sentences_with_avoid']} |"),
        (readme, "chrF row", f"| chrF++ | {g['chrf++']:.2f} | {base['chrf++']:.2f} | {r1['chrf++']:.2f} | {r2['chrf++']:.2f} |"),
        (readme, "COMET row", f"| {g['comet']:.3f} | {base['comet']:.3f} | {r1['comet']:.3f} | {r2['comet']:.3f} |"),
        (readme, "acronym denominator", f"(of {a_base['french_acronyms_in_reference']})"),
        (readme, "general n", f"{base['n_general']} random sentences"),
        (readme, "Termium n", f"all {base['termium_sentences']} that"),
        (readme, "bootstrap run 2", f"in {round(boot_r2 * 100)}% of them"),
        (readme, "bootstrap run 1", f"in {boot_r1 * 100:.1f}%"),
        (readme, "Gemma failures", f"{g['failed_calls']} of its"),
        (readme, "run 1 cost", f"${t1['est_cost_usd']:.2f}"),
        (readme, "run 2 cost", f"${t2['est_cost_usd']:.2f}"),
        (readme, "training size", f"{t2['examples']:,} English"),
        (readme, "corpus size", f"{stats['pairs']:,} OGL pairs"),
        (readme, "catalogue size", f"{stats['records']:,} catalogue records"),
        (readme, "acronym map size", f"{len(amap)} acronyms"),
        (readme, "CRA evidence", f"ARC for CRA ({amap['CRA']['pairs']} of {amap['CRA']['of']}"),
        (readme, "SIN evidence", f"NAS for SIN ({amap['SIN']['pairs']} of {amap['SIN']['of']}"),
    ]
    post = "POST.md"
    c += [
        (post, "acronym row", f"| {pct(a_g['rate'])} | {pct(a_base['rate'])} | {pct(a_r1['rate'])} | **{pct(a_r2['rate'])}** |"),
        (post, "English-left row", f"| {a_g['english_acronyms_left_in']} | {a_base['english_acronyms_left_in']} | "
                                   f"{a_r1['english_acronyms_left_in']} | {a_r2['english_acronyms_left_in']} |"),
        (post, "Termium row", f"(of {base['termium_sentences']}) | {g['termium_sentences_with_avoid']} | "
                              f"{base['termium_sentences_with_avoid']} | {r1['termium_sentences_with_avoid']} | "
                              f"{r2['termium_sentences_with_avoid']} |"),
        (post, "chrF row", f"| chrF++ | {g['chrf++']:.2f} | {base['chrf++']:.2f} | {r1['chrf++']:.2f} | {r2['chrf++']:.2f} |"),
        (post, "bootstrap run 2", f"in {round(boot_r2 * 100)}% of 1,000"),
        (post, "run costs", f"${t1['est_cost_usd']:.2f} and ${t2['est_cost_usd']:.2f}"),
        (post, "title cost", f"${t2['est_cost_usd']:.2f} fine-tune"),
        (post, "corpus size", f"{stats['pairs']:,} pairs"),
        (post, "catalogue size", f"{stats['records']:,} records"),
        (post, "acronym map size", f"{len(amap)} pairs learned"),
        (post, "CRA evidence", f"all {amap['CRA']['of']} times"),
        (post, "SIN evidence", f"NAS in {amap['SIN']['pairs']} of {amap['SIN']['of']} pairs"),
        (post, "acronym-bearing pool", "from the 10,752 that contain a known acronym"),
        (post, "Termium n", f"all {base['termium_sentences']} that touch"),
        (post, "general n", f"{base['n_general']} random sentences"),
    ]
    lq1 = R / "local_run1_q4.json"
    if lq1.exists():
        for doc in (readme, post):
            c.append((doc, "local run 1 chrF", f"chrF++ {res('local_run1_q4')['chrf++']:.2f} against {r1['chrf++']:.2f}"))
    ab = R / "acronym_bootstrap_base_qwen35_4b_vs_ft2_qwen35_4b.json"
    if ab.exists():
        a2 = res("acronym_bootstrap_base_qwen35_4b_vs_ft2_qwen35_4b")
        share = "all 1,000" if a2["b_beats_a_share"] == 1.0 else f"{a2['b_beats_a_share'] * 100:.1f}% of 1,000"
        c.append((post, "acronym bootstrap", f"in {share} bootstrap resamples of the {a2['sentences_with_french_acronyms']} held-out"))
    if (R / "first_user.json").exists():
        fu = res("first_user")
        ft_flags = [fl for b in fu["flagged"] for fl in b["ft_flags"]]
        c.append((post, "first user blocks", f"{fu['blocks']} blocks"))
        c.append((post, "first user flags", f"raised {len(ft_flags)} flags"))
        c.append((post, "first user noise", f"{len(ft_flags) - 1} were noise"))
        c.append((post, "first user real catch", "lesquels avaient déjà été déclarés exempts"))
    if (R / "first_user_keep.json").exists() and (R / "first_user.json").exists():
        fk, fu = res("first_user_keep"), res("first_user")
        before = sum(len(b["ft_flags"]) for b in fu["flagged"])
        c.append((post, "keep list result", f"{before} flags became {fk['ft_flags']}"))
        if fk["ft_flags"] == 1 and any(f.get("expected") == "IA" for x in fk["flagged"] for f in x["flags"]):
            c.append((post, "keep list leaves the real catch", "the one left is the real catch"))
        else:
            c.append((post, "keep list leaves the real catch", "THE RECORDED RUN NO LONGER SUPPORTS THIS CLAIM"))
    if (R / "local_run2_q4.json").exists():
        l2 = res("local_run2_q4")
        a_l2 = acr("ft2_qwen35_4b", "local_run2_q4", "local_run2_q4")
        boot_l2_vs_cloud = res("compare_ft2_qwen35_4b_vs_local_run2_q4")["chrf_b_beats_a_share"]
        boot_l2_vs_base = res("compare_base_qwen35_4b_vs_local_run2_q4")["chrf_b_beats_a_share"]
        for doc in (readme, post):
            c.append((doc, "local run 2 chrF", f"{l2['chrf++']:.2f} against {r2['chrf++']:.2f}"))
            c.append((doc, "local run 2 acronyms", f"{pct(a_l2['rate'])} of the time against {pct(a_r2['rate'])}"
                      if doc == readme else f"{pct(a_l2['rate'])} of the government's acronyms right against {pct(a_r2['rate'])}"))
        c.append((readme, "local vs cloud bootstrap", f"ahead in {boot_l2_vs_cloud * 100:.1f}% of resamples"))
        c.append((readme, "local vs base bootstrap", f"({boot_l2_vs_base * 100:.1f}% of resamples)"))
    return c


QUOTED_OUTPUTS = [  # (system in demo_outputs.json, text the docs quote it as writing)
    ("run2", "de l’ARC"), ("run2", "exercice financier"), ("run2", "NIS"), ("run2", "Conserver"),
    ("run1", "de la RC"), ("run1", "N° de S de C"), ("base", "RRCQ"), ("base", "numéro d'assurance sociale (NAS)"),
    ("base", "comme année fiscale"), ("run2", "comme année financière"),
    ("base", "comptes à payer"), ("run2", "comptes à payer"),
]


def main() -> int:
    fails = []
    text = {p.name: p.read_text(encoding="utf-8") for p in DOCS}
    for doc, what, expected in claims():
        if doc in text and expected not in text[doc]:
            fails.append(f"{doc}: {what}: expected to find {expected!r}")
    for name, t in text.items():
        # a drafting placeholder that reaches the published page is how SWORN's tagline shipped
        for m in re.finditer(r"\bTBD\b|\[X\b", t):
            fails.append(f"{name}: unresolved placeholder near {t[max(0, m.start() - 40):m.start() + 20]!r}")
    demo = json.loads((R / "demo_outputs.json").read_text(encoding="utf-8"))["systems"]
    for system, quote in QUOTED_OUTPUTS:
        outs = " ".join(o["fr"] for o in demo[system]["outputs"])
        if quote not in outs:
            fails.append(f"demo_outputs.json: {system} does not actually write {quote!r}")
    for f in fails:
        print("FAIL", f)
    print(f"{len(claims()) + len(QUOTED_OUTPUTS)} claims checked, {len(fails)} failed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
