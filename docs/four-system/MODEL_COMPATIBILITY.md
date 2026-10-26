# Preserved model and protocol compatibility

The selected Zenith lineage is unchanged: Qwen2ForCausalLM,
`Qwen/Qwen2.5-0.5B-Instruct` at
`7ae557604adf67be50417f59c2c2f167def9a775`, 494,032,768 base parameters,
24 layers, hidden size 896, and the existing rank-8 LoRA with 4,399,104
parameters. Tokenizer vocabulary is 151,665, embedding vocabulary 151,936;
architectural context ceiling is 32,768, while usable inference budgets remain
configured separately. Nothing here initializes or trains replacement weights.

The [current real checkpoint probe](evidence/current-checkpoint-probe.json)
loaded the preserved checkpoint, answered `4` and retained tokenizer semantic
fingerprint `221ea68122dfcfb2772276b69e62fc97ea9b13785ee069b118ee36498b19a418`.
The production profile stayed unchanged, restricted tools stayed disabled and no
new model promotion was approved. The previously selected adapter retains its
experimental status and recorded failed numerical gates.

The earlier [model inventory](evidence/zenith-model-verification.prior.json) and
[preservation receipt](evidence/model-profile-preservation.json) retain base and
adapter provenance. They are historical measurements, not newly fabricated
financial or coding benchmark results.

TradingAgents' supported `openai_compatible` client can point to a dedicated
Zenith inference sidecar once implemented and authorized. The current custom
application chat endpoint does **not** satisfy OpenAI chat-completion tool-call
contracts. Native managers require structured responses and native analysts need
correct tool calls/results. A successful arithmetic probe does not demonstrate
those financial workflows or justify a claim of model compatibility.

Both TradingAgents quick/deep model tiers must bind explicitly to Zenith with a
service-scoped credential. Native tool/risk/portfolio execution remains in
TradingAgents. Hermes and OpenClaw must retain independent memory and execution
controls. No four-runtime graph, live order capability, external provider key or
messaging destination is enabled by this audit.
