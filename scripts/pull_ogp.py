"""Pull bilingual dataset titles and descriptions from the Open Government Portal.

Licence: Open Government Licence - Canada (ca-ogl-lgo). Every record is kept with its
dataset id and licence so the training corpus can be traced back and published.

Usage: python scripts/pull_ogp.py [max_records]
Writes data/raw/ogp.jsonl (one dataset per line, raw translated fields kept as-is).
"""
import json
import sys
import time
import urllib.request
from pathlib import Path

API = "https://open.canada.ca/data/api/action/package_search"
ROWS = 1000
OUT = Path("data/raw/ogp.jsonl")


def fetch(start: int) -> dict:
    # fl= would trim the payload but silently drops the *_translated fields, so pull full records
    url = f"{API}?rows={ROWS}&start={start}"
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                return json.load(r)["result"]
        except Exception as e:  # network hiccups on a 40k-record crawl are expected
            print(f"start={start} attempt {attempt + 1} failed: {e}", file=sys.stderr)
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"giving up at start={start}")


def main() -> None:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    OUT.parent.mkdir(parents=True, exist_ok=True)
    first = fetch(0)
    total = first["count"] if limit is None else min(limit, first["count"])
    print(f"{first['count']} datasets in catalogue, pulling {total}")
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        start, page = 0, first
        while written < total:
            for rec in page["results"]:
                f.write(json.dumps({
                    "id": rec.get("id"),
                    "license_id": rec.get("license_id"),
                    "title_translated": rec.get("title_translated"),
                    "notes_translated": rec.get("notes_translated"),
                }, ensure_ascii=False) + "\n")
                written += 1
                if written >= total:
                    break
            start += ROWS
            if written < total:
                page = fetch(start)
                if not page["results"]:
                    break
            print(f"{written}/{total}")
    print(f"wrote {written} records to {OUT}")


if __name__ == "__main__":
    main()
