#!/usr/bin/env python3
"""
PATCH: Save Prashna verdicts to messages table (WhatsApp-style history)
Run: python patch_prashna_messages.py

What it does:
1. Adds user_id to the prashna chart query
2. After prashna_log insert, also saves user question + verdict to messages table
3. Creates/updates a conversation thread so verdicts appear in chat history
"""

import shutil
from pathlib import Path
import sys

MAIN = Path("main.py")
if not MAIN.exists():
    print("ERROR: main.py not found"); sys.exit(1)

backup = MAIN.with_suffix(".py.bak_prashna_msg")
shutil.copy2(MAIN, backup)
print(f"✅ Backup: {backup}")

code = MAIN.read_text()

# ═══════════════════════════════════════════════════════════════
# PATCH 1: Add user_id to prashna chart query
# ═══════════════════════════════════════════════════════════════
OLD_SELECT = '.select("chart_data, jaimini_data, lal_kitab_data, first_name, current_country, lagna_sign, latitude, longitude")'
NEW_SELECT = '.select("user_id, chart_data, jaimini_data, lal_kitab_data, first_name, current_country, lagna_sign, latitude, longitude")'

if "user_id, chart_data, jaimini_data, lal_kitab_data, first_name" in code:
    print("⏭️  Patch 1 already applied — skipping")
else:
    # Only replace the one in the prashna endpoint (first occurrence of this exact string)
    if OLD_SELECT in code:
        code = code.replace(OLD_SELECT, NEW_SELECT, 1)
        print("✅ Patch 1: Added user_id to prashna chart query")
    else:
        print("ERROR: Cannot find prashna chart select landmark")
        sys.exit(1)

# ═══════════════════════════════════════════════════════════════
# PATCH 2: Save prashna verdict to messages table after prashna_log insert
# ═══════════════════════════════════════════════════════════════
LANDMARK_MSG = "        # ─── 8. Also save to legacy prashna_readings for backward compat ───"

if "# ─── 7b. Save to messages table" in code:
    print("⏭️  Patch 2 already applied — skipping")
else:
    if LANDMARK_MSG not in code:
        print("ERROR: Cannot find prashna_readings landmark")
        sys.exit(1)

    MSG_INSERT = '''        # ─── 7b. Save to messages table (persistent chat history) ───
        try:
            _prashna_user_id = chart_data.get("user_id") or chart_id
            # Find or create a conversation for this chart's oracle questions
            _oracle_conv = supabase.table("conversations") \\
                .select("id") \\
                .eq("chart_id", chart_id) \\
                .eq("concern", "oracle") \\
                .order("created_at", desc=True) \\
                .limit(1) \\
                .execute()

            if _oracle_conv.data:
                _oracle_conv_id = _oracle_conv.data[0]["id"]
                supabase.table("conversations").update({
                    "preview": f"Oracle: {engine_result['verdict']} ({engine_result['score']}%)",
                    "last_message_at": datetime.now(timezone.utc).isoformat(),
                }).eq("id", _oracle_conv_id).execute()
            else:
                _new_conv = supabase.table("conversations").insert({
                    "user_id": _prashna_user_id,
                    "chart_id": chart_id,
                    "title": "Prashna Oracle",
                    "preview": f"Oracle: {engine_result['verdict']} ({engine_result['score']}%)",
                    "concern": "oracle",
                }).execute()
                _oracle_conv_id = _new_conv.data[0]["id"]

            # Get next sequence number
            _seq_res = supabase.table("messages") \\
                .select("sequence_number") \\
                .eq("conversation_id", _oracle_conv_id) \\
                .order("sequence_number", desc=True) \\
                .limit(1) \\
                .execute()
            _last_seq = _seq_res.data[0]["sequence_number"] if _seq_res.data else 0

            # User question message
            supabase.table("messages").insert({
                "conversation_id": _oracle_conv_id,
                "user_id": _prashna_user_id,
                "role": "user",
                "sequence_number": _last_seq + 1,
                "content": question,
                "concern": engine_result.get("domain", "general"),
            }).execute()

            # Oracle verdict message
            _verdict_content = (
                f"[ORACLE VERDICT] {engine_result['verdict']} ({engine_result['score']}%)\\n"
                f"Domain: {engine_result['domain']}\\n"
                f"Timing: {engine_result['timing']}\\n\\n"
                f"{explanation}\\n\\n"
                f"Remedy: {remedy.get('practice', '')}"
            )
            supabase.table("messages").insert({
                "conversation_id": _oracle_conv_id,
                "user_id": _prashna_user_id,
                "role": "assistant",
                "sequence_number": _last_seq + 2,
                "content": _verdict_content,
                "concern": engine_result.get("domain", "general"),
                "confidence": engine_result["score"] / 100.0,
                "full_response": {
                    "type": "prashna_verdict",
                    "verdict": engine_result["verdict"],
                    "score": engine_result["score"],
                    "domain": engine_result["domain"],
                    "timing": engine_result["timing"],
                    "proof_bars": engine_result.get("proof_bars"),
                    "domain_audit": engine_result.get("domain_audit"),
                    "cooldown_until": engine_result.get("cooldown_until"),
                },
            }).execute()

            print(f"[prashna] Saved to messages table conv={_oracle_conv_id}")
        except Exception as _msg_err:
            print(f"[prashna] Messages save failed (non-fatal): {_msg_err}")

''' + LANDMARK_MSG

    code = code.replace(LANDMARK_MSG, MSG_INSERT, 1)
    print("✅ Patch 2: Added prashna verdict save to messages table")

# ═══════════════════════════════════════════════════════════════
# WRITE
# ═══════════════════════════════════════════════════════════════
MAIN.write_text(code)
print(f"\n✅ ALL PATCHES APPLIED — main.py updated")
print(f"   Backup at: {backup}")
print(f"\n📋 Next steps:")
print(f"   1. git add main.py && git commit -m 'feat: save prashna verdicts to messages table for persistent history'")
print(f"   2. git push")
print(f"   3. Test: ask a prashna question, then check conversations endpoint")
print(f"   4. curl https://antar-fastapi-production.up.railway.app/api/v1/conversations -H 'Authorization: <token>' | python -m json.tool")
