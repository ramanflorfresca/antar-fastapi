# Lovable prompt — remove the public "Try the demo" button; add an unlisted reviewer demo link

Paste into Lovable chat. Backend change is in the feat/demo-guard PR; merge + deploy it first.

---

Frontend only. Do NOT add or change any backend/business logic.

**Why:** "Try the demo — no sign-in" was only for the Apple reviewer. Real users should not see a way to skip sign-in. Replace the public button with an UNLISTED link that only we give out (App Review notes, testers).

**1. Remove the button.** Delete the "Try the demo — no sign-in" link/button from the sign-in screen (the "Welcome back." screen) and from every other place it appears (landing page, onboarding, footer, menus). Keep "New here? Enter your birth details" exactly as is — that is the real onboarding path. Nothing anywhere in the UI, sitemap, robots, or nav may link to the demo route.

**2. Keep an unlisted route `/demo`.** It must not be linked from anywhere and must be `noindex` (`<meta name="robots" content="noindex,nofollow">`; exclude from sitemap).
- On load, read `k` from the query string (`/demo?k=…`).
- Call `GET {API}/api/v1/demo/chart?k={k}`.
- If the response is `{ available: true, chart_id, display_name }`: set the local `demoChartId = chart_id` (no Supabase session, same mechanism the old button used) and navigate to `/ask` bound to that chart.
- If `available` is false (missing/wrong `k`, or demo off): redirect to the normal sign-in screen. Show nothing that reveals a demo exists.
- Do not persist `k` anywhere after the redirect (strip it from the URL with `history.replaceState`).

**3. Demo banner.** While `demoChartId` is active, show a slim persistent banner: "Demo — your changes aren't saved · Sign in". "Sign in" clears `demoChartId` and goes to sign-in.

**4. Read-only handling.** The backend returns `403 {"demo": true, "code": "DEMO_READ_ONLY"}` for writes and `429 {"demo": true, "code": "DEMO_RATE_LIMIT"}` when the daily Ask limit is hit. On 403 show a friendly inline message: "Create your own chart to save this." On 429: "You've reached today's demo limit. Create your own chart to keep asking." Never show these as errors/toasts with technical text. Ask, Today, Year, Practice, People (view) and Places (view) stay fully usable; hide or disable controls that save/edit/delete/connect WhatsApp/register push/billing.

**5. Leave the marketing-page demo hero alone** (`/api/v1/demo/today` is unrelated and stays).

**Acceptance:** sign-in screen has no demo option; `/demo` with no/wrong `k` lands on sign-in; `/demo?k=<token>` opens Ask on the demo chart with the banner; searching the built site for a link to `/demo` finds none.
