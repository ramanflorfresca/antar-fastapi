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
    ap.add_argument("--with-hindi", action="store_true", help="also create/submit the Devanagari Hindi templates (locale hi)")
    a = ap.parse_args()
    sid, tok = os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN")
    if a.go and not (sid and tok):
        # a dry run needs no credentials; a real run without them used to send "None:None" and die on a 401
        sys.exit("Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN in the environment before using --go "
                 "(nothing was sent).")
    auth = base64.b64encode(f"{sid}:{tok}".encode()).decode()
    for name, t in wt.TEMPLATES.items():
        if a.only and name != a.only:
            continue
        # Hindi (locale "hi") is drafted but only created when asked: --with-hindi, or --lang hi
        for lang in (wt.ALL_LANGS if (a.with_hindi or a.lang == "hi") else wt.LANGS):
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
