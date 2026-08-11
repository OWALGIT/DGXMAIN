#!/usr/bin/env python3
"""Turn a Storj *access grant* into S3-compatible credentials via the hosted
auth service over plain HTTPS.

Why this exists: Storj's native protocol (satellite :7777, uplink DRPC) does not
traverse an HTTPS-only egress proxy, and the `uplink` Go binary ignores
HTTPS_PROXY. The auth service, however, exposes a REST endpoint on :443 that any
proxy-aware HTTP client can reach. Registering the grant there returns
gateway.storjshare.io S3 keys that boto3 can use directly.

Usage:
    python3 register_access.py "<ACCESS_GRANT>"
    # prints: export STORJ_ENDPOINT=... STORJ_KEY=... STORJ_SECRET=...
"""
import sys, json, urllib.request

AUTH = "https://auth.storjshare.io/v1/access"


def register(grant: str) -> dict:
    body = json.dumps({"access_grant": grant, "public": False}).encode()
    req = urllib.request.Request(AUTH, data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.loads(r.read().decode())


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: register_access.py <ACCESS_GRANT>")
    c = register(sys.argv[1])
    print(f"export STORJ_ENDPOINT={c['endpoint']}")
    print(f"export STORJ_KEY={c['access_key_id']}")
    print(f"export STORJ_SECRET={c['secret_key']}")
