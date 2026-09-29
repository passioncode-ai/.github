<p align="center">
  <a href="https://passioncode.ai/">
    <img src="../assets/passioncode-icon-256.png" width="132" height="132" alt="PassionCode.ai passion fruit mark">
  </a>
</p>

<h1 align="center">PassionCode.ai</h1>

<p align="center"><strong>From vibe coding to passion coding.</strong></p>
<p align="center"><strong>PassionCode.ai — A toolkit for AI-native teams.</strong></p>

Tools for working with AI agents, starting with what you can use today.
**Switchboard** is a local account manager for Claude Code and Codex CLI.
**Project Observatory** is a local dashboard for the projects your agents work on.
**Fabric Dashboards** shows the local agent services on your Mac in one window.
**Fabric** is the CEO AI agent we are developing to coordinate agents and projects — now an early preview for macOS.

Switchboard, Project Observatory and Fabric Dashboards are source-available under PolyForm
Noncommercial or Internal Use; a commercial license is available on request from
contact@passioncode.ai. Releases already published under MIT stay under MIT: Switchboard up
to 0.3.1-beta.1, Project Observatory up to 0.8.1 and Fabric Dashboards 0.1.0.

## Start with Switchboard

Manage accounts in separate work and personal pools, inspect reported usage limits,
and select which account handles the next managed request. Use the desktop app or the
`switchboard` CLI. Saved credentials use macOS Keychain or Windows DPAPI.

**[Explore Switchboard and download the beta →](https://passioncode.ai/switchboard/)**

- [Download for macOS](https://passioncode.ai/switchboard/download/macos) · Apple silicon + Intel, macOS 14+.
- [Download for Windows](https://passioncode.ai/switchboard/download/windows) · x64 installer + CLI.
- [Read the source](https://github.com/passioncode-ai/fabric-switchboard) · [Releases and checksums](https://github.com/passioncode-ai/fabric-switchboard/releases).

Early beta: macOS is Developer ID signed but not notarized. Windows is unsigned and
cross-built; native Windows execution and live-provider acceptance have not yet been
verified. The download page and release notes describe the installation requirements.

## Project Observatory · available now

See what changed across your projects, what needs attention and where known API keys left
a copy, with the evidence beside each finding. It runs locally on macOS and Linux with
Python 3.11+, in English or Russian. Known-value scanning cannot find unknown secrets.

**[Explore Project Observatory →](https://passioncode.ai/observatory/)**

- [Read the source](https://github.com/passioncode-ai/project-observatory-dashboard) · [Releases](https://github.com/passioncode-ai/project-observatory-dashboard/releases) · latest 0.8.1.

## Fabric Dashboards · available now

One window for the local agent services on your Mac that speak `fabric-service/0.1`,
including Project Observatory's server: each service's state, start, stop and restart
through launchd, and its dashboard inside the app.

- [Download 0.1.0](https://github.com/passioncode-ai/fabric-dashboards/releases/tag/v0.1.0) · macOS 13+, Apple silicon + Intel, DMG, Developer ID signed and notarized · [source](https://github.com/passioncode-ai/fabric-dashboards).

## Inbox · in development

**Fabric Inbox** is a desktop mail client in development for the PassionCode family.
Cloudflare and Gmail are implemented in the preview; a shared account interface is in
progress. General IMAP and Outlook support are planned. There is no public release or
signed download yet.

**[Explore Fabric Inbox →](https://passioncode.ai/inbox/)**

## Fabric · early preview

**Stop managing agents one by one. Start operating projects.**

Fabric is the CEO AI agent we are building around that direction. Its current focus is
agent management: keeping context, work and decisions together. The longer-term aim is
to coordinate projects while people remain accountable for goals and authority.

**[Explore Fabric and download the early preview →](https://passioncode.ai/fabric/)**

- [Download for macOS](https://passioncode.ai/fabric/download/macos) · Apple silicon, macOS 13+, DMG · [release notes and checksum](https://github.com/passioncode-ai/passioncode-ai.github.io/releases/tag/fabric-v0.2.0).

Early preview 0.2.0: Developer ID signed and notarized. It needs Docker and the Supabase
CLI for its local database. The conversation with Fabric saves messages but does not
reply yet. Fabric's source is private.

## The toolkit

| Project | Role | Status |
|---|---|---|
| [Switchboard](https://github.com/passioncode-ai/fabric-switchboard) | Local Claude Code and Codex account manager | Public · source-available · beta downloads |
| [Project Observatory](https://github.com/passioncode-ai/project-observatory-dashboard) | Local dashboard for your agents' projects | Public · source-available · release 0.8.1 |
| [Fabric Dashboards](https://github.com/passioncode-ai/fabric-dashboards) | Local agent services on a Mac in one window | Public · source-available · release 0.1.0 |
| [Fabric Inbox](https://passioncode.ai/inbox/) | Desktop mail client | Private development · no public download |
| [Fabric](https://passioncode.ai/fabric/) | CEO AI agent and its technical foundation | Private source · macOS early preview |
| Agent Contract / Agent Adapter | Supporting compatibility and integration work | Private development |
| [PassionCode.ai](https://passioncode.ai/) | Public home and product pages | Live website |

One family, one visual language. [Our design system](https://passioncode.ai/design-system/)
provides a shared dark palette with an opt-in light one, gold action accents and reusable
tokens. Switchboard, Project Observatory, Fabric Inbox and Fabric Dashboards carry their own
product marks; the passion fruit remains the PassionCode family mark.
