# Release signing — how every PassionCode.ai product is signed

Released builds are signed **only in GitHub Actions**, in each product repository's protected
`release` environment. They are released **only after someone from `release-approvers` approves**,
and that person cannot be whoever pushed the tag. Nobody's laptop holds a release key.
Decisions and design: [docs/release-signing/](../docs/release-signing/BRIEF.md).

## What a release looks like

1. Merge the release pull request (version bump, CHANGELOG section) through the repository's
   required checks.
2. Push the tag: `git tag -a vX.Y.Z <merge commit> -m … && git push origin vX.Y.Z`.
3. The product's `release.yml` starts. Its signing jobs wait for the `release` environment.
4. Someone from `release-approvers` other than the tag's author opens the run and approves
   ("Review deployments"). The jobs build, sign, notarize, staple and assess. The `publish`
   job waits for a second approval, because it holds the GPG key.
5. `publish` attests every file (Sigstore), writes `SHA256SUMS` and `SHA256SUMS.asc`, and
   publishes the release. A published release is never rewritten: a fix is a new tag.

A **rehearsal** runs the whole path without releasing. Push a `vX.Y.Z-rc.N` tag (the push
trigger ignores `-rc` tags), then run
`gh workflow run release.yml --ref vX.Y.Z-rc.N -f publish=false`. The signed set is kept as a
workflow artifact for 14 days, and no release is created.

## The shared pieces (`@v1`)

| Piece | Use |
|---|---|
| [`actions/apple-signing`](../actions/apple-signing/action.yml) + `/cleanup` | A throwaway keychain with the CI Developer ID (and the MAS identities); outputs `identity` |
| [`actions/notarize`](../actions/notarize/action.yml) | Notarize, staple and assess a `.app`, `.dmg` or `.pkg` with the App Store Connect API key |
| [`actions/sign-sums`](../actions/sign-sums/action.yml) | `SHA256SUMS` plus a detached GPG signature |
| [`.github/workflows/release-publish.yml`](../.github/workflows/release-publish.yml) | Attest, sum, sign, then draft and publish the release (or keep a rehearsal) |

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
| CI Developer ID Application (G2), team KJ35UYYL22, certificate id `8BQWYPFLS2`, expires 2031-09-17 | `apple-publisher-kj35uyyl22/prod`: `APPLE_DEVELOPER_ID_P12_B64`, `APPLE_DEVELOPER_ID_P12_PASSWORD` | Used only by CI. The operator's local Developer ID is a different certificate: revoking one leaves the other |
| App Store Connect API key | `apple-publisher-kj35uyyl22/prod`: `ASC_*` | Notarization; reads certificates and profiles; uploads to App Store Connect. It cannot issue Developer ID certificates |
| Organization release GPG key `63B3 0DC3 24BD 6974 87AA 3194 4FAF B8AE C803 B6A7` (ed25519, sign-only, expires 2029-10-02) | `passioncode-release/prod`: `RELEASE_GPG_PRIVATE_KEY_B64`, `RELEASE_GPG_PASSPHRASE` | Public key: [passioncode-release-signing.asc](passioncode-release-signing.asc) |

## Rotating

- **Developer ID (CI).** Only the Account Holder can issue one; the API answers 403.
  1. Run `scripts/new-apple-cert.sh --csr-only <new dir>` under the `ASC_*` slot.
  2. Upload the CSR at developer.apple.com → Certificates → + → Developer ID Application (G2
     Sub-CA).
  3. Run `scripts/new-apple-cert.sh --cert-id <id> DEVELOPER_ID_APPLICATION <same dir>`.
  4. `vault.py rotate` both names.
  5. Sync the secrets, then revoke the old certificate in the portal.
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
- Never approve a release you started; GitHub refuses it anyway (`prevent_self_review`).
- Never rewrite a published release. A wrong release is fixed with a new tag.
