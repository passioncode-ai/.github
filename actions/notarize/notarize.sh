#!/bin/bash
# Notarize a signed .app, .dmg or .pkg with the team's App Store Connect API key, staple the
# ticket and assess the result the way Gatekeeper will on another Mac.
#
#   ASC_KEY_ID=… ASC_ISSUER_ID=… ASC_API_KEY_P8_B64=… notarize.sh <path>
#
# .app: zipped with ditto for the upload, stapled in place, assessed as an executable.
# .dmg: uploaded as is, stapled, assessed with --context context:primary-signature.
# .pkg: uploaded as is, stapled, assessed as an installer.
# Exit 2: refused before upload (a missing credential, another file type). Exit 1: Apple did
# not accept (its log is printed), or a staple or assessment failed. Stdout carries
# `submission=<id>` for $GITHUB_OUTPUT. The key lives in a 0600 file inside a private temp
# directory for the call and is removed on exit; no credential is printed.
set -euo pipefail
TARGET=${1:?path to a signed .app, .dmg or .pkg}
for v in ASC_KEY_ID ASC_ISSUER_ID ASC_API_KEY_P8_B64; do
  [[ -n "${!v:-}" ]] || { echo "notarize: $v is empty; is the release environment's secret set?" >&2; exit 2; }
done
case "$TARGET" in
  *.app) KIND=app ;; *.dmg) KIND=dmg ;; *.pkg) KIND=pkg ;;
  *) echo "notarize: $TARGET is not a .app, .dmg or .pkg" >&2; exit 2 ;;
esac
[[ -e "$TARGET" ]] || { echo "notarize: $TARGET does not exist" >&2; exit 2; }

WORK=$(mktemp -d "${RUNNER_TEMP:-${TMPDIR:-/tmp}}/notarize.XXXXXX")
trap 'rm -rf "$WORK"' EXIT
chmod 700 "$WORK"
( umask 077; printf '%s' "$ASC_API_KEY_P8_B64" | base64 --decode > "$WORK/key.p8" )
CREDS=(--key "$WORK/key.p8" --key-id "$ASC_KEY_ID" --issuer "$ASC_ISSUER_ID")

UPLOAD=$TARGET
if [[ $KIND == app ]]; then
  UPLOAD="$WORK/upload.zip"
  ditto -c -k --keepParent "$TARGET" "$UPLOAD"
fi

xcrun notarytool submit "$UPLOAD" "${CREDS[@]}" --wait --timeout 45m --output-format json > "$WORK/submit.json"
read -r STATUS SUBMISSION < <(python3 -c '
import json, sys
d = json.load(open(sys.argv[1])); print(d.get("status") or "unknown", d.get("id") or "-")' "$WORK/submit.json")
if [[ "$STATUS" != Accepted ]]; then
  echo "notarize: Apple answered $STATUS for submission $SUBMISSION; its log follows" >&2
  xcrun notarytool log "$SUBMISSION" "${CREDS[@]}" >&2 || true
  exit 1
fi
echo "notarize: $TARGET accepted (submission $SUBMISSION)" >&2

xcrun stapler staple "$TARGET" >&2
xcrun stapler validate "$TARGET" >&2
case $KIND in
  app) spctl --assess --type execute --verbose=2 "$TARGET" ;;
  dmg) spctl --assess --type open --context context:primary-signature --verbose=2 "$TARGET" ;;
  pkg) spctl --assess --type install --verbose=2 "$TARGET" ;;
esac
echo "submission=$SUBMISSION"
