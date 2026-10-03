#!/usr/bin/env python3
"""A minimal App Store Connect API client for release-signing setup.

Reads the team's API key from the environment, as the release workflows do:
ASC_KEY_ID, ASC_ISSUER_ID and ASC_API_KEY_P8_B64 (the .p8 file, base64). Run it under a
runner that injects them without printing, e.g. the Observatory's
`use_secret.py run --env prod <slot> ASC_API_KEY_P8_B64,ASC_KEY_ID,ASC_ISSUER_ID -- …`.

Commands:
  certs                              list certificates: id, type, name, serial, expiry
  create-cert TYPE CSR_FILE OUT_CER  issue a certificate of TYPE from a CSR, write the DER .cer
                                     (Developer ID types: refused unless the key is the Account Holder's)
  get-cert ID OUT_CER                write an existing certificate's DER .cer
  profiles                           list provisioning profiles: id, name, type, state
  bundle-ids                         list bundle ids: id, identifier, platform

Nothing here prints a key, a token or a certificate body; it prints ids, names and dates.
Requires the `cryptography` package (ES256 signing of the request token).
"""
from __future__ import annotations

import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature

API = "https://api.appstoreconnect.apple.com"


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def token() -> str:
    key = serialization.load_pem_private_key(base64.b64decode(os.environ["ASC_API_KEY_P8_B64"]), password=None)
    header = {"alg": "ES256", "kid": os.environ["ASC_KEY_ID"], "typ": "JWT"}
    now = int(time.time())
    claims = {"iss": os.environ["ASC_ISSUER_ID"], "iat": now, "exp": now + 600, "aud": "appstoreconnect-v1"}
    signing_input = _b64url(json.dumps(header).encode()) + "." + _b64url(json.dumps(claims).encode())
    der = key.sign(signing_input.encode(), ec.ECDSA(hashes.SHA256()))
    r, s = decode_dss_signature(der)
    return signing_input + "." + _b64url(r.to_bytes(32, "big") + s.to_bytes(32, "big"))


def call(method: str, path: str, body: dict | None = None) -> dict:
    req = urllib.request.Request(API + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": "Bearer " + token(), "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as err:
        detail = json.loads(err.read() or b"{}").get("errors", [])
        sys.exit(f"asc.py: {method} {path} -> HTTP {err.code}: "
                 + "; ".join(f"{e.get('code')}: {e.get('detail')}" for e in detail))


def paged(path: str):
    while path:
        doc = call("GET", path)
        yield from doc.get("data", [])
        nxt = doc.get("links", {}).get("next")
        path = nxt[len(API):] if nxt else None


def main(argv: list[str]) -> int:
    cmd = argv[0] if argv else ""
    if cmd == "certs":
        for c in paged("/v1/certificates?limit=200"):
            a = c["attributes"]
            print(c["id"], a.get("certificateType"), repr(a.get("name")), a.get("serialNumber"),
                  a.get("expirationDate"), sep="\t")
    elif cmd == "create-cert" and len(argv) == 4:
        csr = open(argv[2]).read()
        doc = call("POST", "/v1/certificates", {"data": {"type": "certificates", "attributes": {
            "certificateType": argv[1], "csrContent": csr}}})
        a = doc["data"]["attributes"]
        with open(argv[3], "wb") as f:
            f.write(base64.b64decode(a["certificateContent"]))
        print(doc["data"]["id"], a.get("certificateType"), repr(a.get("name")), a.get("serialNumber"),
              a.get("expirationDate"), sep="\t")
    elif cmd == "get-cert" and len(argv) == 3:
        doc = call("GET", f"/v1/certificates/{argv[1]}")
        a = doc["data"]["attributes"]
        with open(argv[2], "wb") as f:
            f.write(base64.b64decode(a["certificateContent"]))
        print(doc["data"]["id"], a.get("certificateType"), repr(a.get("name")), a.get("serialNumber"),
              a.get("expirationDate"), sep="\t")
    elif cmd == "profiles":
        for p in paged("/v1/profiles?limit=200"):
            a = p["attributes"]
            print(p["id"], repr(a.get("name")), a.get("profileType"), a.get("profileState"), a.get("expirationDate"), sep="\t")
    elif cmd == "bundle-ids":
        for b in paged("/v1/bundleIds?limit=200"):
            a = b["attributes"]
            print(b["id"], a.get("identifier"), a.get("platform"), repr(a.get("name")), sep="\t")
    else:
        print(__doc__, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
