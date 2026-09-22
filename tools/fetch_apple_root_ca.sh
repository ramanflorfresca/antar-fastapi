#!/usr/bin/env bash
# Fetch Apple Root CA G3 — the trust anchor for App Store Server Notifications V2.
#
# antar_engine/iap_renewals.py FAILS CLOSED without it: an unverified Apple
# notification is an attacker-controlled renewal, so no cert means no renewals
# are processed at all.
#
# Usage:  bash tools/fetch_apple_root_ca.sh
# Then either commit certs/AppleRootCA-G3.pem, or put its contents in the
# APPLE_ROOT_CA_PEM env var on Railway (safer for a public repo).
set -euo pipefail

OUT_DIR="certs"
DER="${OUT_DIR}/AppleRootCA-G3.cer"
PEM="${OUT_DIR}/AppleRootCA-G3.pem"
URL="https://www.apple.com/appleca/AppleRootCA-G3.cer"

mkdir -p "$OUT_DIR"
echo "→ downloading ${URL}"
curl -fsSL "$URL" -o "$DER"

echo "→ converting DER to PEM"
openssl x509 -inform DER -in "$DER" -out "$PEM"

echo
echo "→ VERIFY THIS BEFORE TRUSTING IT:"
openssl x509 -in "$PEM" -noout -subject -issuer -fingerprint -sha256
echo
echo "Subject and issuer must both be Apple Inc. / Apple Root CA - G3 (it is"
echo "self-signed). Cross-check the SHA-256 fingerprint against Apple's own"
echo "listing at https://www.apple.com/certificateauthority/ before shipping."
echo
echo "Written: ${PEM}"
