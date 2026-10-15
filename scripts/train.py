"""LoRA fine-tune on Tinker: English -> Canadian French, Open Government Licence pairs only.

The run refuses to start if its estimated training cost exceeds --budget, because the
credit is a one-time $10 grant. The estimate uses Tinker's published per-token training
price and the real token count of the rendered examples.

Usage: python scripts/train.py --n 8000 --epochs 2 --budget 3.00
Writes results/train_run.json with the checkpoint path, token counts and loss curve.
"""
import argparse
import asyncio
import json
import random
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))
from translate import RENDERER, SYSTEM  # noqa: E402

load_dotenv()
PRICE_PER_M_TRAIN = {"Qwen/Qwen3.5-4B": 0.737, "Qwen/Qwen3-8B": 0.44, "Qwen/Qwen3.5-9B": 1.463}


def load_pairs(n: int, acronym_share: float = 0.0) -> list[dict]:
    eval_en = set()
    ev = Path("data/eval_private/pairs.jsonl")
    if ev.exists():  # never train on a sentence that also appears in the held-out set
        eval_en = {json.loads(l)["en"] for l in ev.open(encoding="utf-8")}
    rows = [json.loads(l) for l in Path("data/train.jsonl").open(encoding="utf-8")]
    rows = [r for r in rows if r["en"] not in eval_en]
    rng = random.Random(0)
    picked = []
    if acronym_share > 0:
        # pairs where an English acronym appears and the French uses the government's own form
        # (the map is learned from these same OGL pairs, never from the eval set)
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))
        from review import ACR, acronym_map
        amap = acronym_map()
        acr_rows = [r for r in rows if any(a in amap and amap[a]["fr"] in r["fr"] for a in ACR.findall(r["en"]))]
        picked = rng.sample(acr_rows, min(int(n * acronym_share), len(acr_rows)))
        print(f"{len(acr_rows)} acronym-bearing pairs available, {len(picked)} used")
        taken = {r["en"] for r in picked}
        rows = [r for r in rows if r["en"] not in taken]
    rest = n - len(picked)
    sentences = [r for r in rows if len(r["en"].split()) >= 6]
    titles = [r for r in rows if len(r["en"].split()) < 6]
    n_sent = int(rest * 0.75)  # mostly running text, some titles so short labels are covered too
    return picked + rng.sample(sentences, min(n_sent, len(sentences))) + rng.sample(titles, min(rest - n_sent, len(titles)))


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="Qwen/Qwen3.5-4B")
    ap.add_argument("--n", type=int, default=8000)
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--rank", type=int, default=32)
    ap.add_argument("--budget", type=float, default=3.0)
    ap.add_argument("--acronym-share", type=float, default=0.0)
    ap.add_argument("--name", default="run1")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    import tinker
    from tinker_cookbook import renderers
    from tinker_cookbook.renderers import TrainOnWhat
    from tinker_cookbook.supervised.data import conversation_to_datum
    from tinker_cookbook.tokenizer_utils import get_tokenizer

    renderer = renderers.get_renderer(RENDERER[a.base], get_tokenizer(a.base))
    pairs = load_pairs(a.n, a.acronym_share)
    data = [conversation_to_datum([{"role": "system", "content": SYSTEM}, {"role": "user", "content": p["en"]},
                                   {"role": "assistant", "content": p["fr"]}],
                                  renderer, max_length=768, train_on_what=TrainOnWhat.LAST_ASSISTANT_MESSAGE)
            for p in pairs]
    tokens = sum(d.model_input.length for d in data)
    est = tokens * a.epochs / 1e6 * PRICE_PER_M_TRAIN[a.base]
    print(f"{len(data)} examples, {tokens:,} tokens/epoch, {a.epochs} epochs -> est. ${est:.2f} (budget ${a.budget:.2f})")
    if est > a.budget:
        sys.exit(f"refusing to train: estimated ${est:.2f} exceeds budget ${a.budget:.2f}")
    if a.dry_run:
        return

    svc = tinker.ServiceClient()
    tc = await svc.create_lora_training_client_async(base_model=a.base, rank=a.rank)
    losses, step, t0 = [], 0, time.time()
    for epoch in range(a.epochs):
        random.Random(epoch).shuffle(data)
        for i in range(0, len(data), a.batch):
            batch = data[i:i + a.batch]
            fb = await tc.forward_backward_async(batch, "cross_entropy")
            op = await tc.optim_step_async(tinker.AdamParams(learning_rate=a.lr))
            res = await fb.result_async()
            await op.result_async()
            loss = res.metrics.get("loss:sum", None) if hasattr(res, "metrics") else None
            losses.append({"step": step, "epoch": epoch, "loss": loss})
            if step % 10 == 0:
                print(f"epoch {epoch} step {step} loss {loss} ({time.time() - t0:.0f}s)")
            step += 1
    saved = await tc.save_weights_for_sampler_async(name=f"cafr-{a.name}")
    path = (await saved.result_async()).path
    # the archive download of sampler weights is deprecated and timed out for run 1, and the
    # newer export only works while the training session is alive, so do it now
    try:
        ext = await tc.save_weights_external_async(name=f"cafr-{a.name}-hf")
        ext_path = (await ext.result_async()).path if hasattr(ext, "result_async") else ext.path
    except Exception as e:
        ext_path = None
        print(f"external weights export failed: {type(e).__name__}: {e}")
    run = {"name": a.name, "base": a.base, "examples": len(data), "acronym_share": a.acronym_share,
           "tokens_per_epoch": tokens, "epochs": a.epochs,
           "est_cost_usd": round(est, 2), "lr": a.lr, "rank": a.rank, "batch": a.batch,
           "sampler_path": path, "external_path": ext_path, "seconds": round(time.time() - t0), "losses": losses}
    Path("results").mkdir(exist_ok=True)
    # every run is kept; results/train_run.json is only the one the app serves, chosen by hand
    Path(f"results/train_{a.name}.json").write_text(json.dumps(run, indent=1), encoding="utf-8")
    print(f"saved sampler weights: {path}")


if __name__ == "__main__":
    asyncio.run(main())
