"""Vehicle life-event metadata normalisation (buy-vs-lease study capture)."""
import ast, pathlib

src = pathlib.Path(__file__).resolve().parent.parent / "main.py"
tree = ast.parse(src.read_text())
wanted = {"_LE_DIRECTION", "_LE_DOMAIN", "_LE_VEHICLE_ACQ", "_LE_VEHICLE_OUTCOME"}
ns = {}
for node in tree.body:
    if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", None) in wanted:
        exec(compile(ast.Module([node], []), "main.py", "exec"), ns)
    if isinstance(node, ast.FunctionDef) and node.name == "_normalize_life_event_meta":
        exec(compile(ast.Module([node], []), "main.py", "exec"), ns)
ns["_resolve_primary_chart_id"] = lambda uid: "chart-1"
norm = ns["_normalize_life_event_meta"]


def test_vehicle_canonicalised():
    m = norm({"vehicle": {"acquisition": "Leased", "outcome": "Crash"}}, "u")
    assert m["vehicle"] == {"acquisition": "leased", "outcome": "accident"}
    assert m["domain"] == "vehicle" and m["chart_id"] == "chart-1"


def test_unknown_values_pass_through_and_explicit_domain_kept():
    m = norm({"domain": "money", "vehicle": {"acquisition": "gifted"}}, "u")
    assert m["vehicle"]["acquisition"] == "gifted" and m["domain"] == "money"


def test_car_domain_alias():
    assert norm({"domain": "Car"}, "u")["domain"] == "vehicle"
