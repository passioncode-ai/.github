# Release signing — how every PassionCode.ai product is signed

Released builds are signed **only in GitHub Actions**, in each product repository's protected
`release` environment. They are released **only after someone from `release-approvers` approves**:
a person looks at the run and clicks. The release's author may approve it (operator decision,
2026-10-03; `prevent_self_review` in [products.json](products.json) turns four eyes back on). Nobody's laptop holds a release key.
Decisions and design: [docs/release-signing/](../docs/release-signing/BRIEF.md).

## What a release looks like

1. Merge the release pull request (version bump, CHANGELOG section) through the repository's
   required checks.
2. Push the tag: `git tag -a vX.Y.Z <merge commit> -m … && git push origin vX.Y.Z`.
3. The product's `release.yml` starts. Its signing jobs wait for the `release` environment.
4. Someone from `release-approvers` opens the run and approves ("Review deployments" →
   `release` → "Approve and deploy"). The jobs build, sign, notarize, staple and assess. The `publish`
   job waits for a second approval, because it holds the GPG key.
5. `publish` attests every file (Sigstore), writes `SHA256SUMS` and `SHA256SUMS.asc`, and
   publishes the release. A published release is never rewritten: a fix is a new tag.

**Prereleases.** A product that ships betas adds `"v[0-9]+.[0-9]+.[0-9]+-beta.[0-9]+"` (or
`-alpha.N`, `-preview.N`) to its push trigger. Such a tag is published like any release and marked
a prerelease (`prerelease: auto`). An `-rc` tag is never published.

**Never behind the latest release.** A release whose version is not newer than the repository's
latest release is refused before anything is written: "latest" is where installed copies read their
update feed (`releases/latest/download/…`), so an old run approved late would offer every copy a
downgrade, or a feed that is not there. Seen 2026-10-07: Fabric Inbox's v0.10.0 run had waited
for approval for two days while v0.11.0 was already latest. A maintenance release of an older
line sets `allow-older: true` and is published without becoming latest. Prereleases never compete
for latest.

A **rehearsal** runs the whole path without releasing. Push a `vX.Y.Z-rc.N` tag (the push
trigger ignores `-rc` tags), then run
`gh workflow run release.yml --ref vX.Y.Z-rc.N -f publish=false`. The signed set is kept as a
workflow artifact for 14 days, and no release is created.

## Verifying a release

```sh
gpg --import passioncode-release-signing.asc          # once; key 63B3 0DC3 24BD 6974 87AA 3194 4FAF B8AE C803 B6A7
gpg --verify SHA256SUMS.asc SHA256SUMS
shasum -a 256 -c SHA256SUMS --ignore-missing
gh attestation verify <file> --owner passioncode-ai --signer-repo passioncode-ai/.github
```

The attestation is signed by the shared `release-publish` workflow, so its signer is
`passioncode-ai/.github`. Its provenance names the product's own `release.yml`, tag and commit.
`gh attestation verify <file> -R <product>` alone fails with "verifying with issuer
sigstore.dev". All four steps were run against Fabric VR's first rehearsal
(`v0.1.0-rc.1`) on 2026-10-03.

## The shared pieces (`@v1`)

| Piece | Use |
|---|---|
| [`actions/apple-signing`](../actions/apple-signing/action.yml) + `/cleanup` | A throwaway keychain with the CI Developer ID (and the MAS identities); outputs `identity` |
| [`actions/notarize`](../actions/notarize/action.yml) | Notarize, staple and assess a `.app`, `.dmg` or `.pkg` with the App Store Connect API key |
| [`actions/sign-sums`](../actions/sign-sums/action.yml) | `SHA256SUMS` plus a detached GPG signature |
| [`.github/workflows/release-publish.yml`](../.github/workflows/release-publish.yml) | Attest, sum, sign, then draft and publish the release (or keep a rehearsal) |
| [`actions/windows-signing`](../actions/windows-signing/action.yml) | Sign Windows files with Azure Artifact Signing over OIDC, then verify them; outputs `report` (JSON for the receipt) |
| [`actions/windows-signing/login`](../actions/windows-signing/login/action.yml) + [`/verify`](../actions/windows-signing/verify/action.yml) | For a packager that signs by itself (electron-builder `azureSignOptions`): the OIDC sign-in before it, the same verification after it |

A minimal macOS product (`.github/workflows/release.yml` in the product):

```yaml
on:
  push: { tags: ["v[0-9]+.[0-9]+.[0-9]+"] }
  workflow_dispatch: { inputs: { publish: { type: boolean, default: false } } }
permissions: { contents: read }
jobs:
  macos:
    runs-on: macos-latest
    environment: release
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with: { fetch-depth: 0 }
      - id: sign
        uses: passioncode-ai/.github/actions/apple-signing@v1
        with:
          developer-id-p12-b64: ${{ secrets.APPLE_DEVELOPER_ID_P12_B64 }}
          p12-password: ${{ secrets.APPLE_DEVELOPER_ID_P12_PASSWORD }}
          team-id: ${{ vars.APPLE_TEAM_ID }}
      - run: <the product's build, signing with "${{ steps.sign.outputs.identity }}">
      - uses: passioncode-ai/.github/actions/notarize@v1
        with:
          path: <the .app, .dmg or .pkg>
          asc-key-id: ${{ secrets.ASC_KEY_ID }}
          asc-issuer-id: ${{ secrets.ASC_ISSUER_ID }}
          asc-key-p8-b64: ${{ secrets.ASC_API_KEY_P8_B64 }}
      - uses: actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a # v7.0.1
        with: { name: release-macos, path: <the files to release> }
      - if: always()
        uses: passioncode-ai/.github/actions/apple-signing/cleanup@v1
  publish:
    needs: [macos]
    uses: passioncode-ai/.github/.github/workflows/release-publish.yml@v1
    with:
      publish: ${{ github.event_name == 'push' || inputs.publish }}
    secrets: inherit
```

## Windows (every product that ships for Windows)

Every PassionCode.ai product ships for macOS, Windows and Linux (operator decision 2026-10-09;
fabric-workspace [knowledge/platforms.md](https://github.com/passioncode-ai/fabric-workspace/blob/main/knowledge/platforms.md)
holds the packages, updates and places). Windows files are Authenticode-signed through **one**
Azure Artifact Signing account and Public Trust certificate profile (`azure_signing` in
[products.json](products.json)); each repository signs in over OIDC with **its own** identity,
whose only federated credential is its `release` environment and whose only role is the signer
role on that account. No secret is stored anywhere. Linux packages are not code-signed: they are
covered by `SHA256SUMS`, its GPG signature and the attestations, like every release file.

A Tauri or native product, in its `windows` job (`runs-on: windows-latest` / `windows-11-arm`,
`environment: release`, `permissions: { contents: read, id-token: write }`):

```yaml
      # Pass 1: the executables, before the installer packs them.
      - if: vars.AZURE_SIGNING_ENABLED == 'true'
        uses: passioncode-ai/.github/actions/windows-signing@v1
        with:
          files: |
            ${{ github.workspace }}\target\release\<product>.exe
          client-id: ${{ vars.AZURE_CLIENT_ID }}
          tenant-id: ${{ vars.AZURE_TENANT_ID }}
          subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}
          endpoint: ${{ vars.AZURE_SIGNING_ENDPOINT }}
          account: ${{ vars.AZURE_SIGNING_ACCOUNT }}
          certificate-profile: ${{ vars.AZURE_CERTIFICATE_PROFILE }}
      - run: <build the installer around the signed executables>
      # Pass 2: the installer itself; its report goes into the receipt.
      - if: vars.AZURE_SIGNING_ENABLED == 'true'
        id: signed
        uses: passioncode-ai/.github/actions/windows-signing@v1
        with:
          files-folder: ${{ github.workspace }}\target\release\bundle\nsis
          files-folder-filter: exe
          # …the same six AZURE inputs
```

GitHub does not support YAML anchors in workflows; write the six inputs out in both steps.

An Electron product signs inside electron-builder (`win.azureSignOptions` with
`AZURE_SIGNING_ENDPOINT`, `AZURE_SIGNING_ACCOUNT`, `AZURE_CERTIFICATE_PROFILE`): run
`actions/windows-signing/login` before the build and `actions/windows-signing/verify` on every
`.exe` it produced after it. Either way the job fails unless every file is `Valid` **and
timestamped**, before anything reaches `publish`.

While `AZURE_SIGNING_ENABLED` is `false` a product may ship unsigned Windows files only if it
says so: the receipt carries `windows_authenticode: NOT_SIGNED` and the release notes say
"Windows installers are not Authenticode-signed yet; SmartScreen warns once. Verify them with
`SHA256SUMS`." (PL-03).

**Adding Windows signing to a product** — the operator's `az login` and `gh` admin:

1. `"windows": true` and `"AZURE_SIGNING_ENABLED": "false"` in the product's entry in
   [products.json](products.json).
2. `scripts/setup-windows-signing.py --repo passioncode-ai/<repo>` (dry run), then `--apply`:
   the app registration `github-release-signing-<repo>`, its service principal, the federated
   credential `repo:passioncode-ai/<repo>:environment:release`, the signer role on the account,
   and `AZURE_CLIENT_ID`/`AZURE_TENANT_ID`/`AZURE_SUBSCRIPTION_ID`. An identity the environment
   already names is kept.
3. `scripts/setup-release-env.py --repo passioncode-ai/<repo> --apply`: the account's endpoint,
   account and profile variables.
4. Set `AZURE_SIGNING_ENABLED` to `"true"` in products.json, apply step 3 again, and rehearse on
   a `vX.Y.Z-rc.N` tag: the `windows` job must report every file `Valid`. **products.json is the
   switch's source of truth** — `setup-release-env.py` writes what it says, so a variable flipped
   only in GitHub is switched back by the next run.

**What the first products learned (check these in yours):**

- **No timestamp, no release.** The profile's certificates live about three days; a signature
  without an RFC 3161 timestamp stops validating when its certificate expires, so the release
  would read "unsigned" to every user three days after shipping. `verify` refuses it.
- **Sign the executables, then pack, then sign the installer.** An installer built around unsigned
  executables installs unsigned files even when the installer itself is signed (Switchboard).
  Tauri's generated NSIS uninstaller is signed only through Tauri's own `signCommand`.
- **The NSIS stub is x86 on both architectures** (`PE 0x14c`, Switchboard 2026-10-10); the arm64
  runner `windows-11-arm` builds and packages without changes, and its emulated x86 uninstaller
  takes about four minutes (Inbox).
- **A new certificate profile:** `includeStreetAddress` and `includePostalCode` stay `false` — the
  subject would otherwise publish the validated person's home address in every signature. ARM
  answers "could not find identity validation id" until Microsoft completes the validation; the
  id is read in the portal (there is no ARM resource for it). Of several validation e-mails,
  only the newest link works.
- **A role assignment can take minutes to reach the signing service**: a 403 right after
  `setup-windows-signing.py --apply` is retried by a later rehearsal, not by widening the role.
- **Only the job's own sign-in signs.** `windows-signing` excludes every other Azure credential
  the runner might carry; never add a client secret.

## Adding a product

1. Add it to [products.json](products.json) with its secret groups and variables.
2. `scripts/setup-release-env.py --repo passioncode-ai/<repo> --apply` creates `release`:
   - reviewers `release-approvers`;
   - no self-review and no admin bypass;
   - `v*` tags only;
   - the team's read access;
   - the variables.

   Without `--apply` it is a dry run.
3. Sync the secrets from the Observatory vault, one slot per run. Values go over stdin and only
   names and fingerprints are printed:

   ```sh
   T="$(project-observatory full-path)/tools"
   python "$T/use_secret.py" run --env prod apple-publisher-kj35uyyl22 \
     APPLE_DEVELOPER_ID_P12_B64,APPLE_DEVELOPER_ID_P12_PASSWORD,ASC_API_KEY_P8_B64,ASC_KEY_ID,ASC_ISSUER_ID -- \
     scripts/sync-release-secrets.py --repo passioncode-ai/<repo> --apply
   python "$T/use_secret.py" run --env prod passioncode-release RELEASE_GPG_PRIVATE_KEY_B64,RELEASE_GPG_PASSPHRASE -- \
     scripts/sync-release-secrets.py --repo passioncode-ai/<repo> --apply
   ```
4. Write the product's `release.yml` from the template above, and rehearse it on an `-rc` tag.

## Keys and their homes

| Key | Vault slot (Observatory) | Notes |
|---|---|---|
| CI Developer ID Application (G2), team KJ35UYYL22, certificate id `FAWGBTTFGC`, expires 2031-09-17 (rotated 2026-10-03 from `8BQWYPFLS2`, whose key was destroyed unused) | `apple-publisher-kj35uyyl22/prod`: `APPLE_DEVELOPER_ID_P12_B64`, `APPLE_DEVELOPER_ID_P12_PASSWORD` | Used only by CI. The operator's local Developer ID is a different certificate: revoking one leaves the other |
| App Store Connect API key | `apple-publisher-kj35uyyl22/prod`: `ASC_*` | Notarization; reads certificates and profiles; uploads to App Store Connect. It cannot issue Developer ID certificates |
| CI Mac App Distribution (`4K8Y54M3FC`) and Mac Installer Distribution (`KM2FU4HAB2`), team KJ35UYYL22; their names in a keychain are "3rd Party Mac Developer Application/Installer: …" | `apple-publisher-kj35uyyl22/prod`: `APPLE_DISTRIBUTION_P12_B64`, `APPLE_INSTALLER_P12_B64`, `APPLE_MAS_P12_PASSWORD` (one password for both) | Issued through the API (`scripts/new-apple-cert.sh`) |
| Fabric Inbox Mac App Store profile `A82J7K8VTT` (bundle id `ai.passioncode.fabric-inbox`, resource `CMB7CQ54FX`), expires 2027-10-03 | `fabric-inbox/prod`: `MAS_PROVISION_PROFILE_B64` | Authorizes only the CI Mac App Distribution certificate; renew it yearly with `scripts/asc.py create-profile` |
| Fabric VR release keystore, alias `fabricvr`, RSA 4096, valid until 2056-09-25. Certificate SHA-256 `06:69:C0:CF:49:07:E4:11:41:AC:5C:4B:F8:2A:25:CE:75:C9:1E:33:BF:B0:D7:FC:A0:55:40:E3:94:C6:D5:41` | `fabric-vr/prod`: `ANDROID_KEYSTORE_B64`, `ANDROID_KEYSTORE_PASSWORD`, `ANDROID_KEY_PASSWORD`, `ANDROID_KEY_ALIAS` | Made by `scripts/new-android-keystore.sh`. **Losing it means the installed app can never be updated**: the vault's encrypted off-disk backup is the second copy |
| Azure Artifact Signing account `passioncodesigning` (North Europe), Public Trust profile `passioncode-public-trust`, created 2026-10-10 on a completed identity validation | none: each repository signs in over OIDC with its own app registration (`setup-windows-signing.py`) | The subject's address fields are off. The validation and the profile are renewed in the Azure portal by the operator |
| Organization release GPG key `63B3 0DC3 24BD 6974 87AA 3194 4FAF B8AE C803 B6A7` (ed25519, sign-only, expires 2029-10-02) | `passioncode-release/prod`: `RELEASE_GPG_PRIVATE_KEY_B64`, `RELEASE_GPG_PASSPHRASE` | Public key: [passioncode-release-signing.asc](passioncode-release-signing.asc) |

## Rotating

- **Developer ID (CI).** Only the Account Holder can issue one; the API answers 403.
  1. Run `scripts/new-apple-cert.sh --csr-only <new dir>` under the `ASC_*` slot.
  2. Upload the CSR at developer.apple.com → Certificates → + → Developer ID Application (G2
     Sub-CA).
  3. Run `scripts/new-apple-cert.sh --cert-id <id> DEVELOPER_ID_APPLICATION <same dir>`.
  4. `vault.py rotate` both names. The vault must then serve the new `.p12`: compare sha256
     prefixes, never values.
  5. Sync the secrets into every Apple product.
  6. The portal cannot revoke a Developer ID certificate. Only Apple can, on a request to
     Developer Support, because revoking one can stop already-shipped apps from opening.
     - **An unused certificate** needs no revocation: destroy its key with
       `vault.py remove … --retired` once the new one is synced. The GitHub secrets are already
       overwritten, so the key then exists nowhere.
     - **A certificate whose key leaked** goes to Apple. The operator sends that request.

  Done once as a drill on 2026-10-03: `8BQWYPFLS2` → `FAWGBTTFGC`.
- **MAS certificates.** `scripts/new-apple-cert.sh MAC_APP_DISTRIBUTION|MAC_INSTALLER_DISTRIBUTION <dir>`
  works through the API with no portal step.
- **GPG.**
  1. Run `scripts/new-release-gpg-key.sh <dir>`.
  2. Publish the new public key next to the old one; publish the old key's revocation once no
     supported release depends on it.
  3. Sync the secrets.
- **Every rotation** is recorded with `vault.py rotate`, which archives the old value, plus a
  line in this table.

## Rules for agents and people

- A build signed anywhere other than the `release` environment (a laptop, a fork, a dispatch on
  a branch) is a debug build. It is never published or attached to a release.
- Never print, log or commit a key, a `.p12`, a password or a token. Values move over stdin
  (`vault.py put`, `gh secret set`) and nothing else.
- **Approvals.** An approval is the operator's call. On 2026-10-03 the operator told the
  agent to approve rehearsals and releases itself. It does so with the comment "approved on the
  operator's explicit instruction". Without such an instruction, an agent starts the run and says
  where to approve.
- **Default branches** cannot be deleted or force-pushed. `scripts/protect-default-branches.py
  --apply` gives every repository the ruleset `protect-default-branch` (`deletion` +
  `non_fast_forward` on `~DEFAULT_BRANCH`, no bypass). Run it for a new repository too.
  - On GitHub Free, a private repository cannot hold rulesets. `fabric-workspace` and
    `org-index` stay unprotected until the organization moves to Team or they become public.
  - The script reports them as NOT PROTECTED.
- Never rewrite a published release. A wrong release is fixed with a new tag.
