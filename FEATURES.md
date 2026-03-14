# Antar AI — Feature Tracker
> Last updated: 2026-03-14
> Backend: https://antar-fastapi-production.up.railway.app
> Frontend: https://antar.world (Lovable)

---

## ✅ COMPLETED — Backend

### Core Engine
- [x] Vimsottari Dasha calculation (MD + AD, correct sequence from lord)
- [x] Jaimini Dasha calculation
- [x] Ashtottari Dasha calculation
- [x] D1 chart calculation (lagna, planets, nakshatras)
- [x] Geocoding (city → lat/lng/timezone) — 50+ cities
- [x] Supabase schema aligned (charts, dasha_periods tables)
- [x] Dasha insert fixed (planet_or_sign, type, metadata columns)
- [x] `_current_dasha_str()` returns correct MD-AD (verified Mars-Moon, Venus-Mercury)

### API Endpoints
- [x] `GET  /health`
- [x] `POST /api/v1/chart/create` — returns lagna, moon, dasha, chart_id
- [x] `GET  /api/v1/chart/{chart_id}` — returns full chart
- [x] `POST /api/v1/predict` — LLM prediction with DKP context
- [x] `POST /api/v1/predict/daily-practice` — daily signal
- [x] `POST /api/v1/proof-points` — 3 past-life pattern statements
- [x] `POST /api/v1/chapter-arc` — current life chapter narrative
- [x] `POST /api/v1/chakra` — chakra reading
- [x] `POST /api/v1/career` — career reading
- [x] `GET  /api/v1/locale/{country_code}` — language detection

### Intelligence Layers
- [x] DKP (Desh-Kaal-Patra) synthesis in all predictions
- [x] Patra context (age, career stage, marital status, etc.)
- [x] Desh context (country-aware cultural framing)
- [x] Rate limiting (3 free predictions/month)
- [x] Multi-language (EN, HI, ES, PT-BR)
- [x] Ayurveda + Astrology food guidance module
- [x] Psychology layer (soul archetype, life stage, gender-aware framing)
- [x] Gender field added to chart create + patra
- [x] Current city/country fields added

### Infrastructure
- [x] Railway deployment with 300s timeout
- [x] railway.toml valid TOML config
- [x] DeepSeek LLM integration
- [x] Supabase client (supabase==2.28.0)
- [x] pyswisseph ephemeris

---

## ✅ COMPLETED — Frontend (Lovable)

### Funnel
- [x] Step 1: Birth data collection (DOB, time, city, country)
- [x] Step 2: Waze animation (4-phase loading)
- [x] Step 3: Proof points display (3 cards)
- [x] Step 4: Accuracy score screen

### Auth
- [x] Google OAuth
- [x] Email magic link
- [x] Auth modal (bottom sheet)

### Portal
- [x] Dashboard (/dashboard) — daily signal
- [x] Chat (/chat) — Ask Antar
- [x] Patterns (/patterns) — prediction tracker
- [x] Practices (/practices) — mantras, remedies

### Pricing
- [x] Upgrade modal with local pricing
- [x] pricing.ts — 11 currencies
- [x] PlanGate component (feature locks)
- [x] UsageBar component (free limit indicator)

---

## 🔴 IN PROGRESS

### Backend
- [ ] Compatibility engine — `antar_engine/compatibility.py` ← JUST BUILT
  - [ ] Wire to new endpoint: `POST /api/v1/compatibility`
  - [ ] Add to main.py router
  - [ ] Test with known charts

### Frontend
- [ ] Proof points — 3 response buttons (Yes/Partially/No)
- [ ] Proof points — card advance animation
- [ ] Score screen — "See What's Coming" routes to /dashboard not /
- [ ] Rising sign blank on animation screen (map response.lagna)
- [ ] Life Stage field on animation screen
- [ ] Daily greeting — time-aware (Good morning/afternoon/evening)
- [ ] Ayurveda tip card in /dashboard
- [ ] DKP context strip in /dashboard (3 pills)
- [ ] Soul archetype in /profile
- [ ] Gender pill in Step 1 of funnel
- [ ] Current city field in Patra screen
- [ ] Section headers — "pattern" not "chart" everywhere

---

## 🟡 PLANNED — Backend (Priority Order)

### Week 1
- [ ] Wire compatibility.py to API endpoint
  ```
  POST /api/v1/compatibility
  Body: { chart_id_a, chart_id_b, 
          name_a, name_b,
          birth_date_a, birth_date_b,
          compatibility_type: 'relationship'|'business' }
  Returns: full compatibility report with % scores
  ```
- [ ] Add current_city/current_country to Supabase charts table
  ```sql
  ALTER TABLE charts ADD COLUMN IF NOT EXISTS current_city text;
  ALTER TABLE charts ADD COLUMN IF NOT EXISTS current_country text;
  ```
- [ ] Lunar cycle engine — `antar_engine/lunar_cycle.py`
  - Phase calculation from natal Moon longitude
  - Returns phase name + days remaining

### Week 2
- [ ] Muhurta (auspicious timing) engine
  ```
  GET /api/v1/muhurta?chart_id=X&event=marriage|business|travel
  Returns: best windows in next 90 days with reasons
  ```
- [ ] Astrocartography engine (best cities)
  - Already has endpoint skeleton
  - Needs planet line calculations by geography
- [ ] Team/Organizational compatibility
  ```
  POST /api/v1/team/analyze
  Body: { chart_ids: [id1, id2, ...], 
          org_goal: 'startup'|'enterprise'|'creative' }
  Returns: role suggestions, compatibility matrix, timing
  ```

### Week 3
- [ ] Prashna (horary) astrology
  ```
  POST /api/v1/prashna
  Body: { question, question_time, location }
  Returns: answer based on chart cast at question moment
  ```
- [ ] Varshphal (solar return / yearly chart)
  ```
  GET /api/v1/varshphal/{chart_id}?year=2026
  Returns: annual chart + theme for the year
  ```
- [ ] Transit alerts (push/email)
  - Cron job checking major transits
  - Alert when Jupiter/Saturn changes signs
  - Personal transit hits on natal chart

### Month 2
- [ ] Lal Kitab deep analysis (already has data)
- [ ] Nakshatra-based compatibility (Kuta system extended)
- [ ] Marriage timing prediction (Vivaha Muhurta)
- [ ] Career timing prediction (specific promotion/change windows)
- [ ] Health signal (6th house + MD transits)
- [ ] Wealth signal (2nd, 11th house analysis)

---

## 🟡 PLANNED — Frontend (Priority Order)

### UX Critical (fix before launch)
- [ ] Landing page — full redesign (prompt written, apply to Lovable)
- [ ] Prove-it funnel — all 3 response buttons + card animation
- [ ] Score screen routing → /dashboard
- [ ] Rising sign showing on animation screen
- [ ] Remove ALL emojis except 🔥 streak

### Week 1 Features
- [ ] Compatibility UI — /compare page
  - Two-person birth data entry
  - Animated compatibility calculation
  - Score reveal (large % with color)
  - Five dimension breakdown
  - Strengths and growth areas
  - Yin-yang insights section
  - D9 soul connection section
  - Dasha timing alignment
- [ ] Profile page — soul archetype card
- [ ] Dashboard — ayurveda tip card
- [ ] Dashboard — DKP context strip

### Week 2 Features  
- [ ] Astrocartography card (Navigator gate)
- [ ] Mantra audio playback (Seeker gate)
- [ ] Prediction tracker (Seeker gate)
- [ ] Monthly life briefing page

### Week 3 Features
- [ ] Team compatibility (/team page, Enterprise gate)
- [ ] Muhurta calendar (auspicious dates)
- [ ] Varshphal annual chart view
- [ ] Transit alert preferences in profile

### Month 2
- [ ] Offline mode (PWA)
- [ ] Push notifications (daily signal)
- [ ] WhatsApp integration (Navigator — daily signal to WhatsApp)
- [ ] PDF report export (Navigator)
- [ ] Share card (social — compatibility score, dasha info)

---

## 💳 PAYMENTS (Phase 2)

### Integration Todo
- [ ] Add VITE_STRIPE_KEY to Lovable env vars
- [ ] `POST /api/v1/payments/create-checkout-session`
- [ ] `POST /api/v1/payments/webhook` (Stripe)
- [ ] Razorpay integration for INR (India)
- [ ] Update Supabase profiles.plan on subscription events
- [ ] Subscription management page
- [ ] Cancellation flow

### Markets
- [ ] USA/CA/UK/AU/NZ/ES: Stripe (card, Apple Pay, Google Pay)
- [ ] India: Razorpay (UPI, PhonePe, Paytm, NetBanking)
- [ ] Brazil: Stripe (PIX, boleto)
- [ ] Mexico: Stripe (OXXO, SPEI)
- [ ] Colombia: Stripe (PSE, Nequi)
- [ ] Argentina: Stripe USD only (never ARS)

---

## 🌐 SEO & MARKETING (Ongoing)

- [ ] Meta tags on all pages
- [ ] OG images (1200x630)
- [ ] JSON-LD structured data
- [ ] sitemap.xml
- [ ] robots.txt
- [ ] Google Analytics (VITE_GA_MEASUREMENT_ID)
- [ ] Blog/content — "What is Vimsottari Dasha" etc.
- [ ] Language-specific landing pages (Hindi, Spanish, Portuguese)

---

## 🔒 SECURITY & COMPLIANCE

- [x] Supabase leaked password protection — ENABLED
- [ ] RLS (Row Level Security) policies on all tables
- [ ] GDPR data deletion endpoint
- [ ] Privacy policy page
- [ ] Terms of service page
- [ ] Data export (user can download their chart)
- [ ] Cookie consent banner (EU users)

---

## 🧪 TESTING

- [x] API audit script (`/tmp/audit_antar_v2.py`) — 14/15 passing
- [x] Dasha verification script (`tools/verify_dasha.py`)
- [x] Local end-to-end test (Mars-Moon confirmed)
- [x] Test case: Nov 26 1974, New Delhi → Mars-Moon ✓
- [x] Test case: Jan 8 1975, Kuwait City → Venus-Mercury ✓
- [ ] Test compatibility engine with known charts
- [ ] Automated test suite (pytest)
- [ ] Load testing (Railway scaling)

---

## 📊 METRICS TO TRACK

- Prove-it funnel conversion (Step 1 → Step 4)
- Auth conversion (Step 4 → account creation)
- Free → Seeker conversion rate (target: 3%)
- D7 retention (target: 40%)
- D30 retention (target: 20%)
- Prediction accuracy rating (user feedback)
- Ayurveda tip engagement (tap rate)

---

## 🏗️ INFRASTRUCTURE TODOS

- [ ] Railway: set custom domain antar.world → Railway
- [ ] Railway: scale to 2 workers (already in start command)
- [ ] Supabase: enable RLS on all tables
- [ ] Supabase: set up backup schedule
- [ ] Resend.com: set up custom email domain
- [ ] Sentry: error monitoring
- [ ] Uptime monitoring (Better Stack or similar)

---

## VERSION HISTORY

| Version | Date | What shipped |
|---------|------|-------------|
| v0.1.0 | 2026-03-10 | Initial Railway deployment |
| v0.2.0 | 2026-03-12 | Supabase schema fixed, chart create working |
| v0.3.0 | 2026-03-13 | Dasha insert fixed (planet_or_sign, type columns) |
| v0.4.0 | 2026-03-14 | Mars-Moon dasha correct, ayurveda + psychology modules |
| v0.5.0 | 2026-03-14 | Compatibility engine built (D1+D9+Houses+Timing) |
