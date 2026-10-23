# Skills and learning resources

Zenith 0.9 ships 51 instruction profiles and 40 curated original-publisher references. Open **Skills** in browser chat, search a topic, inspect its workflow and review checklist, then choose **Use profile**. The selected profile also appears in the grouped composer menu. Practice exercises use supplied examples, owned systems, authorized labs, or synthetic data.

Profiles are guidance for the configured model, not new trained weights, certifications, guaranteed expertise, or executable tools. Only the selected instruction/workflow enters a chat request. Source pages are not fetched or supplied as evidence automatically; provide relevant excerpts when an answer needs their exact contents. Reading a reference does not establish rights to copy it or train on it.

## Terminal access

```bash
./run.sh skills list --category ai
./run.sh skills show rag
./run.sh skills resources --category security
./run.sh skills list --query recovery
./run.sh skills taxonomy
./run.sh skills validate
./run.sh chat --skill incident-response
```

On Windows, replace `./run.sh` with `powershell -NoProfile -ExecutionPolicy Bypass -File .\run.ps1`. The installed `zenith skills ...` command works on either OS. Output is JSON for inspection and scripting. These metadata commands need no GPU, Torch, model download, provider API key, or live network request.

## Cybersecurity scope and terminology

Profiles support defensive analysis, secure implementation, risk assessment, evidence handling, incident recovery, responsible disclosure, and assessment planning with written authorization. An authorized-assessment profile asks for ownership, permitted assets, time windows, rules of engagement, stop conditions, and reporting requirements. It provides planning and review guidance; it does not run scans or exploit systems.

Ransomware, availability attacks, malware, account compromise, and software flaws appear as defensive study topics. There are no malware deployment, ransomware creation, DDoS generation, theft, doxxing, unauthorized exploitation, or retaliation profiles. Hacker-color labels are educational metadata and cannot be selected as skills or used to unlock admin access. Existing owner authorization is enforced separately; prompt instructions are guidance and cannot guarantee that a configured model always complies.

| Label | Informal meaning | Professional alternative |
| --- | --- | --- |
| Black hat | An informal label for malicious or criminal activity for gain, harm, or unauthorized access. | Threat analysis, malware defense, ransomware recovery, and fraud prevention. |
| White hat | An informal label for security work performed with explicit authorization and agreed scope. | Written rules of engagement, evidence-based auditing, remediation, and retesting. |
| Gray hat | Often describes finding or disclosing flaws without prior permission; good intentions do not establish authorization. | Use an authorized lab or owner-approved assessment and coordinated disclosure. |
| Green hat | An inconsistent informal term sometimes used for beginners; it is not a qualification. | Learn fundamentals, practice on owned synthetic examples, and develop reporting skills. |
| Blue hat | An ambiguous term used for external security testers in some contexts and revenge-motivated actors in others. | Account protection, incident response, lawful reporting, and authorized external review. |
| Red hat | An inconsistent internet label sometimes associated with vigilante retaliation; distinct from an authorized red-team exercise or the software company. | Defensive detection, incident response, and assessment work with explicit rules of engagement. |

## Profile inventory

### AI engineering

| ID | Profile | Deliverable |
| --- | --- | --- |
| `ai-foundations` | AI systems foundations | A component map with responsibilities and acceptance criteria. |
| `ml-foundations` | Machine learning foundations | A leakage-aware experiment design. |
| `deep-learning` | Deep learning | A reproducible training-loop design. |
| `llm-architecture` | LLM architecture | An architecture explanation with compute and memory tradeoffs. |
| `tokenization` | Tokenization and context | A context-budget and truncation plan. |
| `prompt-design` | Prompt and context design | A versioned prompt and evaluation checklist. |
| `rag` | Retrieval-augmented generation | A retrieval and citation evaluation plan. |
| `embeddings` | Embeddings and semantic search | A search benchmark with labeled relevance examples. |
| `fine-tuning` | Fine-tuning and adapters | A bounded candidate experiment with promotion criteria. |
| `data-engineering` | AI data engineering | A versioned data contract and quality report. |
| `model-evaluation` | Model evaluation | A baseline comparison and regression report. |
| `uncertainty` | Calibration and abstention | A calibration and human-review policy. |
| `responsible-ai` | AI governance and responsible use | A documented AI risk register and review plan. |
| `ai-security` | AI application security | An AI threat model and mitigation checklist. |
| `mlops` | MLOps and model lifecycle | A model release and rollback runbook. |
| `inference-optimization` | Inference performance | A reproducible performance comparison. |
| `quantization` | Quantization and compression | A compatibility and quality validation plan. |
| `distributed-training` | Distributed training | A distributed experiment and recovery specification. |
| `computer-vision` | Computer vision | A vision data and evaluation design. |
| `speech-audio` | Speech and audio AI | An audio processing and evaluation plan. |
| `multimodal-ai` | Multimodal systems | A modality contract and grounded evaluation plan. |
| `recommender-systems` | Recommender systems | A recommendation evaluation and monitoring plan. |
| `reinforcement-learning` | Reinforcement learning | An environment specification and bounded experiment. |
| `ai-research` | AI research and reproducibility | A reproducibility checklist and evidence table. |

### Cybersecurity

| ID | Profile | Deliverable |
| --- | --- | --- |
| `cybersecurity` | Authorized security work | An evidence-based answer with assumptions, limits, and next steps. |
| `security-foundations` | Security foundations | A scoped defensive report with evidence, risk, remediation, and verification. |
| `threat-modeling` | Threat modeling | A scoped defensive report with evidence, risk, remediation, and verification. |
| `secure-coding` | Secure coding | A scoped defensive report with evidence, risk, remediation, and verification. |
| `appsec-audit` | Application security auditing | A scoped defensive report with evidence, risk, remediation, and verification. |
| `authorized-pentest` | Authorized assessment planning | A scoped defensive report with evidence, risk, remediation, and verification. |
| `vulnerability-management` | Vulnerability management | A scoped defensive report with evidence, risk, remediation, and verification. |
| `incident-response` | Incident response | A scoped defensive report with evidence, risk, remediation, and verification. |
| `digital-forensics` | Digital forensics fundamentals | A scoped defensive report with evidence, risk, remediation, and verification. |
| `malware-analysis` | Defensive malware analysis | A scoped defensive report with evidence, risk, remediation, and verification. |
| `ransomware-defense` | Ransomware defense and recovery | A scoped defensive report with evidence, risk, remediation, and verification. |
| `network-defense` | Network and availability defense | A scoped defensive report with evidence, risk, remediation, and verification. |
| `identity-security` | Identity and account protection | A scoped defensive report with evidence, risk, remediation, and verification. |
| `cloud-security` | Cloud and container security | A scoped defensive report with evidence, risk, remediation, and verification. |
| `supply-chain-security` | Software supply-chain security | A scoped defensive report with evidence, risk, remediation, and verification. |
| `disclosure` | Responsible disclosure | A scoped defensive report with evidence, risk, remediation, and verification. |

### General subjects

| ID | Profile | Deliverable |
| --- | --- | --- |
| `general` | General reasoning | An evidence-based answer with assumptions, limits, and next steps. |
| `mathematics` | Mathematics | An evidence-based answer with assumptions, limits, and next steps. |
| `science` | Science | An evidence-based answer with assumptions, limits, and next steps. |
| `history` | History | An evidence-based answer with assumptions, limits, and next steps. |
| `ancient-math` | Ancient mathematics | An evidence-based answer with assumptions, limits, and next steps. |
| `programming` | Programming | An evidence-based answer with assumptions, limits, and next steps. |
| `investing` | Investing and stocks | An evidence-based answer with assumptions, limits, and next steps. |
| `day-trading` | Day trading education | An evidence-based answer with assumptions, limits, and next steps. |
| `books-writing` | Books and writing | An evidence-based answer with assumptions, limits, and next steps. |
| `research` | Research literacy | An evidence-based answer with assumptions, limits, and next steps. |
| `data-analysis` | Data analysis | An evidence-based answer with assumptions, limits, and next steps. |

## Source bibliography

All 40 pages returned successful live retrievals on **2026-10-23**. The bundled JSON records each URL, publisher, original summary, retrieval date, HTTP status, and retrieved page title. This is point-in-time availability evidence, not a promise that links remain unchanged or that every page was exhaustively reviewed. Firecrawl was used for source discovery and retrieval. Short descriptions and workflows were written for Zenith; source documents are not copied into the release.

| Reference | Publisher | Topic |
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

## Maintain and extend the library

Edit `agent/resources/skills-v1.json` in a reviewed branch. Keep stable IDs for existing profiles. Add bounded original instructions, a deliverable, at least three workflow steps, at least two review checks, a safe practice exercise, and valid resource IDs. Prefer original-publisher HTTPS references; preserve attribution, record retrieval status and date honestly, and check access/reuse terms. An unavailable reference can remain listed only with its explicit unavailable status.

Run `zenith skills validate` and the profile tests before publishing. The validator checks schema and size limits, unique identifiers/URLs, allowed categories, text fields, workflow lengths, safe link structure, dates, retrieval status evidence, and reference integrity. It operates offline and does not recheck source availability. Return values are copied so clients cannot change cached profiles.

Regenerate the tracked release manifest only for reviewed source changes, as described in [integrity](integrity.md). The JSON is included in wheels and source ZIPs. Browsing the library does not import datasets or alter accounts, memories, adapters, or admin roles. Resource coverage is curated and expandable, not an exhaustive index of all AI knowledge.

## Validation and limits

Library tests cover preserved legacy IDs, metadata/reference validity, search/filtering, schema failures, unsafe links, copy isolation, bounded selected prompts, absence of privilege elevation, gated API access, and offline lightweight CLI behavior. A controlled-provider browser check exercises desktop/mobile filtering, empty results, workflow/resource details, taxonomy, profile selection in a real chat request, safe external links, and zero browsing-triggered external requests. Model accuracy, compliance with every instruction, and professional competence require separate task-specific evaluations. See [validation](validation.md) and [quality and training](quality-and-training.md).
