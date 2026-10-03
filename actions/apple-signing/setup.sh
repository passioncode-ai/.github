#!/bin/bash
# Put Apple signing identities into a throwaway keychain that `codesign` and `productbuild`
# use without any prompt, and print the Developer ID identity's full name.
#
# Inputs (environment): DEVELOPER_ID_P12_B64 + P12_PASSWORD (required);
# DISTRIBUTION_P12_B64, INSTALLER_P12_B64 + MAS_P12_PASSWORD (optional, Mac App Store);
# TEAM_ID (required: the identity must belong to it); KEYCHAIN (path to create);
# SEARCH_LIST=1 to put the keychain first in the user's search list (CI); without it the
# keychain is only usable through `codesign --keychain`, which a local check relies on so the
# person's own search list is never touched.
# Outputs (stdout, KEY=value lines): identity, keychain, and mas_app_identity /
# mas_installer_identity when given. Values of the inputs are never printed.
set -euo pipefail

need() { [[ -n "${!1:-}" ]] || { echo "apple-signing: $1 is empty; is the release environment's secret set?" >&2; exit 2; }; }
need DEVELOPER_ID_P12_B64; need P12_PASSWORD; need TEAM_ID; need KEYCHAIN

WORK=$(mktemp -d); trap 'rm -rf "$WORK"' EXIT; chmod 700 "$WORK"
KC_PASSWORD=$(openssl rand -base64 24)
security create-keychain -p "$KC_PASSWORD" "$KEYCHAIN"
security set-keychain-settings -lut 21600 "$KEYCHAIN"      # stays unlocked for a 6-hour job
security unlock-keychain -p "$KC_PASSWORD" "$KEYCHAIN"

import_p12() { # $1 = base64 var name, $2 = password var name
  printf '%s' "${!1}" | base64 --decode > "$WORK/id.p12"
  security import "$WORK/id.p12" -k "$KEYCHAIN" -f pkcs12 -P "${!2}" \
    -T /usr/bin/codesign -T /usr/bin/productbuild -T /usr/bin/productsign -T /usr/bin/security >/dev/null
  rm -f "$WORK/id.p12"
}
import_p12 DEVELOPER_ID_P12_B64 P12_PASSWORD
if [[ -n "${DISTRIBUTION_P12_B64:-}" ]]; then need MAS_P12_PASSWORD; import_p12 DISTRIBUTION_P12_B64 MAS_P12_PASSWORD; fi
if [[ -n "${INSTALLER_P12_B64:-}" ]]; then need MAS_P12_PASSWORD; import_p12 INSTALLER_P12_B64 MAS_P12_PASSWORD; fi

# Without this, the first use of the key raises "codesign wants to access key" and a CI job hangs.
security set-key-partition-list -S apple-tool:,apple:,codesign: -s -k "$KC_PASSWORD" "$KEYCHAIN" >/dev/null

# The user's search list, one path per element (bash 3.2: no mapfile; paths may hold spaces).
search_list() { security list-keychains -d user | sed 's/^ *"//; s/" *$//'; }
if [[ "${SEARCH_LIST:-}" == 1 ]]; then
  LIST=("$KEYCHAIN")
  while IFS= read -r k; do [[ -n "$k" && "$k" != "$KEYCHAIN" ]] && LIST+=("$k"); done < <(search_list)
  security list-keychains -d user -s "${LIST[@]}"
fi

identity() { # the full name of the first valid identity whose name starts with $1 and carries the team
  # `|| true`: no match is an empty answer, not an error. Under `set -e -o pipefail` a failing
  # grep inside `X=$(identity …)` would end the script silently before the fallback name is tried.
  security find-identity -v -p "${2:-codesigning}" "$KEYCHAIN" \
    | sed -n 's/^ *[0-9]*) [0-9A-F]\{40\} "\(.*\)"$/\1/p' | grep -F "$1" | grep -F "($TEAM_ID)" | head -n 1 || true
}
ID=$(identity "Developer ID Application:")
[[ -n "$ID" ]] || { echo "apple-signing: no valid 'Developer ID Application' identity of team $TEAM_ID in the .p12" >&2; exit 1; }
echo "identity=$ID"
echo "keychain=$KEYCHAIN"
if [[ -n "${DISTRIBUTION_P12_B64:-}" ]]; then
  MAS=$(identity "Apple Distribution:")
  [[ -n "$MAS" ]] || MAS=$(identity "3rd Party Mac Developer Application:")
  [[ -n "$MAS" ]] || { echo "apple-signing: no Mac App Store application identity of team $TEAM_ID" >&2; exit 1; }
  echo "mas_app_identity=$MAS"
fi
if [[ -n "${INSTALLER_P12_B64:-}" ]]; then
  # Installer identities are not code-signing identities; find-identity lists them under `basic`.
  INST=$(identity "3rd Party Mac Developer Installer:" basic)
  [[ -n "$INST" ]] || INST=$(identity "Mac Installer Distribution:" basic)
  [[ -n "$INST" ]] || { echo "apple-signing: no Mac installer identity of team $TEAM_ID" >&2; exit 1; }
  echo "mas_installer_identity=$INST"
fi
