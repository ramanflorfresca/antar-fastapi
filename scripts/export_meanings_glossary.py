"""Print the glossary (antar_engine.meanings.glossary) as JSON for en and es, for the frontend content file.

    venv311/bin/python scripts/export_meanings_glossary.py > /tmp/meanings_glossary.json

The Glossary page ships this as static copy (public pages are prerendered), so re-run it and copy the
result into the frontend when antar_engine/meanings.py changes. tests/test_meanings_glossary.py pins the shape.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from antar_engine import meanings as M  # noqa: E402

print(json.dumps({lg: M.glossary(lg) for lg in M.LANGS}, ensure_ascii=False, indent=1))
