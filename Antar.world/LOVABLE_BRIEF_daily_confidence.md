# Lovable Brief — Today card: "How sure is this?" (convergence-confidence)

Additive. The Today card endpoint now returns a new **`confidence`** object. Nothing
else on the card changes — this is a quiet conviction read *below* the existing
headline/verdict. It NEVER changes the verdict; it reports how much the independent
timing layers agree with it.

**`GET /api/v1/daily-signal/{chart_id}`** (the Today card; also the `POST` form) now includes:
```json
"confidence": {
  "level": "moderate",                     // "high" | "moderate" | "low"  (STABLE enum)
  "line": "Most of the day lines up toward opportunity (the day's star, where the Moon is today and your current chapter), though your chart's own pattern pulls the other way — a fairly confident read, not a certainty.",
  "aligned": ["the day's star", "where the Moon is today", "your current chapter"],
  "tension": ["your chart's own pattern"],
  "layers_read": 4
}
```

Real examples seen live (2026-09-16):
- **Steady day, decent agreement** → `level:"moderate"`, aligned has 3, tension has 1.
- **Hard-season / split day** → `level:"low"`, `line:"The forces are split today — some readings lean toward caution (…), others the opposite (…). Hold this as a mixed read, not a sure thing."`
- **es user** → same shape, every string already in Spanish: `line:"La mayor parte del día se alinea hacia la oportunidad…"`, `aligned:["la estrella del día", …]`.

`confidence` is **absent** on a genuinely quiet day with nothing converging → **hide the whole section** (treat missing/`null` the same as "don't render").

## Where + how to render (Today page)
A small block directly **under the headline/verdict**, above or beside the day actions:

1. **Primary — the sentence.** Render `confidence.line` as one plain line. This is the
   whole user-facing message; jargon-free and already localized. If you show nothing
   else, show this.
2. **Level indicator.** Style off `confidence.level` (do NOT re-derive it):
   - `high` → strongest treatment (e.g. 3 filled dots, or a "Strong alignment" chip).
   - `moderate` → medium (2 dots / "Fairly confident").
   - `low` → lightest (1 dot / "Mixed signals").
   - Optional label copy: high="Strong alignment", moderate="Fairly confident", low="Mixed read".
3. **Optional detail (collapsed by default).** `aligned[]` = what points the same way,
   `tension[]` = what pulls the other way. Render as two tiny labelled lists/chips
   ("Pointing the same way" / "Pulling the other way"). These are already plain,
   localized phrases. Skip either array if empty.

## Rules (important)
- **`level` is a stable enum — never translate it, never recompute it.** `line`,
  `aligned[]`, `tension[]` are display prose and arrive already localized (es/pt/fr);
  render them as-is, don't run them through any client i18n.
- **`low` is NOT "bad".** It means the signals are *mixed / not converged* — the day can
  still be positive. Style `low` as **neutral/muted**, never alarm-red. Confidence is
  about certainty, not good-vs-bad; the good-vs-bad tone lives in the existing
  headline/`direction`/`day_energy`, which this must never contradict or override.
- **Don't render a second verdict.** No YES/NO, no percentage. `layers_read` is metadata —
  only surface it if framed softly ("read across 4 signals"), otherwise ignore it.
- **Card only.** The 7-day strip (`/api/v1/daily-week`) does NOT carry `confidence`;
  render this on the single Today card, not on strip days.
- The season-cap ("A steadier day for X — a small opening in a demanding stretch") is
  already baked into the `headline` string — no new field, nothing to do for it.

## Why
This is what makes the daily read feel like a careful astrologer, not a horoscope: a
day is only as strong as the *agreement* among independent timing layers (the day's
star, the Moon's placement, the running chapter, the chart's own pattern, the longer
season). Surfacing conviction honestly — "strong alignment" vs "mixed read" — earns
trust and sets expectations, without ever over-claiming. It pairs with the deployed
convergence engine (backend `antar_engine/daily_convergence.py`); the sentence is the
product, the dots are the glance.
