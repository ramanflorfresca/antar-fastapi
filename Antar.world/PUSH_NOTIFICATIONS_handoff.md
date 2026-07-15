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

## ⛔ Left to do — needs the Apple Developer portal + a sender (not code)

1. **Enable the capability on the App ID** (you must — portal login):
   - Apple Developer → Certificates, IDs & Profiles → your `world.antar.app` App ID
     → enable **Push Notifications**. Regenerate the provisioning profile.
   - In Xcode: open `App.xcworkspace` → target **App** → Signing & Capabilities →
     **+ Capability → Push Notifications** (this reconciles the entitlement above).
2. **Create an APNs Auth Key** (portal): Keys → **+** → enable **Apple Push
   Notifications service (APNs)** → download the `.p8` **once** (can't re-download).
   Note the **Key ID** and your **Team ID**.
3. **The sender** — the piece that actually pushes the daily reading. Two options:
   - **Direct APNs** — a small backend job that signs a JWT with the `.p8` and
     POSTs to `api.push.apple.com`. No third party. (Android would need FCM too.)
   - **Firebase Cloud Messaging** — one API for both iOS + Android; upload the
     `.p8` to FCM. Adds `@capacitor/push-notifications` works as-is on iOS; Android
     needs the FCM `google-services.json` + `@capacitor/android` (not yet installed).
   Wire this into the existing daily-reading generation so each `push_tokens` row
   for a chart gets that chart's Today headline. **Tell me which sender you want
   and I'll build the send side.**

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
