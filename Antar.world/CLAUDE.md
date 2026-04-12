## Project: Antar Backend (antarai)

### Stack
- FastAPI / Python backend
- Deployed on Railway (auto-deploys on git push to main)
- Supabase database
- Swiss Ephemeris for live transit computation
- Claude Sonnet as primary LLM (via Anthropic SDK)

### Working directory
~/antarai

### Activate environment before any Python work
source venv311/bin/activate

### Deploy process
git add <specific files>   # never git add -A
git commit -m "description"
git push origin main
# Railway auto-deploys. Watch logs at railway.app dashboard.

### Never commit
- .bak files
- patch_*.py scripts
- __pycache__

### Key files
- main.py — all API endpoints, Claude API call, connections system
- antar_engine/symptom_library.py — 12-channel diagnostic engine
- antar_engine/plain_english.py — plain_summary formatting rules
- antar_engine/prashna_engine.py — Prashna Oracle logic
- antar_engine/chart_context_builder.py — context pruning, question_mode gating
- antar_engine/pattern_memory.py — C3 memory (MEMORY_LIMIT=3)
- antar_engine/compatibility_session_engine.py — type-specific compatibility
- antar_engine/astrocartography.py — Swiss Ephemeris MC/ASC computation

### Test chart ID (use for all curl tests)
de02bb52-d43a-4b09-be25-b45a07bfbf8a  (Capricorn Rising)

### Base URL
https://antar-fastapi-production.up.railway.app

### Shell testing rule
Run curl commands one at a time — never combine with # comments in zsh

### Claude API call location
Inside the /predict endpoint in main.py. The messages.create() call uses:
- model=CLAUDE_MODEL
- system=system_prompt (or system blocks for KV cache)
- messages=conversation_messages

### Current Claude model string
claude-sonnet-4-20250514

### Patching rule
When modifying Python files, always search for a unique string landmark to locate
the insertion point. Never use line numbers. Always create a .bak before editing.                     ### Git credentials
Git is already configured with push access to origin.
Always push to: main branch only.
Never force push.                                 ### After any code change
1. git add <only the file you changed>
2. git commit -m "perf/fix/feat: short description"
3. git push origin main
4. Confirm Railway deploy started by checking the push was accepted