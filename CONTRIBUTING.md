# Contributing to PassionCode.ai repositories

This is the default contribution guide for every repository of the `passioncode-ai`
organization. A repository with its own `CONTRIBUTING.md` adds to it; where the two differ, the
repository's own file wins. It is written for people and for coding agents alike — **an agent
reads this file and the repository's `AGENTS.md` before its first edit, in every repository,
every time.**

## 1. Read first, in this order

1. **The repository's `AGENTS.md`** (its `CLAUDE.md` imports it): what the repository is, the exact
   commands that test a change, and its local rules.
2. **This file**: the rules every repository shares.
3. **How the system works** — organization members: [Fabric Workspace](https://wiki.passioncode.ai/),
   the wiki of every tool (Fabric, its protocols, MCP, the agents), and the organization's rules
   in [org-index](https://github.com/passioncode-ai/org-index) (`RULES.md`). Both are private;
   outside contributors work from the repository's own documents.

## 2. Names

| Name | What it is |
|---|---|
| **PassionCode.ai** (short: PassionCode) | the organization; its toolkit is for AI-native teams |
| **Fabric** | the product: the CEO AI agent — the desktop app and its engine |
| **Fabric Inbox**, **Fabric Dashboards**, **Fabric Switchboard**, **Fabric VR** | Fabric's tools; each also works on its own. Use the full name before the short one |
| **Fabric Agent Contract**, **Fabric Agent Adapter** | what makes any agent Fabric-compatible; protocol ids stay lowercase (`fabric-service/0.1`) |
| **Fabric Workspace** | the wiki of how every tool works |
| **Project Observatory** | a PassionCode.ai product; Fabric-compatible, works without Fabric |

Never "PassionCode app", never "Passion Code".

## 3. How a change lands

- Work in a worktree from `origin/main` on your own branch (`<who>/<topic>`). A checkout can be
  shared by several people or agents: never switch, reset or stash someone else's work.
- Run the repository's gate (named in its `AGENTS.md`) and read its exit code before you push. A
  check that did not run is not a green check.
- Never force-push `main`, never move a released tag. A mistake gets a new commit or a new tag.
- Documentation changes in the same commit as the code it describes.
- No secrets, tokens or machine paths in any commit, issue or log.

## 4. Mark the code you write

A feature, a module or a special condition is fenced, and the fence points at its documentation,
so the next reader — person or agent — lands on the documented truth and can check the code
against it:

```ts
// #region registry-scan — docs: docs/design.md#registry
…
// #endregion registry-scan
```

Any comment leader works (`//`, `#`, `--`, `/*`, `<!--`). The reference is repository-root
relative and must resolve; repositories that ship the check (`check-regions`) fail a region that
is unclosed or whose reference does not open.

## 5. Recommended tools

A shared base keeps the process and the documentation format the same across repositories and
people, which removes a whole class of mistakes. Adapt it to your own style; keep the base.

- **[sshlg-skills](https://github.com/ssheleg/sshlg-skills)** — `task-pipeline` (a change moves
  through brief → design → spec → plan → build → tests → docs), `agent-sync` (leases on shared
  files and race-free ids), and the rest of the family. Install: `npx --yes sshlg-skills@latest update`.
- **[@passioncode-ai/passioncode](https://www.npmjs.com/package/@passioncode-ai/passioncode)** —
  every PassionCode.ai skill for every agent on the machine, including `working-in-passioncode`
  (the organization's rules as a skill). Install: `npx @passioncode-ai/passioncode@latest update`.

## 6. Security

Report a vulnerability privately to contact@passioncode.ai, not in a public issue.
