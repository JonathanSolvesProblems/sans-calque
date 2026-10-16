# Demo video script (about 80 seconds)

Record the screen from the deployed URL (https://sans-calque.51-161-82-166.sslip.io) in dark mode at 1280x720.
The laptop shot is Ollama running `cafr-run2`. Read the narration as written; every fact in it is checked by check_claims.py or recorded in results/.

| Time | On screen | Narration |
|---|---|---|
| 0:00 to 0:08 | The hero. Hold on the untouched sheet, "auprès du RRCQ" circled. | Ask an open 4B model to put "a business number from the CRA" into French, and it writes RRCQ. There is no RRCQ. |
| 0:08 to 0:20 | Slow move down to the fine-tuned sheet, "de l'ARC", then the 66.9% pinned beside it. | So I fine-tuned it on Tinker, for a dollar thirty-five, on 8,000 sentences the Government of Canada's own translators wrote. Now it writes ARC, the way they do. |
| 0:20 to 0:28 | Click "Use the sample", then Translate. The rows land. | This is the side hustle: a small business needs its page in French, and someone like me does it. |
| 0:28 to 0:45 | Row 2: untouched "année fiscale" circled, fine-tuned "année financière" clean. Then row 4: "comptes à payer" circled on both. | Termium, the Translation Bureau's term bank, says année fiscale is a calque. The fine-tune doesn't write it. Comptes à payer gets flagged on both models, because the fine-tune still writes it too. |
| 0:45 to 0:55 | Row 5: "NIS" circled, margin note "should be NAS for SIN, 10 of 10 government pairs". | It still gets things wrong. It wrote NIS for SIN. Every flag says where its rule came from, so I know what to check. |
| 0:55 to 1:05 | Cut to the laptop: Ollama translating the same sentence offline. | And the weights are mine. The same model runs on my laptop's GPU, 32 tokens a second, and the client's text never leaves the machine. |
| 1:05 to 1:20 | Back to the page. Scroll to "French, ready to send": "2 of 5 blocks have something showing through", the French with the flagged terms marked, then click "Copy the French". **Final shot.** | Two blocks flagged. Check those, then send it. |

Do not show the grading table as the climax. It is in the post. The last frame is the French, ready to send.
