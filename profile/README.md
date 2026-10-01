<p align="center">
  <a href="https://passioncode.ai/">
    <img src="../assets/passioncode-icon-256.png" width="132" height="132" alt="PassionCode.ai passion fruit mark">
  </a>
</p>

<h1 align="center">PassionCode.ai</h1>

<p align="center"><strong>From vibe coding to passion coding.</strong></p>
<p align="center"><strong>PassionCode.ai — A toolkit for AI-native teams.</strong></p>

**PassionCode.ai is the organization; its toolkit is for AI-native teams.** **Fabric** is the
product: the CEO AI agent that plans, coordinates agents and runs projects — an early preview for
macOS. It grows through its own tools, and each of them also works on its own: **Fabric
Switchboard** manages Claude Code and Codex CLI accounts, **Fabric Dashboards** shows the local
agent services on your Mac in one window, **Fabric Inbox** puts the mail that needs you first, and
**Fabric VR** brings Fabric's surfaces to Meta Quest. The **Fabric Agent Contract** and the
**Fabric Agent Adapter** make any agent Fabric-compatible. Beside Fabric, PassionCode.ai builds
**Project Observatory**, a local dashboard for the projects your agents work on, which speaks
Fabric's protocol and runs without it, and **Okolos**, browser security for the age of AI agents.

Every product here is open source under AGPL-3.0. For use the AGPL doesn't cover, a commercial
license is available from contact@passioncode.ai. Released versions keep the license they shipped with:
releases made before the move to AGPL stay under MIT or PolyForm Noncommercial or Internal Use —
MIT up to Switchboard 0.3.1-beta.1, Project Observatory 0.8.1 and Fabric Dashboards 0.1.0, PolyForm
for Switchboard 0.4.0-beta.1, Project Observatory 0.8.2 to 0.9.1 and Fabric Dashboards 0.2.0 and
0.3.0 — and each repository's README names its own.

## Start with Switchboard

Manage accounts in separate work and personal pools, inspect reported usage limits,
and select which account handles the next managed request. Use the desktop app or the
`switchboard` CLI; agents read the usage that's left through `switchboard mcp`. Saved credentials
use macOS Keychain or Windows DPAPI.

**[Explore Switchboard and download the beta →](https://passioncode.ai/switchboard/)**

- [Download for macOS](https://passioncode.ai/switchboard/download/macos) · Apple silicon + Intel, macOS 14+.
- [Download for Windows](https://passioncode.ai/switchboard/download/windows) · x64 installer + CLI.
- [Read the source](https://github.com/passioncode-ai/fabric-switchboard) · [Releases and checksums](https://github.com/passioncode-ai/fabric-switchboard/releases) · beta 0.4.0-beta.1.

Early beta: macOS is Developer ID signed and notarized. Windows is unsigned and
cross-built; native Windows execution and live-provider acceptance have not yet been
verified. The download page and release notes describe the installation requirements.

## Project Observatory · available now

See what changed across your projects, what needs attention and where known API keys left
a copy, with the evidence beside each finding. It runs locally on macOS and Linux with
Python 3.11+, in English or Russian, and agents drive it over MCP. Known-value scanning cannot
find unknown secrets.

**[Explore Project Observatory →](https://passioncode.ai/observatory/)**

- [Read the source](https://github.com/passioncode-ai/project-observatory-dashboard) · [Releases](https://github.com/passioncode-ai/project-observatory-dashboard/releases) · latest 0.9.1.

## Fabric Dashboards · available now

One window for the local agent services on your Mac that speak `fabric-service/0.1`,
including Project Observatory's server: each service's state, start, stop and restart
through launchd, and its dashboard inside the app. Agents drive it over MCP.

- [Download 0.3.0](https://github.com/passioncode-ai/fabric-dashboards/releases/tag/v0.3.0) · macOS 13+, Apple silicon + Intel, DMG, Developer ID signed and notarized · [source](https://github.com/passioncode-ai/fabric-dashboards).

## Fabric Inbox · development preview

Gmail and Cloudflare mailboxes in one list, with the mail that needs you on top and the rest in
groups; addresses on your own domains answered by agents within the rules you set. The Mac app
creates its server in your own Cloudflare account, and every function of the app is also an MCP
tool. General IMAP and Outlook support are planned.

**[Explore Fabric Inbox and download the preview →](https://passioncode.ai/inbox/)**

- [Download for macOS](https://passioncode.ai/inbox/download/macos) · Apple silicon + Intel, macOS 12+, DMG, Developer ID signed and notarized · [release notes and checksum](https://github.com/passioncode-ai/fabric-inbox/releases/tag/v0.8.2) · [source](https://github.com/passioncode-ai/fabric-inbox).

Development preview 0.8.2: agent answers have not yet been tried with a real model call, and
Gmail has not yet been accepted on a real account.

## Fabric · early preview

**Stop managing agents one by one. Start operating projects.**

Fabric is the CEO AI agent we are building around that direction. Its current focus is
agent management: keeping context, work and decisions together. The longer-term aim is
to coordinate projects while people remain accountable for goals and authority.

**[Explore Fabric and download the early preview →](https://passioncode.ai/fabric/)**

- [Download for macOS](https://passioncode.ai/fabric/download/macos) · Apple silicon, macOS 13+, DMG · [release notes and checksum](https://github.com/passioncode-ai/passioncode-ai.github.io/releases/tag/fabric-v0.2.0) · [source](https://github.com/passioncode-ai/fabric).

Early preview 0.2.0: Developer ID signed and notarized. It needs Docker and the Supabase
CLI for its local database. The conversation with Fabric saves messages but does not
reply yet, and Fabric has no MCP entry of its own for other agents yet.

## The toolkit

| Project | Role | Status |
|---|---|---|
| [Fabric](https://github.com/passioncode-ai/fabric) | The CEO AI agent: desktop app and engine | Public · AGPL-3.0 · macOS early preview 0.2.0 |
| [Fabric Switchboard](https://github.com/passioncode-ai/fabric-switchboard) | Local Claude Code and Codex account manager | Public · AGPL-3.0 · beta 0.4.0-beta.1 |
| [Fabric Dashboards](https://github.com/passioncode-ai/fabric-dashboards) | Local agent services on a Mac in one window | Public · AGPL-3.0 · release 0.3.0 |
| [Fabric Inbox](https://github.com/passioncode-ai/fabric-inbox) | Desktop mail client with agents on your addresses | Public · AGPL-3.0 · development preview 0.8.2 |
| [Fabric VR](https://github.com/passioncode-ai/fabric-vr) | Fabric's remote surfaces, Meta Quest first | Public · AGPL-3.0 · built from source, no release |
| [Fabric Agent Contract](https://github.com/passioncode-ai/fabric-agent-contract) | What makes any agent Fabric-compatible: schemas, profiles, conformance | Public · AGPL-3.0 |
| [Fabric Agent Adapter](https://github.com/passioncode-ai/fabric-agent-adapter) | Makes an agent Fabric-compatible: kits, skills, a conformance probe | Public · AGPL-3.0 · release 0.5.4 |
| [Project Observatory](https://github.com/passioncode-ai/project-observatory-dashboard) | Local dashboard for your agents' projects | Public · AGPL-3.0 · release 0.9.1 |
| [Project Observatory Contract](https://github.com/passioncode-ai/project-observatory-contract) | Observatory's schemas and admission fixtures for a Fabric host | Public · AGPL-3.0 |
| [Okolos](https://github.com/passioncode-ai/okolos) | Browser security for the age of AI agents | Public · AGPL-3.0 · pre-alpha, no release |
| [PassionCode.ai launcher](https://github.com/passioncode-ai/passioncode) | Installs and updates every PassionCode.ai skill and plugin: `npx @passioncode-ai/passioncode@latest update` | Public · AGPL-3.0 · release 0.1.13 |
| [PassionCode.ai](https://passioncode.ai/) | Public home and product pages | Live website |

One family, one visual language. [Our design system](https://passioncode.ai/design-system/)
provides a shared dark palette with an opt-in light one, gold action accents and reusable
tokens. Switchboard, Project Observatory, Fabric Inbox and Fabric Dashboards carry their own
product marks; the passion fruit remains the PassionCode family mark.
