# Demo video (about 90 seconds)

## Narration (read this)

Here's a sentence almost every small business site in Canada has somewhere: you need a business number from the CRA.

I gave it to an open 4B model, and it wrote RRCQ. There's no such thing. In French it's ARC, and the government's own translators wrote ARC every single time. 31 out of 31.

So I fine-tuned the model on Tinker. 8,000 sentences from Canada's open data, all translated by government translators. It cost a dollar thirty-five. Now it writes ARC.

Here's how I'd actually use it. I paste the English, and I get the original model and my fine-tune side by side.

Fiscal year. The original writes année fiscale, which the Translation Bureau says to avoid. Mine writes année financière.

Accounts payable. Both models get this one wrong, and it's flagged on both. It doesn't hide mine.

And mine still makes mistakes. It wrote NIS for SIN. It's NAS, and it tells me that, and where that came from.

I can also just give it a page's address. This is my own site. The first time, it flagged words like MCP and SDK, which I keep in English. So I added a list for that. Eight flags went down to one, and the one left was a real mistake.

And it's mine. Wi-Fi off, same page, on my laptop. Nothing leaves the machine.

Two blocks to check. I check those, and I send it.

## What's on screen for each line

| Line starts with | On screen |
|---|---|
| "Here's a sentence…" | The live site's hero, dark mode, 1280x720. Hold on the English line. |
| "I gave it to…" | Slow move down to the untouched sheet, "auprès du RRCQ" circled, and its margin note. |
| "So I fine-tuned…" | The fine-tuned sheet, "de l'ARC", then the 66.9% beside it. |
| "Here's how I'd actually use it." | Scroll to the table. Click "Use the sample", then Translate. Cut the wait. |
| "Fiscal year." | Row 2: "année fiscale" circled on the untouched strip, "année financière" clean below it. |
| "Accounts payable." | Row 4: "comptes à payer" and "comptes à recevoir" circled on both strips, notes in the margin. |
| "And mine still makes mistakes." | Row 5: "NIS" circled, margin note "should be NAS for SIN, 10 of 10 government pairs". |
| "I can also just give it…" | Type `https://jonathanandrei.com/how-i-work/`, click "Fetch the page", show "41 blocks". Type `MCP, LLM, RAG, FHIR, SDK, NG133` in "Keep in English". You don't need to translate all 41 blocks on camera; the 8-to-1 result is in the post. |
| "And it's mine." | Switch to the laptop page at http://127.0.0.1:8791 (header: "On this computer, through Ollama"). Turn Wi-Fi off on camera. Paste the first two sample lines, Translate, cut the wait. "de l'ARC" and "année financière" appear. |
| "Two blocks to check." | Back on the live site: "French, ready to send", "2 of 5 blocks have something showing through", click "Copy the French". **Last frame.** |

## Before recording

Start local mode while Wi-Fi is still on, and open it once so the models load:

```
$env:FT_SPEC='ollama:cafr-run2'; $env:BASE_SPEC='ollama:qwen3.5:4b'; .venv\Scripts\python.exe -m uvicorn app.server:app --port 8791
```

Every font and image is self-hosted, so the page works with Wi-Fi off. A translation takes about 20 seconds online and offline; cut the waits.

Every fact in the narration is checked: 31 of 31 and 10 of 10 (data/acronym_map.json), 8,000 and $1.35 (results/train_run2.json), the row outputs (results/demo_outputs.json), 41 blocks and 8 to 1 (results/first_user.json, results/first_user_keep.json), 2 of 5 blocks (the live run).
