"""Build the held-out eval set from canada.ca small-business pages and their French twins.

canada.ca content is licensed for non-commercial reproduction only, so this text is used
for grading and never committed: it lands in data/eval_private/ (gitignored). The repo
ships this script and the URL list, so anyone can rebuild the same set.

Pairing: each English page links its French version through the language toggle
(hreflang="fr"). Paragraphs and list items inside <main> are paired by position, and a
page is kept only when both sides have the same number of blocks, so no pair is guessed.

Usage: python scripts/pull_eval.py [max_pages]
"""
import json
import re
import sys
import time
from collections import deque
from pathlib import Path
from urllib.parse import urljoin, urldefrag

import requests
from bs4 import BeautifulSoup

SEEDS = [
    "https://www.canada.ca/en/services/business.html",
    "https://www.canada.ca/en/services/business/start.html",
    "https://www.canada.ca/en/services/business/taxes.html",
    "https://www.canada.ca/en/revenue-agency/services/tax/businesses.html",
    "https://www.canada.ca/en/revenue-agency/services/tax/businesses/topics/sole-proprietorships-partnerships.html",
    "https://www.canada.ca/en/revenue-agency/services/tax/businesses/topics/gst-hst-businesses.html",
]
ALLOWED = ("/en/services/business", "/en/revenue-agency/services/tax/businesses")
OUT_DIR = Path("data/eval_private")
HEADERS = {"User-Agent": "eval-builder (non-commercial research; contact via github)"}


def get(url: str) -> BeautifulSoup | None:
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
    except requests.RequestException:
        return None
    if r.status_code != 200 or "text/html" not in r.headers.get("content-type", ""):
        return None
    time.sleep(0.5)  # be polite to canada.ca
    return BeautifulSoup(r.text, "lxml")


def blocks(soup: BeautifulSoup) -> list[str]:
    main = soup.find("main")
    if not main:
        return []
    # drop page chrome that sits inside <main> on canada.ca (report-a-problem, date modified)
    for el in main.select(".pagedetails, .gc-pg-hlpfl, .datemod, nav, aside"):
        el.decompose()
    out = []
    for el in main.find_all(["p", "li", "h2", "h3"]):
        if el.find(["p", "li"]):  # keep leaf blocks only, so nested lists are not doubled
            continue
        text = re.sub(r"\s+", " ", el.get_text(" ", strip=True)).strip()
        if text:
            # no length filter here: French runs longer, so filtering each side separately
            # drops a short English item while keeping its twin and breaks positional pairing
            out.append(text)
    return out


def french_url(soup: BeautifulSoup, url: str) -> str | None:
    link = soup.find("link", attrs={"rel": "alternate", "hreflang": "fr"})
    if link and link.get("href"):
        return urljoin(url, link["href"])
    toggle = soup.select_one("#wb-lng a[lang='fr'], a[hreflang='fr']")
    return urljoin(url, toggle["href"]) if toggle and toggle.get("href") else None


def main() -> None:
    max_pages = int(sys.argv[1]) if len(sys.argv) > 1 else 150
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    seen, queue = set(), deque(SEEDS)
    pairs, kept, skipped = [], [], 0
    while queue and len(kept) + skipped < max_pages:
        # /content/canadasite/ is an alias of the public path and would duplicate pages
        url = urldefrag(queue.popleft())[0].replace("/content/canadasite/", "/")
        if url in seen:
            continue
        seen.add(url)
        en = get(url)
        if en is None:
            continue
        for a in en.find_all("a", href=True):
            nxt = urldefrag(urljoin(url, a["href"]))[0]
            if nxt.startswith("https://www.canada.ca") and any(p in nxt for p in ALLOWED) and nxt.endswith(".html"):
                queue.append(nxt)
        fr_url = french_url(en, url)
        fr = get(fr_url) if fr_url else None
        if fr is None:
            skipped += 1
            print(f"skip (no French twin): {url}")
            continue
        b_en, b_fr = blocks(en), blocks(fr)
        if not b_en or len(b_en) != len(b_fr):
            skipped += 1
            print(f"skip (blocks {len(b_en)} en vs {len(b_fr)} fr): {url}")
            continue
        # filter after pairing, on the English side, so both sides drop together
        page_pairs = [{"en": e, "fr": f, "en_url": url, "fr_url": fr_url}
                      for e, f in zip(b_en, b_fr) if len(e) >= 20]
        kept.append({"en_url": url, "fr_url": fr_url, "blocks": len(page_pairs)})
        pairs += page_pairs
        print(f"kept {len(kept)} pages / {len(pairs)} pairs  ({url})")
    with (OUT_DIR / "pairs.jsonl").open("w", encoding="utf-8") as f:
        for p in pairs:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    # the URL list is safe to commit: it carries no canada.ca text
    Path("data/eval_urls.json").write_text(json.dumps(kept, indent=1), encoding="utf-8")
    print(f"done: {len(kept)} pages kept, {skipped} skipped (block counts differ or no French twin), {len(pairs)} pairs")


if __name__ == "__main__":
    main()
