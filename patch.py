"""
patch_exec_simple.py
Adds the executive-summary endpoint to main.py safely.

Usage: python patch_exec_simple.py
"""
import os
import shutil

def main():
    target = "main.py"
    backup = "main.py.bak_exec_simple"
    
    if not os.path.exists(target):
        print("ERROR: main.py not found. Run from project root.")
        return
    
    # Read current file
    with open(target, "r") as f:
        content = f.read()
    
    # Check if already added
    if "executive-summary" in content:
        print("executive-summary endpoint already exists. Nothing to do.")
        return
    
    # Backup
    shutil.copy2(target, backup)
    print("Backed up to " + backup)
    
    # The endpoint code to insert
    # Using plain string concatenation to avoid any escaping issues
    endpoint = []
    endpoint.append("")
    endpoint.append("")
    endpoint.append("# --- EXECUTIVE SUMMARY ENDPOINT (auto-inserted) ---")
    endpoint.append("@app.get(\"/api/v1/executive-summary/{chart_id}\")")
    endpoint.append("async def get_executive_summary(chart_id: str):")
    endpoint.append("    try:")
    endpoint.append("        from antar_engine.symptom_library import build_executive_summary")
    endpoint.append("        from datetime import datetime as _exdt")
    endpoint.append("        cr = supabase.table(\"charts\").select(\"chart_data, jaimini_data, lal_kitab_data\").eq(\"id\", chart_id).single().execute()")
    endpoint.append("        if not cr.data:")
    endpoint.append("            return {\"error\": \"Chart not found\"}")
    endpoint.append("        cd = cr.data.get(\"chart_data\", {})")
    endpoint.append("        jd = cr.data.get(\"jaimini_data\", {})")
    endpoint.append("        lk = cr.data.get(\"lal_kitab_data\", {})")
    endpoint.append("        now_str = _exdt.utcnow().isoformat()")
    endpoint.append("        dr = supabase.table(\"dasha_periods\").select(\"planet_or_sign, level, end_date\").eq(\"chart_id\", chart_id).eq(\"system\", \"vimsottari\").lte(\"start_date\", now_str).gte(\"end_date\", now_str).order(\"level\").execute()")
    endpoint.append("        dasha_list = dr.data if dr.data else []")
    endpoint.append("        current_dasha = \"\"")
    endpoint.append("        md_row = None")
    endpoint.append("        ad_row = None")
    endpoint.append("        for d in dasha_list:")
    endpoint.append("            if d.get(\"level\") == 1:")
    endpoint.append("                md_row = d")
    endpoint.append("            if d.get(\"level\") == 2:")
    endpoint.append("                ad_row = d")
    endpoint.append("        if md_row:")
    endpoint.append("            current_dasha = md_row[\"planet_or_sign\"].strip()")
    endpoint.append("            if ad_row:")
    endpoint.append("                current_dasha = current_dasha + \"-\" + ad_row[\"planet_or_sign\"].strip()")
    endpoint.append("        result = build_executive_summary(cd, jd, lk, current_dasha, dasha_list)")
    endpoint.append("        return result")
    endpoint.append("    except Exception as e:")
    endpoint.append("        import traceback")
    endpoint.append("        traceback.print_exc()")
    endpoint.append("        return {\"error\": str(e)}")
    endpoint.append("# --- END EXECUTIVE SUMMARY ENDPOINT ---")
    endpoint.append("")
    
    endpoint_text = "\n".join(endpoint)
    
    # Strategy: find "if __name__" and insert before it
    marker = 'if __name__'
    idx = content.find(marker)
    
    if idx > 0:
        content = content[:idx] + endpoint_text + "\n\n" + content[idx:]
        print("Inserted before 'if __name__'")
    else:
        # No if __name__ block, just append to end
        content = content + endpoint_text
        print("Appended to end of file")
    
    # Write
    with open(target, "w") as f:
        f.write(content)
    
    print("Done. Endpoint added.")
    print("")
    print("Deploy:")
    print("  git add -A && git commit -m 'feat: executive-summary endpoint' && git push")


if __name__ == "__main__":
    main()
