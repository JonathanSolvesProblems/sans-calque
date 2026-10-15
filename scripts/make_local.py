"""Turn an exported run (models/<run>/merged) into a local Ollama model, cafr-<run>.

Steps, each one learned the hard way on this laptop (RTX 5060, 8 GB):
  1. llama.cpp convert_hf_to_gguf.py -> f16 GGUF
  2. llama-quantize -> Q4_K_M (2.6 GB). Q8_0 straight from the converter ran at 0.8 tok/s
     against 20.8 tok/s for Q4_K_M on the same GPU, so Q8_0 is not used.
  3. ollama create with Qwen3.5's renderer/parser and presence_penalty 0 (the stock 1.5 pushes
     a translation away from repeating terms it should repeat).
Ollama 0.40 refuses LoRA adapters and needs MLX (Mac only) to quantise safetensors, which is
why the GGUF route is used.

Needs: tmp/llama.cpp (git clone --depth 1 https://github.com/ggml-org/llama.cpp) and
tmp/llama-bin (the matching win-cpu-x64 release zip). Usage: python scripts/make_local.py run2
"""
import subprocess
import sys
from pathlib import Path

run = sys.argv[1]
d = Path("models") / run
f16, q4 = d / f"cafr-{run}-f16.gguf", d / f"cafr-{run}-q4_k_m.gguf"
quantize = next(Path("tmp/llama-bin").rglob("llama-quantize.exe"))

if not q4.exists():
    subprocess.run([sys.executable, "tmp/llama.cpp/convert_hf_to_gguf.py", str(d / "merged"),
                    "--outtype", "f16", "--outfile", str(f16)], check=True)
    subprocess.run([str(quantize), str(f16), str(q4), "Q4_K_M"], check=True)
    f16.unlink()

modelfile = d / "Modelfile"
modelfile.write_text(f"FROM ./{q4.name}\nRENDERER qwen3.5\nPARSER qwen3.5\n"
                     "PARAMETER presence_penalty 0\nPARAMETER temperature 0\n", encoding="utf-8")
subprocess.run(["ollama", "create", f"cafr-{run}", "-f", "Modelfile"], cwd=d, check=True)
print(f"ollama model cafr-{run} ready ({q4.stat().st_size / 1e9:.2f} GB)")
