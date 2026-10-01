# Working in .github

## Read first

1. The PassionCode.ai knowledge base — `fabric-workspace/knowledge/` in your clone (org-index
   `scripts/clone_all.sh` makes it) or https://wiki.passioncode.ai/knowledge — at least its
   [README](https://github.com/passioncode-ai/fabric-workspace/blob/main/knowledge/README.md),
   vision, principles and how-to-work.
2. This file, then the organization's [CONTRIBUTING.md](CONTRIBUTING.md), which lives here.

## What this repository is

The `.github` repository of the `passioncode-ai` organization: the public organization profile
([profile/README.md](profile/README.md), rendered on https://github.com/passioncode-ai), its brand
assets ([assets/](assets/)), and the defaults GitHub applies to every repository without its own —
[CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md) and the
[pull request template](.github/pull_request_template.md). It lists only public-safe products.

## Commands

| What | Command |
|---|---|
| Install | none — clone it |
| Test (the gate) | `git diff --check`, then confirm every link target in the changed files resolves |
| Build | none; GitHub renders `main` |
| MCP (register + proving call) | none: documents only, no product and no MCP |

After merge, confirm anonymously that https://github.com/passioncode-ai serves the profile
([docs/HANDOFF.md](docs/HANDOFF.md)).

## Local rules

- This repository and the profile are public. Nothing private may be added: no private source, no
  credentials, no machine files, no private repository names, none of the operator's own agents.
- Change public status only on verified release or acceptance evidence. Never advertise a release
  or download that does not exist (`docs/HANDOFF.md`, `docs/INBOX_HANDOFF.md`).
- The website owns the public product facts, download redirects and installation notes
  (passioncode-ai.github.io `docs/brand/facts.md`). The profile links to them and repeats only
  what those facts say.
- License wording follows Fabric ADR-0092 and the knowledge base
  [licensing](https://github.com/passioncode-ai/fabric-workspace/blob/main/knowledge/licensing.md):
  a product with public source is "open source under AGPL-3.0" with a commercial license
  available — every product the profile lists, Fabric and Fabric Inbox included since their
  repositories became public on 2026-09-30; a private repository (Fabric Workspace, org-index) is
  never linked from the profile; MIT and PolyForm name only released versions.
- `CONTRIBUTING.md` is inherited by every repository: it links to the knowledge base for anything
  the knowledge base owns (rules, standard, names, licensing) instead of copying it. A change to
  this repository's role updates its row in org-index `repositories.json` in the same change.
- **Shared registers are edited under a lease.** [docs/AGENT_SYNC.md](docs/AGENT_SYNC.md)
  (generated from `.claude/agent-sync.json` by `agent_sync.py setup`; never edited by hand) lists
  the guarded files and the gate. Run `agent_sync.py acquire <file>` before editing one and
  `agent_sync.py release <file>` after, on every path including failure. The lease is a ref under
  `refs/agent-sync/leases/` on `origin`, so another contributor's agent sees it
  (`git ls-remote origin 'refs/agent-sync/leases/*'`); the record plane is local (`fs`), and
  `.agent-sync/` is git-ignored. No register here carries a "Next free ID" line, so nothing is
  reserved yet; a register that gains one is declared under `idRegisters` and taken with
  `agent_sync.py reserve <REG>`.

## Organisation

This repository is one of the `passioncode-ai` repositories. The org map —
which repository owns what and how they connect — is
[passioncode-ai/org-index](https://github.com/passioncode-ai/org-index) (private; readable by every
org member), with [ONBOARDING.md](https://github.com/passioncode-ai/org-index/blob/main/ONBOARDING.md)
for a new contributor's machine. The working rules are the knowledge base's
[rules.md](https://github.com/passioncode-ai/fabric-workspace/blob/main/knowledge/rules.md).

## Shared backlog

[docs/backlog-sources.json](docs/backlog-sources.json) declares this repository's canonical
local task sources and their vision goals. The [common backlog contract](https://github.com/passioncode-ai/fabric-workspace/blob/main/knowledge/backlog.md)
owns aggregation; [the workspace backlog](https://wiki.passioncode.ai/backlog) is a derived view.
Edit a task only in its canonical source under an agent-sync lease, retain stable IDs and
closure receipts, and declare any new source in the manifest. Do not edit generated task
status in the workspace or copy another repository's task into a second editable row.
Land the source change, then run `node scripts/workspace.mjs sync` from a Fabric checkout
(or use the scheduled sync); check the published source commit before calling it current.

## After work

In the same run: update this repository's docs with the change; if a cross-repository fact changed
(a product, a version, a plan row, a principle), update the page in `fabric-workspace/knowledge/`
that owns it; land both; publish (`node scripts/workspace.mjs sync` from a Fabric checkout) or
leave it to the scheduled sync. Leave a handoff with the exact next task.
