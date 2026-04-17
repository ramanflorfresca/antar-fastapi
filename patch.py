"""
patch_future_windows.py
Adds find_future_windows() and map_future_events() to dasha_event_mapper.py.
Also updates main.py upcoming-themes endpoint to use map_future_events.
Uses landmark string search — never line numbers.
"""
import re
import shutil
from datetime import datetime

MAPPER = "antar_engine/dasha_event_mapper.py"
MAIN = "main.py"

def patch_mapper():
    with open(MAPPER, "r") as f:
        content = f.read()

    # Check if already patched
    if "def find_future_windows" in content:
        print("[MAPPER] find_future_windows already exists — skipping")
        return

    # Backup
    shutil.copy(MAPPER, f"{MAPPER}.bak_future_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

    # Find insertion point — right before map_all_events
    landmark = "def map_all_events(birth_year: int, lagna: str, ads: list) -> dict:"
    idx = content.find(landmark)
    if idx == -1:
        print("[MAPPER] ERROR: could not find map_all_events landmark")
        return

    new_code = '''

# ---------------------------------------------------------------------------
# Future window scanning (for upcoming-themes endpoint)
# ---------------------------------------------------------------------------

def find_future_windows(
    lagna: str,
    birth_year: int,
    ads: list,
    from_date: str = None,
    to_date: str = None,
    min_score: int = 3,
) -> list:
    """
    Scan all ADs from from_date to to_date. For each event type,
    find ALL matching AD windows based on priority rules.
    Returns a list of dicts. No AGE_RANGES cap — future has no age limit.
    """
    from datetime import datetime as _dt

    if not from_date:
        from_date = _dt.now().strftime("%Y-%m-%d")
    if not to_date:
        to_date = _dt(year=_dt.now().year + 5, month=1, day=1).strftime("%Y-%m-%d")

    priorities = _get_priorities(lagna)
    results = []

    # Build a quick lookup: for each event_type, which AD lords score how much
    event_lord_scores = {}
    for event_type, prio_list in priorities.items():
        lord_map = {}
        for planet, reason, score in prio_list:
            if planet and planet not in lord_map:
                lord_map[planet] = (score, reason)
        event_lord_scores[event_type] = lord_map

    for ad in ads:
        ad_start = (ad.get("start_date") or ad.get("start") or "")[:10]
        ad_end = (ad.get("end_date") or ad.get("end") or "")[:10]
        ad_lord = ad.get("planet_or_sign") or ad.get("lord") or ""

        if not ad_start or not ad_end or not ad_lord:
            continue
        # Must overlap the future window
        if ad_end < from_date or ad_start > to_date:
            continue

        # Get parent MD lord
        parent_md = ""
        meta = ad.get("metadata")
        if isinstance(meta, dict):
            parent_md = meta.get("parent_lord") or meta.get("parent_md") or ""

        for event_type, lord_map in event_lord_scores.items():
            ad_score = 0
            ad_reason = ""
            if ad_lord in lord_map:
                ad_score, ad_reason = lord_map[ad_lord]

            # Bonus if MD lord also matches
            md_bonus = 0
            if parent_md and parent_md in lord_map and parent_md != ad_lord:
                md_bonus = min(3, lord_map[parent_md][0] // 3)

            total = ad_score + md_bonus
            if total >= min_score:
                # Try PD drilling
                pd_lord = None
                pd_start = ad_start
                pd_end = ad_end
                precision = "AD"
                try:
                    pds = _compute_pds_for_ad(ad_lord, ad_start, ad_end)
                    if pds:
                        # Find best PD that's in the future window
                        best_pd = None
                        best_pd_score = 0
                        for pd in pds:
                            ps = pd.get("start", "")[:10]
                            pe = pd.get("end", "")[:10]
                            if pe < from_date:
                                continue
                            pl = pd.get("lord", "")
                            ps_score = lord_map.get(pl, (0, ""))[0] if pl in lord_map else 0
                            if ps_score > best_pd_score:
                                best_pd = pd
                                best_pd_score = ps_score
                        if best_pd and best_pd_score > 0:
                            pd_lord = best_pd.get("lord")
                            pd_start = best_pd.get("start", ad_start)[:10]
                            pd_end = best_pd.get("end", ad_end)[:10]
                            precision = "PD"
                            total += 1  # PD bonus
                except Exception:
                    pass

                results.append({
                    "event_type": event_type,
                    "window_start": pd_start if precision == "PD" else ad_start,
                    "window_end": pd_end if precision == "PD" else ad_end,
                    "start": ad_start,
                    "end": ad_end,
                    "planet": ad_lord,
                    "parent_md": parent_md,
                    "score": total,
                    "precision": precision,
                    "pd_lord": pd_lord,
                    "candidate_count": 1,
                    "explanation_short": ad_reason,
                })

    return results


def map_future_events(
    lagna: str,
    birth_year: int,
    ads: list,
    from_date: str = None,
    to_date: str = None,
) -> dict:
    """
    Like map_all_events() but for future windows.
    Returns dict keyed by event_type, value = best future window.
    """
    all_future = find_future_windows(lagna, birth_year, ads, from_date, to_date)

    best = {}
    for w in all_future:
        et = w["event_type"]
        if et not in best or w["score"] > best[et]["score"]:
            best[et] = w

    return best


'''

    content = content[:idx] + new_code + content[idx:]

    with open(MAPPER, "w") as f:
        f.write(content)
    print("[MAPPER] Added find_future_windows + map_future_events")


def patch_main():
    with open(MAIN, "r") as f:
        content = f.read()

    # Check if already patched
    if "map_future_events" in content:
        print("[MAIN] map_future_events already referenced — skipping")
        return

    # Backup
    shutil.copy(MAIN, f"{MAIN}.bak_future_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

    # Find the upcoming-themes endpoint's import block and replace map_all_events with map_future_events
    old_import = """from antar_engine.dasha_event_mapper import (
            map_all_events,
            find_event_window,
            EVENT_DISPLAY_LABELS,
            EVENT_DESCRIPTION,
            build_energy_explanation,
        )"""

    new_import = """from antar_engine.dasha_event_mapper import (
            map_future_events,
            EVENT_DISPLAY_LABELS,
            EVENT_DESCRIPTION,
            build_energy_explanation,
        )"""

    if old_import in content:
        content = content.replace(old_import, new_import, 1)
        print("[MAIN] Replaced import block")
    else:
        # Try finding it with different whitespace
        # Search for map_all_events near upcoming-themes
        pattern = r"(from antar_engine\.dasha_event_mapper import \([\s\S]*?map_all_events[\s\S]*?\))"
        match = re.search(pattern, content[content.find("upcoming-themes"):content.find("upcoming-themes") + 2000])
        if match:
            old_block = match.group(1)
            new_block = old_block.replace("map_all_events", "map_future_events").replace("find_event_window,\n", "").replace("find_event_window,", "")
            offset = content.find("upcoming-themes")
            rel_start = match.start()
            abs_start = offset + rel_start
            abs_end = abs_start + len(old_block)
            content = content[:abs_start] + new_block + content[abs_end:]
            print("[MAIN] Replaced import block (regex)")
        else:
            print("[MAIN] WARNING: Could not find import block to replace")

    # Replace the call: raw_map = map_all_events(birth_year, lagna, ads)
    old_call = "raw_map = map_all_events(birth_year, lagna, ads)"
    new_call = """raw_map = map_future_events(
            lagna, birth_year, ads,
            from_date=today_str,
            to_date=cutoff_date,
        )"""

    if old_call in content:
        content = content.replace(old_call, new_call, 1)
        print("[MAIN] Replaced map_all_events call with map_future_events")
    else:
        print("[MAIN] WARNING: Could not find map_all_events call to replace")

    # Remove the extra find_event_window calls for loss_of_mother/major_acquisition
    # These are no longer needed since map_future_events scans all event types
    extra_block = """for extra_event in ("loss_of_mother", "major_acquisition"):
            if extra_event not in raw_map:
                raw_map[extra_event] = find_event_window(
                    extra_event, lagna, birth_year, ads
                )"""
    if extra_block in content:
        content = content.replace(extra_block, "# map_future_events already scans all event types", 1)
        print("[MAIN] Removed extra find_event_window calls")
    else:
        # Try with different indentation
        alt = re.search(r"for extra_event in.*?loss_of_mother.*?major_acquisition.*?raw_map\[extra_event\].*?find_event_window.*?\)", content, re.DOTALL)
        if alt:
            content = content[:alt.start()] + "# map_future_events already scans all event types" + content[alt.end():]
            print("[MAIN] Removed extra find_event_window calls (regex)")
        else:
            print("[MAIN] NOTE: extra find_event_window block not found (may not exist)")

    with open(MAIN, "w") as f:
        f.write(content)
    print("[MAIN] Updated upcoming-themes endpoint")


if __name__ == "__main__":
    print("=" * 60)
    print("Patching future window scanning")
    print("=" * 60)
    patch_mapper()
    patch_main()
    print()
    print("Done. Run these to verify:")
    print("  python -c \"import ast; ast.parse(open('antar_engine/dasha_event_mapper.py').read()); print('mapper OK')\"")
    print("  python -c \"import ast; ast.parse(open('main.py').read()); print('main OK')\"")
