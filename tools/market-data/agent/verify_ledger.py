#!/usr/bin/env python3
"""Verify the BITFIN ledger: recompute the hash-chain and check every ed25519
signature against the published pubkey. Anyone can run this — no private key needed.
Exit 0 = intact, 1 = tampered/unsealed."""
import os, json, hashlib, sys
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
HERE = os.path.dirname(os.path.abspath(__file__))
JOURNAL = os.path.join(HERE, 'journal.jsonl')
pk = Ed25519PublicKey.from_public_bytes(bytes.fromhex(open(os.path.join(HERE, 'ledger_pub.hex')).read().strip()))
GEN = '0' * 64
def canon(r): return json.dumps({k: v for k, v in r.items() if k not in ('prev', 'h', 'sig')}, sort_keys=True, separators=(',', ':')).encode()
prev, ok, bad = GEN, 0, []
for i, ln in enumerate(open(JOURNAL)):
    ln = ln.strip()
    if not ln: continue
    r = json.loads(ln)
    if 'h' not in r: bad.append([i, 'unsealed']); continue
    h = hashlib.sha256(prev.encode() + canon(r)).hexdigest()
    if h != r.get('h'): bad.append([i, 'chain-break']); prev = r.get('h', prev); continue
    if r.get('prev') != prev: bad.append([i, 'prev-mismatch'])
    try: pk.verify(bytes.fromhex(r['sig']), bytes.fromhex(h)); ok += 1
    except Exception: bad.append([i, 'bad-sig'])
    prev = h
print(json.dumps({'records_verified': ok, 'tampered': bad, 'head': prev[:16] + '...', 'status': 'OK' if not bad else 'TAMPERED'}))
sys.exit(0 if not bad else 1)
