"""
antar_engine/alert_engine.py

Personal Alert Engine
======================
Fires alerts ONLY when a transit personally affects the user's chart.
No generic "Mercury retrograde" noise — only real impact events.

Alert triggers (all 6):
  1. Saturn transiting natal Moon/Sun/Mars (within 3°)
  2. Rahu/Ketu hitting any natal planet (within 3°)
  3. Jupiter entering a new house (opportunity window)
  4. Dasha period changing (life chapter shift)
  5. Eclipse hitting natal planet (within 8°)
  6. Any planet within 3° of any natal planet
"""

import os
from datetime import datetime, date, timedelta
from typing import Optional


# ── Alert type definitions ────────────────────────────────────────

ALERT_TEMPLATES = {

    "saturn_natal_moon": {
        "urgency":   "high",
        "headline":  "Saturn is moving over your natal Moon",
        "body":      (
            "This is one of the most emotionally significant transits in a 29-year cycle. "
            "Saturn crossing your natal Moon can bring emotional heaviness, isolation, or news "
            "about a maternal figure. It asks you to face what you've been avoiding emotionally. "
            "This window lasts approximately 2-3 months."
        ),
        "action":    "Reduce social obligations. Protect sleep. Journal daily. Don't make major relationship decisions.",
        "remedy":    "Offer milk to Shiva on Mondays. Wear silver. Reduce stimulants.",
        "window":    90,
    },

    "saturn_natal_sun": {
        "urgency":   "high",
        "headline":  "Saturn is testing your authority and identity",
        "body":      (
            "Saturn transiting your natal Sun is a once-in-29-years pressure test on your "
            "identity, career authority, and relationship with your father figure. "
            "Things you've built on weak foundations may crack. Things built solidly will be rewarded."
        ),
        "action":    "Focus on what's real and lasting. Avoid ego battles. Do the unglamorous work.",
        "remedy":    "Donate black sesame seeds on Saturday. Serve those less fortunate.",
        "window":    90,
    },

    "saturn_natal_mars": {
        "urgency":   "high",
        "headline":  "Saturn is slowing your Mars energy — frustration possible",
        "body":      (
            "Saturn over natal Mars creates a friction between your drive and the pace of reality. "
            "Anger, frustration, and blocked action are common. This is also a high-risk window "
            "for accidents if energy is not channeled carefully. Lasts 2-3 months."
        ),
        "action":    "Channel energy into disciplined physical practice. Avoid impulsive decisions. Drive carefully.",
        "remedy":    "Hanuman Chalisa on Tuesdays. Donate red items. Avoid arguments.",
        "window":    90,
    },

    "rahu_natal_planet": {
        "urgency":   "medium",
        "headline":  "Rahu is activating your natal {natal_planet}",
        "body":      (
            "Rahu transiting over your natal {natal_planet} amplifies its energy in unexpected, "
            "sometimes obsessive ways. Foreign connections, unconventional opportunities, and "
            "sudden changes in the {natal_planet} domain of your life are likely. "
            "This window lasts approximately 18 months."
        ),
        "action":    "Stay grounded. Unusual opportunities may appear — evaluate carefully before committing.",
        "remedy":    "Feed crows. Donate on Saturdays. Meditate at dusk.",
        "window":    540,
    },

    "ketu_natal_planet": {
        "urgency":   "medium",
        "headline":  "Ketu is bringing detachment from your natal {natal_planet}",
        "body":      (
            "Ketu over your natal {natal_planet} brings spiritual lessons around letting go. "
            "The {natal_planet} domain of your life may feel uncertain or withdrawn. "
            "This is often a period of inner growth and releasing old patterns. "
            "Lasts approximately 18 months."
        ),
        "action":    "Don't force outcomes in this domain. Spiritual practice and inner work are highly productive now.",
        "remedy":    "Donate blankets. Observe silence for 1 hour daily. Ketu mantra at dawn.",
        "window":    540,
    },

    "jupiter_new_house": {
        "urgency":   "opportunity",
        "headline":  "Jupiter enters your {house} house — a 12-month opportunity window opens",
        "body":      (
            "Jupiter moving into your {house} house is one of the most significant annual events "
            "in your chart. This house becomes a zone of expansion, opportunity, and blessing "
            "for the next 12 months. What you start or invest in this area now carries extra momentum."
        ),
        "action":    "Identify the top priority in this life area and take one bold action this month.",
        "remedy":    "Offer yellow flowers to Jupiter on Thursdays. Donate to education.",
        "window":    365,
    },

    "dasha_change": {
        "urgency":   "high",
        "headline":  "Your life chapter is shifting — {old_dasha} ends, {new_dasha} begins",
        "body":      (
            "A major life chapter is ending and a new one beginning. "
            "The {old_dasha} period brought its themes — now {new_dasha} energy takes over. "
            "This is one of the most significant transitions in your chart. "
            "The first 6 months of a new dasha set the tone for the entire period."
        ),
        "action":    "Review what the last chapter taught you. Set a clear intention for this new chapter.",
        "remedy":    "Strengthen the new dasha planet with its specific mantra and offering.",
        "window":    180,
    },

    "eclipse_natal_planet": {
        "urgency":   "high",
        "headline":  "Eclipse activating your natal {natal_planet} — sudden change likely",
        "body":      (
            "An eclipse hitting your natal {natal_planet} is a rare and powerful event. "
            "Eclipses accelerate change — things that have been building will suddenly shift. "
            "The {natal_planet} domain of your life may see unexpected developments within "
            "3 months before or after the eclipse date."
        ),
        "action":    "Don't start major new ventures on eclipse day itself. Watch for sudden news or changes.",
        "remedy":    "Fast on eclipse day. Meditate. Avoid major decisions for 3 days after.",
        "window":    90,
    },

    "planet_conjunct_natal": {
        "urgency":   "medium",
        "headline":  "{transit_planet} is activating your natal {natal_planet}",
        "body":      (
            "{transit_planet} is within 3° of your natal {natal_planet}. "
            "This activates the {natal_planet} themes in your chart — "
            "expect heightened activity in the areas this planet governs for the next few weeks."
        ),
        "action":    "Use this activation consciously — direct the energy intentionally.",
        "remedy":    "Strengthen your natal {natal_planet} with its mantra this week.",
        "window":    30,
    },
}

HOUSE_NAMES = {
    1: "1st (identity)", 2: "2nd (wealth)", 3: "3rd (communication)",
    4: "4th (home)", 5: "5th (creativity)", 6: "6th (health/service)",
    7: "7th (partnership)", 8: "8th (transformation)", 9: "9th (wisdom)",
    10: "10th (career)", 11: "11th (gains)", 12: "12th (liberation)",
}

SIGNS = [
    "Aries","Taurus","Gemini","Cancer","Leo","Virgo",
    "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"
]

ECLIPSE_DATES_2025_2026 = [
    date(2025, 3, 29),
    date(2025, 9, 7),
    date(2025, 9, 21),
    date(2026, 3, 3),
    date(2026, 8, 28),
]


def _degrees_apart(long1: float, long2: float) -> float:
    diff = abs(long1 - long2) % 360
    return min(diff, 360 - diff)


def _get_house(planet_sign: str, lagna_sign: str) -> int:
    if planet_sign not in SIGNS or lagna_sign not in SIGNS:
        return 0
    return (SIGNS.index(planet_sign) - SIGNS.index(lagna_sign)) % 12 + 1


def check_all_triggers(
    natal_chart: dict,
    current_transits: dict,
    dashas: dict,
    chart_id: str,
    sb,
) -> list:
    """
    Check all 6 alert triggers against this chart.
    Returns list of alert dicts ready to save.
    Only fires alerts not already sent (deduped via alert_log).
    """
    alerts = []
    natal_planets = natal_chart.get("planets", {})
    lagna_sign    = natal_chart.get("lagna", {}).get("sign", "Aries")
    today         = date.today()

    # ── Helper: dedup check ───────────────────────────────────────
    def already_sent(key: str) -> bool:
        try:
            res = sb.table("alert_log").select("id").eq(
                "chart_id", chart_id
            ).eq("alert_key", key).execute()
            return bool(res.data)
        except Exception:
            return False

    def mark_sent(key: str):
        try:
            sb.table("alert_log").insert({
                "chart_id":  chart_id,
                "alert_key": key,
            }).execute()
        except Exception:
            pass

    def make_alert(template_key: str, alert_key: str, overrides: dict) -> Optional[dict]:
        if already_sent(alert_key):
            return None
        t = ALERT_TEMPLATES.get(template_key, {})
        window_days = t.get("window", 30)
        headline = t.get("headline", "").format(**overrides)
        body     = t.get("body", "").format(**overrides)
        action   = t.get("action", "")
        remedy   = t.get("remedy", "")
        return {
            "chart_id":       chart_id,
            "alert_type":     template_key,
            "trigger_planet": overrides.get("transit_planet", overrides.get("trigger", "")),
            "natal_planet":   overrides.get("natal_planet", ""),
            "natal_house":    overrides.get("natal_house", 0),
            "headline":       headline,
            "body":           body,
            "urgency":        t.get("urgency", "medium"),
            "window_start":   today.isoformat(),
            "window_end":     (today + timedelta(days=window_days)).isoformat(),
            "action_advice":  action,
            "remedy":         remedy,
            "email_sent":     False,
            "_alert_key":     alert_key,
        }

    # ── Trigger 1+6: Saturn/Rahu/Ketu/any planet within 3° natal ─
    SENSITIVE_TRANSITS = {
        "Saturn": ["Moon", "Sun", "Mars"],
        "Rahu":   list(natal_planets.keys()),
        "Ketu":   list(natal_planets.keys()),
    }
    ALL_TRANSITS = list(natal_planets.keys())

    for t_planet, t_data in current_transits.items():
        t_long = t_data.get("longitude", -1)
        if t_long < 0:
            continue

        for n_planet, n_data in natal_planets.items():
            n_long = n_data.get("longitude", -1)
            if n_long < 0:
                continue
            orb = _degrees_apart(t_long, n_long)
            orb_limit = 8 if t_planet in ("Rahu", "Ketu") else 3

            if orb <= orb_limit:
                n_house = _get_house(n_data.get("sign", ""), lagna_sign)
                alert_key = f"{t_planet}_over_{n_planet}_{today.year}"

                # Specific high-impact templates
                if t_planet == "Saturn" and n_planet == "Moon":
                    a = make_alert("saturn_natal_moon", alert_key,
                        {"natal_planet": "Moon", "natal_house": n_house, "transit_planet": "Saturn"})
                elif t_planet == "Saturn" and n_planet == "Sun":
                    a = make_alert("saturn_natal_sun", alert_key,
                        {"natal_planet": "Sun", "natal_house": n_house, "transit_planet": "Saturn"})
                elif t_planet == "Saturn" and n_planet == "Mars":
                    a = make_alert("saturn_natal_mars", alert_key,
                        {"natal_planet": "Mars", "natal_house": n_house, "transit_planet": "Saturn"})
                elif t_planet == "Rahu":
                    a = make_alert("rahu_natal_planet", alert_key,
                        {"natal_planet": n_planet, "natal_house": n_house, "transit_planet": "Rahu"})
                elif t_planet == "Ketu":
                    a = make_alert("ketu_natal_planet", alert_key,
                        {"natal_planet": n_planet, "natal_house": n_house, "transit_planet": "Ketu"})
                else:
                    # Generic conjunction
                    a = make_alert("planet_conjunct_natal", alert_key,
                        {"transit_planet": t_planet, "natal_planet": n_planet,
                         "natal_house": n_house})

                if a:
                    alerts.append(a)
                    mark_sent(alert_key)

    # ── Trigger 3: Jupiter entering new house ─────────────────────
    jup_sign  = current_transits.get("Jupiter", {}).get("sign", "")
    jup_house = _get_house(jup_sign, lagna_sign)
    if jup_house:
        alert_key = f"jupiter_house_{jup_house}_{today.year}"
        a = make_alert("jupiter_new_house", alert_key,
            {"house": HOUSE_NAMES.get(jup_house, str(jup_house)),
             "transit_planet": "Jupiter"})
        if a:
            alerts.append(a)
            mark_sent(alert_key)

    # ── Trigger 4: Dasha change ───────────────────────────────────
    vim = dashas.get("vimsottari", [])
    now_dt = datetime.utcnow()
    for i, row in enumerate(vim):
        try:
            ed = datetime.strptime(str(row.get("end_date", ""))[:10], "%Y-%m-%d")
            days_to_end = (ed - now_dt).days
            if 0 <= days_to_end <= 30:
                old_lord = row.get("lord_or_sign", "")
                new_lord = vim[i + 1].get("lord_or_sign", "") if i + 1 < len(vim) else ""
                if old_lord and new_lord:
                    alert_key = f"dasha_change_{old_lord}_{new_lord}"
                    a = make_alert("dasha_change", alert_key,
                        {"old_dasha": old_lord, "new_dasha": new_lord,
                         "transit_planet": old_lord})
                    if a:
                        alerts.append(a)
                        mark_sent(alert_key)
        except Exception:
            continue

    # ── Trigger 5: Eclipse hitting natal planet ───────────────────
    for eclipse_date in ECLIPSE_DATES_2025_2026:
        days_to_eclipse = abs((eclipse_date - today).days)
        if days_to_eclipse <= 90:
            # Get eclipse longitude (approx — Rahu/Ketu axis)
            rahu_long = current_transits.get("Rahu", {}).get("longitude", -1)
            if rahu_long < 0:
                continue
            for n_planet, n_data in natal_planets.items():
                n_long = n_data.get("longitude", -1)
                if n_long < 0:
                    continue
                orb = _degrees_apart(rahu_long, n_long)
                if orb <= 8:
                    n_house = _get_house(n_data.get("sign", ""), lagna_sign)
                    alert_key = f"eclipse_{eclipse_date}_{n_planet}"
                    a = make_alert("eclipse_natal_planet", alert_key,
                        {"natal_planet": n_planet, "natal_house": n_house,
                         "eclipse_date": eclipse_date.strftime("%B %d, %Y"),
                         "transit_planet": "Eclipse"})
                    if a:
                        alerts.append(a)
                        mark_sent(alert_key)

    return alerts


def send_alert_email(
    to_email: str,
    first_name: str,
    alert: dict,
    resend_api_key: str,
) -> bool:
    """Send alert email via Resend."""
    try:
        import resend
        resend.api_key = resend_api_key

        urgency_color = {
            "high":        "#EF4444",
            "medium":      "#F59E0B",
            "opportunity": "#00BFA5",
        }.get(alert.get("urgency", "medium"), "#F59E0B")

        urgency_label = {
            "high":        "⚠️ Important Alert",
            "medium":      "📡 Transit Alert",
            "opportunity": "✨ Opportunity Window",
        }.get(alert.get("urgency", "medium"), "📡 Alert")

        name = first_name or "Explorer"

        html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="background:#0A0A0F;color:#F1F5F9;font-family:Inter,Arial,sans-serif;margin:0;padding:0;">
  <div style="max-width:600px;margin:0 auto;padding:32px 24px;">

    <div style="margin-bottom:24px;">
      <span style="color:#00BFA5;font-size:18px;font-weight:700;letter-spacing:-0.5px;">ANTAR</span>
      <span style="color:#64748B;font-size:12px;margin-left:8px;">Life Navigation</span>
    </div>

    <div style="background:#12121A;border:1px solid rgba(255,255,255,0.06);border-left:4px solid {urgency_color};border-radius:12px;padding:24px;margin-bottom:20px;">
      <div style="color:{urgency_color};font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">
        {urgency_label}
      </div>
      <h2 style="color:#F1F5F9;font-size:20px;font-weight:700;margin:0 0 16px 0;line-height:1.3;">
        {alert['headline']}
      </h2>
      <p style="color:#94A3B8;font-size:15px;line-height:1.6;margin:0 0 16px 0;">
        Hey {name} — {alert['body']}
      </p>
    </div>

    <div style="background:#12121A;border:1px solid rgba(255,255,255,0.06);border-radius:12px;padding:20px;margin-bottom:16px;">
      <div style="color:#00BFA5;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">What to do</div>
      <p style="color:#F1F5F9;font-size:14px;line-height:1.6;margin:0;">{alert['action_advice']}</p>
    </div>

    <div style="background:#12121A;border:1px solid rgba(255,255,255,0.06);border-radius:12px;padding:20px;margin-bottom:24px;">
      <div style="color:#F59E0B;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">Recalibration practice</div>
      <p style="color:#F1F5F9;font-size:14px;line-height:1.6;margin:0;">{alert['remedy']}</p>
    </div>

    <div style="text-align:center;">
      <a href="https://antar.world/today" 
         style="background:#00BFA5;color:#0A0A0F;font-weight:700;font-size:14px;padding:12px 28px;border-radius:50px;text-decoration:none;display:inline-block;">
        View Full Reading →
      </a>
    </div>

    <p style="color:#334155;font-size:12px;text-align:center;margin-top:32px;">
      Antar · antar.world · 
      <a href="https://antar.world/alerts/unsubscribe" style="color:#334155;">Manage alerts</a>
    </p>
  </div>
</body>
</html>"""

        resend.Emails.send({
            "from":    "Antar <alerts@antar.world>",
            "to":      [to_email],
            "subject": f"[Antar] {alert['headline']}",
            "html":    html,
        })
        return True
    except Exception as e:
        print(f"Email send failed: {e}")
        return False


def run_daily_alert_check(sb) -> dict:
    """
    Daily cron job — check all charts, fire personal alerts.
    Called by the scheduler in main.py.
    """
    import sys
    sys.path.insert(0, "/app")

    from antar_engine.transits_engine import calculate_current_transits

    resend_key = os.getenv("RESEND_API_KEY", "")
    stats = {"checked": 0, "alerts_fired": 0, "emails_sent": 0, "errors": 0}

    # Get all charts with email (opt-in only)
    try:
        charts = sb.table("charts").select(
            "id,chart_data,email,first_name,lagna_sign"
        ).not_.is_("email", "null").execute()
    except Exception as e:
        return {"error": str(e)}

    for chart_row in charts.data:
        try:
            chart_id    = chart_row["id"]
            natal_chart = chart_row.get("chart_data", {})
            email       = chart_row.get("email", "")
            first_name  = chart_row.get("first_name", "")

            if not natal_chart or not email:
                continue

            # Get current transits
            current_transits = calculate_current_transits(natal_chart)

            # Get dashas for this chart
            dasha_res = sb.table("dasha_periods").select("*").eq(
                "chart_id", chart_id
            ).execute()
            dashas = {"vimsottari": dasha_res.data or []}

            # Check all 6 triggers
            new_alerts = check_all_triggers(
                natal_chart=natal_chart,
                current_transits=current_transits,
                dashas=dashas,
                chart_id=chart_id,
                sb=sb,
            )

            stats["checked"] += 1

            for alert in new_alerts:
                alert_key = alert.pop("_alert_key", "")

                # Save to user_alerts
                sb.table("user_alerts").insert({
                    k: v for k, v in alert.items()
                    if k != "_alert_key"
                }).execute()

                stats["alerts_fired"] += 1

                # Send email if key available
                if resend_key and email:
                    sent = send_alert_email(email, first_name, alert, resend_key)
                    if sent:
                        stats["emails_sent"] += 1

        except Exception as e:
            stats["errors"] += 1
            continue

    return stats
