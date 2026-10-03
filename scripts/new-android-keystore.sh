#!/bin/bash
# Make an Android/Quest app's release keystore: one per app (organization decision D8).
#
#   scripts/new-android-keystore.sh <alias> "<distinguished name>" <private dir>
#   e.g. scripts/new-android-keystore.sh fabricvr "CN=Fabric VR, O=PassionCode.ai" /tmp/x
#
# PKCS12, RSA 4096, valid 30 years (10950 days), SHA256withRSA. PKCS12 has one password for
# the store and the key, so ANDROID_KEY_PASSWORD equals ANDROID_KEYSTORE_PASSWORD. <dir>
# (created 0700, must not exist) receives release.p12 and password; the certificate's SHA-256
# fingerprint is printed, nothing secret. The caller stores both in the vault over stdin
# (ANDROID_KEYSTORE_B64 = base64 of release.p12), publishes the fingerprint in the app's
# docs, and deletes <dir>. Losing this key means the installed app can never be updated: the
# vault's encrypted off-disk backup is the second copy, so run `vault.py backup` after storing.
# KEYTOOL may name keytool (e.g. Android Studio's JBR) when the system has no Java.
set -euo pipefail
ALIAS=${1:?alias}; DNAME=${2:?distinguished name}; DIR=${3:?a new private directory}
KEYTOOL=${KEYTOOL:-keytool}
[[ ! -e "$DIR" ]] || { echo "new-android-keystore.sh: $DIR exists" >&2; exit 2; }
umask 077
mkdir -m 700 "$DIR"
openssl rand -base64 30 | tr -d '\n/+=' > "$DIR/password"
# keytool reads the passwords from files via :file, so they never reach argv.
"$KEYTOOL" -genkeypair -noprompt -storetype PKCS12 -keystore "$DIR/release.p12" \
  -storepass:file "$DIR/password" -keypass:file "$DIR/password" \
  -alias "$ALIAS" -dname "$DNAME" -keyalg RSA -keysize 4096 -sigalg SHA256withRSA -validity 10950
"$KEYTOOL" -list -v -storetype PKCS12 -keystore "$DIR/release.p12" -storepass:file "$DIR/password" -alias "$ALIAS" \
  | sed -n 's/^[[:space:]]*SHA256: /sha256 /p; s/^Valid from: /valid from /p'
