"""
Spillage / jargon scanner. Walks every JSON response, extracts user-facing
string fields, regex-scans for HARD leaks and SOFT flags.
"""
import json, os, re, glob
from collections import defaultdict

OUTDIR = os.path.dirname(os.path.abspath(__file__))

# HARD-leak patterns
HARD = {
    "sanskrit_dasha":     re.compile(r"\b(?:dasha|mahadasha|antardasha|antardasa|pratyantar(?:dasha)?|sookshma|vimsottari|vimshottari|ashtottari)\b", re.I),
    "sanskrit_system":    re.compile(r"\b(?:jaimini|lal\s*kitab|nakshatra|lagna|rashi|tithi|karana|panchanga|panchang|varshphal|graha|bhava|karaka|atmakaraka|amatyakaraka|darakaraka|gochar|sade\s*sati|ithasala|muhurta|muhurat|navamsa|karakamsa|upapada|paada)\b", re.I),
    "planet_in_sign":     re.compile(r"\b(?:Sun|Moon|Mars|Mercury|Jupiter|Venus|Saturn|Rahu|Ketu)\s+(?:in|enters|moves\s+into|transits)\s+(?:Aries|Taurus|Gemini|Cancer|Leo|Virgo|Libra|Scorpio|Sagittarius|Capricorn|Aquarius|Pisces)\b"),
    "node_name":          re.compile(r"\b(?:Rahu|Ketu)\b"),
    "outer_planet_name":  re.compile(r"\b(?:Saturn|Jupiter|Venus|Mercury|Mars|Sun|Moon)\b"),
    "house_number":       re.compile(r"\b(?:1st|2nd|3rd|4th|5th|6th|7th|8th|9th|10th|11th|12th)\s+house\b", re.I),
    "house_short":        re.compile(r"\b(?:1|2|3|4|5|6|7|8|9|10|11|12)H\b"),
    "house_word_n":       re.compile(r"\bhouse\s+(?:1|2|3|4|5|6|7|8|9|10|11|12)\b", re.I),
    "engine_name":        re.compile(r"\b(?:VIMSOTTARI|VIMSHOTTARI|JAIMINI|LAL\s*KITAB|TRANSIT\s+ENGINE)\b"),
    "codename_caps":      re.compile(r"\b(?:AUTHORITY\s+ENGINE|CAPITAL\s+RUNWAY|ALLIANCE\s+SYNC|STRATEGY:\s*[A-Z]+|STAR:\s*[A-Z]+)\b"),
    "template_braces":    re.compile(r"\{[a-zA-Z_][\w\.]*\}|\{\{[^}]+\}\}"),
    "literal_undefined":  re.compile(r"\b(?:undefined|NaN)\b"),
    "literal_none_python":re.compile(r"(?<![\w'])None(?![\w'])"),
    "agg_strength_no_num":re.compile(r"aggregate\s+planetary\s+strength\s+sits\s+at(?!\s*\d)", re.I),
    "sadhana_word":       re.compile(r"\bSadhana\b"),
    "double_space":       re.compile(r"  "),
    "internal_trace":     re.compile(r"\b(?:reasoning_public|reasoning_technical|system_readings\.naisargika|naisargika_active_planet)\b"),
    "bija_syllables":     re.compile(r"\b(?:YAM|RAM|KRIM|HRIM|HUM|KLIM|OM|AUM|GAM|HAUM|SHAUM)\b"),
}

# ─── ATOMIC-LABEL HARD rules (run on every string, no is_prose gate) ────────
# The brief flagged two scanner blind spots: bare planet names ("Sun") and
# CAPS codenames ("THE DISCOVERER") are too short / structurally odd for the
# is_prose filter, so the original HARD rules never see them. These rules
# bypass is_prose and inspect the value as an atomic label.
ATOMIC_HARD = {
    # Whole-value match: a single planet name OR a planet name + one word.
    # Targets attention.planet="Sun", a fallback="Saturn cycle", etc.
    "bare_planet_label": re.compile(
        r"^\s*(?:Sun|Moon|Mars|Mercury|Jupiter|Venus|Saturn|Rahu|Ketu)"
        r"(?:\s+\w+)?\s*$"
    ),
    # Whole-value match: CAPS strategy/archetype codenames.
    # ^(THE )?[A-Z][A-Z ]{4,}$ catches "THE DISCOVERER", "THE TURNAROUND
    # ARCHITECT", "AUTHORITY ENGINE", "CAPITAL RUNWAY", "STRATEGY: COMPENSATE".
    "caps_codename":     re.compile(
        r"^\s*(?:THE\s+)?[A-Z][A-Z\s:]{4,}\s*$"
    ),
}

# Atomic labels that look like a banned token but are SAFE (verdicts, status
# codes, language labels). Pre-check against this allowlist to suppress noise.
ATOMIC_SAFE = frozenset({
    "YES","NO","STRONG NO","LIKELY","UNLIKELY","NOT YET","NOT_YET",
    "SI","SÍ","PROBABLE","IMPROBABLE","STRONG","MIXED",
    "POSITIVE","NEGATIVE","NEUTRAL","FLAT","HIGH","LOW","MEDIUM",
    "OPEN","CLOSE","ACTIVE","CLOSED","PASSED","PENDING",
})

# SOFT flags
SOFT = {
    "energy_word":      re.compile(r"\benergy\b", re.I),
    "frequency_hz":     re.compile(r"\bfrequency\b|\b\d+\s*Hz\b", re.I),
    "chapter_nesting":  re.compile(r"\b(?:sub-?chapter|micro-?chapter|major\s+chapter|chapter\s+nesting)\b", re.I),
}

# Skip these JSON keys (internal/system fields, never rendered)
SKIP_KEY_PARTS = {
    # internal trace surfaces we EXPECT to be filled with jargon
    "_debug","_trace","debug","trace","raw","reasoning_public","reasoning_technical",
    "system_readings","naisargika","chart_data","jaimini_data","lal_kitab_data",
    # identifiers / non-prose
    "chart_id","prediction_id","session_id","id","uuid",
    # metadata
    "created_at","updated_at","timestamp","date","timezone","timezone_name","language","language_preference","country","country_code",
    # numeric/derived
    "score","confidence","weight","strength",
    # technical labels (consumed by frontend, not rendered as-is)
    "atmakaraka","amatyakaraka","lagna","moon_sign","sun_sign","current_dasha",
    # [2026-06-09] atomic-rule skips: internal structural sub-keys that
    # legitimately carry planet names for the frontend's logic. These never
    # appear as prose to the user (they drive selectors/icons/computation).
    "phase","mahadasha","antardasha","pratyantar","sookshma","cause",
    "significator_1","significator_2","significator_x","prashna_chart",
    "chart_gemstone","domain_audit","locale","panchanga","panchanga_5",
    "vara","jaimini_chara","vimsottari","transit_overlay","cycle_cross_check",
    "systems","upcoming_dasha","next_phase_shift_internal",
}

# Keys we know carry user-facing prose and ALWAYS scan (override)
USER_FACING_KEY_HINTS = (
    "summary","plain_summary","prediction","prediction_text","narration","narrative","headline",
    "title","subtitle","label","name","description","why","action","actions","todays_move",
    "todays_nudge","verdict","window","ask","answer","text","copy","body","reason","reasoning",
    "story","insight","theme","focus","caption","message",
)

# Fields we want SOFT scan only (energy/frequency expected sometimes)
SOFT_ONLY_KEY_HINTS = ("chakra","mantra","practice")

def is_skip_key(path_parts, key):
    if any(p in SKIP_KEY_PARTS for p in path_parts):
        return True
    if key in SKIP_KEY_PARTS:
        return True
    return False

def walk_strings(obj, path=()):
    """Yield (json_path, key, string_value) for every string leaf."""
    if isinstance(obj, dict):
        for k,v in obj.items():
            yield from walk_strings(v, path+(k,))
    elif isinstance(obj, list):
        for i,v in enumerate(obj):
            yield from walk_strings(v, path+(f"[{i}]",))
    elif isinstance(obj, str):
        yield (".".join(path), path[-1] if path else "", obj)

def classify_key(path_parts, key):
    """user_facing | soft_only | internal | skip"""
    if any(p in SKIP_KEY_PARTS for p in path_parts) or key in SKIP_KEY_PARTS:
        return "skip"
    pl = (key or "").lower()
    if any(h in pl for h in SOFT_ONLY_KEY_HINTS) or any(h in (p or "").lower() for p in path_parts for h in SOFT_ONLY_KEY_HINTS):
        return "soft_only"
    if any(h in pl for h in USER_FACING_KEY_HINTS):
        return "user_facing"
    # Heuristic: any string > 24 chars that isn't a uuid/url -> treat as user-facing prose
    return "user_facing_heuristic"

UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
URL_RE = re.compile(r"^https?://")

def is_prose(s):
    s=s.strip()
    if len(s) < 8: return False
    if UUID_RE.match(s): return False
    if URL_RE.match(s): return False
    # bare token like 'building'/'partnered'
    if " " not in s and len(s) < 32: return False
    return True

hits = []  # list of (surface, file, path, severity, rule, snippet)

for f in sorted(glob.glob(os.path.join(OUTDIR, "resp_*.json"))):
    base = os.path.basename(f).replace("resp_","").replace(".json","")
    slug, _, surface = base.partition("__")
    try:
        data = json.load(open(f))
    except Exception as e:
        hits.append((slug, surface, "(root)", "HARD", "parse_error", str(e)[:120]))
        continue
    for jp, key, val in walk_strings(data):
        # Path-based skip
        parts = jp.split(".") if jp else []
        cls = classify_key(parts, key)
        if cls == "skip":
            continue

        # ── ATOMIC-LABEL pass (runs BEFORE is_prose gate so short labels
        #    like "Sun" / "THE DISCOVERER" get caught). One value per match.
        _val_stripped = (val or "").strip()
        if _val_stripped and _val_stripped.upper() not in ATOMIC_SAFE:
            for rule, rx in ATOMIC_HARD.items():
                if rx.match(_val_stripped):
                    snippet = _val_stripped[:80]
                    hits.append((slug, surface, jp, "HARD", rule, snippet))
                    break  # one atomic-rule hit per value is enough

        if not is_prose(val):
            continue
        # HARD scans
        soft_only = (cls == "soft_only")
        for rule, rx in HARD.items():
            # skip bija syllables when inside Practices/mantra branches
            if rule == "bija_syllables" and (surface == "practices" or "mantra" in (key or "").lower() or any("mantra" in p.lower() for p in parts) or any("practice" in p.lower() for p in parts)):
                continue
            # outer_planet_name and node_name are noisy in some technical fields; restrict to prose
            m = rx.search(val)
            if m:
                snippet = val[max(0,m.start()-25):m.end()+25].replace("\n"," ")
                hits.append((slug, surface, jp, "HARD" if not soft_only else "HARD", rule, snippet))
        # SOFT scans
        for rule, rx in SOFT.items():
            if soft_only and rule in ("energy_word","frequency_hz"):
                continue
            m = rx.search(val)
            if m:
                snippet = val[max(0,m.start()-25):m.end()+25].replace("\n"," ")
                hits.append((slug, surface, jp, "SOFT", rule, snippet))

# write report
out_csv = os.path.join(OUTDIR, "leak_hits.tsv")
with open(out_csv,"w") as fp:
    fp.write("slug\tsurface\tpath\tseverity\trule\tsnippet\n")
    for h in hits:
        fp.write("\t".join(str(x).replace("\t"," ").replace("\n"," ") for x in h)+"\n")

# Summary by rule
from collections import Counter
print(f"HITS: {len(hits)}")
by_rule = Counter((sev,rule) for (_,_,_,sev,rule,_) in hits)
print("\nBy severity+rule:")
for (sev,rule),n in sorted(by_rule.items(), key=lambda x:-x[1]):
    print(f"  {sev:4} {rule:24} {n}")
by_surface_hard = Counter(surface for (_,surface,_,sev,_,_) in hits if sev=="HARD")
print("\nHARD per surface:")
for surface,n in sorted(by_surface_hard.items(), key=lambda x:-x[1]):
    print(f"  {surface:18} {n}")
by_surface_slug_hard = Counter((slug,surface) for (slug,surface,_,sev,_,_) in hits if sev=="HARD")
print("\nHARD per slug+surface:")
for (slug,surface),n in sorted(by_surface_slug_hard.items()):
    print(f"  {slug:8} {surface:18} {n}")
