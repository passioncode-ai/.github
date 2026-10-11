# Release signing — design

The decisions it implements are in [BRIEF.md](BRIEF.md) (D1–D9). Contracts were checked on
2026-10-03 against GitHub's docs (reusable workflows, environments, deployment policies,
attestations), Azure's `artifact-signing-action` and a read-only App Store Connect API call.

## Shape

```
product repository (e.g. fabric-dashboards)
  .github/workflows/release.yml          on: push tags v*  (+ workflow_dispatch rehearsal, publish=false)
    job guard         runs-on ubuntu-latest  uses actions/release-guard@v1   ← approval happens here
    job build-macos   needs guard            environment: release
      uses passioncode-ai/.github/actions/apple-signing@v1       temp keychain + CI Developer ID
      run  <the product's own build, told the identity by env>
      uses passioncode-ai/.github/actions/notarize@v1            notarytool + staple + spctl
    job build-windows  runs-on windows-latest environment: release  (Switchboard; Azure OIDC)
    job build-android  runs-on ubuntu-latest  environment: release  (Fabric VR; keystore)
    job publish        uses passioncode-ai/.github/.github/workflows/release-publish.yml@v1
                       attest every file, SHA256SUMS + GPG, GitHub release (draft until all green)
```

- **The build stays the product's own.** electron-builder, `@electron/packager` with osx-sign,
  Tauri and `swift build` each sign differently. The shared parts are what is the same everywhere:
  the keychain, notarization, attestation, checksums and publishing. Each is a composite action
  pinned at `@v1`.
- **The keys sit in the `environment: release` on a product's signing jobs.** A job in a
  reusable workflow that names an environment gets the caller repository's environment, with its
  secrets and protection rules (GitHub docs, "Reuse workflows"). So each product has its own
  keys, while the code lives in one place.
- **Approval by checks (operator, 2026-10-11; supersedes the click-per-gate rule below).** Two
  clicks per release left finished, signed builds waiting for hours because nobody saw the request.
  Now the product's `guard` job runs `actions/release-guard@v1` and every job that names
  `environment: release` needs it. The guard passes a tag only when `main` contains the tagged
  commit and each CI workflow the product lists concluded `success` on that exact commit; with no
  run it starts one on the tag (`workflow_dispatch`) and waits (default 60 min), and anything else
  refuses with the reason and the run's link. The environment then has no reviewers
  (`products.json` `"approval": "checks"`); `scripts/setup-release-env.py` lifts them only in a
  repository whose `release.yml` on its default branch runs the guard, so no product is ever left
  with neither. Pushing a `v*` tag is the release decision, so the tag ruleset `release-tags`
  lets only team `release-approvers` create, move or delete one. `"approval": "people"` restores
  the reviewers everywhere.

## The `release` environment (per product repository)

- `reviewers`: none under `"approval": "checks"` once `release.yml` runs the guard; otherwise team
  `release-approvers` (sshlg, khurss, svlab93).
- `prevent_self_review`: from `products.json`; `false` since the operator's amendment of D5
  (any member may approve, the author included).
- `can_admins_bypass: false`: an organization admin cannot skip the review either; otherwise the
  rule would not hold for the admin.
- `deployment_branch_policy: {protected_branches: false, custom_branch_policies: true}`, plus one
  tag policy `v*`: only a version tag can reach the keys. The rehearsal (`workflow_dispatch`) runs
  on a `v*` tag as well.
- Secrets, set by `scripts/sync-release-secrets.py` from the vault over stdin.
- Variables (not secrets): `APPLE_TEAM_ID`, and `AZURE_*` for Switchboard.

**An agent never approves a deployment with a person's account.** Where reviewers remain (a
product without the guard, or `"approval": "people"`), the agent starts the run and names where to
approve; under checks there is nothing to approve, and the agent watches the run and reports it.

**Tag ruleset `release-tags`** (per product repository, `scripts/setup-release-env.py`): target
`refs/tags/v*`, rules creation, update and deletion, bypass team `release-approvers` always. A
workflow or a person outside the team cannot push, move or delete a release tag.

## Composite actions in `.github` (`@v1`)

| Action | Does | Inputs | Leaves behind |
|---|---|---|---|
| `actions/apple-signing` | Creates a random-password temporary keychain. Imports the Developer ID `.p12` (and the MAS `.p12`s when given), sets the partition list so `codesign` never prompts, and puts the keychain first in the search list. Outputs the identity's full name | `p12-b64`, `p12-password`, optional `distribution-p12-b64`, `installer-p12-b64`, `team-id` | Nothing: a final `if: always()` step of the caller runs `actions/apple-signing/cleanup` |
| `actions/notarize` | The generalized Observatory `notarize.sh`. It notarizes an `.app`, `.dmg`, `.zip` or `.pkg` with the ASC API key, requires `Accepted` (printing Apple's log otherwise), staples when the type supports it, and checks with `spctl` (an app; a dmg with `--context context:primary-signature`; a pkg with `--type install`) | `path`, `asc-key-id`, `asc-issuer-id`, `asc-key-p8-b64` | The key file in `$RUNNER_TEMP`, removed |
| `actions/sign-sums` | Writes `SHA256SUMS` over a folder and makes the detached `SHA256SUMS.asc` with the organization GPG key, imported into a throwaway `GNUPGHOME` | `folder`, `gpg-key`, `gpg-passphrase` | Nothing |

Reusable workflow `.github/workflows/release-publish.yml`: it downloads the jobs' artifacts, runs
`actions/attest-build-provenance@v4` on every file (Sigstore; free on public repositories), runs
`sign-sums`, then creates or updates the GitHub release from the tag's CHANGELOG section. The
release stays a draft until every attestation and the signature exist, then it is published.

## Credentials

| Vault slot | Names | Holds | Synced into |
|---|---|---|---|
| `passioncode-release/prod` | `APPLE_DEVELOPER_ID_P12_B64`, `APPLE_DEVELOPER_ID_P12_PASSWORD` | The new CI-only Developer ID Application certificate and key (D4). The key is generated with `openssl` and the CSR goes through the App Store Connect API `POST /v1/certificates` | Every macOS product |
| same | `APPLE_DISTRIBUTION_P12_B64`, `APPLE_INSTALLER_P12_B64`, `APPLE_MAS_P12_PASSWORD`, `MAS_PROVISION_PROFILE_B64` | The CI-only Mac App Distribution and Mac Installer Distribution certificates, and the Inbox profile | fabric-inbox |
| same | `RELEASE_GPG_PRIVATE_KEY_B64`, `RELEASE_GPG_PASSPHRASE` | The organization release key (ed25519, sign-only, 3-year expiry). Its public key is published in `.github/release-signing/` and on the website | Every product |
| `apple-publisher-kj35uyyl22/prod` (existing) | `ASC_API_KEY_P8_B64`, `ASC_KEY_ID`, `ASC_ISSUER_ID` | The team's App Store Connect API key, the one used today | Every Apple product |
| `fabric-vr/prod` | `ANDROID_KEYSTORE_B64`, `ANDROID_KEYSTORE_PASSWORD`, `ANDROID_KEY_ALIAS`, `ANDROID_KEY_PASSWORD` | Fabric VR's release keystore (D8) | fabric-vr |

Every value enters GitHub on stdin (`gh secret set NAME --env release --repo R`). The sync tool
prints names and a fingerprint (an `sha256` prefix), never a value. It is idempotent and does a
dry run unless given `--apply`.

## The products

| Product | macOS build on CI | Other platforms | Changes in the product |
|---|---|---|---|
| Observatory (pilot) | `build-app.sh` with `OBSERVATORY_SIGN_IDENTITY` from `apple-signing` → `notarize` (already the shape of `notarize.sh`) | The wheel (Linux and macOS): attestation and sums | `release.yml`; AGENTS Releasing points at CI |
| Fabric Dashboards | `dist-mac.mjs --identity <from action>`; the notary profile is replaced by the ASC key | — | Accept the ASC key; `spctl` on the app as well |
| Fabric Inbox | `dist-mac.mjs`; MAS `mas-package.mjs` with the MAS identities and profile; upload with `xcrun altool --upload-package` using the API key | — | Accept the ASC key; MAS upload step |
| Fabric | `release-mac.mjs` already uses the ASC key; the identity comes from the action | — | The team id comes from `APPLE_TEAM_ID` (`electron-builder.release.yml:13`) |
| Switchboard | `build_macos.py --identity <from action>`; the notary profile is replaced by the ASC key | Windows: `windows-latest` builds natively, `azure/login` (OIDC) + `Azure/artifact-signing-action@v2`, behind the variable `AZURE_SIGNING_ENABLED` | The team id comes from the build environment (`keychain_macos.rs:58-60` already reads `SWITCHBOARD_SIGNING_TEAM`; its literal default goes) |
| Fabric VR | — | `assembleRelease` with the keystore decoded into `$RUNNER_TEMP`, `apksigner verify --print-certs` | `keystore.properties` from env in CI |

## Failure behaviour

- **A missing secret** fails the job before any build, naming the secret but not its value.
- **Apple rejecting notarization** fails the job and prints Apple's log. Nothing is published.
- **A rejected approval or a 30-day timeout** means no signing job runs and the release stays
  absent; there is no partial publish.
- **Any job failing** leaves the release a draft; `publish` never runs.
- **Windows signing disabled** (`AZURE_SIGNING_ENABLED` not `true`): the job uploads the unsigned
  `.exe`, and the release notes and receipt say `windows_authenticode: NOT_SIGNED`.

## Modules (stages 3→10 run per module)

| Module | REQs | Walking skeleton |
|---|---|---|
| M0 environment, team, sync tool, composite actions, Observatory pilot | R1 R2 R3 R5 R6 R12 (part) | A rehearsal release of Observatory on CI, notarized, attested and summed with a signature |
| M1 keys: CI Developer ID, GPG, Fabric VR keystore, MAS certificates and profile | R4 R9 (certs) R11 (key) R12 (key) | — |
| M2 Fabric Dashboards, Fabric Inbox, Fabric, Switchboard (macOS) | R7 R8 R14 | — |
| M3 Inbox to the Mac App Store | R9 | — |
| M4 Fabric VR on Android | R11 | — |
| M5 Switchboard on Windows, built, with signing behind a switch | R10 | — |
| M6 the rule: `knowledge/rules.md`, the launcher skill, `.github` AGENTS, org-index | R13 | — |
