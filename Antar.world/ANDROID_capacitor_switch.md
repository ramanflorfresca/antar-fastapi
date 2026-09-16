# Android — switch the TWA to a native Capacitor app (same Play listing)

Goal: replace the Bubblewrap **TWA** with a **Capacitor** native app in the SAME
Play listing (`world.antar.twa`, "Closed testing – Alpha"), so push/geolocation/
biometric work — WITHOUT losing the closed-test progress. iOS stays `world.antar.app`.

## Non-negotiables
- **Package must stay `world.antar.twa`** (Google identifies the app by it).
- **Sign with the same key** — `~/antar-android-keystore-BACKUP.keystore`, alias
  `android`. You need the **store + key passwords** (from the Bubblewrap setup). If
  lost: Play Console → App integrity → request an **upload key reset** (adds delay).
- **versionCode must beat the TWA's** (TWA is release 2 → use `versionCode 3+`).

## 1. Swap TWA → Capacitor
```bash
cd ~/antar_lovable/antar_lovable
# keystore already backed up to ~/antar-android-keystore-BACKUP.keystore
rm -rf android
npx cap add android          # scaffolds a Capacitor android/ (uses appId world.antar.app)
```
> Leave `capacitor.config.ts` `appId` as **`world.antar.app`** — that's for iOS.
> We override only the Android applicationId below, so iOS is untouched.

## 2. Make Android use world.antar.twa + sign with your key
Edit **`android/app/build.gradle`**:
```gradle
android {
    namespace "world.antar.app"          // code package — fine to leave as scaffolded
    defaultConfig {
        applicationId "world.antar.twa"  // ← MUST match the Play listing
        versionCode 3                    // ← higher than the TWA (was 2)
        versionName "1.0.1"
        // minSdk/targetSdk left as Capacitor defaults
    }
    signingConfigs {
        release {
            storeFile file("antar-release.keystore")   // copy the keystore here (step below)
            storePassword System.getenv("ANDROID_STORE_PASSWORD")
            keyAlias "android"
            keyPassword System.getenv("ANDROID_KEY_PASSWORD")
        }
    }
    buildTypes {
        release {
            signingConfig signingConfigs.release
            minifyEnabled false
        }
    }
}
```
Copy the keystore in and export the passwords:
```bash
cp ~/antar-android-keystore-BACKUP.keystore android/app/antar-release.keystore
export ANDROID_STORE_PASSWORD='<your store password>'
export ANDROID_KEY_PASSWORD='<your key password>'
```
(`applicationId` ≠ `namespace` is valid — Play only cares about `applicationId`.)

## 3. Firebase / FCM (for Android push)
1. Firebase console → your project (or create one) → **Add app → Android**, package
   name **`world.antar.twa`**.
2. Download **`google-services.json`** → place in **`android/app/`**.
3. Wire the Google-Services Gradle plugin:
   - `android/build.gradle` (project) → in `dependencies`:
     `classpath 'com.google.gms:google-services:4.4.2'`
   - bottom of `android/app/build.gradle`:
     `apply plugin: 'com.google.gms.google-services'`
4. Backend key: Firebase → **Project settings → Service accounts → Generate new
   private key** → set **`FCM_SERVICE_ACCOUNT_JSON`** on Railway. (Sender already
   built + deployed — this is all it needs.)

## 4. Sync, build the AAB
```bash
npm install --legacy-peer-deps
npx cap sync android
cd android && ./gradlew bundleRelease
# output: android/app/build/outputs/bundle/release/app-release.aab
```
(or `npx cap open android` → Android Studio → Build → Generate Signed Bundle.)

Verify the plugins added their permissions to `android/app/src/main/AndroidManifest.xml`
after sync: `POST_NOTIFICATIONS` (push), `ACCESS_FINE/COARSE_LOCATION` (geo),
`USE_BIOMETRIC` (biometric). They're merged in automatically by the plugins.

## 5. Upload to the existing closed track
Play Console → Antar → Test and release → Testing → **Closed testing → Closed
testing – Alpha → Create new release** → upload `app-release.aab` → roll out.
Because the applicationId + signing key match, Play accepts it as an **update** —
testers get the native app in place, the 14-day clock keeps running.

## 6. Verify push end-to-end
On an Android test device: install the update → allow notifications → the app
registers an **FCM** token (POSTed with `platform:"android"`) → `POST
/api/v1/user/push-test {chart_id}` → banner.

---

## 6. Fix the Play "target API level" policy issue → target Android 16 (API 36)

Play flagged the app for an out-of-date `targetSdkVersion` (the Capacitor default).
**Android 16 = API level 36.** (Google's current *minimum* for updates is API 35 /
Android 15; targeting 36 satisfies it and is future-proof.) The Android build is in
the **Capacitor native project** (`world.antar.twa`), not the FastAPI repo.

### 6.1 Bump the SDK (Capacitor centralizes this)
Edit `android/variables.gradle`:
```gradle
ext {
    minSdkVersion = 23
    compileSdkVersion = 36     // Android 16
    targetSdkVersion  = 36     // Android 16  ← the fix
    // ...leave the rest
}
```
(If the values live in `android/app/build.gradle` instead, set `compileSdk 36`
and `targetSdk 36` there.)

### 6.2 Prerequisites for compileSdk 36
- **JDK 17** (AGP 8.x requires it).
- **Android Gradle Plugin ≥ 8.6** and **Gradle ≥ 8.9** (needed for API 36).
- **Android SDK Platform 36** installed (Android Studio → SDK Manager → "Android 16 (API 36)", or `sdkmanager "platforms;android-36" "build-tools;36.0.0"`).
- **Capacitor**: use the latest 7.x (`@capacitor/android`); older Capacitor (6.x, targetSdk 34) is what usually trips this — `npm i @capacitor/core@latest @capacitor/android@latest` then `npx cap sync android`.

### 6.3 Rebuild + upload (DO NOT reset the test clock)
- Bump `versionCode` (must be higher than the last upload).
- `npx cap sync android` → build a **signed release `.aab`** with the **SAME upload/signing key** and **same `applicationId` `world.antar.twa`** (changing either resets the closed-test 12-tester / 14-day clock — see §1).
- Play Console → Antar → Test and release → Testing → **Closed testing – Alpha → Create new release** → upload the `.aab` → roll out.
- The policy issue clears once a build targeting API 36 is live on any active track.

### 6.4 Common gotchas
- `compileSdk 36` with an old AGP → build fails ("compileSdk 36 requires AGP …"): bump AGP/Gradle first.
- Behavior changes at targetSdk 36 (edge-to-edge, predictive back, stricter foreground-service/permissions). For a Capacitor **web-view shell** these rarely bite, but smoke-test: launch, notifications permission, geolocation, back-gesture.
- Keep JDK/AGP/Gradle consistent with what the Lovable build environment uses.
