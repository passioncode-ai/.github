#!/bin/bash
# Write SHA256SUMS over every file in a folder and a detached, armored GPG signature of it,
# SHA256SUMS.asc, with the organization's release key.
#
#   RELEASE_GPG_PRIVATE_KEY_B64=… RELEASE_GPG_PASSPHRASE=… sign-sums.sh <folder>
#
# The key is imported into a throwaway GNUPGHOME (short path: gpg-agent's socket must fit
# 104 bytes) that is removed on exit; the passphrase reaches gpg on a file descriptor, never
# argv. The signature is verified against the key's own public part before the script ends.
# Prints the signing key's fingerprint. Exit 2: a missing input; exit 1: gpg failed.
set -euo pipefail
DIR=${1:?folder of release files}
for v in RELEASE_GPG_PRIVATE_KEY_B64 RELEASE_GPG_PASSPHRASE; do
  [[ -n "${!v:-}" ]] || { echo "sign-sums: $v is empty; is the release environment's secret set?" >&2; exit 2; }
done
[[ -d "$DIR" ]] || { echo "sign-sums: $DIR is not a folder" >&2; exit 2; }

GNUPGHOME=$(mktemp -d /tmp/sums.XXXXXX); export GNUPGHOME
trap 'gpgconf --kill gpg-agent 2>/dev/null || true; rm -rf "$GNUPGHOME"' EXIT
chmod 700 "$GNUPGHOME"
printf '%s' "$RELEASE_GPG_PRIVATE_KEY_B64" | base64 --decode \
  | gpg --batch --pinentry-mode loopback --passphrase-fd 3 --import 3<<<"$RELEASE_GPG_PASSPHRASE" 2>/dev/null
FPR=$(gpg --batch --with-colons --list-secret-keys | awk -F: '$1=="fpr"{print $10; exit}')
[[ -n "$FPR" ]] || { echo "sign-sums: the key did not import" >&2; exit 1; }

cd "$DIR"
rm -f SHA256SUMS SHA256SUMS.asc
find . -maxdepth 1 -type f ! -name 'SHA256SUMS*' -print | sed 's|^\./||' | LC_ALL=C sort \
  | while IFS= read -r f; do shasum -a 256 "$f"; done > SHA256SUMS
[[ -s SHA256SUMS ]] || { echo "sign-sums: no files to sum in $DIR" >&2; exit 2; }
gpg --batch --yes --pinentry-mode loopback --passphrase-fd 3 --local-user "$FPR" \
    --armor --detach-sign --output SHA256SUMS.asc SHA256SUMS 3<<<"$RELEASE_GPG_PASSPHRASE"
gpg --batch --verify SHA256SUMS.asc SHA256SUMS 2>/dev/null || { echo "sign-sums: the signature does not verify" >&2; exit 1; }
echo "fingerprint=$FPR"
