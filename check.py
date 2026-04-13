#!/usr/bin/env python3
import os
TARGET = os.path.expanduser("~/antarai/main.py")
with open(TARGET) as f:
    lines = f.readlines()

# Show context around line 11382
print("=== Around line 11382 (translate call) ===")
for i in range(11375, 11400):
    print(f"{i+1}: {lines[i].rstrip()}")

print()
print("=== Around line 11060 (return statement) ===")  
for i in range(11055, 11085):
    print(f"{i+1}: {lines[i].rstrip()}")
