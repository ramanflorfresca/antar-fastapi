# Push notifications — what's done, what's left

## Status
Push was **scaffolded but not functional** — the plugin was installed and
configured, but iOS had no push entitlement and no APNs callbacks, so
`register()` could never return a token. That gap is now closed in code.

## ✅ Done in this pass (code — compiles clean)

**Native iOS** (`antar_lovable/ios/App/App/`)
- `App.entitlements` — added `aps-environment = development` (Xcode promotes it to
  the production APNs environment automatically for App Store archives).
- `AppDelegate.swift` — added the two APNs delegate callbacks
  (`didRegisterForRemoteNotificationsWithDeviceToken` /
  `didFailToRegister…`) that forward the device token to Capacitor's bridge.
  Without these, the JS `registration` event never fires.

**Web app** (`antar_lovable/src/`) — deploys to antar.world via the normal build
- `lib/pushNotifications.ts` — native-only registration: guards on
  `isInsideNativeWrapper()`, dynamically imports the plugin (so the web bundle
  never resolves the native module), requests the OS permission, `register()`s,
  and POSTs the token to the backend. Fail-open throughout.
- `App.tsx` — mounts `<PushRegistrar/>` (no-op in a browser, active in the wrapper).

**Backend** (`antarai/main.py`) — deployed
- `POST /api/v1/user/push-token` — verifies the bearer token, checks the caller
  owns the chart, and writes `{token, platform, chart_id, user_id, updated_at}`
  into the **existing `device_tokens` table** (reused — it already has owner-scoped
  RLS from the security migration; the backend writes with the service-role key so
  RLS is bypassed). Manual upsert-by-token, no schema change needed.
- **No table to create** — `device_tokens` already exists. (The earlier
  `sql_push_tokens.sql` was retired to avoid a duplicate token table.)

## ✅ The sender is BUILT (direct APNs) — `antar_engine/push_sender.py`
- Signs an ES256 provider JWT with your `.p8` (cached, auto-refreshed), sends over
  HTTP/2 (added `h2` to requirements), prunes dead tokens (410 / BadDeviceToken /
  Unregistered) from `device_tokens`. Fail-open + no-op until configured.
- **Daily cron** `_daily_push_job` (main.py, 14:00 UTC) nudges every registered
  device: *"Your reading for today is ready ☀️"* with `data:{type:"daily"}`. It
  sends a lightweight alert, not the content — zero per-chart LLM cost, nothing
  sensitive in the payload. (Prefs-aware sending / per-timezone timing = later.)
- **Test endpoint** `POST /api/v1/user/push-test { chart_id }` (owner-guarded) —
  fires a push to your own device to verify the whole chain.
- Verified locally: JWT signing, HTTP/2 client, fail-open all pass. Only real APNs
  delivery is untestable without the `.p8`.

## ⛔ Left to do — the Apple Developer portal + env vars (no more code)

1. **Enable the capability on the App ID** (portal login):
   - Apple Developer → Certificates, IDs & Profiles → your `world.antar.app` App ID
     → enable **Push Notifications**. Regenerate the provisioning profile.
   - In Xcode: target **App** → Signing & Capabilities → **+ Capability → Push
     Notifications** (reconciles the `aps-environment` entitlement).
2. **Create an APNs Auth Key** (portal): Keys → **+** → enable **Apple Push
   Notifications service (APNs)** → download the `.p8` **once** (can't re-download).
   Note the **Key ID** and your **Team ID**.
3. **Set these env vars on Railway** (then redeploy):
   ```
   APNS_KEY_P8      = <contents of the .p8>   # newlines OK, or use literal \n
   APNS_KEY_ID      = <10-char Key ID>
   APNS_TEAM_ID     = <10-char Team ID>
   APNS_BUNDLE_ID   = world.antar.app         # (default, optional)
   APNS_USE_SANDBOX = 1                        # dev/TestFlight tokens; 0 for App Store
   ```
   > **Sandbox vs production** matters: a token registered by a `development`/direct-
   > Xcode build only works against `api.sandbox.push.apple.com` (`APNS_USE_SANDBOX=1`).
   > A token from an **App Store / TestFlight** build needs `api.push.apple.com`
   > (`APNS_USE_SANDBOX=0`). Wrong host → `BadDeviceToken`.
4. **Verify:** with a real device token in `device_tokens`, call
   `POST /api/v1/user/push-test {chart_id}` — expect `{status:"sent", sent:1}` and a
   banner on the phone.

## Android note
Android is currently **iOS-first / incomplete** — `@capacitor/android` isn't in
`package.json` (only `@capacitor/ios`) though an `android/` folder exists. Push on
Android needs FCM + that platform properly added. Say the word and I'll wire it.

## Test path once the portal steps are done
1. `npx cap sync ios` → open in Xcode → run on a **real device** (push doesn't work
   in the simulator for token registration).
2. Accept the permission prompt → the device token POSTs to `/api/v1/user/push-token`
   → confirm a row lands in `push_tokens`.
3. Send a test push (direct APNs or FCM console) to that token.
