# Profile handoff · final check: every public product, current releases · 2026-10-01

Objective: the profile follows ADR-0090 and lists every public product with a working link, a
one-line description and its current release; the defaults are right for AGPL + CLA.

- `profile/README.md`: intro in ADR-0090 terms (organization → Fabric, the CEO AI agent → its
  tools → compatibility layer → Project Observatory and Okolos beside Fabric); Fabric and Fabric
  Inbox public since 2026-09-30, so "Fabric's source is private" and "Inbox: private development,
  no public download" were false — Inbox now has its 0.8.2 download section; versions
  Observatory 0.8.1 → 0.9.1, Dashboards 0.1.0 → 0.3.0; the toolkit table lists all eleven public
  product repositories plus the site (licence on `main` read for each: AGPL); the licence-history
  sentence names the PolyForm releases too.
- `CONTRIBUTING.md`: Okolos added to the names table. License section (AGPL or commercial, CLA,
  released versions keep theirs) checked and unchanged. `SECURITY.md` unchanged.
- `AGENTS.md`: the licence rule no longer says Fabric and Inbox are private.
- Checks: `git diff --check` 0; org-index `check_format.py`, `check_names.py`, `check_private.py`
  and `gitleaks detect --no-git` (see the PR); every public link 200/302 anonymously.
- Next task: when a product publishes a new release, update its row here in the same pass as the
  website's `docs/brand/facts.md`.

---

# Profile handoff · AGPL-3.0 (ADR-0092), the knowledge base first (ADR-0093), the repository standard · 2026-09-30

Objective: the organization's defaults and profile say what the operator decided on 2026-09-30,
and this repository carries the repository standard (fabric-workspace `knowledge/repository-standard.md`).

- `CONTRIBUTING.md` (inherited by every repository without its own): read first — 1. the
  knowledge base, 2. the repository's `AGENTS.md`, 3. this file; a new "After work" section
  (update the knowledge base page that owns a changed cross-repository fact, land, publish); rules
  and the standard now link `knowledge/rules.md` and `knowledge/repository-standard.md` instead of
  org-index `RULES.md`; names link `knowledge/principles.md §2`; a license section per
  `knowledge/licensing.md` (AGPL-3.0 or commercial, CLA). The license section says "licensed
  under", not "open source", because this file is read in private repositories too (CO-KB-01).
- `.github/pull_request_template.md` (new): the organization's default template with the CLA box
  the rules require. Not verified yet in a repository without its own template.
- `profile/README.md`: the license paragraph — open source under AGPL-3.0, a commercial license
  from contact@passioncode.ai, released versions keep MIT or PolyForm; table cells
  "source-available" → "AGPL-3.0". Also corrected against the website's facts: Switchboard's macOS
  build is notarized (0.4.0-beta.1 receipt), "Fabric Inbox" in its heading, and Fabric Agent Adapter
  listed as public (it is, per org-index `repositories.json`), Fabric Agent Contract as private.
  Copy through super-ux `copywriting` against the website's brand pack.
- Standard: `LICENSE`, `COMMERCIAL-LICENSE.md`, `CLA.md` from the knowledge base templates,
  `SECURITY.md` (also the organization default), `README.md` quick start and License,
  `AGENTS.md` in the template shape.
- Checks: `git diff --check` exit 0; org-index `check_format.py --offline` 8 → 0 findings,
  `check_names.py --offline` 0; link targets checked (see the PR).
- Landed: fast-forward to `main` (`1fb1013`, PR #4) after the four public products' `main` carried
  the AGPL `LICENSE`. After merge: org-index `check_format.py` (online) 0 findings for `.github`;
  https://github.com/passioncode-ai shows "open source under AGPL-3.0" anonymously; the PR template
  link answers 200.
- Next task: keep the version cells (Observatory 0.8.1, Fabric Dashboards 0.1.0) in step with the
  website's facts when the site's release sync lands; confirm in a repository without its own
  template that a new pull request opens with the CLA box.
---

# Profile handoff · names (ADR-0090) and the default contribution guide · 2026-09-29

Objective: the organisation's names and the read-first contribution rule (Fabric
[ADR-0090](https://github.com/passioncode-ai/fabric) and the agent-registry run, module AR-0).

- `profile/README.md`: the intro now names Fabric first as the product (the CEO AI agent, early
  preview for macOS) and its tools by their full names — Fabric Switchboard, Fabric Dashboards —
  each working on its own; Project Observatory is described alongside them as speaking Fabric's
  protocol and running without it. Taglines, licence lines and every other section unchanged.
- `CONTRIBUTING.md` (new): GitHub's default contribution guide for every repository of the
  organisation without its own — read the repository's `AGENTS.md` first; the names; how a change
  lands; code region markers; the recommended shared tools (sshlg-skills, the
  `@passioncode-ai/passioncode` launcher); private security reporting.
- Checks: `git diff --check` clean; public link targets answer (npmjs.com blocks bots with 403;
  org-index answers 404 anonymously because it is private, as the text says).
- Next: after merge, confirm anonymously that a repository without its own guide shows this one
  in its "Contributing" link.

# Profile handoff · source-available wording, Observatory and Fabric Dashboards · 2026-09-29

Objective: apply the operator's 2026-09-29 decisions to the organisation profile. Switchboard,
Project Observatory and Fabric Dashboards are described as source-available (PolyForm
Noncommercial or Internal Use, commercial license on request); the MIT-published releases are
named and stay MIT; the tagline reads "A toolkit for AI-native teams."; Project Observatory
(release 0.8.1) and Fabric Dashboards (release 0.1.0) have their own sections and table rows
with public repository links; the Inbox text now matches the website's wording; the design
system line matches the website (dark palette, opt-in light, gold accents, four product marks);
the closing slogan, which appeared nowhere on the website, is removed — the category line
"From vibe coding to passion coding." remains at the top.

Facts come from the website's [brand facts](https://github.com/passioncode-ai/passioncode-ai.github.io/blob/main/docs/brand/facts.md),
updated in the same run (site commit `308a440`).

Checks: `git diff --check` exit 0; every link in `profile/README.md` answered HTTP 200 to an
anonymous `curl -I -L` (16 of 16); no "open source", "open-source" or "AI-native work" left in
the profile. Next task: keep the version cells in step with the website facts on the next
release of any listed product.

---

# Public toolkit profile handoff · 2026-09-26

Objective: align the GitHub organization profile with the operator's PassionCode toolkit positioning and first downloadable Switchboard beta. Source: operator request 2026-09-26, Fabric ADR-0057 for CEO name and Switchboard implementation `9e20a49ad7ef917068c266eff4283180209965dc` for beta capabilities/design. Website owns the public OS download redirects and installation notes.

Completed source: [profile](../profile/README.md), product map, macOS/Windows links, MIT source, Fabric development status and shared design-system pointer. The profile preserves the family mark and does not publish private Fabric code.

Publication prerequisite: root launch task must verify anonymous source/download access before integration to main. Final public website delivery index lives at [website HANDOFF](https://github.com/passioncode-ai/passioncode-ai.github.io/blob/main/docs/HANDOFF.md). Validate link targets and no obsolete single-product/kernel-only positioning. No executable behavior changed; no app tests required here.

Local-only: `.DS_Store`, credentials and unrelated machine files remain untracked. Next task: verify the public product path and keep the profile consistent when the next product becomes available.

## Publication receipt — 2026-09-26

Profile source `248df9b197056faea573bbd1c7ecf47e03126f7f` pushed to `main`, remote SHA verified. Fresh anonymous HTTPS checkout with credentials/prompts disabled resolved to the same SHA and identical profile bytes. Public website source `527b5ba41c4aad77512572ec5117beb27ba7fb08` is deployed; both OS download endpoints verified. Switchboard repository is public; `v0.3.1-beta.1` is a published prerelease from binary source `9e20a49ad7ef917068c266eff4283180209965dc`. Next: update public status only from new verified release/acceptance evidence. No full CI was dispatched for this documentation change. Unrelated local .DS_Store is preserved.
