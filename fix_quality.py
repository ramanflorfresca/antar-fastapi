#!/usr/bin/env python3
"""
Fix 3 backend quality issues:
  1. Banned terms still leaking in concern_router.py
  2. Wealth engine "2 out of 6" — house_lords keys are strings not integers
  3. PDF report generation

Run from project root:
    python fix_quality_issues.py
"""

import os, sys, subprocess, time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv("/Users/ramandeepsinghchadha/antarai/.env")
ROOT = Path("/Users/ramandeepsinghchadha/antarai")
os.chdir(ROOT)

print("=" * 60)
print("FIXING 3 BACKEND QUALITY ISSUES")
print("=" * 60)


# ══════════════════════════════════════════════════════════════════
# FIX 1 — BANNED TERMS IN concern_router.py
# ══════════════════════════════════════════════════════════════════
print("\n[1] Fixing banned terms in concern_router.py ...")

router_path = ROOT / "antar_engine" / "concern_router.py"
router_src  = router_path.read_text()
router_orig = router_src

REPLACEMENTS = [
    # Career section
    ("Amatyakaraka (AmK) planet — career's guiding force",
     "career path signal planet — career's guiding force"),
    ("Identify the Amatyakaraka (career's guiding planet) and its current strength",
     "Identify the career path signal planet and its current strength"),
    ("Amatyakaraka", "career path signal planet"),

    # Relationship/Marriage sections
    ("D9 Navamsa — soul-level relationship chart",
     "D9 soul chart — soul-level relationship chart"),
    ("D9 Navamsa — the soul's truth about relationships (deeper than surface)",
     "D9 soul chart — the soul's truth about relationships (deeper than surface)"),
    ("D9 Navamsa lagna and 7th house (soul marriage chart)",
     "D9 soul chart ascendant and 7th house (soul marriage chart)"),
    ("D9 Navamsa 7th house — the soul's truth about the marriage",
     "D9 soul chart 7th house — the soul's truth about the marriage"),
    ("MUST reference: D9 Navamsa, Darakaraka nature, this year's Varshphal",
     "MUST reference: D9 soul chart, partner signal planet nature, this year's annual chart"),
    ("D9 Navamsa for foreign indicators",
     "D9 soul chart for foreign indicators"),
    ("Darakaraka (DK)", "partner signal planet"),
    ("Darakaraka", "partner signal planet"),
    ("Navamsa lagna", "D9 soul chart ascendant"),
    ("Navamsa", "D9 soul chart"),

    # Spiritual section
    ("Atmakaraka planet (soul's core mission)",
     "soul's core signal planet (soul's core mission)"),
    ("1. Atmakaraka — what is this soul's core mission? (translated to plain language)",
     "1. Soul's core signal planet — what is this soul's core mission? (in plain language)"),
    ("MUST mention: Atmakaraka mission, D20 path, Ketu's past-life gift",
     "MUST mention: soul's core signal mission, D20 spiritual path, Ketu's past-life gift"),
    ("Atmakaraka soul mission", "soul's core signal mission"),
    ("[Atmakaraka in plain language]", "[Soul's core signal in plain language]"),
    ("Atmakaraka", "soul's core signal planet"),

    # system_prompt_builder references
    ("Mahadasha", "main life chapter"),
    ("Antardasha", "sub-chapter"),
    ("Dusthana", "challenging house"),
    ("Bhrashta", "dignity-challenged"),
    ("Varshphal", "annual chart"),
]

changes = 0
for old, new in REPLACEMENTS:
    if old in router_src:
        count = router_src.count(old)
        router_src = router_src.replace(old, new)
        changes += count

if router_src != router_orig:
    router_path.write_text(router_src)
    print(f"    ✅ Fixed {changes} banned term instances in concern_router.py")
else:
    print("    ⏭  No banned terms found")

# Also fix system_prompt_builder.py
sysbuilder = ROOT / "antar_engine" / "system_prompt_builder.py"
if sysbuilder.exists():
    sb_src  = sysbuilder.read_text()
    sb_orig = sb_src
    for old, new in REPLACEMENTS:
        sb_src = sb_src.replace(old, new)
    if sb_src != sb_orig:
        sysbuilder.write_text(sb_src)
        print("    ✅ Fixed system_prompt_builder.py")


# ══════════════════════════════════════════════════════════════════
# FIX 2 — WEALTH ENGINE: string keys vs integer keys
# ══════════════════════════════════════════════════════════════════
print("\n[2] Fixing wealth engine house_lords key type mismatch ...")

domain_path = ROOT / "antar_engine" / "domain_engines.py"
domain_src  = domain_path.read_text()
domain_orig = domain_src

# The fix: normalize house_lords keys to integers at the start of run_wealth_engine
OLD_WEALTH = '''def run_wealth_engine(
    planets: dict,
    lagna_sign: str,
    house_lords: dict,
    yogas: list,
    dashas: dict,
    d2_chart: dict,
) -> dict:
    """
    Score wealth/billionaire potential deterministically.
    Returns score, verdict, peak_window, wealth_type.
    """
    found = []
    total_weight = 0.0

    lagna_idx  = SIGNS.index(lagna_sign) if lagna_sign in SIGNS else 0
    lord_2_planet  = house_lords.get(2, {}).get("lord", "") if isinstance(house_lords, dict) else ""
    lord_11_planet = house_lords.get(11, {}).get("lord", "") if isinstance(house_lords, dict) else ""
    lord_5_planet  = house_lords.get(5, {}).get("lord", "") if isinstance(house_lords, dict) else ""
    lord_9_planet  = house_lords.get(9, {}).get("lord", "") if isinstance(house_lords, dict) else ""'''

NEW_WEALTH = '''def run_wealth_engine(
    planets: dict,
    lagna_sign: str,
    house_lords: dict,
    yogas: list,
    dashas: dict,
    d2_chart: dict,
) -> dict:
    """
    Score wealth/billionaire potential deterministically.
    Returns score, verdict, peak_window, wealth_type.
    """
    found = []
    total_weight = 0.0

    # Normalize house_lords keys to integers (DB stores as strings "1","2" etc)
    if isinstance(house_lords, dict):
        house_lords = {int(k) if str(k).isdigit() else k: v
                       for k, v in house_lords.items()}

    lagna_idx  = SIGNS.index(lagna_sign) if lagna_sign in SIGNS else 0
    lord_2_planet  = house_lords.get(2, {}).get("lord", "") if isinstance(house_lords, dict) else ""
    lord_11_planet = house_lords.get(11, {}).get("lord", "") if isinstance(house_lords, dict) else ""
    lord_5_planet  = house_lords.get(5, {}).get("lord", "") if isinstance(house_lords, dict) else ""
    lord_9_planet  = house_lords.get(9, {}).get("lord", "") if isinstance(house_lords, dict) else ""'''

if OLD_WEALTH in domain_src:
    domain_src = domain_src.replace(OLD_WEALTH, NEW_WEALTH, 1)
    print("    ✅ Fixed house_lords string→int normalization in run_wealth_engine")
else:
    print("    ⚠️  Pattern not found — checking for alternate format...")
    idx = domain_src.find("def run_wealth_engine")
    print(f"    Found at line: {domain_src[:idx].count(chr(10)) + 1}")

# Also fix same issue in any other engines that use house_lords
# Career engine
OLD_CAREER_HL = '''def run_career_engine('''
if OLD_CAREER_HL in domain_src:
    # Find all functions that take house_lords and add normalization
    # Pattern: after function signature, before first house_lords.get()
    import re
    def add_hl_normalization(src, func_name):
        pattern = f'(def {func_name}.*?house_lords: dict.*?\\n)(.*?)(house_lords\\.get\\()'
        match = re.search(pattern, src, re.DOTALL)
        if match and "str(k).isdigit()" not in src[match.start():match.start()+500]:
            insert_pos = src.find("house_lords.get(", src.find(f"def {func_name}"))
            if insert_pos > 0:
                # Find start of line
                line_start = src.rfind("\n", 0, insert_pos) + 1
                indent = len(src[line_start:]) - len(src[line_start:].lstrip())
                normalization = " " * indent + "house_lords = {int(k) if str(k).isdigit() else k: v for k, v in house_lords.items()} if isinstance(house_lords, dict) else {}\n"
                src = src[:line_start] + normalization + src[line_start:]
        return src

    for func in ["run_career_engine", "run_relationship_engine", "run_health_engine"]:
        if f"def {func}" in domain_src:
            new_src = add_hl_normalization(domain_src, func)
            if new_src != domain_src:
                domain_src = new_src
                print(f"    ✅ Fixed house_lords normalization in {func}")

if domain_src != domain_orig:
    domain_path.write_text(domain_src)


# ══════════════════════════════════════════════════════════════════
# FIX 3 — PDF REPORT GENERATION
# ══════════════════════════════════════════════════════════════════
print("\n[3] Building PDF report engine ...")

PDF_ENGINE = '''"""
antar_engine/pdf_engine.py

PDF Life Report Generator
==========================
Generates a complete Vedic astrology life report as PDF.
Uses HTML → PDF via weasyprint or reportlab fallback.
"""

import os
from datetime import datetime, date
from typing import Optional


PLANET_GLYPHS = {
    "Sun": "☉", "Moon": "☽", "Mars": "♂", "Mercury": "☿",
    "Jupiter": "♃", "Venus": "♀", "Saturn": "♄",
    "Rahu": "☊", "Ketu": "☋",
}


def generate_pdf_html(
    chart_data: dict,
    dashas: dict,
    predictions: list,
    remedies: list,
    first_name: str,
    birth_date: str,
    birth_city: str,
    lagna: str,
    moon_sign: str,
    moon_nakshatra: str,
    sun_sign: str,
    dasha_string: str,
    accuracy_pct: Optional[float] = None,
) -> str:
    """Generate HTML content for the PDF report."""

    planets     = chart_data.get("planets", {})
    yogas       = chart_data.get("yogas", [])
    house_lords = chart_data.get("house_lords", {})
    atmakaraka  = chart_data.get("atmakaraka", "")
    today       = date.today().strftime("%B %d, %Y")
    birth_year  = str(birth_date)[:4]

    # Build planet table rows
    planet_rows = ""
    for planet, data in planets.items():
        glyph = PLANET_GLYPHS.get(planet, "◈")
        planet_rows += f"""
        <tr>
          <td>{glyph} {planet}</td>
          <td>{data.get('sign','')}</td>
          <td>{data.get('house','')}</td>
          <td>{data.get('nakshatra','')}</td>
          <td>{round(data.get('degree', 0), 2)}°</td>
        </tr>"""

    # Build yoga rows
    yoga_rows = ""
    for yoga in yogas[:8]:
        yoga_rows += f"""
        <tr>
          <td>{yoga.get('name','')}</td>
          <td>{yoga.get('effect','')[:80]}</td>
          <td>{yoga.get('strength','').title()}</td>
        </tr>"""

    # Build dasha timeline
    dasha_rows = ""
    vim = dashas.get("vimsottari", [])
    now_dt = datetime.now()
    for d in vim[:12]:
        level = d.get("level", 0)
        if level != 1:
            continue
        lord      = d.get("planet_or_sign", "")
        start     = str(d.get("start_date",""))[:10]
        end       = str(d.get("end_date",""))[:10]
        try:
            sd = datetime.fromisoformat(start)
            ed = datetime.fromisoformat(end)
            is_current = sd <= now_dt <= ed
            years = round((ed - sd).days / 365.25, 1)
        except Exception:
            is_current = False
            years = 0
        highlight = 'style="background:#00BFA520;font-weight:bold;"' if is_current else ""
        current_badge = " ← NOW" if is_current else ""
        dasha_rows += f"""
        <tr {highlight}>
          <td>{PLANET_GLYPHS.get(lord,'◈')} {lord}{current_badge}</td>
          <td>{start[:7]}</td>
          <td>{end[:7]}</td>
          <td>{years} years</td>
        </tr>"""

    # Build remedies section
    remedy_html = ""
    for rem in remedies[:3]:
        remedy_html += f"""
        <div class="remedy-card">
          <div class="remedy-planet">{PLANET_GLYPHS.get(rem.get('planet',''),'◈')} {rem.get('planet','')} — {rem.get('priority_label','')}</div>
          <div class="remedy-why">{rem.get('why','')[:200]}</div>
          <div class="remedy-what"><strong>Practice:</strong> {rem.get('mantra','')}</div>
          <div class="remedy-how"><strong>When:</strong> {rem.get('best_time','')} · {rem.get('best_day','')}</div>
        </div>"""

    # Accuracy badge
    accuracy_html = ""
    if accuracy_pct and accuracy_pct >= 60:
        accuracy_html = f'<div class="accuracy-badge">◎ Antar has been {accuracy_pct}% accurate in your readings</div>'

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: 'Georgia', serif;
    background: #FAFAF8;
    color: #1A1A2E;
    font-size: 11pt;
    line-height: 1.6;
  }}
  .cover {{
    background: #0A0A0F;
    color: white;
    padding: 80px 60px;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    justify-content: center;
  }}
  .cover-brand {{ color: #00BFA5; font-size: 14pt; letter-spacing: 4px; margin-bottom: 40px; }}
  .cover-name {{ font-size: 36pt; font-weight: bold; margin-bottom: 8px; }}
  .cover-subtitle {{ color: #94A3B8; font-size: 14pt; margin-bottom: 40px; }}
  .cover-details {{ color: #64748B; font-size: 11pt; line-height: 2; }}
  .cover-details span {{ color: #F1F5F9; }}
  .cover-footer {{ margin-top: auto; color: #334155; font-size: 9pt; }}
  .page {{
    padding: 50px 60px;
    page-break-before: always;
  }}
  .section-title {{
    color: #00BFA5;
    font-size: 9pt;
    letter-spacing: 3px;
    text-transform: uppercase;
    border-bottom: 1px solid #E2E8F0;
    padding-bottom: 8px;
    margin-bottom: 24px;
    margin-top: 32px;
  }}
  .section-title:first-child {{ margin-top: 0; }}
  h1 {{ font-size: 22pt; color: #0A0A0F; margin-bottom: 16px; }}
  h2 {{ font-size: 14pt; color: #1A1A2E; margin-bottom: 12px; }}
  table {{
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 24px;
    font-size: 10pt;
  }}
  th {{
    background: #F1F5F9;
    padding: 8px 12px;
    text-align: left;
    font-size: 9pt;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: #64748B;
  }}
  td {{
    padding: 8px 12px;
    border-bottom: 1px solid #F1F5F9;
  }}
  tr:hover td {{ background: #FAFAFA; }}
  .highlight-row td {{ background: #00BFA510; font-weight: bold; }}
  .stat-grid {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
    margin-bottom: 24px;
  }}
  .stat-card {{
    background: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 16px;
  }}
  .stat-label {{ font-size: 8pt; color: #94A3B8; text-transform: uppercase; letter-spacing: 1px; }}
  .stat-value {{ font-size: 16pt; font-weight: bold; color: #0A0A0F; margin-top: 4px; }}
  .remedy-card {{
    border-left: 3px solid #00BFA5;
    padding: 16px 20px;
    margin-bottom: 16px;
    background: #F8FAFC;
  }}
  .remedy-planet {{ font-weight: bold; font-size: 12pt; margin-bottom: 6px; }}
  .remedy-why {{ color: #475569; font-size: 10pt; margin-bottom: 6px; }}
  .remedy-what, .remedy-how {{ font-size: 10pt; color: #1A1A2E; }}
  .accuracy-badge {{
    background: #FFF7ED;
    border: 1px solid #F59E0B;
    border-radius: 6px;
    padding: 10px 16px;
    font-size: 10pt;
    color: #92400E;
    margin-bottom: 16px;
  }}
  .footer {{
    text-align: center;
    color: #94A3B8;
    font-size: 8pt;
    margin-top: 40px;
    padding-top: 16px;
    border-top: 1px solid #E2E8F0;
  }}
  @page {{ margin: 0; size: A4; }}
</style>
</head>
<body>

<!-- COVER PAGE -->
<div class="cover">
  <div class="cover-brand">✦ ANTAR</div>
  <div class="cover-name">{first_name}</div>
  <div class="cover-subtitle">Life Navigation Report</div>
  <div class="cover-details">
    Born: <span>{birth_date} · {birth_city}</span><br>
    Rising Sign: <span>{lagna}</span><br>
    Moon: <span>{moon_sign} ({moon_nakshatra})</span><br>
    Sun: <span>{sun_sign}</span><br>
    Current Chapter: <span>{dasha_string}</span><br>
    Report Date: <span>{today}</span>
  </div>
  <div class="cover-footer">
    Generated by Antar AI · antar.world · Vedic Astrology Life Navigation
  </div>
</div>

<!-- PAGE 1: CHART OVERVIEW -->
<div class="page">
  <div class="section-title">Your Chart</div>
  <h1>Planetary Positions</h1>

  {accuracy_html}

  <div class="stat-grid">
    <div class="stat-card">
      <div class="stat-label">Rising Sign</div>
      <div class="stat-value">{lagna}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Moon Sign</div>
      <div class="stat-value">{moon_sign}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Moon Nakshatra</div>
      <div class="stat-value">{moon_nakshatra}</div>
    </div>
  </div>

  <table>
    <tr>
      <th>Planet</th><th>Sign</th><th>House</th>
      <th>Nakshatra</th><th>Degree</th>
    </tr>
    {planet_rows}
  </table>

  <div class="section-title">Active Yogas (Planetary Combinations)</div>
  <table>
    <tr><th>Yoga</th><th>Effect</th><th>Strength</th></tr>
    {yoga_rows if yoga_rows else '<tr><td colspan="3">No major yogas detected</td></tr>'}
  </table>
</div>

<!-- PAGE 2: LIFE CHAPTERS -->
<div class="page">
  <div class="section-title">Your Life Timeline</div>
  <h1>Vimsottari Dasha — Life Chapters</h1>
  <p style="color:#475569;margin-bottom:20px;font-size:10pt;">
    Each planetary period brings its themes to the foreground.
    The current period is highlighted.
  </p>

  <table>
    <tr><th>Planet</th><th>Starts</th><th>Ends</th><th>Duration</th></tr>
    {dasha_rows}
  </table>
</div>

<!-- PAGE 3: PRACTICES & REMEDIES -->
<div class="page">
  <div class="section-title">Your Practices</div>
  <h1>Active Recalibration Practices</h1>
  <p style="color:#475569;margin-bottom:20px;font-size:10pt;">
    These practices are specific to your current planetary period
    and chart pattern — not generic recommendations.
  </p>

  {remedy_html if remedy_html else '<p style="color:#94A3B8;">Generate your practices in the app for personalized recommendations.</p>'}

  <div class="footer">
    This report was generated by Antar AI on {today}.
    Antar · antar.world · Your life, navigated.
  </div>
</div>

</body>
</html>"""

    return html


async def generate_pdf_report(
    chart_id: str,
    sb,
    remedies: list = None,
) -> bytes:
    """
    Generate complete PDF report for a chart.
    Returns PDF bytes.
    """
    # Load chart
    chart_res = sb.table("charts").select(
        "chart_data,first_name,birth_date,birth_city,"
        "lagna_sign,moon_sign,moon_nakshatra,sun_sign"
    ).eq("id", chart_id).execute()

    if not chart_res.data:
        raise ValueError("Chart not found")

    row        = chart_res.data[0]
    chart_data = row.get("chart_data", {})
    first_name = row.get("first_name","") or "Explorer"

    # Load dashas
    dasha_res = sb.table("dasha_periods").select("*").eq(
        "chart_id", chart_id
    ).eq("system","vimsottari").order("sequence").execute()
    dashas = {"vimsottari": dasha_res.data or []}

    # Get current dasha string
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    current_md = current_ad = ""
    for d in dashas["vimsottari"]:
        try:
            sd = datetime.fromisoformat(str(d.get("start_date",""))[:10].replace("Z",""))
            ed = datetime.fromisoformat(str(d.get("end_date",""))[:10].replace("Z",""))
            if sd.date() <= now.date() <= ed.date():
                if d.get("level") == 1: current_md = d.get("planet_or_sign","")
                elif d.get("level") == 2: current_ad = d.get("planet_or_sign","")
        except Exception:
            pass
    dasha_str = f"{current_md}-{current_ad}" if current_ad else current_md

    # Get accuracy
    try:
        acc = sb.table("prediction_accuracy").select("accuracy_pct").eq(
            "chart_id", chart_id
        ).execute()
        accuracy_pct = acc.data[0].get("accuracy_pct") if acc.data else None
    except Exception:
        accuracy_pct = None

    # Generate HTML
    html = generate_pdf_html(
        chart_data     = chart_data,
        dashas         = dashas,
        predictions    = [],
        remedies       = remedies or [],
        first_name     = first_name,
        birth_date     = str(row.get("birth_date",""))[:10],
        birth_city     = row.get("birth_city",""),
        lagna          = row.get("lagna_sign",""),
        moon_sign      = row.get("moon_sign",""),
        moon_nakshatra = row.get("moon_nakshatra",""),
        sun_sign       = row.get("sun_sign",""),
        dasha_string   = dasha_str,
        accuracy_pct   = accuracy_pct,
    )

    # Convert to PDF
    try:
        import weasyprint
        pdf_bytes = weasyprint.HTML(string=html).write_pdf()
        return pdf_bytes
    except ImportError:
        try:
            # Fallback: return HTML as bytes (user can print to PDF)
            return html.encode("utf-8")
        except Exception as e:
            raise ValueError(f"PDF generation failed: {e}")
'''

pdf_path = ROOT / "antar_engine" / "pdf_engine.py"
pdf_path.write_text(PDF_ENGINE)
print(f"    ✅ Created {pdf_path}")

# Add PDF endpoint to main.py
main_path = ROOT / "main.py"
main_src  = main_path.read_text()
main_orig = main_src

PDF_ENDPOINT = '''

# ── PDF Report Endpoint ───────────────────────────────────────────

@app.get("/api/v1/report/{chart_id}/pdf")
async def generate_life_report(chart_id: str):
    """
    Generate and download complete PDF life report.
    Requires Seeker or Navigator plan.
    """
    from antar_engine.subscription_engine import get_subscription
    from antar_engine.pdf_engine import generate_pdf_report
    from fastapi.responses import Response

    # Check subscription
    sub = get_subscription(chart_id, supabase)
    if sub.get("plan","free") == "free":
        raise HTTPException(403, {
            "error": "upgrade_required",
            "message": "PDF reports are available on Seeker and Navigator plans",
            "upgrade_url": "https://antar.world/upgrade",
        })

    # Get remedies for the report
    try:
        from antar_engine import remedy_selector
        chart_res = supabase.table("charts").select(
            "chart_data,birth_date,first_name,career_stage,health_status"
        ).eq("id", chart_id).execute()
        chart_data = chart_res.data[0]["chart_data"] if chart_res.data else {}
        dasha_res  = supabase.table("dasha_periods").select("*").eq(
            "chart_id", chart_id
        ).execute()
        dashas = {"vimsottari": dasha_res.data or []}
        remedies = remedy_selector.select_remedies(
            supabase=supabase, chart_data=chart_data,
            dashas=dashas, transits={}, user_age=35,
            question="general", patra=None, limit=3,
        )
    except Exception:
        remedies = []

    pdf_bytes = await generate_pdf_report(chart_id, supabase, remedies)

    # Determine content type
    content_type = "application/pdf"
    filename     = f"antar-report-{chart_id[:8]}.pdf"

    if pdf_bytes[:4] != b"%PDF":
        # Fallback HTML returned
        content_type = "text/html"
        filename     = f"antar-report-{chart_id[:8]}.html"

    return Response(
        content=pdf_bytes,
        media_type=content_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )

'''

if "/api/v1/report/" not in main_src:
    main_src = main_src.rstrip() + "\n" + PDF_ENDPOINT + "\n"
    print("    ✅ Added PDF report endpoint")
else:
    print("    ⏭  PDF endpoint already present")

if main_src != main_orig:
    main_path.write_text(main_src)


# ══════════════════════════════════════════════════════════════════
# SYNTAX CHECKS
# ══════════════════════════════════════════════════════════════════
print("\n[4] Syntax checks ...")
for p in [main_path, domain_path, router_path, pdf_path]:
    r = subprocess.run(
        ["python3","-c",f"import ast; ast.parse(open('{p}').read()); print('OK')"],
        capture_output=True, text=True)
    icon = "✅" if "OK" in r.stdout else "❌"
    print(f"    {icon} {p.name}: {'OK' if 'OK' in r.stdout else r.stderr[-100:]}")
    if "OK" not in r.stdout:
        sys.exit(1)

# Add weasyprint to requirements
req_path = ROOT / "requirements.txt"
req_src  = req_path.read_text()
if "weasyprint" not in req_src:
    req_path.write_text(req_src.rstrip() + "\nweasyprint\n")
    print("    ✅ Added weasyprint to requirements.txt")


# ══════════════════════════════════════════════════════════════════
# COMMIT AND PUSH
# ══════════════════════════════════════════════════════════════════
print("\n[5] Committing ...")
subprocess.run(["git","add",
    "antar_engine/concern_router.py",
    "antar_engine/system_prompt_builder.py",
    "antar_engine/domain_engines.py",
    "antar_engine/pdf_engine.py",
    "main.py",
    "requirements.txt",
], check=True)

subprocess.run(["git","commit","-m",
    "fix: 3 backend quality issues\n\n"
    "1. Banned terms — remove Atmakaraka/Navamsa/Amatyakaraka etc\n"
    "   from concern_router.py system instructions\n"
    "2. Wealth engine — normalize house_lords string keys to int\n"
    "   fixes '2 out of 6' combinations found issue\n"
    "3. PDF report — new pdf_engine.py with HTML→PDF generation\n"
    "   GET /api/v1/report/{chart_id}/pdf (Seeker/Navigator only)"
], check=True)
subprocess.run(["git","push","origin","main"], check=True)
print("    ✅ Pushed")

print("\n[6] Waiting 50s ...")
time.sleep(50)
print("    Done — run: python test_quality.py")
