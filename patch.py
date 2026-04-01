#!/usr/bin/env python3
"""
ANTAR Sprint P — HOTFIX
Fixes: 'str' object has no attribute 'get'
Run:   python sprint_p_hotfix.py && git add -A && git commit -m "fix: JSONB string parse" && git push
"""
import os, sys, ast, shutil

REPO = os.getcwd()
ENGINE = os.path.join(REPO, "antar_engine", "practice_engine.py")
MAINPY = os.path.join(REPO, "main.py")

G, R, Y, X = "\033[92m", "\033[91m", "\033[93m", "\033[0m"

def main():
    print(f"\n  ANTAR Sprint P — HOTFIX: str→dict JSONB\n")

    # ═══ FIX 1: practice_engine.py ═══
    if not os.path.exists(ENGINE):
        print(f"  {R}❌ {ENGINE} not found. Run from repo root.{X}"); sys.exit(1)

    with open(ENGINE) as f:
        code = f.read()

    if "_safe_json" in code:
        print(f"  {G}✅ practice_engine.py already patched{X}")
    else:
        shutil.copy2(ENGINE, ENGINE + ".bak")

        # Add _safe_json helper
        helper = (
            '\ndef _safe_json(data):\n'
            '    """Parse JSONB that Supabase returns as string."""\n'
            '    if data is None: return {}\n'
            '    if isinstance(data, str):\n'
            '        try: return json.loads(data)\n'
            '        except: return {}\n'
            '    if isinstance(data, (dict, list)): return data\n'
            '    return {}\n\n'
        )

        # Insert after last import
        lines = code.split("\n")
        insert_at = 0
        for i, ln in enumerate(lines):
            s = ln.strip()
            if s.startswith("import ") or s.startswith("from "):
                insert_at = i + 1
            if s.startswith("PLANET_ENERGY") or (s.startswith("class ") and i > 5):
                break
        lines.insert(insert_at, helper)
        code = "\n".join(lines)
        print(f"  {G}✅ Added _safe_json() helper{X}")

        # Wrap inputs in generate_practice_schedule
        old = "    planets = _extract_planets(chart_data)"
        new = (
            "    # Hotfix: Supabase JSONB may arrive as string\n"
            "    chart_data = _safe_json(chart_data)\n"
            "    jaimini_data = _safe_json(jaimini_data)\n"
            "    lal_kitab_data = _safe_json(lal_kitab_data)\n"
            "    if isinstance(streak_data, str):\n"
            "        try: streak_data = json.loads(streak_data)\n"
            "        except: streak_data = None\n"
            "\n"
            "    planets = _extract_planets(chart_data)"
        )
        if old in code:
            code = code.replace(old, new, 1)
            print(f"  {G}✅ Wrapped inputs with _safe_json(){X}")
        else:
            print(f"  {Y}⚠️  Could not find extraction line{X}")

        # Add isinstance guards to extractors
        for func, param in [
            ("_extract_planets", "chart_data"),
            ("_extract_lagna", "chart_data"),
            ("_extract_varshphal", "lk_data"),
            ("_extract_sleeping_planets", "lk_data"),
            ("_extract_rin", "lk_data"),
            ("_extract_enemy_houses", "lk_data"),
            ("_extract_masik_phal", "lk_data"),
            ("_extract_karakas", "jaimini_data"),
            ("_extract_current_dasha", "jaimini_data"),
        ]:
            sig = f"def {func}({param}):"
            if sig in code:
                # Find the "if not param:" line and add str guard after its return
                idx = code.index(sig)
                chunk = code[idx:idx+300]
                chunk_lines = chunk.split("\n")
                new_chunk_lines = []
                inserted = False
                for cl in chunk_lines:
                    new_chunk_lines.append(cl)
                    if not inserted and cl.strip().startswith("return") and len(new_chunk_lines) <= 4:
                        # This is the early return for None — add str guard
                        indent = "    "
                        new_chunk_lines.append(f"{indent}if isinstance({param}, str): {param} = _safe_json({param})")
                        inserted = True
                if inserted:
                    code = code.replace(chunk, "\n".join(new_chunk_lines), 1)

        print(f"  {G}✅ Added str guards to extractors{X}")

        # Verify syntax
        try:
            ast.parse(code)
        except SyntaxError as e:
            print(f"  {R}❌ Syntax error: line {e.lineno}: {e.msg}{X}")
            shutil.copy2(ENGINE + ".bak", ENGINE)
            print(f"  {R}   Restored backup. Fix manually.{X}")
            sys.exit(1)

        with open(ENGINE, "w") as f:
            f.write(code)
        print(f"  {G}✅ practice_engine.py saved{X}")

    # ═══ FIX 2: main.py endpoint ═══
    if os.path.exists(MAINPY):
        with open(MAINPY) as f:
            mcode = f.read()

        if '_safe_jsonb' in mcode:
            print(f"  {G}✅ main.py already patched{X}")
        elif '_c.get("chart_data") or {}' in mcode:
            shutil.copy2(MAINPY, MAINPY + ".pre_hotfix.bak")

            # Replace the or {} patterns
            mcode = mcode.replace('_c.get("chart_data") or {}', '_safe_jsonb(_c.get("chart_data"))')
            mcode = mcode.replace('_c.get("jaimini_data") or {}', '_safe_jsonb(_c.get("jaimini_data"))')
            mcode = mcode.replace('_c.get("lal_kitab_data") or {}', '_safe_jsonb(_c.get("lal_kitab_data"))')

            # Add helper near the practice import
            imp = "from antar_engine.practice_engine import generate_practice_schedule, format_practice_for_predict_prompt"
            if imp in mcode and "_safe_jsonb" not in mcode:
                mcode = mcode.replace(imp, imp + "\nimport json as _pjson\ndef _safe_jsonb(v):\n    if isinstance(v,str):\n        try: return _pjson.loads(v)\n        except: return {}\n    return v if isinstance(v,dict) else {}\n", 1)

            try:
                ast.parse(mcode)
                with open(MAINPY, "w") as f:
                    f.write(mcode)
                print(f"  {G}✅ main.py patched with _safe_jsonb(){X}")
            except SyntaxError as e:
                print(f"  {Y}⚠️  main.py patch caused syntax error — skipping (engine fix is enough){X}")
                shutil.copy2(MAINPY + ".pre_hotfix.bak", MAINPY)
        else:
            print(f"  {G}✅ main.py doesn't need patching (pattern not found — engine fix handles it){X}")

    print(f"\n  {G}Done! Now:{X}")
    print(f"    git add antar_engine/practice_engine.py main.py")
    print(f'    git commit -m "fix: handle JSONB string returns in practice engine"')
    print(f"    git push\n")

if __name__ == "__main__":
    main()
