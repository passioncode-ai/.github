# Release signing — status and close-out (2026-10-03)

This is the state at the end of the run that built the system. Decisions: [BRIEF.md](BRIEF.md);
design: [DESIGN.md](DESIGN.md); plan: [PLAN.md](PLAN.md); usage:
[release-signing/README.md](../../release-signing/README.md).

## Where every product stands

| Product | `release.yml` on main | Rehearsal run (tag, `publish=false`) | Waiting for |
|---|---|---|---|
| Project Observatory | PR #126 → `b02e3df` | [`v0.13.1-rc.1`](https://github.com/passioncode-ai/project-observatory-dashboard/actions/runs/37127335035): wheel ✓, macos waiting | an approver |
| Fabric Dashboards | PR #22 → `ec2a29f` | [`v0.4.1-rc.1`](https://github.com/passioncode-ai/fabric-dashboards/actions/runs/37128282549): version ✓, check ✓, macos waiting | an approver |
| Fabric Inbox (DMG + Mac App Store) | PR #13 → `8783a0f` | [`v0.8.2-rc.1`](https://github.com/passioncode-ai/fabric-inbox/actions/runs/37128797464): gate ✓, macos and mas waiting | an approver; the App Store Connect app record, for the upload |
| Fabric | PR #3 → `8c68c60` (ADR-0111) | [`v0.2.0-rc.1`](https://github.com/passioncode-ai/fabric/actions/runs/37129440752): preflight refused, because the release gate names 0.3.0 and the app is 0.2.0. Correct; re-run as `v0.3.0-rc.1` | 0.3.0 on main (the Fabric session, P-03) |
| Fabric Switchboard (macOS + Windows) | PR #24 → `e9ae011` | [`v0.5.3-rc.1`](https://github.com/passioncode-ai/fabric-switchboard/actions/runs/37128681124): preflight ✓, macos and windows waiting | an approver; Azure for Windows signing |
| Fabric VR (Quest APK) | PR #10 → `0367521` (DEC-0104) | [`v0.1.0-rc.1`](https://github.com/passioncode-ai/fabric-vr/actions/runs/37132362073): the sign-and-verify job is waiting | an approver |

Every `release` environment was checked with `gh api repos/<r>/environments/release`: reviewers
are the team `release-approvers` (sshlg, khurss, svlab93); `prevent_self_review: false` since the
operator's amendment (any member, the author included, may approve);
`can_admins_bypass: false`, and the only deployment policy is the tag `v*`. The secrets are
synced, and the counts match the manifest: 7 per Apple product, 11 for Inbox, 6 for VR.

## Requirements

| REQ | State | Evidence |
|---|---|---|
| R1 shared actions and workflow `@v1` | **done** (v1 → 1.1.0) | `self-test.yml` green on ubuntu and macos (runs 37126174373, 37127228934, 37128831069); 33 tests across fake `gh`, fake Apple tools and real `gpg`; planted defects watched failing |
| R2 a `release` environment per product | **done** | `setup-release-env.py --apply` is idempotent, and its second run reports every item `unchanged` |
| R3 team `release-approvers` | **done** | `gh api orgs/passioncode-ai/teams/release-approvers/members` → khurss, sshlg, svlab93 |
| R4 a CI-only Developer ID | **done**; **the signed artifact is pending approval** | Certificate `FAWGBTTFGC` (rotated from `8BQWYPFLS2`) (G2, valid to 2031-09-17), a key different from the local one. Proven locally through `actions/apple-signing`: `codesign` with no prompt, and the user's search list unchanged |
| R5 one notary convention (`ASC_*`) | **done** | Every CI path reads `ASC_*`; no Keychain notary profile is used in CI. The local profile paths remain, marked debug only |
| R6 sync tool | **done** | `tests/test_release_env_scripts.py`; real syncs printed names and sha256 prefixes only |
| R7 no hardcoded team id | **done** | `git grep KJ35UYYL22 origin/main` outside docs is empty in all six products; Dashboards' hit is its own guard test |
| R8 the five macOS products release through CI | **merged; a notarized CI artifact is pending approval** | The runs above |
| R9 Inbox in the Mac App Store | **certificates, profile, job and app record (`6818818207`) done; the first upload is pending approval** | Certificates `4K8Y54M3FC` and `KM2FU4HAB2`, profile `A82J7K8VTT`, bundle id resource `CMB7CQ54FX` |
| R10 Windows Authenticode | **wired behind `AZURE_SIGNING_ENABLED=false`** | Until Azure exists, the receipt and notes say `windows_authenticode: NOT_SIGNED`; Switchboard `docs/DISTRIBUTION.md` holds the human steps |
| R11 Fabric VR keystore | **done; the signed APK is pending approval** | PKCS12 RSA 4096, valid to 2056-09-25, SHA-256 `06:69:C0:CF:…:94:C6:D5:41`; `verify-release-apk.sh` checks it on every release |
| R12 Sigstore and GPG | **done; the first real run is pending approval** | Key `63B3 0DC3 24BD 6974 87AA 3194 4FAF B8AE C803 B6A7`, public part in `release-signing/` |
| R13 the rule where agents read it | **done** | fabric-workspace `knowledge/rules.md` §11 (#25); launcher 0.1.24 `working-in-passioncode` (published to npm and installed here); `.github` AGENTS.md; org-index row (#34) |
| R14 product docs describe CI | **done** | Each product PR rewrote its release docs, with local signing marked debug only |

**The verification trio is open:** a signed artifact, its Gatekeeper/`apksigner` verdict and its
attestation all wait for the first approved run. *Green* here means merged and tested, not yet
*verified on a release*.

## Human steps, in one place

1. **A member of release-approvers (the operator included) approves the rehearsals above.** Open each run, choose "Review
   deployments" and approve; `publish` asks a second time. A rehearsal creates no release. It
   proves the signed path and keeps the signed set as a workflow artifact for 14 days.
2. **Azure Artifact Signing** for Windows: an EU company, a subscription, identity validation, a
   certificate profile and a federated credential for Switchboard's `release` environment. Then
   set the `AZURE_*` variables and `AZURE_SIGNING_ENABLED=true` (Switchboard
   `docs/DISTRIBUTION.md`). Add those variables to `products.json` here.
3. ~~The App Store Connect app record~~ — **done 2026-10-03** through the operator's App Store
   Connect session: "Fabric Inbox", Apple id `6818818207`, SKU `fabric-inbox`, primary language
   en-US, macOS.
4. **Developer ID rotation** before 2031-09-17 needs the Account Holder in the portal
   (README → Rotating). It was rehearsed on 2026-10-03: CI certificate `8BQWYPFLS2` →
   `FAWGBTTFGC`, synced into the five Apple products, and the old key destroyed. The old
   certificate signed nothing.

## Retrospective

- **Stamp:** `.github` at v1.1.0 (`ecc3ae7`); products as in the table above.
- **What diverged, and the check that now catches it:**
  - **A secret-handling chain in zsh deleted the first Fabric VR keystore before it was
    stored.** An unsplit `$V` made every `put` fail, and the `rm -rf` after them still ran. No
    key had signed anything; it was regenerated. *Fix:* the store scripts confirm every name in
    the vault and only then remove the working copy (`store-fvr.sh`, `store-mas.sh` pattern).
    *Rule:* never put a delete in the same chain as the stores it depends on.
  - **`apple-signing/setup.sh` exited silently** when the first MAS name did not match
    (`set -e` + `pipefail` inside `$(…)`). *Caught by* the local proof with the real `.p12`s.
    *Guarded by* `tests/test_apple_signing.py`, watched failing.
  - **The first `release-publish` draft could rewrite a published release** on a rehearsal of an
    existing tag. Caught at review before any run. *Guarded by* `tests/test_publish_step.py`: a
    published release is refused, and `-rc` is never published.
  - **A Linux-only portability break in a test fake** (BSD `stat`). *Caught by* the hosted
    self-test, which is why it runs on both OSes.
- **Standing instruction (one):** for a value that must survive, store it, verify it, and only
  then remove the source copy, each as its own step.

## Rehearsal results (2026-10-03, evening)

The operator told the agent to approve rehearsals. Every approval carries the comment "approved
on the operator's explicit instruction". Each result below was checked from the downloaded signed
set:
`gpg --verify SHA256SUMS.asc SHA256SUMS` (key `63B3…B6A7`), `shasum -a 256 -c SHA256SUMS`, and
`gh attestation verify <file> --owner passioncode-ai --signer-repo passioncode-ai/.github`. On
macOS, Gatekeeper also assessed a copy that carried a browser's quarantine flag.

| Product | Rehearsal | Result |
|---|---|---|
| Fabric VR | `v0.1.0-rc.1`, run 37132362073 | **Green.** APK signed with the published key; GPG, sums and attestation OK |
| Project Observatory | `v0.13.1-rc.1`, run 37127335035 | **Green.** Wheel and app; app accepted as "Notarized Developer ID", signed by CI certificate `FAWGBTTFGC` (serial `4F2105B4…`); attestations 2 of 2 |
| Fabric Dashboards | `v0.4.1-rc.1`, run 37128282549 | **Green.** DMG notarized and stapled; attestations 4 of 4; CI certificate |
| Fabric Inbox | `v0.9.0-rc.3`, run 37149725167 | **Green.** DMG notarized and attested. The MAS `.pkg` is signed by "3rd Party Mac Developer Installer (KJ35UYYL22)"; a rehearsal does not upload it |
| Fabric Switchboard | `v0.5.3-rc.3`, run 37148716778 | **macOS green, Windows native tests green.** Windows packaging refused a dirty tree; Switchboard is fixing it (it now names the changed paths). Next: `rc.4` |
| Fabric | — | Waits for 0.3.0 on main (preflight refused 0.2.0 correctly) |

Defects the first approved runs found, all fixed:
- `.github` 1.1.2: invalid YAML in `apple-signing/cleanup/action.yml`, which every macOS
  signing job hit. A test now parses every action manifest.
- `.github` 1.1.3: the attestation verify command printed in the release notes failed.
- fabric-inbox #19: the profile check read `AppIdentifierPrefix`; Apple writes
  `ApplicationIdentifierPrefix`.
- fabric-inbox #21: empty entitlements on library code reached plistlib.
- fabric-inbox #22: the entitlements refusal now names the file and the keys.
- fabric-inbox #23: the app's own executable carries the app's entitlements.
- fabric-switchboard #27: the storage owner check on an elevated Windows token.
- fabric-switchboard #28: seven Windows-unaware tests or fixtures, and a 2 s → 5 s loopback bound.

Azure (Windows signing): subscription "Azure subscription 1", tenant `c7dee310…`, account
`passioncodesigning` (North Europe, Basic, `https://neu.codesigning.azure.net/`). An OIDC
federated credential is limited to `repo:passioncode-ai/fabric-switchboard:environment:release`,
with the role "Artifact Signing Certificate Profile Signer" on the account only. The six
`AZURE_*` variables are set in Switchboard's `release` environment. The organization's identity
validation (SV Lab / Siarhei Sheleh, DUNS) is **in progress** at Microsoft. After it, create the
certificate profile `passioncode-public-trust` and set `AZURE_SIGNING_ENABLED=true`.
