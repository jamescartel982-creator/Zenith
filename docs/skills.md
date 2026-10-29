# Built-in skill commands and owner-only security

Zenith has **16 public conversation skills** and **16 owner-only defensive cybersecurity skills**. AI engineering is how the software is built; it has been removed from the runtime skill menu. See [engineering standards and implementation](engineering.md) for the actual code boundaries and developer review material. The optional [reviewed instruction-pack library](productivity.md) adds indexed imports separately from these bundled profiles.

## Activate a skill with a command

Type these directly into browser chat or `zenith chat`:

```text
/skill list
/skill mathematics
/skill status
/skill off
```

`/skills` also lists available skills. Commands are processed by Zenith, not the model. They consume no model tokens and are not saved as chat turns or training examples. Selection is saved for the current conversation in SQLite and restored after reload. A new conversation starts with General. The menu and Use button call the same command endpoint.

## Owner-only security activation

In browser chat:

1. Sign in as the account configured as the owner.
2. Type `/admin unlock` or open **Admin workspace**, then enter the private local admin code in its masked field.
3. Type `/skill list` to see the available security IDs.
4. Activate one explicitly, for example `/skill incident-response` or `/skill cybersecurity`.
5. Use `/skill off` for General, or `/admin lock` to lock Admin and clear protected activations.

Unlocking does not activate a security skill automatically. Security profiles are hidden from other accounts and from locked owners. The owner account, valid login, and current code elevation are all required; the code alone does not grant another account access. See [owner setup](admin.md) if you have not initialized your account.

In terminal chat, `/admin unlock` asks for your owner username, account password, and private admin code. Password and code use masked prompts and require an interactive terminal. Never pass them as command arguments. Successful unlock starts a new private owner conversation. `/admin lock` locks and signs out that terminal login, then starts an anonymous conversation. Exiting terminal chat revokes its temporary login. Starting `zenith chat --skill incident-response` while locked is rejected; unlock inside chat first.

Admin elevation lasts 15 minutes. Protected activation is bound to that specific login session using its hash, not a raw token or code. Lock, logout, successful re-unlock, and code rotation clear protected state; expired or different logins cannot inherit it. After unlocking again, activate the desired skill again. Browser skills refresh after unlock, lock, expiry, account changes, and conversation changes.

The backend enforces this on the command endpoint and both chat endpoints, including forged request fields. The core checks again before model work, between streamed chunks, and before saving. If access is revoked during a security answer, partial text is discarded and no completed turn is saved. A running device kernel or blocked read is not forcibly interrupted; see [provider cancellation limits](provider-reliability.md). An unknown browser skill state blocks sending until it can be confirmed.

The local operating-system owner controls the files, database, and Python installation. This is a Zenith account boundary, not a sandbox against somebody who controls the host. Skills remain instruction profiles for the configured model; activation does not grant tools, run scans, train weights, or guarantee professional competence. Security profiles retain their defensive and authorized scope.

## Terminal metadata commands

```bash
./run.sh skills list
./run.sh skills show programming
./run.sh skills resources
./run.sh skills validate
./run.sh skills recipes install --approve
./run.sh skills recipes status
./run.sh skills search --query "Python correctness beginner"
./run.sh chat
```

On Windows replace `./run.sh` with `powershell -NoProfile -ExecutionPolicy Bypass -File .\run.ps1`. Metadata commands do not load a model. Public listing/show commands expose public skills; the in-chat `/skill list` includes security only after owner unlock. Offline validation checks the bundled library: 32 profiles, 24 application references, and six owner-visible terminology records. Imported profiles are validated separately on import. Developer documentation preserves the broader 40-reference bibliography.

## API behavior

The optional [generated recipe library](generated-recipes.md) installs 100,000
labeled combinations separately from curated profiles. It uses the same owner
checks and paginated installed-library search; no recipe grants tool permissions.

- `GET /api/skills`: role-filtered bundled catalog; 16 public profiles or 32 for the currently unlocked owner, plus imported-library status. A client cannot enable private results with a query flag.
- `GET /api/skills/search`: signed-in, paginated imported profile search with the same owner visibility rule.
- `GET /api/skills/profile/ID`: signed-in imported or bundled profile details after authorization.
- `GET /api/skills/current?session_id=UUID`: current skill after conversation-ownership and expiration checks.
- `POST /api/skills/command`: `{"session_id": "UUID", "command": "/skill ID"}`. Uses the existing server gate and login cookie. No codes or passwords belong in this payload.
- `POST /api/chat` and `/api/chat/stream`: omitted/null `skill` resolves the saved server-side selection. An explicit skill is a per-request override and receives the same owner checks. Flags claiming admin status cannot bypass authorization.

Commands are separate from model prompts. Sending `/skill ...` or `/admin ...` through a raw chat endpoint returns a validation error; use the command endpoint. Conversation state is account scoped. Security metadata and activation responses contain no session hashes or secret codes. Deleting a conversation removes its activation record. Schema creation is additive and preserves existing chats and memories.

## Public conversation skills

| Command | Skill |
| --- | --- |
| `/skill general` | General reasoning |
| `/skill mathematics` | Mathematics |
| `/skill science` | Science |
| `/skill history` | History |
| `/skill ancient-math` | Ancient mathematics |
| `/skill programming` | Programming |
| `/skill investing` | Investing and stocks |
| `/skill day-trading` | Day trading education |
| `/skill books-writing` | Books and writing |
| `/skill research` | Research literacy |
| `/skill data-analysis` | Data analysis |
| `/skill csv-quality` | CSV quality review |
| `/skill decimal-statistics` | Decimal statistics |
| `/skill analysis-review` | Analysis review |
| `/skill evidence-check` | Evidence checking |
| `/skill adaptive-explanation` | Adaptive explanation |

## Owner-only security skills

| Command | Skill | Deliverable |
| --- | --- | --- |
| `/skill cybersecurity` | Authorized security work | An evidence-based answer with assumptions, limits, and next steps. |
| `/skill security-foundations` | Security foundations | A scoped defensive report with evidence, risk, remediation, and verification. |
| `/skill threat-modeling` | Threat modeling | A scoped defensive report with evidence, risk, remediation, and verification. |
| `/skill secure-coding` | Secure coding | A scoped defensive report with evidence, risk, remediation, and verification. |
| `/skill appsec-audit` | Application security auditing | A scoped defensive report with evidence, risk, remediation, and verification. |
| `/skill authorized-pentest` | Authorized assessment planning | A scoped defensive report with evidence, risk, remediation, and verification. |
| `/skill vulnerability-management` | Vulnerability management | A scoped defensive report with evidence, risk, remediation, and verification. |
| `/skill incident-response` | Incident response | A scoped defensive report with evidence, risk, remediation, and verification. |
| `/skill digital-forensics` | Digital forensics fundamentals | A scoped defensive report with evidence, risk, remediation, and verification. |
| `/skill malware-analysis` | Defensive malware analysis | A scoped defensive report with evidence, risk, remediation, and verification. |
| `/skill ransomware-defense` | Ransomware defense and recovery | A scoped defensive report with evidence, risk, remediation, and verification. |
| `/skill network-defense` | Network and availability defense | A scoped defensive report with evidence, risk, remediation, and verification. |
| `/skill identity-security` | Identity and account protection | A scoped defensive report with evidence, risk, remediation, and verification. |
| `/skill cloud-security` | Cloud and container security | A scoped defensive report with evidence, risk, remediation, and verification. |
| `/skill supply-chain-security` | Software supply-chain security | A scoped defensive report with evidence, risk, remediation, and verification. |
| `/skill disclosure` | Responsible disclosure | A scoped defensive report with evidence, risk, remediation, and verification. |

The six hacker-color labels remain educational metadata visible to the unlocked owner; they cannot activate a mode or grant privileges. There are no malware deployment, ransomware creation, DDoS generation, theft, doxxing, unauthorized exploitation, or retaliation profiles.

## Maintaining the system

`agent/resources/skills-v1.json` uses schema version 2. Security-category profiles must declare `access: admin`; public profiles declare `access: public`. Keep stable IDs, original instructions, bounded workflow/checklist fields, safe source links, and honest retrieval evidence. Run `zenith skills validate`, the full test suite, and the owner/command tests before release. Catalog visibility is a convenience; activation authorization belongs in `agent/skill_access.py` and core/API checks.

Resources open only when a user follows a link. Selecting a skill fetches no external documents and does not copy courses or books into training. Source terms still apply. The original references and engineering material are retained in [engineering standards](engineering.md). Regenerate the release manifest only for reviewed changes, as explained in [integrity](integrity.md).
