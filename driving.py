#!/usr/bin/env python3
"""
Jaimini Wiring Discovery — Run this to find exact insertion points in main.py
=============================================================================
Run: python3 discover_wiring_points.py

This finds the exact line numbers for all 5 integration points and prints
the surrounding code so you can see exactly where to insert.
"""

import re

def find_lines(content, patterns, label=""):
    """Find all lines matching any pattern."""
    lines = content.split("\n")
    results = []
    for i, line in enumerate(lines):
        for pat in patterns:
            if pat.lower() in line.lower():
                results.append((i + 1, line.rstrip()))
                break
    return results

def show_context(lines, line_num, before=3, after=3):
    """Show surrounding lines."""
    start = max(0, line_num - 1 - before)
    end = min(len(lines), line_num + after)
    for i in range(start, end):
        marker = ">>>" if i == line_num - 1 else "   "
        print(f"  {marker} {i+1:5d} | {lines[i].rstrip()}")

def main():
    with open("main.py", "r") as f:
        content = f.read()
    lines = content.split("\n")
    total = len(lines)

    print(f"main.py: {total} lines")
    print()

    # ── 1. Find chart/create endpoint ──
    print("=" * 60)
    print("  1. CHART CREATION (POST /api/v1/chart/create)")
    print("=" * 60)
    hits = find_lines(content, ["/chart/create", "def create_chart", "chart_create"])
    for num, line in hits:
        print(f"  Line {num}: {line[:100]}")
    
    # Find where chart is inserted to Supabase
    hits2 = find_lines(content, ['supabase.table("charts").insert', "supabase.table('charts').insert", 'table("charts").upsert'])
    print("\n  Chart insert to DB:")
    for num, line in hits2:
        print(f"  Line {num}: {line.strip()[:100]}")
        show_context(lines, num, 2, 5)
    print()

    # ── 2. Find predict endpoint ──
    print("=" * 60)
    print("  2. PREDICT ENDPOINT (POST /api/v1/predict)")
    print("=" * 60)
    hits = find_lines(content, ["/api/v1/predict", "def predict", "build_complete_context"])
    for num, line in hits:
        print(f"  Line {num}: {line.strip()[:100]}")

    # Find where LK context is added (this is where Jaimini goes after)
    hits2 = find_lines(content, ["format_lk_context", "lk_context", "lal_kitab", "build_lk_advanced"])
    print("\n  LK context insertion points:")
    for num, line in hits2[:10]:
        print(f"  Line {num}: {line.strip()[:100]}")

    # Find where Claude is called
    hits3 = find_lines(content, ["messages.create", "anthropic.messages", "claude_response", "raw_prediction"])
    print("\n  Claude API call:")
    for num, line in hits3[:5]:
        print(f"  Line {num}: {line.strip()[:100]}")
    print()

    # ── 3. Find welcome endpoint ──
    print("=" * 60)
    print("  3. WELCOME ENDPOINT (GET /api/v1/welcome)")
    print("=" * 60)
    hits = find_lines(content, ["/api/v1/welcome", "def get_welcome", "generate_welcome_signal", "welcome_signal"])
    for num, line in hits:
        print(f"  Line {num}: {line.strip()[:100]}")
    print()

    # ── 4. Find prashna endpoint ──
    print("=" * 60)
    print("  4. PRASHNA ENDPOINT (POST /api/v1/prashna)")
    print("=" * 60)
    hits = find_lines(content, ["/api/v1/prashna", "def prashna", "verdict", "confidence_score"])
    for num, line in hits[:10]:
        print(f"  Line {num}: {line.strip()[:100]}")
    print()

    # ── 5. Find dashboard endpoint ──
    print("=" * 60)
    print("  5. DASHBOARD ENDPOINT (GET /api/v1/dashboard)")
    print("=" * 60)
    hits = find_lines(content, ["/api/v1/dashboard", "def get_dashboard", "def dashboard"])
    for num, line in hits:
        print(f"  Line {num}: {line.strip()[:100]}")

    # Find where response dict is built
    hits2 = find_lines(content, ['response["', "response['" , "return {", "return response", '"lal_kitab"'])
    print("\n  Response builder (last 10 matches near dashboard):")
    for num, line in hits2[-10:]:
        print(f"  Line {num}: {line.strip()[:100]}")
    print()

    # ── 6. Existing Jaimini references ──
    print("=" * 60)
    print("  6. EXISTING JAIMINI REFERENCES")
    print("=" * 60)
    hits = find_lines(content, ["jaimini", "chara_dasha", "chara dasha", "karakas", "arudha"])
    for num, line in hits[:20]:
        print(f"  Line {num}: {line.strip()[:100]}")
    print()

    # ── 7. Import block location ──
    print("=" * 60)
    print("  7. JAIMINI IMPORT (already added)")
    print("=" * 60)
    hits = find_lines(content, ["jaimini_integration", "welcome_signal_v2", "jaimini_engine"])
    for num, line in hits:
        print(f"  Line {num}: {line.strip()[:100]}")
    print()

    print("=" * 60)
    print("  DONE — Use these line numbers to wire the 5 integration points")
    print("  Or paste this output and I'll build the exact patcher for you.")
    print("=" * 60)


if __name__ == "__main__":
    main()
