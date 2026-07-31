# Lovable Brief — Google auth failure + wrong-chart binding

Two frontend/Supabase-side fixes. The FastAPI backend is already correct and
hardened (it now rejects bad/foreign chart ids with 400 instead of 500, and `/me`
returns the right `primary_chart_id`). These two are the remaining causes.

---

## 1. Google OAuth: "Authorization failed — State verification failed / invalid_request"

**Symptom:** tapping "See where you are — free" on the marketing site → Google →
`lovable.app` shows *State verification failed*; retry bounces marketing → auth →
marketing. Result: the user lands as guest and sees a stale/demo chart.

**Cause:** the OAuth flow **starts on one origin and finishes on another**. The PKCE
`code_verifier`/`state` is saved in storage on the origin that *started* the flow
(the marketing site / antar.world) and isn't available on the origin that handles
the *callback* (the app / lovable.app) → state mismatch.

**Fix (do all three):**
1. **Supabase → Authentication → URL Configuration**
   - **Site URL** = the app origin (the domain that runs the app), NOT the marketing site.
   - **Redirect URLs** = add the app's exact callback (e.g. `https://<app-origin>/auth/callback`). Include every origin the app actually runs on (custom domain + lovable.app if used).
2. **Start OAuth from the app origin, not the marketing button.** The "See where you
   are — free" CTA should route the user to the **app's own login page first** (same
   origin that will handle the callback), and only there call
   `supabase.auth.signInWithOAuth(...)`. Don't initiate the Google flow from
   antar.world and land on lovable.app.
3. **`redirectTo` must be same-origin:**
   ```ts
   await supabase.auth.signInWithOAuth({
     provider: 'google',
     options: { redirectTo: `${window.location.origin}/auth/callback` },
   });
   ```
   (Same origin that started it → the verifier is present → state verifies.)

**Verify:** sign in with Google in Safari (ITP is strictest). Should land signed-in,
and `GET /api/v1/me` should return your real `primary_chart_id` (not guest).

---

## 2. `ensureChartBound` can bind the WRONG chart (bypasses the backend guard)

**File:** `src/lib/chartBinding.ts`

**Issue:** after the `patchMe({ primary_chart_id: localChartId })` call, the code ALSO
does a **direct** Supabase write:
```ts
await supabase.from("profiles")
  .update({ primary_chart_id: localChartId })
  .eq("user_id", data.user.id);
```
`localChartId` comes from **browser localStorage** and can be a *stale or foreign*
chart id (e.g. a chart created in an earlier guest/test session on that browser —
this is how an account can show someone else's chart). The backend PATCH `/me`
now **rejects** a chart the user doesn't own (400), but this direct write **bypasses
that guard** and can mis-set `primary_chart_id`.

**Fix (pick one):**
- **Preferred — drop the direct write entirely.** The backend PATCH `/me` already
  binds `primary_chart_id` safely (with ownership check). The belt-and-braces
  Supabase write is redundant and unsafe; remove it.
- **Or gate it on ownership** — only run the direct update if `localChartId` is a
  chart the signed-in user actually owns:
  ```ts
  const { data: owned } = await supabase.from("charts")
    .select("id").eq("id", localChartId).eq("user_id", uid).maybeSingle();
  if (owned) { /* then update profiles.primary_chart_id */ }
  ```
- **Also:** only treat `localChartId` as bindable if it's a well-formed UUID
  (`/^[0-9a-f-]{36}$/i`) — a short/demo id should never be sent as `primary_chart_id`.

**Verify:** on an account whose real chart is X, with a *different* chart id sitting
in localStorage, after login `GET /api/v1/me` still returns X (not the localStorage
chart).

---

*Backend already shipped (main):* `/me` PATCH no longer 500s on a bad id (returns
400), and rejects non-owned charts. These two fixes close the loop on the app side.
