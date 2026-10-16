"""First user, second pass: the same page through the app's own fetch, now with a keep list.

The first pass (results/first_user.json) flagged 8 things on jonathanandrei.com/how-i-work/,
7 of them tech acronyms Jonathan's own fr-CA page keeps in English. This reruns the page
with those acronyms on the keep list and records what is still flagged.
Writes results/first_user_keep.json. Usage: python scripts/first_user_keep.py [app_url]
"""
import json
import sys
import time
from pathlib import Path

import requests

APP = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8790"
KEEP = ["MCP", "LLM", "RAG", "FHIR", "SDK", "NG133"]
for _ in range(60):
    try:
        requests.get(APP + "/api/meta", timeout=3)
        break
    except requests.RequestException:
        time.sleep(2)

page = requests.post(APP + "/api/fetch", json={"url": "https://jonathanandrei.com/how-i-work/"}, timeout=60).json()
r = requests.post(APP + "/api/translate", json={"text": page["text"], "compare": False, "keep": KEEP}, timeout=600).json()
flags = [{"en": b["en"], "ft": b["ft"].get("text"), "flags": b["ft_flags"]} for b in r["blocks"] if b["ft_flags"]]
out = {"page": page["url"], "blocks": len(r["blocks"]), "keep": KEEP,
       "ft_flags": sum(len(f["flags"]) for f in flags),
       "flagged": flags}
Path("results/first_user_keep.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"{out['blocks']} blocks, keep={KEEP}, flags left: {out['ft_flags']}")
for f in flags:
    print(" -", [x["term"] + ("->" + x["expected"] if x.get("expected") else "") for x in f["flags"]], "|", f["en"][:90])
