# Dependency, license and platform compatibility

**2026-10-26 — audit/proposal only.** No existing source, model, tokenizer, adapter, configuration or native state is changed. Existing upstream features remain owned by their original runtimes. S = source evidence; D = documentation claim; M = actual measurement; P = proposal. Source presence is not live interoperability or feature-parity verification.

| Component | Requirement at pin | Current observation / decision |
| --- | --- | --- |
| Zenith0.17.2 | Python>=3.10; selected Transformers/PEFT/PyTorch CPU stack | Existing Python3.12 environment runs its unchanged baseline. Do not change its dependencies. |
| Hermes managed app/PM | Python3.14; root bridge/updater range>=3.11,<3.15; Node>=26 for JS surfaces | Python3.12 does not establish managed runtime readiness; no prepared app/test environment. |
| OpenClaw Gateway | Node>=24.22.1<25 or>=26.12.1; pnpm12.15.0 | Host Node24.19.0 is too old. Client-package Node>=22.19.0 does not relax Gateway requirement. |
| Shared Python dependencies | Hermes cryptography50.0.2 versus Zenith>=44,<48 | Do not merge requirements, force pins, remove markers or patch tests; independent environments. |
| Native JS dependencies | Separate root/workspace locks, native SQLite/PTY/media packages | Resolve each exact lock under supported platform/runtime; no shared node_modules. |
| Native clients | OS/device/permission/signing constraints | Source presence does not verify macOS/iOS/Android/Windows clients from a Linux checkout. |

[Dependency declarations](../evidence/dependency-declarations.json) and all lockfile hashes in the source indexes are inventories, not a resolved transitive SBOM or legal clearance. At observation only about1.2GiB disk headroom remained after the requested clones. Actual full dependency footprints were not measured. Do not silently install multi-runtime stacks into the working Zenith environment or delete model caches to make room. Use a separately provisioned supported baseline/build host with adequate storage.

The live OpenClaw homepage describes a broader older Node minimum than the pinned package. The package engines at the chosen commit govern this source build; current web docs are floating references, not permission to bypass the pin's runtime checks. Hermes marketing lists five environments while source indexing records additional backend declarations; neither marketing count nor declaration count proves a tested runtime.

## License obligations

Zenith root is Apache-2.0; Hermes root is MIT (Nous Research2025); OpenClaw root is MIT (OpenClaw Foundation2026). Keep each whole native source tree, LICENSE and applicable notices. The audit retains root license texts and legal-path/hash inventories. Do not rename authors, strip notices, rebrand upstream code as proprietary Zenith implementation or treat catalog packages/model weights as covered automatically by a root MIT license. Third-party assets/native binaries/plugins and service/model/dataset terms require their own resolved provenance and obligations. No license is bypassed.

The proposed bridge uses supported wire APIs/extensions and its own isolated dependency lock. Native dependencies, telemetry choices, update policies and license notices remain native. No upstream code, package manifest, lock, test, configuration or source asset is patched. If an interface gap ultimately needs a source change, document the exact file/diff and obtain explicit approval before doing it.
