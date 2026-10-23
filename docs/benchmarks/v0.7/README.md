# Efficiency and regression evidence

`speed-before.json` records five actual model-generated requests on merged v0.6; `speed-after.json` records the same requests with v0.7 Auto. Both use the same pinned Qwen2.5-0.5B, two CPU threads, temperature 0, 256-token configured maximum, 2,048-token input budget, no adapter, separate warm-up, and isolated conversation storage. Auto intentionally changes prompting and caps simple replies at 96 tokens. `comparison.json` preserves the numerical comparison and limits.

- Prompt tokens: **940 → 555** (41% fewer).
- Retokenized visible reply tokens: **572 → 120** (79% fewer).
- Median complete reply: **13.17 → 6.99 seconds** (47% lower).
- Median first visible text: **1.09 → 1.36 seconds**; this did not improve.

These are single, five-question development runs. The rainbow request became slower. Some scientific explanations remain incorrect; the evaporation explanation, for example, wrongly attributes evaporation to heat absorbed during condensation. Shortness and speed do not establish correctness. There is no ChatGPT/Claude comparison or parity claim. Raw provider generation counts can include EOS; retokenized visible text is used consistently for the before/after token comparison.

`diagnostic.json` is a separate 14-case public diagnostic, measured with a 64-token cap, used as the frozen CI regression baseline. It scored **13/14**, with no slice accuracy regression against v0.6. The base-60 history error remains. Its five model-generated cases had a 2.61-second median full reply and 0.97-second median first text in that run. This suite was used during development, not kept as a blind generalization test; keyword scoring has material limitations. No new adapter was trained or promoted for this change.
