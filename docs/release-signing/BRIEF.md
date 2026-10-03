# Release signing for every PassionCode.ai product — brief

Run: task-pipeline, 2026-10-03. Owner of this record: `passioncode-ai/.github`.

## The request

Sign every PassionCode.ai product with the key the organization distributes. Do it so that
several people can work on one product and an agent working in any shared repository does it
correctly. Write the rule where every agent reads it.

## Decisions (operator, 2026-10-03)

| # | Decision | Answer |
|---|---|---|
| D1 | Where signing runs | Only in GitHub Actions, in a protected `release` environment that a person approves |
| D2 | Apple account | The operator's Developer ID team `KJ35UYYL22` |
| D3 | Home of the shared mechanism | `passioncode-ai/.github`: reusable workflows and scripts, versioned by tag (`@v1`) |
| D4 | CI certificate | A new Developer ID Application certificate for CI only. Its key is generated outside any Keychain. The operator's local certificate stays untouched and is revoked separately |
| D5 | Who approves | GitHub team `release-approvers`: sshlg, khurss, svlab93. The author of a release cannot approve it (`prevent_self_review`) |
| D6 | Windows | Azure Artifact Signing, opened on an EU company the operator names, through OIDC (no stored secret) |
| D7 | Linux, and every artifact | A Sigstore build-provenance attestation on every release artifact on every platform, plus a detached GPG signature on `SHA256SUMS` with an organization key |
| D8 | Android/Quest | One release keystore per app, starting with Fabric VR. RSA 4096, valid 30 years. The original lives in the Observatory vault (encrypted off-disk backup); a copy goes to the `release` environment |
| D9 | Mac App Store | CI builds, signs and uploads Fabric Inbox to App Store Connect after approval. Submitting for review stays a person's click |

Defaults this run took without a question (the autonomy sweep):
- **Source of truth for credentials.** The Observatory vault. A sync tool writes each value into a
  repository's `release` environment over stdin and never prints it.
- **One set of names for every product.** `ASC_KEY_ID`, `ASC_ISSUER_ID`, `ASC_API_KEY_P8_B64`,
  `APPLE_TEAM_ID`, `APPLE_DEVELOPER_ID_P12_B64` / `_PASSWORD`, `APPLE_DISTRIBUTION_P12_B64`,
  `APPLE_INSTALLER_P12_B64`, `MAS_PROVISION_PROFILE_B64`, `ANDROID_KEYSTORE_B64`,
  `ANDROID_KEYSTORE_PASSWORD`, `ANDROID_KEY_ALIAS`, `ANDROID_KEY_PASSWORD`,
  `RELEASE_GPG_PRIVATE_KEY_B64`, `RELEASE_GPG_PASSPHRASE`. Azure takes `AZURE_*` variables, not
  secrets.
- **Release workflows run on a `v*` tag.** They are not test suites, so the nightly CI batching
  (org-index `docs/CI-BATCHING.md`) does not delay them; the rules say so in words.
- **Local signing stays possible for debugging.** A locally signed artifact is never published.
- **Cut-over order.** Observatory (the pilot), Fabric Dashboards, Fabric Inbox, Fabric,
  Switchboard, Fabric VR.
- **The operator's personal agents are not part of this system**, per the operator's standing
  rule.

## Source ledger

| Source | What it says about this task |
|---|---|
| `fabric-workspace/knowledge/rules.md` §3, §6 | Hosted CI runs nightly, with no per-push triggers. No CI result is not a green result. Secrets are never in git, argv or logs, and never copied between machines. Nothing about signing |
| Inventory of the product repositories, 2026-10-03 (`origin/main` of each) | Every macOS app is signed by hand on the operator's Mac with Developer ID `KJ35UYYL22`. There are four notary conventions: the vault slot `apple-publisher-kj35uyyl22` (Fabric), the Keychain profiles `fabric-notary` (Inbox, Dashboards) and `switchboard-notary`, and `OBSERVATORY_NOTARY_*`. The team id is hardcoded in `fabric/apps/desktop/electron-builder.release.yml:13` and `fabric-switchboard/crates/switchboard-core/src/keychain_macos.rs:58-60`. No workflow references a secret. Windows is `NOT_SIGNED`; Fabric VR has no release keystore; MAS has no identities or profile |
| `.github` repository | Profile, CONTRIBUTING, CLA and a PR template, with no `.github/workflows`. Its AGENTS.md calls it "documents only", so its role changes in this run |
| `docs/evidence/retro.md` | None in the repositories this run touches |
| Code graph | Not built for these repositories; the seams here are workflow YAML, not code |

## Requirements

Frozen: adding a row is free, removing one needs the operator.

| REQ | Requirement | Verified by |
|---|---|---|
| R1 | `.github` publishes reusable release workflows at `@v1`: sign and notarize a macOS app (Developer ID, hardened runtime, timestamp, staple, `spctl`), attest, `SHA256SUMS` plus GPG signature, GitHub release | A fixture app released through them in a test workflow; `actionlint` clean |
| R2 | Each product repository has a `release` environment: deployment only from `v*` tags, required reviewers `release-approvers`, `prevent_self_review` | `gh api repos/<r>/environments/release` per repository |
| R3 | Team `release-approvers` = sshlg, khurss, svlab93 | `gh api orgs/passioncode-ai/teams/release-approvers/members` |
| R4 | A CI-only Developer ID Application certificate for `KJ35UYYL22`. Its key is generated off-Keychain and stored in the vault, then synced into the environments | The CI artifact's `codesign -dv` authority; the certificate serial differs from the local one |
| R5 | One notary convention, the App Store Connect API key (`ASC_*`), in every product's release path | `git grep` finds no `fabric-notary`, `switchboard-notary` or `OBSERVATORY_NOTARY_PROFILE` on the CI path |
| R6 | A vault → `release` environment secret sync tool: stdin only, idempotent, dry run by default | Tests with a fake `gh`; a run that prints names, never values |
| R7 | No team id hardcoded in product code or config: it comes from `APPLE_TEAM_ID` / the build environment | `git grep KJ35UYYL22` in product sources finds only docs and receipts |
| R8 | Observatory, Fabric Dashboards, Fabric Inbox, Fabric and Switchboard each release macOS through the shared workflow. One real tag per product gives a notarized artifact accepted by `spctl` | The release receipt per product |
| R9 | Fabric Inbox for the Mac App Store: CI-only Apple Distribution and Mac Installer Distribution certificates, a provisioning profile, the app record; CI uploads the signed `.pkg` after approval | The App Store Connect build list shows the uploaded build |
| R10 | Switchboard for Windows: Azure Artifact Signing through OIDC in the Windows release job; until the account exists, the job records `NOT_SIGNED` and says why | `Get-AuthenticodeSignature` reports `Valid` once enabled; until then the receipt line |
| R11 | Fabric VR: a release keystore per D8. CI's `assembleRelease` is signed, and the fingerprint is published in the repository's docs | `apksigner verify --print-certs` on the CI artifact |
| R12 | Every release artifact carries a Sigstore attestation; `SHA256SUMS` carries a detached GPG signature from the organization key, whose public key is published | `gh attestation verify`; `gpg --verify SHA256SUMS.asc` |
| R13 | The rule is written where agents read it: `knowledge/rules.md` gets a "Release signing" section, the launcher's `working-in-passioncode` skill mirrors it, `.github` AGENTS.md states its new role, and the org-index row is updated | The text at those paths |
| R14 | Each product's docs describe the CI path; the by-hand release instructions are replaced, and local signing is marked as debug only | The text at the named paths |

## Carry-over

| Item | Why it is not in this run | Home |
|---|---|---|
| Publishing Okolos to the Chrome Web Store and Firefox Add-ons (the stores sign on upload) | Publication, not signing; the extension is pre-alpha | Okolos backlog |
| Moving to an Apple organization account (the certificate would show a company name) | The operator chose the personal team (D2) | Operator decision, later |
| The EU entity for Azure, its subscription and identity validation | A person's documents and payment | Human steps |
