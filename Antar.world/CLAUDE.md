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

### Deploy process — branch, PR, squash-merge
Work goes to main through a pull request, never by pushing to main directly.

git checkout -b fix/short-description origin/main
git add <specific files>   # never git add -A
git commit -m "description"
git push -u origin fix/short-description
gh pr create --base main --title "..." --body "..."
gh pr merge <n> --squash   # repo convention: every PR lands as ONE commit

Railway auto-deploys from main, so the squash-merge IS the deploy. Watch logs at
the railway.app dashboard afterwards.

Check CI before merging (`gh pr checks <n>`), and know which red checks are
pre-existing rather than yours — at time of writing the Cloudflare
"Workers Builds" check fails on every commit on main (a Workers project is
connected to this repo with nothing here to build; it needs disconnecting on the
Cloudflare side). The gate that actually matters is `test`.

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
de0c6265-96cc-41ba-a39c-e55868fa5806
(previous test chart de02bb52-… was deleted from the charts table — verified gone 2026-06-04)

### Base URL
https://antar-fastapi-production.up.railway.app

### Shell testing rule
Run curl commands one at a time — never combine with # comments in zsh

### Claude model identifiers
Centralized in antar_engine/constants.py — update there, never at a call site:
- SONNET_MODEL = "claude-sonnet-4-6"   (the default working model)
- HAIKU_MODEL  = "claude-haiku-4-5-20251001"

The central Ask/predict prose path can also be overridden at runtime via the
app_config key `claude_model` (choices: claude-sonnet-4-6, claude-opus-4-8,
claude-haiku-4-5-20251001), and the provider via `llm_provider`.

(There is no CLAUDE_MODEL constant — this file used to name one, and to pin
claude-sonnet-4-20250514. Both were stale.)

### Patching rule
When modifying Python files, search for a unique string landmark to locate the
insertion point. Never use line numbers — main.py is ~40k lines and they move.

Do NOT create .bak files. The branch is the backup: `git diff` shows your change
and `git checkout -- <file>` reverts it. The old .bak habit left 262 of them in
the repo root, which is what the "Never commit" rule above is defending against.

### Git credentials
Git is already configured with push access to origin.
Never push directly to main, and never force-push main.
Force-pushing your OWN feature branch is fine and sometimes necessary — use
`--force-with-lease`. You will need it after a PR ahead of yours is squash-
merged: the squash gives those commits a new SHA, so your branch still carries
the originals and GitHub reports a conflict. Rebase onto the new main
(`git rebase --onto origin/main <old-base> <your-branch>`) and force-with-lease.

Syncing local main: `git merge --ff-only origin/main`, NOT `git reset --hard` —
reset discards uncommitted work in the tree without warning.

### After any code change
1. Run the tests: `venv311/bin/python -m pytest tests -q`
   **The suite is GREEN — 445 passed, 0 failed (2026-10-02).** Any red is yours; do not
   wave one through as pre-existing. (Until 2026-09-29 three
   tests/test_event_narrator.py failures were treated that way. They were a
   stale time-dependent fixture, not broken code, and they trained everyone to
   read past a red suite — which is how a real regression slips in.)
2. git add <only the files you changed>
3. git commit -m "perf/fix/feat: short description"
4. Push the branch and open a PR (see Deploy process)
5. After the squash-merge, confirm Railway picked it up