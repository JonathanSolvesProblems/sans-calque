"""Record what each model actually writes for the demo sentences, with the review flags.

Every example quoted on the page, in the README or in the post ("writes NIS for SIN",
"de l'ARC") must be a line in results/demo_outputs.json; scripts/check_claims.py fails if a
quoted example is not found here. The sentences are written for this project, not copied
from canada.ca, so the file can be committed.
"""
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "app"))
from review import review  # noqa: E402
from translate import backend  # noqa: E402

SENTENCES = [
    "Before you register your business, you need a business number (BN) from the CRA.",
    "Most small businesses use the calendar year as their fiscal year.",
    "Keep your accounting records for six years after the end of the fiscal year they relate to.",
    "Keep a copy of your accounts payable and accounts receivable for each fiscal year.",
    "You can apply for your SIN at a Service Canada office.",
]


def spec(run: str | None) -> str:
    r = json.loads((ROOT / "results" / f"train_{run or 'run1'}.json").read_text(encoding="utf-8"))
    return f"tinker:{r['base']}" if run is None else f"tinker:{r['base']}@{r['sampler_path']}"


async def main() -> None:
    systems = {"base": spec(None), "run1": spec("run1"), "run2": spec("run2")}
    if len(sys.argv) > 1:  # optional local model, e.g. ollama:cafr-run2
        systems["local"] = sys.argv[1]
    out = {"sentences": SENTENCES, "systems": {}}
    for name, s in systems.items():
        b = backend(s)
        texts = await asyncio.gather(*(b.translate(x) for x in SENTENCES))
        out["systems"][name] = {"backend": s, "outputs": [
            {"en": e, "fr": f, "flags": [{k: v for k, v in fl.items() if k in ("kind", "term", "expected")}
                                        for fl in review(e, f)]} for e, f in zip(SENTENCES, texts)]}
        print(name, *texts, sep="\n  ")
    (ROOT / "results" / "demo_outputs.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())
