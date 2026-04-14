#!/usr/bin/env python3
"""
patch_phase4e_full_response.py
Replace the entire JSON path return dict to exactly match PredictResponse model.
Required: prediction(str), confidence(float), factors(List[str])
"""
import sys, ast
from pathlib import Path

def main():
    if not Path("main.py").exists():
        print("❌ Run from ~/antarai/"); sys.exit(1)

    content = Path("main.py").read_text(encoding="utf-8")

    # Find and replace the full return dict — anchor on the unique block
    old = '''                # Build prediction string (required by response model)
                _pred_text = (
                    _parsed.get("verdict", "") + " " +
                    _parsed.get("plain_summary", "")
                ).strip()

                return {
                    # Fields required by response model
                    "prediction": _pred_text,
                    "factors": _parsed.get("layers_used", []),
                    # Structured fields for frontend
                    "plain_summary": _parsed.get("plain_summary", ""),
                    "signal_line": _parsed.get("signal_line", ""),
                    "action_item": _parsed.get("action_item", ""),
                    "timing_window": _parsed.get("timing_window", ""),
                    "confidence": _parsed.get("confidence", ""),
                    "verdict": _parsed.get("verdict", ""),
                    "why_this": _parsed.get("why_this", ""),
                    "layers_used": _parsed.get("layers_used", []),
                    "bridge_practice_note": _parsed.get("bridge_practice_note", ""),
                    "prediction": (_parsed.get("verdict","") + " " + _parsed.get("plain_summary","")).strip(),
                    "factors": _parsed.get("layers_used", []),
                    "context_path": "json-v2",
                    "tokens_used": _json_tokens,
                }'''

    # Also try the version without the duplicate keys (after phase4c patch)
    old_v2 = '''                return {
                    "plain_summary": _parsed.get("plain_summary", ""),
                    "signal_line": _parsed.get("signal_line", ""),
                    "action_item": _parsed.get("action_item", ""),
                    "timing_window": _parsed.get("timing_window", ""),
                    "confidence": _parsed.get("confidence", ""),
                    "verdict": _parsed.get("verdict", ""),
                    "why_this": _parsed.get("why_this", ""),
                    "layers_used": _parsed.get("layers_used", []),
                    "bridge_practice_note": _parsed.get("bridge_practice_note", ""),
                    "prediction": (_parsed.get("verdict","") + " " + _parsed.get("plain_summary","")).strip(),
                    "factors": _parsed.get("layers_used", []),
                    "context_path": "json-v2",
                    "tokens_used": _json_tokens,
                }'''

    new_return = '''                # Map confidence string -> float for PredictResponse model
                _conf_map = {"high": 0.85, "medium": 0.65, "low": 0.45}
                _conf_str = str(_parsed.get("confidence", "medium")).lower()
                _conf_float = _conf_map.get(_conf_str, 0.65)
                _pred_text = (
                    _parsed.get("verdict", "") + " " + _parsed.get("plain_summary", "")
                ).strip()
                _factors = [str(x) for x in _parsed.get("layers_used", [])]

                return {
                    # Required fields (PredictResponse model)
                    "prediction":   _pred_text,
                    "confidence":   _conf_float,
                    "factors":      _factors,
                    # Optional structured fields for frontend
                    "plain_summary":        _parsed.get("plain_summary", ""),
                    "signal_line":          _parsed.get("signal_line", ""),
                    "action_item":          _parsed.get("action_item", ""),
                    "timing_window":        _parsed.get("timing_window", ""),
                    "why_this":             _parsed.get("why_this", ""),
                    "bridge_practice_note": _parsed.get("bridge_practice_note", ""),
                    "signal_confidence":    _conf_str,
                    "rarity_signals":       [],
                    "precision_windows":    [],
                    "all_domains":          [],
                }'''

    if old in content:
        content = content.replace(old, new_return, 1)
        print("✅ Replaced full return dict (v1)")
    elif old_v2 in content:
        content = content.replace(old_v2, new_return, 1)
        print("✅ Replaced full return dict (v2)")
    else:
        # Last resort: find by anchor and show context
        idx = content.find('"context_path": "json-v2"')
        if idx == -1:
            print("❌ json-v2 not found in main.py")
            sys.exit(1)
        # Find the return { that contains this
        block_start = content.rfind("return {", 0, idx)
        block_end = content.find("\n                }", idx) + len("\n                }")
        actual_block = content[block_start:block_end]
        print("⚠️  Could not match pattern. Actual block in main.py:")
        print(repr(actual_block))
        sys.exit(1)

    try:
        ast.parse(content)
        print("✅ syntax OK")
    except SyntaxError as e:
        print(f"❌ {e}"); sys.exit(1)

    Path("main.py").write_text(content, encoding="utf-8")
    print("\ngit add -A && git commit -m 'fix: complete JSON path response to match PredictResponse model' && git push")

if __name__ == "__main__":
    main()
