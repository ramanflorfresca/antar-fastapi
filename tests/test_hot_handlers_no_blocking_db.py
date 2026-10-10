"""The first-screen / signup handlers are `async def`, so a bare supabase
`.execute()` inside them freezes the whole event loop (every other request on
that worker queues behind it). Each DB call must go through run_in_threadpool.
"""
import ast
from pathlib import Path

HOT = {"get_alerts", "get_home", "get_welcome", "_create_chart_for_user",
       "predict_year_attention"}


def _bare_executes(fn):
    found = []

    def visit(node):
        for ch in ast.iter_child_nodes(node):
            if isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
                continue  # nested sync helpers run in a thread / are offloaded themselves
            if (isinstance(ch, ast.Call) and isinstance(ch.func, ast.Attribute)
                    and ch.func.attr == "execute" and not ch.args and not ch.keywords):
                found.append(ch.lineno)
            visit(ch)

    visit(fn)
    return found


def test_hot_async_handlers_offload_db_calls():
    src = (Path(__file__).resolve().parent.parent / "main.py").read_text()
    tree = ast.parse(src)
    seen = set()
    for n in tree.body:
        if isinstance(n, ast.AsyncFunctionDef) and n.name in HOT:
            seen.add(n.name)
            assert not _bare_executes(n), f"{n.name}: bare .execute() at lines {_bare_executes(n)}"
    assert seen == HOT, f"handlers missing or no longer async: {HOT - seen}"
