#!/bin/bash
# Remove the throwaway keychain made by setup.sh, and take it out of the user's search list.
# Safe to run when setup failed half way or never ran.
set -uo pipefail
KEYCHAIN=${KEYCHAIN:?path of the keychain setup.sh created}
LIST=(); FOUND=
while IFS= read -r k; do
  if [[ "$k" == "$KEYCHAIN" ]]; then FOUND=1; elif [[ -n "$k" ]]; then LIST+=("$k"); fi
done < <(security list-keychains -d user | sed 's/^ *"//; s/" *$//')
if [[ -n "$FOUND" ]]; then security list-keychains -d user -s "${LIST[@]}"; fi
security delete-keychain "$KEYCHAIN" 2>/dev/null || true
rm -f "$KEYCHAIN"
echo "apple-signing: keychain removed"
