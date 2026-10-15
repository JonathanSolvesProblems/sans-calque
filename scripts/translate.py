"""One translation call, three backends, the same prompt for all of them.

tinker:<base_model>         the untouched base model on Tinker (the ablation)
tinker:<base>@<model_path>  a fine-tuned checkpoint on Tinker
ollama:<model>              a local model through Ollama (e.g. ollama:gemma3:4b)
"""
import asyncio
import os

import requests
from dotenv import load_dotenv

load_dotenv()

SYSTEM = ("Translate the user's English text into Canadian French, in the plain-language style "
          "the Government of Canada uses for public pages. Output only the French translation.")
RENDERER = {"Qwen/Qwen3.5-4B": "qwen3_5_disable_thinking", "Qwen/Qwen3.5-9B": "qwen3_5_disable_thinking",
            "Qwen/Qwen3-8B": "qwen3_disable_thinking"}


class TinkerBackend:
    def __init__(self, spec: str):
        import tinker
        from tinker_cookbook import renderers
        from tinker_cookbook.tokenizer_utils import get_tokenizer

        base, _, path = spec.partition("@")
        self.tinker = tinker
        svc = tinker.ServiceClient()
        self.client = svc.create_sampling_client(model_path=path) if path else svc.create_sampling_client(base_model=base)
        self.renderer = renderers.get_renderer(RENDERER[base], get_tokenizer(base))
        self.params = tinker.SamplingParams(max_tokens=512, temperature=0.0,
                                            stop=self.renderer.get_stop_sequences())

    async def translate(self, text: str) -> str:
        msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": text}]
        resp = await self.client.sample_async(prompt=self.renderer.build_generation_prompt(msgs),
                                              num_samples=1, sampling_params=self.params)
        msg, _ = self.renderer.parse_response(resp.sequences[0].tokens)
        content = msg["content"]
        if isinstance(content, list):  # some renderers return content parts
            content = "".join(p.get("text", "") for p in content if isinstance(p, dict))
        return content.strip()


class OllamaBackend:
    def __init__(self, model: str):
        self.model = model
        self.url = os.environ.get("OLLAMA_URL", "http://localhost:11434") + "/api/chat"

    async def translate(self, text: str) -> str:
        # think=False matches the Tinker runs (qwen3_5_disable_thinking); models without a
        # thinking mode (gemma3) ignore it
        body = {"model": self.model, "stream": False, "think": False, "options": {"temperature": 0},
                "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": text}]}
        r = await asyncio.to_thread(requests.post, self.url, json=body, timeout=300)
        r.raise_for_status()
        return r.json()["message"]["content"].strip()


def backend(spec: str):
    kind, _, rest = spec.partition(":")
    if kind == "tinker":
        return TinkerBackend(rest)
    if kind == "ollama":
        return OllamaBackend(rest)
    raise ValueError(f"unknown backend {spec!r}")
