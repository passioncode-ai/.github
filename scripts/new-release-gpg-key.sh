#!/bin/bash
# Make the organization's release-signing GPG key in a throwaway GNUPGHOME.
#
#   scripts/new-release-gpg-key.sh <private dir>
#
# ed25519, sign-only, expiring in 3 years, protected by a random passphrase. <dir> (created
# 0700, must not exist) receives private.asc (armored, passphrase-protected), passphrase and
# public.asc. The fingerprint is printed; nothing secret is. The caller stores private.asc and
# passphrase in the vault over stdin, publishes public.asc (release-signing/ in this repository
# and the website), then deletes <dir>. Rotation is the same script plus a revocation of the
# old key. Design: docs/release-signing/DESIGN.md → Credentials.
set -euo pipefail
DIR=${1:?a new private directory}
UID_TEXT=${RELEASE_GPG_UID:-"PassionCode.ai releases <contact@passioncode.ai>"}
[[ ! -e "$DIR" ]] || { echo "new-release-gpg-key.sh: $DIR exists" >&2; exit 2; }
umask 077
mkdir -m 700 "$DIR"
# A short home: gpg-agent's socket path must fit a Unix socket (104 bytes on macOS), which a
# deep project or temp path does not.
GNUPGHOME=$(mktemp -d /tmp/rgpg.XXXXXX); export GNUPGHOME
trap 'gpgconf --kill gpg-agent 2>/dev/null || true; rm -rf "$GNUPGHOME"' EXIT
openssl rand -base64 30 | tr -d '\n' > "$DIR/passphrase"
gpg --batch --pinentry-mode loopback --passphrase-file "$DIR/passphrase" \
    --quick-generate-key "$UID_TEXT" ed25519 sign 3y
FPR=$(gpg --batch --with-colons --list-keys | awk -F: '$1=="fpr"{print $10; exit}')
gpg --batch --pinentry-mode loopback --passphrase-file "$DIR/passphrase" --armor --export-secret-keys "$FPR" > "$DIR/private.asc"
gpg --batch --armor --export "$FPR" > "$DIR/public.asc"
echo "fingerprint $FPR"
