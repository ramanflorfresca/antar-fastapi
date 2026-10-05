"""Create every antar_* WhatsApp template in Twilio's Content API and submit it to Meta for approval.

Usage:  python scripts/wa_submit_templates.py            # dry run: prints what would be created
        python scripts/wa_submit_templates.py --go       # creates + submits (needs TWILIO_ACCOUNT_SID/AUTH_TOKEN)
        python scripts/wa_submit_templates.py --go --only antar_checkin_v1 --lang hinglish

Prints the env lines to set once Meta approves (WA_TPL_<NAME>_<LANG>=HX…). Idempotent only by
friendly_name — re-running creates new Content rows, so run it once per template revision.
"""
import argparse
import base64
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from antar_engine import wa_templates as wt  # noqa: E402

CONTENT = "https://content.twilio.com/v1/Content"


def _post(url, payload, auth):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST",
                                 headers={"Authorization": "Basic " + auth, "Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--go", action="store_true")
    ap.add_argument("--only")
    ap.add_argument("--lang")
    a = ap.parse_args()
    auth = base64.b64encode(f"{os.getenv('TWILIO_ACCOUNT_SID')}:{os.getenv('TWILIO_AUTH_TOKEN')}".encode()).decode()
    for name, t in wt.TEMPLATES.items():
        if a.only and name != a.only:
            continue
        for lang in wt.LANGS:
            if a.lang and lang != a.lang:
                continue
            body = wt.content_payload(name, lang)
            tag = f"{name}/{lang} ({body['language']}, {t['category']})"
            if not a.go:
                print("would create", tag)
                continue
            c = _post(CONTENT, body, auth)
            _post(f"{CONTENT}/{c['sid']}/ApprovalRequests/whatsapp",
                  {"name": body["friendly_name"], "category": t["category"]}, auth)
            print(f"submitted {tag}\n  {wt.env_key(name, lang)}={c['sid']}")


if __name__ == "__main__":
    main()
