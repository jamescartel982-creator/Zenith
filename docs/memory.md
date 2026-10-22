# Accounts, welcome greetings, and memory

Start `zenith serve` using your platform wrapper. Select **Sign in / Create account**, choose a username, display name, and a password of at least 12 characters. On each sign-in and returning browser visit Zenith says **Welcome back, <name>.** The top of the workspace includes the Zenith mark and the existing original banner.

These are local server accounts. They do not connect to Anthropic, OpenAI, Hugging Face login, or an email service. Passwords use salted PBKDF2-SHA256 (600,000 rounds). The browser receives an HttpOnly, SameSite=Strict session cookie lasting seven days; HTTPS cookies also have Secure set. Signing out revokes that session. Sign-in/registration attempts are bounded per client address. There is no email password reset. Use HTTPS when exposing a server publicly; the existing server access-token gate still applies when configured.

## What Zenith remembers

Open **Memory** after signing in and explicitly save a preference, project fact, or personal note. Notes remain in the server's SQLite database across restarts and conversations. Zenith does not automatically extract personal information from everything you say. Up to 50 notes of 500 characters can be saved. At most eight notes fit into a bounded context budget; query overlap and recency choose relevant notes. Notes are supplied as user context, not higher-priority instructions or independently verified facts.

**Forget** removes a note; **Forget all** removes your saved notes. Removal affects subsequent requests. Existing assistant responses, exported datasets, backups, and trained weights are separate artifacts. If you approve an answer and its context for training, relevant personal notes included in that context can also be exported. Review before approving.

## Conversation ownership

Signed-in accounts have separate conversation histories and memory lists. Guessing another account's conversation UUID does not grant read, write, review, or deletion access. A returning account can resume recent conversations from the sidebar. Signed-out sessions keep the existing local workspace behavior; they have no persistent personal-memory API. Old anonymous conversations remain anonymous and cannot be claimed by signing in.

The person operating the server still controls its database, disk, imported knowledge index, model configuration, and training/export commands. Accounts are not encryption at rest, separate operating-system tenants, or a guarantee against a malicious server administrator. Imported dataset knowledge remains shared server context. This local application has not received a production multi-tenant security audit.

## Interface and answer quality

The workspace has safe Markdown/code rendering, code copying, a persistent greeting, saved conversation navigation, and explicit memory controls. Model text is rendered with DOM text nodes; scripts and raw HTML supplied by a model are not executed. The system prompt asks Zenith to answer clearly, acknowledge uncertainty, and avoid invented memories, citations, or tool actions.

Interface changes and memory do not establish that Zenith outperforms Claude. Answer quality depends on the selected model, hardware, relevant context, and evaluation. Zenith does not call Claude or claim to be an Anthropic model.
