"""Create Antar's WhatsApp templates in Twilio Content API and submit them to
Meta for approval. Run ONCE after the Twilio Business Profile is approved:

    TWILIO_ACCOUNT_SID=... TWILIO_AUTH_TOKEN=... venv311/bin/python scripts/twilio_create_templates.py

Credentials are read from the environment and never printed. Prints, for each
template × language, the ContentSid and the Railway variable to set once Meta
approves it (WA_TPL_<NAME>_<LANG>). Re-running skips names that already exist.
Use --dry-run to print the payloads without calling Twilio.
"""
import base64, json, os, sys, urllib.request
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from antar_engine import wa_templates as wt  # noqa: E402

API = "https://content.twilio.com/v1/Content"


def _auth():
    sid, tok = os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN")
    if not (sid and tok):
        sys.exit("Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN in the environment.")
    return {"Authorization": "Basic " + base64.b64encode(f"{sid}:{tok}".encode()).decode(),
            "Content-Type": "application/json"}


def _existing(h):
    names, url = {}, API + "?PageSize=200"
    while url:
        with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=20) as r:
            d = json.loads(r.read())
        for c in d.get("contents", []):
            names[c["friendly_name"]] = c["sid"]
        url = (d.get("meta") or {}).get("next_page_url")
    return names


def main():
    dry = "--dry-run" in sys.argv
    h = None if dry else _auth()
    have = {} if dry else _existing(h)
    for name, t in wt.TEMPLATES.items():
        # MARKETING (offers & news) is a separate, paid Meta category and a separate owner decision:
        # it is only created/submitted when asked for explicitly.
        if t["category"] == "MARKETING" and "--with-marketing" not in sys.argv:
            if not dry:
                print(f"skipped (marketing)  {name}   — pass --with-marketing to submit")
            continue
        for lang in wt.LANGS:
            p = wt.content_payload(name, lang)
            env = wt.env_key(name, lang)
            if dry:
                print(json.dumps(p, ensure_ascii=False, indent=1)); continue
            sid = have.get(p["friendly_name"])
            if not sid:
                req = urllib.request.Request(API, data=json.dumps(p).encode(), headers=h, method="POST")
                with urllib.request.urlopen(req, timeout=20) as r:
                    sid = json.loads(r.read())["sid"]
                appr = {"name": p["friendly_name"], "category": t["category"]}
                urllib.request.urlopen(urllib.request.Request(
                    f"{API}/{sid}/ApprovalRequests/whatsapp", data=json.dumps(appr).encode(),
                    headers=h, method="POST"), timeout=20)
                print(f"created + submitted  {p['friendly_name']:34s} {sid}")
            else:
                print(f"exists               {p['friendly_name']:34s} {sid}")
            print(f"   once APPROVED set Railway: {env}={sid}")


if __name__ == "__main__":
    main()
