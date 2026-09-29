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
