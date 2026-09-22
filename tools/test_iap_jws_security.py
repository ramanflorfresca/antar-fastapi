#!/usr/bin/env python3
"""
tools/test_iap_jws_security.py — proves the Apple JWS verifier actually
rejects forgeries.

The end-to-end test only shows that malformed input is refused. What matters
is the real attack: a WELL-FORMED JWS signed by a certificate the attacker
controls. If chain validation is wrong, that forgery buys a free subscription
forever, so it is tested here against a synthetic CA hierarchy.

Run:  ./venv311/bin/python tools/test_iap_jws_security.py
"""
import base64
import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature

NOW = datetime.now(timezone.utc)


def make_cert(cn, issuer_cert=None, issuer_key=None, not_after_days=365):
    key = ec.generate_private_key(ec.SECP256R1())
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])
    issuer = issuer_cert.subject if issuer_cert else subject
    signing_key = issuer_key or key
    cert = (x509.CertificateBuilder()
            .subject_name(subject).issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(NOW - timedelta(days=1))
            .not_valid_after(NOW + timedelta(days=not_after_days))
            .sign(signing_key, hashes.SHA256()))
    return key, cert


def b64u(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def make_jws(payload: dict, signing_key, chain):
    header = {"alg": "ES256",
              "x5c": [base64.b64encode(c.public_bytes(serialization.Encoding.DER)).decode()
                      for c in chain]}
    h = b64u(json.dumps(header).encode())
    p = b64u(json.dumps(payload).encode())
    der = signing_key.sign(f"{h}.{p}".encode(), ec.ECDSA(hashes.SHA256()))
    r, s = decode_dss_signature(der)
    raw = r.to_bytes(32, "big") + s.to_bytes(32, "big")
    return f"{h}.{p}.{b64u(raw)}"


# Synthetic "Apple" hierarchy: root -> intermediate -> leaf
root_key, root_cert = make_cert("Synthetic Root")
int_key, int_cert = make_cert("Synthetic Intermediate", root_cert, root_key)
leaf_key, leaf_cert = make_cert("Synthetic Leaf", int_cert, int_key)

# Attacker's own hierarchy — structurally identical, different root.
evil_root_key, evil_root_cert = make_cert("Evil Root")
evil_key, evil_cert = make_cert("Evil Leaf", evil_root_cert, evil_root_key)

os.environ["APPLE_ROOT_CA_PEM"] = root_cert.public_bytes(
    serialization.Encoding.PEM).decode()

import antar_engine.iap_renewals as R

PAYLOAD = {"notificationType": "DID_RENEW", "data": {"bundleId": "world.antar.app"}}
PASS = FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name} {detail}")


def rejects(name, jws):
    try:
        R.verify_apple_jws(jws)
        check(name, False, "ACCEPTED A FORGERY")
    except ValueError as e:
        check(name, True)
    except Exception as e:
        check(name, False, f"wrong error type {type(e).__name__}: {e}")


print("\nJWS verification")

good = make_jws(PAYLOAD, leaf_key, [leaf_cert, int_cert, root_cert])
try:
    out = R.verify_apple_jws(good)
    check("genuine chain verifies", out["notificationType"] == "DID_RENEW", str(out))
except Exception as e:
    check("genuine chain verifies", False, f"{type(e).__name__}: {e}")

# THE attack: valid signature, valid self-consistent chain, wrong root.
rejects("attacker-rooted chain rejected",
        make_jws(PAYLOAD, evil_key, [evil_cert, evil_root_cert]))

# Leaf swapped in under the real root without being signed by it.
rejects("leaf not issued by the chain rejected",
        make_jws(PAYLOAD, evil_key, [evil_cert, int_cert, root_cert]))

# Payload tampered after signing.
h, p, s = good.split(".")
tampered = {"notificationType": "DID_RENEW", "data": {"bundleId": "evil.app"}}
rejects("tampered payload rejected", f"{h}.{b64u(json.dumps(tampered).encode())}.{s}")

# Signature replaced with noise.
rejects("bad signature rejected", f"{h}.{p}.{b64u(b'0' * 64)}")

# No chain at all.
no_chain = ".".join([b64u(json.dumps({"alg": "ES256"}).encode()),
                     b64u(json.dumps(PAYLOAD).encode()), b64u(b"0" * 64)])
rejects("missing x5c rejected", no_chain)

# alg confusion.
alt = {"alg": "none", "x5c": [base64.b64encode(
    leaf_cert.public_bytes(serialization.Encoding.DER)).decode()]}
rejects("alg=none rejected",
        ".".join([b64u(json.dumps(alt).encode()),
                  b64u(json.dumps(PAYLOAD).encode()), b64u(b"0" * 64)]))

# Expired leaf, otherwise genuine.
exp_key, exp_cert = make_cert("Expired Leaf", int_cert, int_key, not_after_days=-1)
rejects("expired certificate rejected",
        make_jws(PAYLOAD, exp_key, [exp_cert, int_cert, root_cert]))

# Fail closed when no root is configured at all.
os.environ.pop("APPLE_ROOT_CA_PEM")
os.environ["APPLE_ROOT_CA_PATH"] = "/nonexistent/root.pem"
rejects("no root configured -> fails closed", good)
os.environ["APPLE_ROOT_CA_PEM"] = root_cert.public_bytes(
    serialization.Encoding.PEM).decode()
os.environ.pop("APPLE_ROOT_CA_PATH")

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
