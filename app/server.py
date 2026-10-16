"""Web app: paste English, get Canadian French plus a review list, side by side with the base model.

Engines come from the environment, so the same code serves both modes:
  FT_SPEC    fine-tuned model, e.g. tinker:Qwen/Qwen3.5-4B@tinker://.../cafr-final  or  ollama:cafr
  BASE_SPEC  untouched base model for the comparison column, e.g. tinker:Qwen/Qwen3.5-4B
  DAILY_WORDS  hosted-mode cap on English words translated per day (default 20000)

Run: uvicorn app.server:app --port 8000
"""
import asyncio
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "app"))
load_dotenv(ROOT / ".env")
import requests  # noqa: E402
from fetch_page import FetchError, blocks_from_url  # noqa: E402
from review import review  # noqa: E402
from translate import backend  # noqa: E402

RUN = json.loads((ROOT / "results" / "train_run.json").read_text(encoding="utf-8"))
FT_SPEC = os.environ.get("FT_SPEC", f"tinker:{RUN['base']}@{RUN['sampler_path']}")
BASE_SPEC = os.environ.get("BASE_SPEC", f"tinker:{RUN['base']}")
DAILY_WORDS = int(os.environ.get("DAILY_WORDS", "20000"))
MAX_CHARS = 6000

app = FastAPI()
app.mount("/static", StaticFiles(directory=ROOT / "app" / "static"), name="static")
_engines: dict[str, object] = {}
_usage = {"day": None, "words": 0}


def engine(spec: str):
    if spec not in _engines:
        _engines[spec] = backend(spec)
    return _engines[spec]


def blocks(text: str) -> list[str]:
    return [b.strip() for b in re.split(r"\n\s*\n|\n", text) if b.strip()]


def scorecard() -> dict:
    def load(n):
        p = ROOT / "results" / f"{n}.json"
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
    ft_name = RUN.get("eval_name", "ft_qwen35_4b")  # the run the app serves, chosen by hand
    cmp = load(f"compare_base_qwen35_4b_vs_{ft_name}") or {}
    acr = cmp.get("acronyms_all_rows", {})
    out = {}
    for key, name in [("gemma", "gemma3_4b"), ("base", "base_qwen35_4b"), ("ft", ft_name)]:
        r = load(name)
        if r:
            out[key] = {"chrf": r["chrf++"], "comet": r["comet"], "termium": r["termium_sentences_with_avoid"],
                        "termium_of": r["termium_sentences"], "n": r["n_general"]}
    if acr:
        out["base"]["english_acronyms_left"] = acr["base_qwen35_4b"]["english_acronyms_left_in"]
        out["ft"]["english_acronyms_left"] = acr[ft_name]["english_acronyms_left_in"]
        out["base"]["french_acronym_rate"] = acr["base_qwen35_4b"]["rate"]
        out["ft"]["french_acronym_rate"] = acr[ft_name]["rate"]
    g = load(f"compare_gemma3_4b_vs_{ft_name}") or load("compare_gemma3_4b_vs_ft_qwen35_4b")
    if g and "gemma" in out:
        out["gemma"]["english_acronyms_left"] = g["acronyms_all_rows"]["gemma3_4b"]["english_acronyms_left_in"]
        out["gemma"]["french_acronym_rate"] = g["acronyms_all_rows"]["gemma3_4b"]["rate"]
    out["bootstrap_ft_beats_base_chrf"] = cmp.get("chrf_b_beats_a_share")
    out["training"] = {k: RUN[k] for k in ("base", "examples", "epochs", "est_cost_usd", "seconds")}
    return out


class Req(BaseModel):
    text: str
    compare: bool = True
    keep: list[str] = []  # acronyms the client wants left in English


class FetchReq(BaseModel):
    url: str


@app.get("/")
def index():
    return FileResponse(ROOT / "app" / "static" / "index.html")


@app.post("/api/fetch")
async def fetch(req: FetchReq):
    """Text blocks of a public page, so a whole page can be translated by address."""
    try:
        page = await asyncio.to_thread(blocks_from_url, req.url)
    except FetchError as e:
        raise HTTPException(400, str(e))
    except requests.RequestException as e:
        raise HTTPException(502, f"Could not fetch that page ({type(e).__name__}).")
    except Exception as e:  # never surface a raw 500 to the page; say what failed instead
        raise HTTPException(502, f"That page could not be read ({type(e).__name__}).")
    if not page["blocks"]:
        raise HTTPException(422, "No readable text was found on that page.")
    text, kept = "", 0
    for b in page["blocks"]:  # fill up to the demo's limit, whole blocks only
        if len(text) + len(b) + 1 > MAX_CHARS:
            break
        text += b + "\n"
        kept += 1
    return {"url": page["url"], "title": page["title"], "text": text.strip(),
            "blocks_total": len(page["blocks"]), "blocks_kept": kept}


@app.get("/api/meta")
def meta():
    return {"ft": FT_SPEC.split("@")[0], "local": FT_SPEC.startswith("ollama"), "scorecard": scorecard(),
            "daily_words": DAILY_WORDS}


@app.post("/api/translate")
async def translate(req: Req):
    text = req.text.strip()
    if not text:
        raise HTTPException(400, "Paste some English text first.")
    if len(text) > MAX_CHARS:
        raise HTTPException(413, f"That is {len(text):,} characters; the demo takes up to {MAX_CHARS:,} at a time.")
    today = dt.date.today().isoformat()
    if _usage["day"] != today:
        _usage.update(day=today, words=0)
    words = len(text.split())
    if not FT_SPEC.startswith("ollama") and _usage["words"] + words > DAILY_WORDS:
        raise HTTPException(429, "The hosted demo has used today's translation allowance. "
                                 "Run it locally (instructions in the repo) or try again tomorrow.")
    _usage["words"] += words

    parts = blocks(text)
    ft = engine(FT_SPEC)
    base = engine(BASE_SPEC) if req.compare else None
    sem = asyncio.Semaphore(8)

    async def one(eng, b):
        async with sem:
            try:
                return {"ok": True, "text": await eng.translate(b)}
            except Exception as e:  # a failed block is shown as failed, never as an empty translation
                return {"ok": False, "error": f"{type(e).__name__}"}

    ft_out = await asyncio.gather(*(one(ft, b) for b in parts))
    base_out = await asyncio.gather(*(one(base, b) for b in parts)) if base else [None] * len(parts)
    result = []
    for en, f, b in zip(parts, ft_out, base_out):
        keep = set(req.keep)
        result.append({"en": en, "ft": f, "base": b,
                       "ft_flags": review(en, f["text"], keep) if f["ok"] else [],
                       "base_flags": review(en, b["text"], keep) if b and b["ok"] else []})
    return {"blocks": result, "words": words}
