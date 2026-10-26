# Continuous operation design — not yet deployed

**2026-10-26 — audit/proposal only.** No new bridge, model endpoint, service, profile, credential or deployment has been enabled; existing native code/configuration/state remains unchanged.

24/7 capability requires an always-powered supported host and persistent supervised deployment; a temporary execution session or powered-off laptop cannot provide it. No production host/cloud account/uptime contract was supplied or configured and no daemon was installed here.

Use a dedicated Linux host/VM or owned private container deployment first. Keep Zenith/inference Python, Hermes managed Python3.14, OpenClaw Node26.12.1+ and bridge environments separate. Use independent native state/secret volumes and a control-only bridge ledger. Restrict private/TLS ingress, egress per service/tool and CPU/RAM/PIDs/output/time/concurrency. Never expose host root/home or unrestricted Docker sockets to native model tools.

Retain native service owners. OpenClaw gateway install/start/stop/restart and native systemd/launchd/Task Scheduler behavior remain; Hermes retains systemd/launchd/Windows/s6 service-manager behavior. Use unique new integration profiles/service names, not overwritten original units or a competing supervisor that defeats a deliberate stop. The unchanged Zenith app remains available; new inference is separate and approval-gated.

Bound restart/backoff/start rates, startup/readiness dependencies, graceful drain and process-group cleanup. Preserve native queues/sessions and bridge ID mappings. Provider outage produces visible unavailability, not automatic external-model substitution or replay of an effectful task. A restart is not permission to rerun a cancelled job.

Monitor process liveness, authenticated native readiness/capabilities and a short actual stateless Zenith inference separately. healthz200 need not mean loaded weights, working tools or external delivery. Do not write health probes into user history/training data. Track queue age/depth, deadlines/approvals, unknown effects, delivery errors, latency/tokens/resources/disk. Export only deliberate redacted metadata; retain private native logs under owner policy.

Prove consistent separate native backups/restores with schema/keys in a disposable environment. After restart reconcile native IDs/status before retries; expose partial/degraded/uncertain state. Emergency stop controls only owned work; external/cloud effects may require reconciliation.

Pin SHA/locks/images. Update using candidate copies, original suites, interoperability/security/restore tests and explicit promotion; retain prior versions/state until rollback compatibility is proven. Do not run native in-place updates on an immutable live pin and call it unchanged.

Acceptance proposal: a recorded **24-hour minimum** smoke plus a longer agreed soak (for example72hours), forced process/reboot/network/provider/disk failures, job catch-up, deliberate stop/start, real channel delivery, restore and resource headroom under representative concurrency. These are targets, not measured results. Choose an SLO/sizing after infrastructure and workload measurements; no uptime, latency or GPU-capacity guarantee is supported by current CPU probes.

Windows/macOS/mobile products keep native OS/device/signing permissions. A Linux bridge does not emulate macOS/iOS hardware. Each unsupported service/platform remains individually BLOCKED instead of silently omitted.
