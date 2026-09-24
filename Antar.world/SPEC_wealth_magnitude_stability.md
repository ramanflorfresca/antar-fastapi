# Spec — Wealth Magnitude + Stability read (native-level, NOT vertical)

## Why
The "chart predicts which business vertical / which company succeeds" idea was
tested and FALSIFIED (see business-timing study — naive-sector falsified,
dasha-timing p≈0.40 on the clean cohort). Do NOT resurrect it.

But a *different*, chart-defensible read survives and is what owners actually
need: grade the **native's own wealth engine** —
- **MAGNITUDE** — how big can this person's wealth go? (yogas + strength of the
  wealth houses)
- **STABILITY** — does it HOLD, or arrive-and-dissolve? (nodes in the money
  houses) → the *sizing discipline* that fits the chart.

This is the read that would have (a) framed a founder's multi-venture play
correctly and (b) flagged the Ketu-11th "gains don't hold" bankruptcy risk
BEFORE a $3M concentrated loss. It never picks the vertical or predicts a
specific company — it grades capacity + how to size bets.

## Boundary (hard)
- NEVER name or rank a vertical (restaurant vs tech vs real-estate).
- NEVER predict a specific company's success/failure.
- Frame everything as native CAPACITY (magnitude), native STABILITY, and the
  SIZING RULE that follows — then "execution + market decide which vehicle wins."

## Engine — `antar_engine/wealth_magnitude.py`
`wealth_profile(chart_data, dashas=None, chart_record=None) -> dict`

**Magnitude** (how big):
- Wealth/raj/mahapurusha yogas from `yogas.detect_all_yogas` (strong=3, moderate=2,
  weak=1). yogas.py is the source of truth.
- Dignity of the wealth-house lords (2 own capital, 10 work/status, 11 gains) +
  benefic/malefic occupants (exalted/own +, debilitated −).
- (If dashas given) whether a wealth-yoga planet's Mahadasha is running/next →
  "switched on now" note (magnitude realises IN its period; latent otherwise).
- score → label: `modest | solid | high | exceptional` (exceptional is rare).

**Stability** (does it hold) — nodes in money houses {2, 8, 11}:
- **Ketu in 2/8/11 → `fragile`**: gains arrive and dissolve; concentration is the
  trap. Sizing = "cap exposure per venture, take profits off the table, never bet
  the house on one thing."
- **Rahu in 11 → `volatile` (large-but-swingy)**: big upside, prone to over-reach.
  Sizing = "spread across bets, cap the downside per bet — your instinct to run
  several is chart-appropriate."
- **Rahu in 2/8 → `volatile` (leverage/debt)**: guard against over-leverage.
- No node, but a 6/8/12 lord or malefic afflicts 2/11 → `moderate`.
- Else → `stable`.

## Output
```
{ "available": true,
  "magnitude": {"score": 7.5, "label": "high", "activated_now": true, "drivers": [...] },
  "stability": {"grade": "volatile", "node": "Rahu-11",
                "sizing_advice": "spread across bets, cap the downside per bet …",
                "drivers": [...] },
  "headline": "A large wealth engine — but a volatile one: spread your bets.",
  "summary": "<plain paragraph, zero jargon>",
  "guard": "This grades your wealth capacity and how to size bets — it does NOT
            pick which venture or predict a specific company." }
```
Plain language in headline/summary (no planet/house/sign words).

## Surfacing
1. `GET /api/v1/wealth-profile/{chart_id}` (this build).
2. Ask: route "how big will my wealth be / should I concentrate or diversify /
   will it last" → this read (follow-up).
3. Later: a Full-Chart "Your wealth engine" card.

## Validation to run later
Retro-check the stability flag against known outcomes: Ketu-money-house natives
who took concentrated losses (Shashi $3M) should read `fragile`; steady
compounders should read `stable`. Magnitude is descriptive (capacity), not a
dated prediction — no accuracy gate needed, but keep it honest and un-hyped.
