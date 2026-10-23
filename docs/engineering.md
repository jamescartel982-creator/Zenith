# Zenith engineering standards

AI engineering describes how Zenith is built and reviewed. It is not a user-selectable subject or an admin mode. The previous AI engineering profiles have been removed from the runtime catalog. This guide keeps the design/review material for maintainers and links it to actual implementation.

## Implemented boundaries

| Concern | Implementation | Verification |
| --- | --- | --- |
| Conversation skill state | `agent/skill_access.py` and SQLite `skill_activations` | Selection persists per conversation; conversation ownership gates reads and writes |
| Owner-only security access | Live owner/session/code elevation checked in core and API | Forged chat/stream fields, other accounts, missing tokens, and expired elevation are denied |
| Revocation | Lock, logout, rotation, expiry, and different login sessions clear protected selection | Recheck before model work, at streamed chunks, and before saving; partial failures are discarded |
| Commands | Shared parser and command API; terminal control path | Commands bypass model prompts, history, training exports, and generation locks |
| Secret handling | Masked terminal prompts, existing private browser unlock, hashed session bindings | Codes/passwords are absent from model inputs and activation records |
| Data upgrades | Additive SQLite table creation | Existing turns and memories survive upgrades; deleting a conversation removes its selection |
| Inference | `agent/providers.py` and `agent/transport.py` | Bounded framing, explicit completion, response cleanup, and interrupted-stream rejection |
| Release integrity | `agent/integrity.py`, source manifest, installed-wheel checks | Complete source ZIP and normal wheel verification on Windows/Linux CI |
| Quality and observation | Evaluation suites, bounded reply budgets, private performance aggregates | Public diagnostic regression watch; results keep their actual scope and limitations |

Authorization is application code, not a prompt promise or a client-side flag. The trusted server reads login cookies and owner elevation; callers cannot assert that they are administrators. The local OS operator controls the database and installed Python code, so this is an account-level boundary rather than a sandbox against somebody who controls the machine.

Revocation is checked between streamed chunks and before storing a completed response. A running device kernel or blocked upstream read cannot be forcibly interrupted; existing provider cancellation limits still apply. See [provider reliability](provider-reliability.md).

## Development review checklists

Use these when implementing and evaluating code. They are documentation, not selectable instructions or new trained capabilities.

### AI systems foundations

Map models, harness, memory, data pipelines, and governance to a concrete use case.

- Define the user task and measurable baseline.
- Map data and inference flow across the five components.
- Specify failure modes, monitoring, and ownership.
- Keep model capability separate from application features.
- Include latency, quality, and cost budgets.

### Machine learning foundations

Choose an interpretable baseline before increasing model complexity.

- Define prediction time and labels.
- Split by entity or time before fitting preprocessing.
- Compare held-out metrics against a simple baseline.
- Avoid target and time leakage.
- Inspect subgroup and class imbalance.

### Deep learning

Explain tensor shapes, gradients, optimization, and generalization precisely.

- Check input and output tensor contracts.
- Specify loss, optimizer, and validation cadence.
- Diagnose learning curves and gradient problems.
- Distinguish train and evaluation behavior.
- Account for seeds and numerical precision.

### LLM architecture

Reason about tokenization, attention, positional encoding, context, and decoding.

- Define model inputs and outputs.
- Trace attention and next-token prediction.
- Estimate constraints and identify unsupported assumptions.
- Distinguish parameters, context length, and output length.
- Use the actual model configuration when supplied.

### Tokenization and context

Treat tokenizer behavior and chat templates as model-specific contracts.

- Identify tokenizer and special tokens.
- Reserve output space and preserve complete recent turns.
- Check multilingual and boundary-case behavior.
- Do not equate characters with model tokens.
- Preserve system and current-user messages.

### Prompt and context design

Create concise instructions with explicit task, evidence, output contract, and uncertainty.

- Define success and required evidence.
- Separate trusted instructions from untrusted content.
- Test ordinary, missing-information, and adversarial examples.
- Avoid unsupported tool or memory claims.
- Measure quality alongside token and latency budgets.

### Retrieval-augmented generation

Ground answers in supplied retrievable evidence and preserve provenance.

- Define corpus rights, freshness, and access rules.
- Choose chunking, retrieval, and reranking baselines.
- Evaluate retrieval recall and answer support independently.
- Enforce document access before retrieval.
- Abstain when relevant evidence is missing.

### Embeddings and semantic search

Choose embedding and similarity methods using task-specific retrieval evidence.

- Define query and document distributions.
- Compare embedding normalization and search baselines.
- Measure recall, ranking quality, latency, and drift.
- Keep evaluation queries out of tuning data.
- Check multilingual and near-duplicate cases.

### Fine-tuning and adapters

Use representative licensed data and compare adapters to the unchanged base.

- Prepare versioned grouped data splits.
- Define trainable parameters, loss masking, and resource limits.
- Evaluate answer quality and regressions before promotion.
- Never train on the sealed final test set.
- Lower training loss alone is insufficient for release.

### AI data engineering

Audit provenance, permissions, schemas, missingness, duplicates, and leakage.

- Define row grain, schema, source, and retention.
- Clean and deduplicate before creating isolated splits.
- Record checksums, transformations, and known gaps.
- Preserve source notices and access controls.
- Do not infer data rights from public availability.

### Model evaluation

Use task-specific, slice-aware tests and inspect actual outputs.

- Define metrics and error costs before testing.
- Evaluate independent representative examples and slices.
- Inspect failures and set promotion and rollback gates.
- Separate development diagnostics from sealed tests.
- Report uncertainty and scorer limitations.

### Calibration and abstention

Separate subjective confidence from validated probability and decide when to abstain.

- Define correctness labels and costly error cases.
- Fit thresholds on a validation set only.
- Measure calibration, coverage, and abstention error on held-out data.
- Do not present uncalibrated confidence as probability.
- Refit when model or inference configuration changes.

### AI governance and responsible use

Assess affected people, privacy, misuse, fairness, and accountability.

- Identify users, intended use, and consequential decisions.
- Map risks to evidence, controls, and accountable owners.
- Define monitoring, appeal, and rollback processes.
- Avoid fairness claims without relevant subgroup evidence.
- Separate legal questions from technical findings.

### AI application security

Treat retrieved content and model output as untrusted; use least privilege and external authorization.

- Map trust boundaries, sensitive data, and tool permissions.
- Review prompt injection, retrieval poisoning, and data leakage defenses.
- Plan controlled defensive tests and incident handling.
- Prompts cannot grant admin privileges.
- Require application-enforced authorization for every privileged action.

### MLOps and model lifecycle

Make experiments, artifacts, configuration, and releases reproducible and reviewable.

- Version code, data, model identifiers, and configuration.
- Define automated checks and artifact integrity.
- Stage deployment and monitor quality and resource regressions.
- Use explicit promotion approval and rollback gates.
- Keep private conversations and credentials out of artifacts.

### Inference performance

Profile first; separate loading, first-text latency, total time, and throughput.

- Fix hardware, model, prompts, seeds, and output policy.
- Measure tokenization, prefill, decoding, and transport separately.
- Apply one change and compare quality and resource usage.
- Do not compare different output budgets as pure model speed.
- Report warm-up, sample size, and outliers.

### Quantization and compression

Explain precision, calibration, hardware support, and quality tradeoffs.

- Identify supported model format and runtime.
- Estimate memory and choose representative calibration examples.
- Compare task quality, latency, and memory to a baseline.
- A smaller file is not proof of faster execution.
- Retain base-model attribution and artifact checksums.

### Distributed training

Plan parallelism around communication, memory, checkpointing, and recovery limits.

- Estimate model, optimizer, activation, and communication costs.
- Choose data or model parallelism and effective batch size.
- Plan checkpoint consistency and failure recovery tests.
- Document topology, precision, and accumulation.
- Verify equivalence against a small single-device baseline.

### Computer vision

Evaluate image models with appropriate spatial labels and distribution checks.

- Define task, image rights, and labeling quality.
- Choose augmentations without validation leakage.
- Evaluate domain shift, error slices, and deployment conditions.
- Check subject overlap between splits.
- Avoid identity or sensitive-attribute conclusions without valid evidence.

### Speech and audio AI

Account for sample rate, transcript quality, language, noise, and speaker overlap.

- Define consent, language coverage, and input format.
- Choose preprocessing and a documented baseline.
- Evaluate recognition errors, noise slices, and latency.
- Split speakers and recordings appropriately.
- Do not impersonate people or infer consent from a recording.

### Multimodal systems

Distinguish what the configured interface and model actually support.

- Inventory input modalities and preprocessing.
- Map alignment, missing-modality, and context limits.
- Evaluate cross-modal grounding and unsupported claims.
- Do not claim Zenith accepts images or audio unless implemented.
- Respect consent and provenance for every modality.

### Recommender systems

Compare ranking baselines while avoiding temporal and user-level leakage.

- Define feedback, exposure, and candidate generation.
- Build chronological splits and simple popularity baselines.
- Evaluate ranking, coverage, diversity, and feedback bias.
- Offline metrics do not prove user benefit.
- Respect user deletion and sensitive preference boundaries.

### Reinforcement learning

Specify states, actions, rewards, constraints, and evaluation separately.

- Define the task and simulator assumptions.
- Compare a simple baseline under fixed evaluation episodes.
- Check reward hacking, instability, and transfer limits.
- Simulation success does not establish real-world safety.
- Use resource and action bounds.

### AI research and reproducibility

Separate paper claims, reproduced results, and speculation.

- State the research question and baseline.
- Inspect datasets, compute, ablations, and evaluation validity.
- Document reproduction differences and unresolved uncertainty.
- Do not invent citations or executed experiments.
- Report negative results and limitations.

## Reference bibliography

These original-publisher URLs were retrieved on 2026-10-23 during the earlier source review. Links and original summaries are retained; content reuse and training rights require their own review. Point-in-time availability does not guarantee future contents or completeness.

| Reference | Publisher | Scope |
| --- | --- | --- |
| [PyTorch tutorials](https://pytorch.org/tutorials/) | PyTorch | Tensor operations, training loops, autograd, and deployment tutorials. |
| [Hugging Face LLM course](https://huggingface.co/learn/llm-course/en/chapter1/1) | Hugging Face | Transformers, tokenizers, datasets, and practical language-model workflows. |
| [Transformers documentation](https://huggingface.co/docs/transformers/index) | Hugging Face | Model loading, generation, configuration, and supported architectures. |
| [Datasets documentation](https://huggingface.co/docs/datasets/index) | Hugging Face | Dataset loading, transformation, streaming, and reproducible data handling. |
| [PEFT documentation](https://huggingface.co/docs/peft/index) | Hugging Face | Parameter-efficient adaptation and supported fine-tuning methods. |
| [Accelerate documentation](https://huggingface.co/docs/accelerate/index) | Hugging Face | Distributed and mixed-precision training configuration. |
| [Scikit-learn user guide](https://scikit-learn.org/stable/user_guide.html) | Scikit-learn | Supervised learning, preprocessing, model selection, and evaluation. |
| [NumPy learning resources](https://numpy.org/learn/) | NumPy | Numerical arrays, broadcasting, and scientific computing foundations. |
| [SciPy user guide](https://docs.scipy.org/doc/scipy/tutorial/) | SciPy | Optimization, probability, statistics, and numerical methods. |
| [Pandas user guide](https://pandas.pydata.org/docs/user_guide/index.html) | Pandas | Tabular cleaning, joins, time series, and data inspection. |
| [Jupyter documentation](https://docs.jupyter.org/en/latest/) | Project Jupyter | Reproducible computational notebooks and supported environments. |
| [MLflow documentation](https://mlflow.org/docs/latest/index.html) | MLflow | Experiment tracking, model lifecycle, deployment, and evaluation. |
| [ONNX Runtime documentation](https://onnxruntime.ai/docs/) | ONNX Runtime | Portable inference, execution providers, and runtime optimization. |
| [PyTorch Profiler recipe](https://docs.pytorch.org/tutorials/recipes/recipes/profiler_recipe.html) | PyTorch | Measure operator time, memory, and performance bottlenecks. |
| [Dive into Deep Learning](https://d2l.ai/) | D2L authors | Open textbook covering neural networks and modern deep-learning concepts. |
| [AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework) | NIST | Risk identification, measurement, governance, and trustworthy AI guidance. |
| [Hugging Face Audio course](https://huggingface.co/learn/audio-course/en/chapter0/introduction) | Hugging Face | Audio data, speech recognition, and audio-model workflows. |
| [Hugging Face Computer Vision course](https://huggingface.co/learn/computer-vision-course/en/unit0/welcome/welcome) | Hugging Face | Image data, computer vision models, and evaluation concepts. |
| [Sentence Transformers documentation](https://sbert.net/) | Sentence Transformers | Embedding models, semantic search, and reranking. |
| [Gymnasium documentation](https://gymnasium.farama.org/) | Farama Foundation | Reinforcement-learning environment interfaces and evaluation basics. |
| [Cybersecurity Framework](https://www.nist.gov/cyberframework) | NIST | Governance, identification, protection, detection, response, and recovery. |
| [NICE workforce framework](https://www.nist.gov/itl/applied-cybersecurity/nice/nice-framework-resource-center) | NIST | Cybersecurity work roles, knowledge, and skills; useful for learning paths. |
| [Technical guide to security testing and assessment](https://csrc.nist.gov/pubs/sp/800/115/final) | NIST | Planning, authorization, assessment governance, analysis, and reporting. |
| [Incident response recommendations, SP 800-61 Rev. 3](https://csrc.nist.gov/pubs/sp/800/61/r3/final) | NIST | Incident preparation, detection, response, recovery, and improvement. |
| [Secure Software Development Framework](https://csrc.nist.gov/projects/ssdf) | NIST | Integrate secure development practices throughout the software lifecycle. |
| [Application Security Verification Standard](https://owasp.org/www-project-application-security-verification-standard/) | OWASP | Structured application-security requirements and verification evidence. |
| [OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/) | OWASP | Defensive implementation guidance for authentication, input handling, and application controls. |
| [Software Assurance Maturity Model](https://owaspsamm.org/) | OWASP | Assess and improve an organization's software security practices. |
| [OWASP GenAI Security Project](https://genai.owasp.org/) | OWASP | Threat awareness and mitigations for LLM and generative-AI applications. |
| [StopRansomware guide](https://www.cisa.gov/stopransomware/ransomware-guide) | CISA | Prevention, incident preparation, containment, and recovery guidance. |
| [Understanding and responding to DDoS attacks](https://www.cisa.gov/resources-tools/resources/understanding-and-responding-distributed-denial-service-attacks) | CISA | Recognize availability attacks and coordinate defensive response. |
| [Cross-sector cybersecurity performance goals](https://www.cisa.gov/cross-sector-cybersecurity-performance-goals) | CISA | Prioritized baseline controls and measurable security improvements. |
| [D3FEND defensive techniques](https://d3fend.mitre.org/) | MITRE | Vocabulary and relationships for cybersecurity countermeasures. |
| [National Vulnerability Database](https://nvd.nist.gov/) | NIST | Vulnerability records and enrichment for defensive prioritization. |
| [MIT OpenCourseWare](https://ocw.mit.edu/) | MIT | University course materials for mathematics, computing, and science. |
| [OpenStax subjects](https://openstax.org/subjects) | OpenStax | Textbooks covering mathematics, statistics, science, and other subjects. |
| [Project Gutenberg](https://www.gutenberg.org/) | Project Gutenberg | Book discovery with jurisdiction-dependent public-domain and reuse notices. |
| [Library of Congress primary sources](https://www.loc.gov/classroom-materials/) | Library of Congress | Primary-source collections and evidence-based historical learning. |
| [Investor education](https://www.investor.gov/introduction-investing) | U.S. Securities and Exchange Commission | Investment concepts, risks, fees, diversification, and fraud awareness. |
| [Khan Academy](https://www.khanacademy.org/) | Khan Academy | Foundational mathematics, statistics, science, and computing lessons. |
