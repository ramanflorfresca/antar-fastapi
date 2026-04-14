import os, json
from dotenv import load_dotenv
load_dotenv()
from supabase import create_client

url = os.environ["SUPABASE_URL"]
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")
sb = create_client(url, key)

r = sb.table("charts").select("chart_data").eq("id", "de02bb52-d43a-4b09-be25-b45a07bfbf8a").single().execute()
cd = r.data["chart_data"]
if isinstance(cd, str):
    cd = json.loads(cd)

print("Top-level chart_data keys:")
for k in sorted(cd.keys()):
    v = cd[k]
    if isinstance(v, dict):
        print(f"  {k}: dict with {len(v)} keys: {list(v.keys())[:5]}")
    elif isinstance(v, list):
        print(f"  {k}: list[{len(v)}]")
    else:
        print(f"  {k}: {type(v).__name__} = {str(v)[:60]}")

print()
print("Looking for D9-ish keys anywhere in the nested structure...")

def find_d9(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            newpath = f"{path}.{k}" if path else k
            if "d9" in k.lower() or "navamsa" in k.lower() or k == "D9":
                print(f"  FOUND: {newpath} -> {type(v).__name__}")
                if isinstance(v, dict):
                    print(f"    keys: {list(v.keys())[:10]}")
                    if "planets" in v:
                        pc = len(v["planets"]) if isinstance(v["planets"], dict) else "not a dict"
                        print(f"    planets count: {pc}")
            find_d9(v, newpath)

find_d9(cd)
