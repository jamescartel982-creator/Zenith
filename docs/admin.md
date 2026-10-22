# Owner access and Devil mode

First create your own account in the browser. In the **server's terminal**, using the same Zenith profile/data directory as that server, run:

```text
zenith admin init --username YOUR_USERNAME
```

On Windows without environment activation:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\run.ps1 admin init --username YOUR_USERNAME
```

On Linux: `./run.sh admin init --username YOUR_USERNAME`.

The command binds the existing account to the owner role and prints the location of `admin-code.txt` under your `ZENITH_HOME`. Read that file privately on your machine. Each installation generates its own cryptographically random code; there is no shared default code, embedded API key, or code committed to Git. The database stores a salted PBKDF2 hash. The file uses a private temporary file and replacement; POSIX permissions are 0600. On Windows, keep the containing user-profile directory protected with your normal account permissions; Python's file mode does not establish a new Windows ACL.

Sign in as that account, open **Admin workspace**, and enter the code. Both the owner account's login session and the code are required. Knowing the code does not elevate another account. Unlocking lasts 15 minutes for that login session; it does not extend automatically. **Lock admin access**, signing out, session expiry, or code rotation removes access.

```text
zenith admin init --username YOUR_USERNAME --rotate
```

Rotation generates a replacement code, revokes all elevations, and can bind a different existing owner account. This command is a local OS-owner operation: anyone controlling the server files/database already controls the deployment. Do not expose shell access to untrusted users.

Normal chat, saved memories, and training corrections reject the owner-code format before calling the model or saving it. If you paste exactly the code into the browser composer, the interface routes it directly to the private admin-unlock endpoint and clears the composer. Prefer the masked Admin field. The code is never placed in browser storage or a model prompt. Application logs record tool/event names, not codes or tool inputs.

## Devil mode

The owner can enable **Devil mode · authorized security workspace** after unlocking. It provides these explicit, offline operations:

| Tool | Behavior |
| --- | --- |
| Calculator | Bounded numeric expressions without Python evaluation |
| SHA-256 | Hash pasted text |
| Decode Base64 | Decode bounded pasted data |
| Pasted code security review | Flag a small set of risky patterns for human inspection |
| Inspect URL offline | Parse a URL and highlight suspicious features without fetching it |

The mode has a visible accent and follows the same expiry. Tools operate only on submitted text. There is no arbitrary command execution, scanning of external systems, automatic exploit execution, file access, or tool invocation by the language model. Heuristic code review is not a security audit. Cybersecurity instruction profiles can help explain defenses and write code, subject to the configured model's capabilities.

Admin also has a **human review queue**. Users explicitly submit a question and answer for review; the owner can respond and close the request. No external person is contacted or notified automatically. The regular server access token, if configured, remains an additional gate for all these endpoints. Use HTTPS when hosting publicly.
