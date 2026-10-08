# Lovable prompt — fast login: one bootstrap call, no duplicate fetches

Paste into Lovable chat. Backend is live once the perf/login-bootstrap PR is merged and deployed.

---

Performance fix for login/app-shell load. Frontend only; do NOT change any backend logic or add new business logic.

**Problem (from Railway logs of a real login):** after sign-in the app fires ~20 separate API calls, each preceded by a CORS preflight, in a slow sequence (~5 s apart), and several repeat 3–4×: `/chart/{id}` ×3, `/entitlements/{id}` ×4, `/messaging/whatsapp/status` ×4, `/alerts/{id}` ×3, `/me` ×3. `auth/link-chart` runs LAST (~30 s in). The backend answers every one quickly; the delay is the request chain.

**1. One bootstrap call.** New endpoint: `GET {API}/api/v1/bootstrap/{chart_id}?language={lang}&tz_offset={minutes}` returns
`{ chart, entitlements, subscription, streak, accuracy, pending_feedback, errors: string[] }`.
Each section has the exact same shape as its individual endpoint. A failed section is `null` and named in `errors`. 404 = chart not found.
Call it ONCE as soon as `chart_id` is known, and seed the react-query cache from it with `queryClient.setQueryData` under the SAME keys the individual hooks use (chart, entitlements, subscription, streak, prediction accuracy, pending feedback). Components keep using their existing hooks and now find the data already cached. If a section is `null`, leave that hook to fetch normally.

**2. Stop duplicate fetches.** Set a global `staleTime` of 60 s on the QueryClient (`refetchOnWindowFocus: false`, `refetchOnMount: false` for these queries) and make sure each query key above is defined in ONE shared hook, not re-declared per component. A given endpoint must fire at most once per page load.

**3. Reorder.** Fire `POST /api/v1/auth/link-chart` immediately after sign-in, in parallel with bootstrap — not after the chart loads. Start `daily-signal` (Today card) in parallel with bootstrap as well, not after.

**4. Render from cache first.** Render the Today card as soon as daily-signal returns; do not block it on entitlements/subscription/streak/accuracy/alerts/WhatsApp status. Those fill in afterward with skeletons, never a full-page spinner.

**5. Defer the non-critical.** `alerts`, `messaging/whatsapp/status`, `/me`, `/me/charts`, `chart/{id}/topic-read`, `chart/{id}/topic-checkbacks`, `chart/{id}/topics`, `circle/{id}` and `people/{id}` load after first paint (e.g. `requestIdleCallback` or after the Today card renders), once each. In prod logs `alerts` fired 82× and `whatsapp/status` 75× in 6 hours: poll `alerts` at most every 5 minutes and only while the tab is visible, and fetch `whatsapp/status` once per session (refetch only after the user connects/disconnects). `topic-read` and `topic-checkbacks` must be fetched only when the user opens that topic, not for every topic on mount.

**6. Fix the missing auth header.** `GET /api/v1/outcomes/due/{chart_id}` returns 422 because the request is sent WITHOUT the `Authorization: Bearer <supabase access token>` header (4 failures in one session). Send it like the other authenticated calls (`/me`, `/me/charts`).

**Acceptance:** `outcomes/due` returns 200; with the Network tab open on a fresh login, each endpoint appears at most once, bootstrap + link-chart + daily-signal start together, and the Today card paints without waiting on the others.
