# .github — working in this repository

## Role

This is the public GitHub profile of the `passioncode-ai` organisation. GitHub renders
[profile/README.md](profile/README.md) on the organisation page, and the brand assets it uses are
in [assets/](assets/) (`README.md`). It lists only public-safe products.

## Build and test

There is no build, test or CI. The checks the handoffs record for a profile change are:

```sh
git diff --check
```

After that, confirm that every link target in `profile/README.md` resolves. After publication,
confirm anonymously that `main` serves the profile ([docs/HANDOFF.md](docs/HANDOFF.md)).

## Where things live

- `profile/README.md` is the rendered organisation profile.
- `assets/` holds the family mark and the social card.
- [docs/HANDOFF.md](docs/HANDOFF.md) and [docs/INBOX_HANDOFF.md](docs/INBOX_HANDOFF.md) record
  profile changes, their evidence and the next task.

## Rules in this repository

- This repository and the profile are public. Nothing private may be added: no private source, no
  credentials, no machine files.
- Change public status only on verified release or acceptance evidence. Never advertise a release
  or download that does not exist (`docs/HANDOFF.md`, `docs/INBOX_HANDOFF.md`).
- The website owns the public download redirects and installation notes. The profile links to
  them (`docs/HANDOFF.md`).

## Organisation

This repository is one of the `passioncode-ai` repositories. **The org map, the shared
rules and onboarding live in [passioncode-ai/org-index](https://github.com/passioncode-ai/org-index)**
(private; readable by every org member):

- [README](https://github.com/passioncode-ai/org-index#repositories): which repository owns what, and how they connect
- [RULES.md](https://github.com/passioncode-ai/org-index/blob/main/RULES.md): branches, commits, CI, leases, secrets, handoffs
- [ONBOARDING.md](https://github.com/passioncode-ai/org-index/blob/main/ONBOARDING.md): setting up a new contributor's machine

Where this file is stricter than RULES.md, this file wins. A change to this repository's
role, dependencies or test command updates its row in `org-index/repositories.json` in the same change.
