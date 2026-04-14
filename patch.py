#!/usr/bin/env python3
"""
patch_phase4c_fix_return.py
Direct fix: add prediction + factors to JSON path return dict in main.py.
"""
import sys
from pathlib import Path

def main():
    if not Path("main.py").exists():
        print("❌ Run from ~/antarai/"); sys.exit(1)

    content = Path("main.py").read_text(encoding="utf-8")

    # Find the exact return dict by its unique anchor
    old = '                    "context_path": "json-v2",\n                    "tokens_used": _json_tokens,\n                }'
    new = '                    "prediction": (_parsed.get("verdict","") + " " + _parsed.get("plain_summary","")).strip(),\n                    "factors": _parsed.get("layers_used", []),\n                    "context_path": "json-v2",\n                    "tokens_used": _json_tokens,\n                }'

    if old not in content:
        print("❌ Pattern not found. Searching for context_path json-v2...")
        idx = content.find('"context_path": "json-v2"')
        if idx == -1:
            print("❌ json-v2 not found in main.py at all — JSON path may not be deployed")
            sys.exit(1)
        # Show context
        print("Found at char", idx)
        print(repr(content[idx-200:idx+100]))
        sys.exit(1)

    content = content.replace(old, new, 1)

    import ast
    try:
        ast.parse(content)
        print("✅ syntax OK")
    except SyntaxError as e:
        print(f"❌ {e}"); sys.exit(1)

    Path("main.py").write_text(content, encoding="utf-8")
    print("✅ prediction + factors added to JSON path return")
    print("\ngit add -A && git commit -m 'fix: add prediction+factors to json-v2 return' && git push")

if __name__ == "__main__":
    main()
