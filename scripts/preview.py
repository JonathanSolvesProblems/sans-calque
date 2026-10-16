"""Gallery previews: up to 8 images at 3:2 in the demo video's order, one caption each, 140 max.

Live shots render the deployed page at a native 1500x1000 viewport (dark), driving the real
flow where a shot needs it. Evidence shots are frames from the raw b-roll takes (no burned-in
captions), letterboxed to 3:2 in their own background colour.
Output: preview/N-name.png plus preview/captions.md (caption only in each block; the count is
printed here, never written next to a caption).

    py scripts/preview.py
"""
import subprocess
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "preview"
URL = "https://sans-calque.51-161-82-166.sslip.io/"
W, H = 1500, 1000

CAPTIONS = {
    "1-hero": "An open 4B model wrote RRCQ for CRA. Fine-tuned on Tinker, it writes ARC and gets 66.9% of government acronyms right.",
    "2-record": "The proof: a Government of Canada open-data record, CRA in English and ARC in French. 31 of 31 pairs agree.",
    "3-termium": "Termium Plus, the Translation Bureau's term bank, labels année fiscale a calque to avoid. Every flag cites a source like this.",
    "4-compare": "Paste English, get the untouched model and the fine-tune side by side. Anything that shows through is circled, with its source.",
    "5-nis": "It still makes mistakes: it wrote NIS for SIN. The check says NAS, 10 of 10 government pairs, before it reaches the client.",
    "6-first-user": "My own page, fetched by address, with MCP and SDK kept in English: 1 of 41 blocks flagged, down from 8, and that one is real.",
    "7-offline": "The same fine-tune on my laptop through Ollama. The untouched model writes RReC; the fine-tune writes de l'ARC.",
    "8-graded": "Graded by Government of Canada translators on held-out pages: 66.9% of acronyms right, against 50.8% untouched.",
}
for k, c in CAPTIONS.items():
    assert len(c) <= 140, f"{k}: {len(c)} characters, limit is 140"
assert len(CAPTIONS) <= 8

OUT.mkdir(exist_ok=True)


def letterbox(src: Path, dst: Path):
    im = Image.open(src).convert("RGB")
    bg = im.getpixel((2, 2))
    th = im.width * 2 // 3
    if im.height >= th:
        top = (im.height - th) // 2
        canvas = im.crop((0, top, im.width, top + th))
    else:
        canvas = Image.new("RGB", (im.width, th), bg)
        canvas.paste(im, (0, (th - im.height) // 2))
    canvas.save(dst)


def frame(clip: str, at: float, dst: Path):
    tmp = OUT / "_frame.png"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(at), "-i", str(ROOT / "broll" / f"{clip}.mp4"),
                    "-frames:v", "1", str(tmp)], check=True)
    letterbox(tmp, dst)
    tmp.unlink()


def to_top(pg, sel, offset=24):
    pg.evaluate(f"window.scrollTo(0, document.querySelector('{sel}').getBoundingClientRect().top + window.scrollY - {offset})")
    pg.wait_for_timeout(700)


with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge")
    ctx = b.new_context(viewport={"width": W, "height": H}, device_scale_factor=1, color_scheme="dark")
    pg = ctx.new_page()
    pg.goto(URL, wait_until="domcontentloaded", timeout=60000)
    pg.evaluate("document.fonts.ready")
    pg.wait_for_selector("#figure .big", timeout=60000)
    pg.wait_for_timeout(800)
    pg.screenshot(path=str(OUT / "1-hero.png"))

    pg.click("#sample")
    pg.click("#go")
    pg.wait_for_selector(".deliver", timeout=240000)
    pg.wait_for_timeout(1200)
    to_top(pg, ".diff")
    pg.screenshot(path=str(OUT / "4-compare.png"))
    rows = pg.locator(".row")
    y = rows.nth(4).evaluate("e => e.getBoundingClientRect().top + window.scrollY")
    pg.evaluate(f"window.scrollTo(0, {y} - 14)")
    pg.wait_for_timeout(700)
    pg.screenshot(path=str(OUT / "5-nis.png"))
    to_top(pg, ".receipt", 40)
    pg.screenshot(path=str(OUT / "8-graded.png"))

    pg.goto(URL, wait_until="domcontentloaded", timeout=60000)
    pg.wait_for_selector("#figure .big", timeout=60000)
    to_top(pg, ".bench", 40)
    pg.fill("#url", "https://jonathanandrei.com/how-i-work/")
    pg.click("#fetch")
    pg.wait_for_function("document.querySelector('#msg').textContent.includes('blocks')", timeout=60000)
    pg.fill("#keep", "MCP, LLM, RAG, FHIR, SDK, NG133")
    pg.uncheck("#cmp")
    pg.click("#go")
    pg.wait_for_function("document.querySelector('.deliver') && /of 41 blocks/.test(document.querySelector('.deliver').textContent)", timeout=600000)
    pg.wait_for_timeout(1200)
    print("  first user:", pg.locator(".deliver").inner_text().splitlines()[1])
    to_top(pg, ".deliver", 40)
    pg.screenshot(path=str(OUT / "6-first-user.png"))
    b.close()

frame("e02-ogp", 9.0, OUT / "2-record.png")
frame("e03-termium", 7.0, OUT / "3-termium.png")
letterbox(ROOT / "docs" / "offline.png", OUT / "7-offline.png")

order = list(CAPTIONS)
lines = ["# Image gallery, upload in this order", "", "One caption per image. Copy the block contents only.", ""]
for name in order:
    lines += [f"## {name}.png", "", "```", CAPTIONS[name], "```", ""]
(OUT / "captions.md").write_text("\n".join(lines), encoding="utf-8")

for name in order:
    f = OUT / f"{name}.png"
    im = Image.open(f)
    ok = "ok " if abs(im.width / im.height - 1.5) < 0.01 and f.stat().st_size < 5_000_000 else "BAD"
    print(f"  {ok} {f.name:<20} {im.width}x{im.height}  {f.stat().st_size // 1024:>4} KB   caption {len(CAPTIONS[name]):>3}/140")
