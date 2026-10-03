# Release signing — plan

Each task is TDD where code exists: a failing test or a planted defect first, then the change,
then a review. Repositories are changed from worktrees on `origin/main`. A product's shared
checkout often holds another session's work.

## M0 — the skeleton and the pilot (`.github`, `project-observatory-dashboard`)

- **T0.1 Team `release-approvers`** with sshlg, khurss and svlab93.
  Implements: R3
- **T0.2 `scripts/setup-release-env.py`** creates or updates `release` in a repository:
  - reviewers = the team;
  - `prevent_self_review`, `can_admins_bypass: false`;
  - the custom tag policy `v*`;
  - the variables.

  Idempotent, dry run by default. Tested against a fake `gh`.
  Implements: R2
- **T0.3 `scripts/sync-release-secrets.py`** reads a manifest of repository → secret names and
  sets each from the environment over stdin with `gh secret set --env release`. It prints names
  and fingerprints. Tested with a fake `gh` that records stdin and argv: no value appears in argv
  or output.
  Implements: R6
- **T0.4 `actions/apple-signing` and `actions/apple-signing/cleanup`.** The temporary keychain, the
  imports, the partition list, the identity output. Bats-style shell tests with faked `security`.
  Implements: R1
- **T0.5 `actions/notarize`.** It generalizes `notarize.sh` to `.app`, `.dmg`, `.zip` and `.pkg`,
  using only the ASC key. Its tests are Observatory's fakes, extended per type.
  Implements: R1, R5
- **T0.6 `actions/sign-sums` and `.github/workflows/release-publish.yml`.** Attestations,
  `SHA256SUMS`, `.asc`, a draft and then the published release. A self-test workflow in `.github`
  releases a fixture through them on a test tag. `actionlint` runs on every workflow.
  Implements: R1, R12
- **T0.7 Observatory `release.yml`**, using the actions. Its rehearsal is a `workflow_dispatch` on
  the tag `v0.13.0` with `publish=false`: it signs, notarizes, attests and stops. AGENTS.md
  Releasing names the CI path.
  Implements: R8 (Observatory), R14 (Observatory)

## M1 — keys

- **T1.1 The CI Developer ID Application certificate.** Generate the key with openssl, then issue
  it through the ASC API (`scripts/asc.py create-cert`); if the API refuses, use the portal in
  Safari. Package it as a `.p12` and store it in the vault slot `passioncode-release/prod`.
  Implements: R4
- **T1.2 The organization GPG release key**, ed25519, sign-only, 3-year expiry. The private key
  goes to the vault; the public key is published in `.github/release-signing/` and on the website.
  Implements: R12
- **T1.3 Fabric VR's keystore**, RSA 4096, 30 years: the vault slot `fabric-vr/prod`, with its
  fingerprint in the repository's docs.
  Implements: R11
- **T1.4 The MAS certificates** (Mac App Distribution, Mac Installer Distribution), the Inbox
  provisioning profile and the App Store Connect app record, through the ASC API or Safari.
  Implements: R9
- **T1.5 Sync** into every product's `release` environment (T0.3).
  Implements: R4, R6

## M2 — the other macOS products

- **T2.1 Fabric Dashboards `release.yml`.** `dist-mac.mjs` accepts the ASC key and runs `spctl`
  on the app as well.
  Implements: R5, R8, R14
- **T2.2 Fabric Inbox `release.yml`**, for the DMG.
  Implements: R5, R8, R14
- **T2.3 Fabric `release.yml`.** The team id comes from `APPLE_TEAM_ID` in
  `electron-builder.release.yml`.
  Implements: R7, R8, R14
- **T2.4 Switchboard `release.yml`** for macOS. `build_macos.py` accepts the ASC key, and the
  literal team default leaves `keychain_macos.rs`.
  Implements: R5, R7, R8, R14

## M3 — the Mac App Store

- **T3.1 The Inbox MAS job**: `mas-package.mjs` with the CI identities and profile, then an upload
  through `xcrun altool --upload-package` with the API key.
  Implements: R9

## M4 — Android

- **T4.1 Fabric VR's `release.yml` job**: decode the keystore, `assembleRelease`, then
  `apksigner verify --print-certs` and an attestation.
  Implements: R11

## M5 — Windows

- **T5.1 Switchboard's `build-windows` job** on `windows-latest`: the native build, then
  `azure/login` (OIDC) and `artifact-signing-action@v2` behind `AZURE_SIGNING_ENABLED`. Until the
  Azure account exists the receipt says `NOT_SIGNED`; the human steps for the account are written
  down.
  Implements: R10

## M6 — the rule

- **T6.1 The "Release signing" section** in `fabric-workspace/knowledge/rules.md`; the launcher's
  `working-in-passioncode` skill mirrors it; `.github` AGENTS.md states the new role; org-index
  `repositories.json` gets the `.github` row and a note in `docs/CI-BATCHING.md`.
  Implements: R13

## The REQ set comparison

The `Implements:` lines above, taken together, cover R1–R14, the same set as the brief's
requirements.
