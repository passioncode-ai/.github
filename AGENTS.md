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
  available; Fabric and Fabric Inbox, whose source is private, are never called open source or
  AGPL; MIT and PolyForm name only released versions.
- `CONTRIBUTING.md` is inherited by every repository: it links to the knowledge base for anything
  the knowledge base owns (rules, standard, names, licensing) instead of copying it. A change to
  this repository's role updates its row in org-index `repositories.json` in the same change.

## After work

In the same run: update this repository's docs with the change; if a cross-repository fact changed
(a product, a version, a plan row, a principle), update the page in `fabric-workspace/knowledge/`
that owns it; land both; publish (`node scripts/workspace.mjs sync` from a Fabric checkout) or
leave it to the scheduled sync. Leave a handoff with the exact next task.
