# Contributing to PassionCode.ai repositories

This is the default contribution guide for every repository of the `passioncode-ai`
organization. A repository with its own `CONTRIBUTING.md` adds to it; where the two differ, the
repository's own file wins. It is written for people and for coding agents alike — **an agent
reads the knowledge base, the repository's `AGENTS.md` and this file before its first edit, in
every repository, every time.**

## 1. Read first, in this order

1. **The knowledge base**: `fabric-workspace/knowledge/` in your clone (org-index
   `scripts/clone_all.sh` makes it), or
   [knowledge/README.md](https://github.com/passioncode-ai/fabric-workspace/blob/main/knowledge/README.md)
   on GitHub (private: organization members). At least its vision, principles and how to work.
2. **The repository's `AGENTS.md`** (its `CLAUDE.md` imports it): what the repository is, the exact
   commands that test a change, and its local rules.
3. **This file**: what every repository shares.

The organization's working rules — branches, CI, coordination, secrets, handoffs — are
[knowledge/rules.md](https://github.com/passioncode-ai/fabric-workspace/blob/main/knowledge/rules.md),
and the files every repository carries are the
[repository standard](https://github.com/passioncode-ai/fabric-workspace/blob/main/knowledge/repository-standard.md).
Outside contributors, who cannot open the knowledge base, work from the repository's own
documents and this file.

## 2. After work

In the same run, before you call the work done:

1. update the repository's own docs in the change that changes the behaviour;
2. if a fact that crosses repositories changed — a product, a version, a plan row, a principle,
   a rule — update the knowledge base page that owns it;
3. land both, then publish: `node scripts/workspace.mjs sync` from a Fabric checkout, or leave it
   to the scheduled sync ([how to work → publishing](https://github.com/passioncode-ai/fabric-workspace/blob/main/knowledge/how-to-work.md#publishing)).

Leave a tracked handoff with the exact next task, not a chat message.

## Shared backlog

Each repository declares canonical local task sources in `docs/backlog-sources.json`.
Read the [backlog contract](https://github.com/passioncode-ai/fabric-workspace/blob/main/knowledge/backlog.md)
and the repository's declared source before starting work. Update task status in that owner
under its coordination lease, retain stable IDs and closure receipts, and add new sources to
the manifest. Cross-repository tasks have one owner; dependent repositories link to that row.
The [workspace backlog](https://wiki.passioncode.ai/backlog) combines these sources with their
vision goals and source commits. It is derived, never a second editable task register.
After landing, publish through Fabric's workspace sync and verify the recorded source commit.

## 3. Names

| Name | What it is |
|---|---|
| **PassionCode.ai** (short: PassionCode) | the organization; its toolkit is for AI-native teams |
| **Fabric** | the product: the CEO AI agent — the desktop app and its engine |
| **Fabric Inbox**, **Fabric Dashboards**, **Fabric Switchboard**, **Fabric VR** | Fabric's tools; each also works on its own. Use the full name before the short one |
| **Fabric Agent Contract**, **Fabric Agent Adapter** | what makes any agent Fabric-compatible; protocol ids stay lowercase (`fabric-service/0.1`) |
| **Fabric Workspace** | the wiki of how every tool works, and the knowledge base |
| **Project Observatory** | a PassionCode.ai product; Fabric-compatible, works without Fabric |
| **Okolos** | a PassionCode.ai product: browser security for the age of AI agents |

Never "PassionCode app", never "Passion Code". The knowledge base
[principles §2](https://github.com/passioncode-ai/fabric-workspace/blob/main/knowledge/principles.md#2-names)
owns this list; org-index `scripts/check_names.py` checks it.

## 4. How a change lands

- Work in a worktree from `origin/main` on your own branch (`<who>/<topic>`). A checkout can be
  shared by several people or agents: never switch, reset or stash someone else's work.
- Run the repository's gate (named in its `AGENTS.md`) and read its exit code before you push. A
  check that did not run is not a green check.
- Land by the repository's rule: a pull request, or a fast-forward after its local gate passes
  ([rules §2](https://github.com/passioncode-ai/fabric-workspace/blob/main/knowledge/rules.md#2-branches-commits-landing)).
- Never force-push `main`, never move a released tag. A mistake gets a new commit or a new tag.
- Documentation changes in the same commit as the code it describes.
- No secrets, tokens or machine paths in any commit, issue or log.

## 5. Mark the code you write

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

## 6. License and your contribution

Every PassionCode.ai repository is licensed under the
[GNU AGPL-3.0](https://www.gnu.org/licenses/agpl-3.0.html) (its `LICENSE`), or under a commercial
license from PassionCode.ai for use that does not meet the AGPL's terms (its
`COMMERCIAL-LICENSE.md`) — contact@passioncode.ai. SPDX:
`AGPL-3.0-only OR LicenseRef-PassionCode-Commercial`. A version released earlier keeps the license
it was released under, and third-party code keeps its own.

A contribution is accepted under the repository's `CLA.md`: tick the box in the pull request
template — the repository's own, or the organization's default in
[`.github`](https://github.com/passioncode-ai/.github/blob/main/.github/pull_request_template.md).
The CLA lets PassionCode.ai offer your contribution under both licenses; without it a pull request
is not merged. What each license means for users and contributors:
[knowledge/licensing.md](https://github.com/passioncode-ai/fabric-workspace/blob/main/knowledge/licensing.md).

## 7. Recommended tools

A shared base keeps the process and the documentation format the same across repositories and
people, which removes a whole class of mistakes. Adapt it to your own style; keep the base.

- **[sshlg-skills](https://github.com/ssheleg/sshlg-skills)** — `task-pipeline` (a change moves
  through brief → design → spec → plan → build → tests → docs), `agent-sync` (leases on shared
  files and race-free ids), and the rest of the family. Install: `npx --yes sshlg-skills@latest update`.
- **[@passioncode-ai/passioncode](https://www.npmjs.com/package/@passioncode-ai/passioncode)** —
  every PassionCode.ai skill for every agent on the machine, including `working-in-passioncode`
  (the organization's rules as a skill). Install: `npx @passioncode-ai/passioncode@latest update`.

## 8. Security

Report a vulnerability privately to contact@passioncode.ai, not in a public issue.
