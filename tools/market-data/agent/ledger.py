#!/usr/bin/env python3
"""Tamper-evident ledger for the BITFIN journal.

Each record is sealed with (a) a SHA-256 hash chained to the previous record and
(b) an ed25519 signature over that hash. Editing any past record breaks the chain
for every record after it, and forging a record requires the private key (kept
off-repo at /opt/quant/.bitfin_ledger_key, chmod 600). The public key is published
next to the code so anyone can verify with verify_ledger.py.
"""
import os, json, hashlib
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
HERE = os.path.dirname(os.path.abspath(__file__))
KEY_PATH = os.environ.get('BITFIN_LEDGER_KEY', '/opt/quant/.bitfin_ledger_key')
PUB_PATH = os.path.join(HERE, 'ledger_pub.hex')
GENESIS = '0' * 64
_SK = None

def _key():
    global _SK
    if _SK is not None: return _SK
    if os.path.exists(KEY_PATH):
        _SK = Ed25519PrivateKey.from_private_bytes(open(KEY_PATH, 'rb').read())
    else:
        _SK = Ed25519PrivateKey.generate()
        raw = _SK.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())
        fd = os.open(KEY_PATH, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600); os.write(fd, raw); os.close(fd)
    pub = _SK.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
    if not (os.path.exists(PUB_PATH) and open(PUB_PATH).read().strip() == pub):
        open(PUB_PATH, 'w').write(pub)   # publish pubkey for third-party verification
    return _SK

def canon(rec):
    """Canonical bytes of a record, excluding the seal fields."""
    r = {k: v for k, v in rec.items() if k not in ('prev', 'h', 'sig')}
    return json.dumps(r, sort_keys=True, separators=(',', ':')).encode()

def head_hash(journal_path):
    last = GENESIS
    if os.path.exists(journal_path):
        for ln in open(journal_path):
            ln = ln.strip()
            if ln:
                try: last = json.loads(ln).get('h', last)
                except Exception: pass
    return last

def seal(rec, prev_hash):
    h = hashlib.sha256(prev_hash.encode() + canon(rec)).hexdigest()
    sig = _key().sign(bytes.fromhex(h)).hex()
    out = dict(rec); out['prev'] = prev_hash; out['h'] = h; out['sig'] = sig
    return out
