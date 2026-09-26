# Public toolkit profile handoff · 2026-09-26

Objective: align the GitHub organization profile with the operator's PassionCode toolkit positioning and first downloadable Switchboard beta. Source: operator request 2026-09-26, Fabric ADR-0057 for CEO name and Switchboard implementation `9e20a49ad7ef917068c266eff4283180209965dc` for beta capabilities/design. Website owns the public OS download redirects and installation notes.

Completed source: [profile](../profile/README.md), product map, macOS/Windows links, MIT source, Fabric development status and shared design-system pointer. The profile preserves the family mark and does not publish private Fabric code.

Publication prerequisite: root launch task must verify anonymous source/download access before integration to main. Final public website delivery index lives at [website HANDOFF](https://github.com/passioncode-ai/passioncode-ai.github.io/blob/main/docs/HANDOFF.md). Validate link targets and no obsolete single-product/kernel-only positioning. No executable behavior changed; no app tests required here.

Local-only: `.DS_Store`, credentials and unrelated machine files remain untracked. Next task: verify the public product path and keep the profile consistent when the next product becomes available.

## Publication receipt — 2026-09-26

Profile source `248df9b197056faea573bbd1c7ecf47e03126f7f` pushed to `main`, remote SHA verified. Fresh anonymous HTTPS checkout with credentials/prompts disabled resolved to the same SHA and identical profile bytes. Public website source `527b5ba41c4aad77512572ec5117beb27ba7fb08` is deployed; both OS download endpoints verified. Switchboard repository is public; `v0.3.1-beta.1` is a published prerelease from binary source `9e20a49ad7ef917068c266eff4283180209965dc`. Next: update public status only from new verified release/acceptance evidence. No full CI was dispatched for this documentation change. Unrelated local .DS_Store is preserved.
