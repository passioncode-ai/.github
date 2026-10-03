#!/bin/bash
# Issue a CI-only Apple signing certificate and package it as a .p12, without any Keychain.
#
#   scripts/new-apple-cert.sh DEVELOPER_ID_APPLICATION <private dir>
#   scripts/new-apple-cert.sh MAC_APP_DISTRIBUTION     <private dir>
#   scripts/new-apple-cert.sh MAC_INSTALLER_DISTRIBUTION <private dir>
#   scripts/new-apple-cert.sh --csr-only <private dir>                 then, after the portal:
#   scripts/new-apple-cert.sh --cert-id <ID> DEVELOPER_ID_APPLICATION <same dir>
#
# Developer ID certificates can be issued only by the Account Holder: the API answers 403
# ("This operation can only be performed by the Account Holder", measured 2026-10-03). For
# them, --csr-only makes key.pem and csr.pem; the Account Holder uploads csr.pem at
# developer.apple.com → Certificates → + → Developer ID Application (G2 Sub-CA); then
# --cert-id fetches the issued certificate through the API and packages it.
#
# The private key is generated here with openssl (RSA 2048, what Apple accepts), the CSR is
# sent through the App Store Connect API (scripts/asc.py; ASC_* in the environment), and
# <dir> receives: cert.cer (DER), cert.pem, key.pem, cert.p12 (key + certificate + Apple's
# intermediate, legacy PBE so macOS `security import` reads it) and p12.password. Nothing
# secret is printed: the output is the certificate's id, name, serial and expiry, and the
# p12's sha256 prefix. <dir> must not exist yet; it is created 0700.
#
# The caller then stores cert.p12 (base64) and p12.password in the vault over stdin and
# deletes <dir>. Design: docs/release-signing/DESIGN.md → Credentials.
set -euo pipefail
MODE=create; CERT_ID=
if [[ "${1:-}" == "--csr-only" ]]; then MODE=csr; shift; set -- DEVELOPER_ID_APPLICATION "$@"; fi
if [[ "${1:-}" == "--cert-id" ]]; then MODE=fetch; CERT_ID=${2:?certificate id}; shift 2; fi
TYPE=${1:?type: DEVELOPER_ID_APPLICATION, MAC_APP_DISTRIBUTION or MAC_INSTALLER_DISTRIBUTION}
DIR=${2:?a new private directory}
HERE=$(cd "$(dirname "$0")" && pwd)
PYTHON=${ASC_PYTHON:-python3}

case "$TYPE" in
  DEVELOPER_ID_APPLICATION|DEVELOPER_ID_INSTALLER) CA_URLS="https://www.apple.com/certificateauthority/DeveloperIDG2CA.cer https://www.apple.com/certificateauthority/DeveloperIDCA.cer" ;;
  MAC_APP_DISTRIBUTION|MAC_INSTALLER_DISTRIBUTION|DISTRIBUTION) CA_URLS="https://www.apple.com/certificateauthority/AppleWWDRCAG3.cer https://www.apple.com/certificateauthority/AppleWWDRCAG4.cer" ;;
  *) echo "new-apple-cert.sh: unsupported type $TYPE" >&2; exit 2 ;;
esac
if [[ "$MODE" == fetch ]]; then
  [[ -f "$DIR/key.pem" ]] || { echo "new-apple-cert.sh: $DIR/key.pem missing; run --csr-only into it first" >&2; exit 2; }
else
  [[ ! -e "$DIR" ]] || { echo "new-apple-cert.sh: $DIR exists; give a new directory" >&2; exit 2; }
fi
for v in ASC_KEY_ID ASC_ISSUER_ID ASC_API_KEY_P8_B64; do
  [[ -n "${!v:-}" ]] || { echo "new-apple-cert.sh: $v is not set (run under the vault's use_secret.py)" >&2; exit 2; }
done

umask 077
if [[ "$MODE" != fetch ]]; then
  mkdir -m 700 "$DIR"
  openssl genrsa -out "$DIR/key.pem" 2048 2>/dev/null
  openssl req -new -key "$DIR/key.pem" -subj "/CN=PassionCode CI $TYPE" -out "$DIR/csr.pem"
fi
case "$MODE" in
  csr) printf 'csr: %s (upload it in the portal, then run --cert-id)\n' "$DIR/csr.pem"; exit 0 ;;
  fetch) "$PYTHON" "$HERE/asc.py" get-cert "$CERT_ID" "$DIR/cert.cer" ;;
  create) "$PYTHON" "$HERE/asc.py" create-cert "$TYPE" "$DIR/csr.pem" "$DIR/cert.cer" ;;
esac
# The issued certificate must carry this key: compare the public keys.
[[ "$(openssl x509 -inform der -in "$DIR/cert.cer" -noout -pubkey)" == "$(openssl pkey -in "$DIR/key.pem" -pubout)" ]] \
  || { echo "new-apple-cert.sh: the certificate does not match key.pem" >&2; exit 1; }
openssl x509 -inform der -in "$DIR/cert.cer" -out "$DIR/cert.pem"

# The intermediate that issued it, so a runner's keychain can build the chain to Apple's root.
ISSUER=$(openssl x509 -in "$DIR/cert.pem" -noout -issuer)
: > "$DIR/chain.pem"
for url in $CA_URLS; do
  curl -fsSL "$url" -o "$DIR/ca.cer"
  openssl x509 -inform der -in "$DIR/ca.cer" -out "$DIR/ca.pem"
  SUBJECT=$(openssl x509 -in "$DIR/ca.pem" -noout -subject)
  if [[ "${ISSUER#issuer=}" == "${SUBJECT#subject=}" ]]; then cp "$DIR/ca.pem" "$DIR/chain.pem"; break; fi
done
[[ -s "$DIR/chain.pem" ]] || { echo "new-apple-cert.sh: no known Apple intermediate matches: $ISSUER" >&2; exit 1; }

openssl rand -base64 30 | tr -d '\n' > "$DIR/p12.password"
openssl pkcs12 -export -legacy -inkey "$DIR/key.pem" -in "$DIR/cert.pem" -certfile "$DIR/chain.pem" \
  -name "PassionCode CI $TYPE" -passout "file:$DIR/p12.password" -out "$DIR/cert.p12"
rm -f "$DIR/csr.pem" "$DIR/ca.cer" "$DIR/ca.pem"
printf 'p12 sha256 %s\n' "$(shasum -a 256 "$DIR/cert.p12" | cut -c1-12)"
