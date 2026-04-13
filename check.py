#!/usr/bin/env python3
import os
TARGET = os.path.expanduser("~/antarai/main.py")
with open(TARGET) as f:
    lines = f.readlines()

# Find daily-week route and function
for i,l in enumerate(lines):
    if 'daily-week' in l and ('app.get' in l or 'async def' in l):
        print(f"{i+1}: {l.rstrip()}")

print()
# Find where signal and move fields are set
for i,l in enumerate(lines):
    if ('"signal"' in l or '"move"' in l or '"aligned_for"' in l) and ('=' in l or ':' in l):
        print(f"{i+1}: {l.rstrip()[:120]}")
