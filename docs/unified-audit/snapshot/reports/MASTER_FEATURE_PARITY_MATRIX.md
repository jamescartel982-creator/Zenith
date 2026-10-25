# Master feature and coverage matrix

**Date:** 2026-10-25 UTC. **Scope:** audit/design only; further Zenith edits await approval of this expanded project.

OpenClaw `2f5727b9c61c2ba9dccc3c880d9115f02cb8652f`; Hermes `d05095663342556788cf2a198bfa7844cc7968ab`; Zenith main `e6963d9c6f45c196ae2e301819ae1ae093b35c41`; unmerged PR #19 `44d55d23cb946254a4a718a35a7c5432003cc01b`.

**Evidence:** S = source-verified code/declaration; D = upstream documentation/policy claim; M = actually measured; P = proposed; H = hypothesis. A manifest, tool schema, doc page or test filename does not prove successful execution. Status describes Zenith parity, not whether a reference project works.

The unabridged [CSV](MASTER_FEATURE_PARITY_MATRIX.csv) and [JSON](../evidence/master-feature-matrix.json) retain every indexed declaration, skill path, documentation surface and catalog reference. The [source mapping](SOURCE_TO_ZENITH_MAPPING.md) explains the 72 manually traced behavioral groups. There are **3672 coverage records, not 3672 independent capabilities**: a channel can appear in its plugin, registration, documentation and tool records. No percentage of parity can validly be computed from these counts.

| Record type | Rows |
| --- | --- |
| core_behavior | 72 |
| plugin_declaration | 292 |
| channel_integration | 55 |
| model_provider_identity | 90 |
| platform_registration | 29 |
| tool_declaration | 51 |
| toolset_member | 55 |
| skill_package | 339 |
| documentation_surface | 1855 |
| catalog_reference | 827 |
| execution_backend | 7 |

| Zenith parity status | Rows |
| --- | --- |
| PARTIAL | 33 |
| NOT STARTED | 2807 |
| BLOCKED | 832 |

`PARTIAL` means a Zenith equivalent covers part of the contract, sometimes only in unmerged PR #19. `NOT STARTED` means the proposed compatible implementation has not been accepted. `BLOCKED` includes external catalog packages whose source/license was not available in the audited checkout, and platform/service prerequisites. `IMPLEMENTED` requires production code; `VERIFIED` additionally requires the recorded supported-environment acceptance run. No new unified parity record is verified by this audit.

Each row includes reference project, pinned source, configuration/dependency reference, main equivalent, unmerged-pilot equivalent, missing behavior, integration strategy, destination files, security implications, acceptance files/behavior and status. Exact manifest schemas and environment **names** are retained in [manifest evidence](../evidence/plugin-manifests.json), not credential values. Import statements and dependency declarations are inventories, not a resolved dependency lock or proof of compatibility.

Applicability must be reviewed before implementation: documentation can describe the same feature, historical/restricted models, examples or unsupported platforms; fixture/vendor skills are coverage evidence rather than a request to install them. QA/test channels are test fixtures, not public messaging services. Reference-specific branding, release destinations, update URLs, account identities and telemetry are not applicable Zenith features. Legal access, source review, platform testing and behavior-level acceptance remain required for external plugins. Declared tools do not inherit execution permission.

Channel identities are enumerated independently (28 OpenClaw and 27 Hermes manifest declarations, plus 29 Hermes registration sites). They overlap and must not be summed as unique services. Protocol variants must retain their distinctions: personal-session WhatsApp and business/cloud WhatsApp, or callback and relay transports, cannot be treated as interchangeable. Each deployable variant needs its own actual service fixture and permission tests.
