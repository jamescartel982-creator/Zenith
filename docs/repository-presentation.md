# GitHub presentation

`assets/zenith-social-preview.png` is an original 2:1 PNG under 1 MB, prepared
for repository cards and social sharing. The README uses this banner; the
original `assets/zenith-banner.png` remains intact.

GitHub's documented upload flow is repository **Settings → General → Social
preview → Edit → Upload an image**. Upload the prepared PNG at
<https://github.com/n8storm/Zenith/settings>. There is no supported social-preview
upload operation in the available GitHub connector or documented REST API, so
this manual setting is not claimed complete.

The About description and relevant topics help describe the actual project.
GitHub controls search indexing, Explore placement, stars and trending status;
artwork and metadata cannot guarantee the Oppia screenshot's placement or counts.

Reference: <https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/customizing-your-repositorys-social-media-preview>.

The current GitHub integration returned **HTTP 403: Resource not accessible by
integration** for both supported repository-description and topics updates.
Those settings were not changed. A repository administrator can use the About
gear on the repository home page to set this proposed description:

> Local AI workspace with private memory, secure agent tools and reviewed learning. Windows, Linux and macOS installation.

Suggested topics: `artificial-intelligence`, `local-ai`, `ai-assistant`, `python`,
`llm`, `privacy`, `agent-framework`, `windows`, `linux`, `macos`, `machine-learning`.
The README banner is delivered through the normal reviewed source change.
