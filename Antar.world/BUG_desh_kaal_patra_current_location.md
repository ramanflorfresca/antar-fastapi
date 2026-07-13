# BUG — देश-काल-पात्र: daily timing uses country-capital, not the user's actual city

**Severity:** High · **Type:** correctness (timing) + data quality
**Found:** live-audit, 2026-07-12, on user Kulbir (`b1ec259a-4c53-4525-9bb9-61ca134638e2`)

**Status (2026-07-12):** **P1 DONE** — daily-signal now geocodes the user's
`current_city` (via existing `_geocode_city`: local 60-city table → Google) and
computes the panchanga/hora with those coords + a **DST-correct IANA offset**
(`antar_engine.tz_utils.iana_offset_hours`), falling back to the old
country-capital behavior only when the city can't be geocoded. Works fully in
prod (Google key present); local table covers 60 major cities. **P0 (persist
geocoded current coords/tz to avoid per-request geocoding + backfill), P2 (real
birth coords), P3 (faith-aware remedy) still open.**

## One-line
For a user who has migrated, the daily reading's **sunrise-anchored timing**
(best window, Rahu Kalam, Abhijit, lucky hours) is computed for the **capital of
their current country + a single fixed country timezone**, not for the city they
actually live in — so the "when to act today" is off by hours (and ignores DST).

## Who is affected
- **Every user whose current city ≠ their country's capital** — i.e. almost
  everyone in a large/multi-timezone country.
- **Every US user** gets **US-Eastern (−5)** regardless of real timezone; a user
  in California (−8) or New Mexico (−7/−6) is 2–3 hours off.
- **Daylight-saving is never applied** (offsets are fixed integers).
- Migrated users specifically, where the gap is most visible.

## Concrete repro (Kulbir)
```
curl -s "https://antar-fastapi-production.up.railway.app/api/v1/daily-signal/b1ec259a-4c53-4525-9bb9-61ca134638e2?language=en"
```
Stored on the chart:
- `current_city = Albuquerque`, `current_country = US`  ← engine knows he's in NM
- `latitude/longitude = 20.5937, 78.9629`  ← **India-centroid placeholder**, not real Faridabad
- `timezone_offset = 5.5` (IST, birth), no current-location tz

What the engine computes the panchanga/hora with:
- **coords:** `COUNTRY_COORDS["US"] = (38.9072, −77.0369)` → **Washington DC**
- **tz:** `_COUNTRY_TZ_OFFSETS["US"] = −5` → **US Eastern**

Kulbir is in **Albuquerque (35.08, −106.65), Mountain (−7 / −6 DST)**.
→ ~30° of longitude + 2 timezones off. Symptom in the payload: `lucky_hours`
land at **12 AM / 2 AM / 3 AM / 5 AM** (dead of night).

## देश-काल-पात्र mapping (what's right vs wrong)
| Layer | Should use | Actually uses | Status |
|---|---|---|---|
| Pātra — birth chart | Faridabad 1957 (fixed) | fixed, but on **India-centroid placeholder** coords | ⚠️ wrong birth coords |
| Kāl — transits | global | global | ✅ |
| Kāl — daily local timing | Albuquerque, Mountain | **US capital DC + fixed −5, no DST** | ❌ |
| Desh — country narrative | US | US (`current_country`) | ✅ |
| Desh/Pātra — culture/faith | Sikh | generic "**church**" remedy | ❌ (see related) |

## Root cause
The location design is *correct in intent* — `_resolve_moment_coords` docstring
says "use where the user IS NOW, not where they were born." The gap is
**granularity + missing geocode**:

1. **`current_city` is never geocoded.** The chart stores the city string
   ("Albuquerque") but no current lat/long/IANA-tz. `geocode_source = None`.
2. **`_resolve_moment_coords`** (`main.py:23762`) therefore falls through to
   priority 2: `COUNTRY_COORDS[current_country]` — the **country capital**, not
   the city.
3. **`_get_local_start_date` / daily-signal** (`main.py:~17746`) derive the tz
   from **`_COUNTRY_TZ_OFFSETS[current_country]`** — one fixed integer per
   country, no sub-country zones, no DST.

## Affected code
- `main.py:23762` — `_resolve_moment_coords()` (country-capital fallback)
- `main.py` — `_COUNTRY_TZ_OFFSETS` (`"US": -5`, fixed; has `DEFAULT`)
- `main.py:~17746` — `get_daily_signal_endpoint` (uses both above for panchanga)
- `antar_engine/day_chart_engine.py` — `COUNTRY_COORDS` (`"US": (38.9072,-77.0369)`)
- also used by: Prashna, welcome prediction, hora/muhurta, ask intraday clock
  (anything sunrise-anchored routes through `_resolve_moment_coords`)

## Fix plan (prioritized)
- **P0 — geocode current_city on save.** When a user sets/updates their current
  city, geocode it → store `current_lat`, `current_lng`, and an **IANA timezone**
  (e.g. `America/Denver`). Backfill existing rows that have a `current_city` but
  no current coords.
- **P1 — consume it.** `_resolve_moment_coords` should prefer stored
  `current_lat/lng` over the country-capital fallback; the daily-signal tz should
  come from the IANA timezone (DST-correct via `zoneinfo`), not
  `_COUNTRY_TZ_OFFSETS`. Keep country-capital only as a last resort.
- **P2 — birth coords.** Backfill real birth-city coordinates (Faridabad ≈
  28.41, 77.31) to replace the India-centroid placeholder; his natal
  ascendant/houses are currently built on the centroid.
- **P3 — faith-aware remedy layer.** The nudge said "leave a donation at the
  **church**"; for a Sikh (Kulbir *Singh*) it should be **gurdwara / langar**.
  Either infer from name/region or avoid naming a specific place of worship.

## Acceptance criteria
- Kulbir's daily best window / Rahu Kalam / Abhijit / lucky hours match
  **Albuquerque Mountain time** (and shift correctly across DST).
- Two users in the same country but different timezones (e.g. NY vs LA) get
  **different** daily timing.
- No `lucky_hours` in the 12 AM–5 AM band for a normally-located user.

## Related
- Lucky-hours-at-2AM symptom (same root cause).
- Earlier flag: "is the intraday window location-sensitive?" — answer: only to
  country-capital granularity, which is this bug.
