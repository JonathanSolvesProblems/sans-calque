"""Download a fine-tuned LoRA from Tinker and build local copies the user owns.

models/<run>/adapter/  raw Tinker checkpoint
models/<run>/peft/     PEFT adapter (small, loads on top of the public base model)
models/<run>/merged/   full merged Hugging Face model (for local inference)
models/base/           the public base model, downloaded as plain files: the Hugging Face
                       cache uses symlinks, which Windows refuses without Developer Mode

Usage: python scripts/export_model.py run1
"""
import json
import sys
from pathlib import Path

from dotenv import load_dotenv
from huggingface_hub import snapshot_download
from tinker_cookbook import weights

load_dotenv()
name = sys.argv[1] if len(sys.argv) > 1 else "run1"
run = json.loads(Path(f"results/train_{name}.json").read_text(encoding="utf-8"))
out = Path("models") / name
adapter = out / "adapter"

if not (adapter / "checkpoint_complete").exists():
    # the archive is built on request and the first request can time out while it builds;
    # a second attempt usually finds it ready
    weights.download(tinker_path=run["sampler_path"], output_dir=str(adapter))
print("adapter at", adapter)

base_dir = Path("models/base")
if not (base_dir / "config.json").exists():
    snapshot_download(repo_id=run["base"], local_dir=str(base_dir))
print("base model at", base_dir)

weights.build_lora_adapter(base_model=str(base_dir), adapter_path=str(adapter), output_path=str(out / "peft"))
print("PEFT adapter written to", out / "peft")
weights.build_hf_model(base_model=str(base_dir), adapter_path=str(adapter), output_path=str(out / "merged"))
print("merged model written to", out / "merged")
