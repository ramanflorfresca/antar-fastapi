# App Store 4.3(b) Resubmission Playbook — Antar
Submission rejected 2026-07-27 (iPad Air, v1.0 build 3). This is everything to clear it.

## Diagnosis (what actually triggered it)
4.3(b) = "saturated category / duplicates other astrology apps." The rejection is **NOT the metadata** — that's already well-repositioned:
- Name: "Antar World: Your life GPS" · Subtitle: "Timing for your big decisions"
- Category: Lifestyle / Reference · Keywords: timing, decision, guidance, planner, clarity… (zero astrology terms)
- Description: leads with "Not predictions. Not horoscopes. Tactical intelligence."

The trigger was the **experience the reviewer saw**:
- Screenshots led with `daily_signal`, `daily_texture` (horoscope-style) + `compatibility` (astrology feature).
- The app opened on the daily-signal screen → felt like a daily-horoscope app.

## What's already fixed (LIVE on antar.world as of 2026-07-31)
The iOS app loads antar.world **remotely** (Capacitor `server.url = https://antar.world`, confirmed in the built `ios/App/App/capacitor.config.json`). So publishing the web reposition **already reaches the reviewer's build 3 — no new binary needed.** Verified live:
- App **opens on ASK**: "Ask about a real decision — a job, a move, a relationship, the timing" + example chips.
- **Today** = "What's in play for you now" + one action + the anushthana line.
- Nav: Ask · Today · Practice · Timing · Places · Settings — **no** Compatibility / horoscope / zodiac. Title: "Your Life Navigation System."
- A real answer (verified): Q "Is this the right time to change jobs?" → *"Tech is flat for you today — what's actually live is property,"* with a timing window ("NEXT CHECKPOINT OPENS AROUND 2026-08-13"), domain (BUSINESS), **YOUR MOVE**, and **CONFIDENCE · MEDIUM**.

## STILL TO DO (morning)

### 1. (Optional) tiny Lovable copy softener
```
Replace "reading" in the UI (reads as astrology). Two spots:
1. Today header "READING · <name>" → "NAVIGATOR · <name>".
2. Ask loading state "reading your chart…" → "checking your timing…".
No other copy/data/api changes.
```

### 2. Screenshots — Chrome DevTools device mode (≈3 min, exact 6.9″, no browser chrome)
Chrome on antar.world (logged in) → `Cmd+Option+I` → `Cmd+Shift+M` → device **iPhone 16 Pro Max** → per screen: DevTools `⋮` → **Capture screenshot**. Order + captions:

| # | Screen | Caption |
|---|---|---|
| 1 | Ask home (chips) | "Ask about a real decision" |
| 2 | The answer (ask "Is this the right time to change jobs?") | "Get the timing + your move" |
| 3 | Today ("What's in play for you now") | "Know what's in play now" |
| 4 | Timing tab | "Your windows — not a horoscope" |
| 5 | Places tab | "Where you'll do best" |

App Store Connect → Media Manager (iPhone 6.9″): delete `daily_signal / daily_texture / compatibility`, upload these 5 in order.

*(Native-frame alternative: iOS Simulator was blocked by a CoreSimulator version-mismatch. Fix if wanted: quit Simulator, `sudo xcrun simctl shutdown all`, relaunch Simulator or reboot — then build App.xcodeproj (SPM, scheme App) to iPhone 16 Pro Max and screenshot. DevTools is enough to ship.)*

### 3. Resubmit
- Upload the 5 screenshots + captions.
- App version page → **Update Review** / resubmit **build 3** (unchanged — loads the repositioned web).
- Paste the Apple reply (below) in the Resolution Center.

## Apple reply (paste in Resolution Center)
```
Hello, and thank you for the review.

We'd like to clarify how Antar differs from the astrology/horoscope apps in this category, and describe the changes in this build.

Antar is a personal decision-timing and life-navigation tool. It does NOT provide daily horoscopes, sun-sign readings, fortune-telling, palm reading, or zodiac entertainment. Instead, the user asks a specific, real-life question — "Is this the right time to change careers?", "When are things likely to settle at home?", "Should I take this offer?" — and the app returns a specific, structured answer: the likely time window (when), the underlying cause (why), and a concrete action to take now (what to do), in plain language.

What makes this a distinct experience rather than another entry in the category:

1. It is a question-answering decision tool, not a content feed. There is no daily-horoscope loop; the core interaction is the user asking about their own life decisions and receiving a timed, actionable answer.
2. The answers are computed deterministically from the individual's birth data by a multi-system timing engine across specific life domains (career, relationships, health, relocation, legal), each producing real time windows — not generic sun-sign text shared by millions of users.
3. Every answer ends in agency: a concrete next step, framed as coaching, never a fatalistic prediction.
4. It is personalized to the individual and gets more tailored over time; two users never receive the same generic reading.

In this build we have also repositioned the experience to make this clear on first run: the app now opens on the decision/question experience rather than a daily reading, the daily surface leads with "what's in play now + one action to take," and the relationship feature is framed around timing between two people rather than star-sign matching. The store metadata (name, subtitle, description, keywords, category) reflects this decision-tool positioning.

We believe this delivers a genuinely different, useful experience and respectfully request re-review. We're glad to walk through the app live or answer any questions here.

Thank you.
```

## Notes
- Ensure antar.world deploys from the **current** frontend (`antar_fe_work`), not the stale `antar_lovable` clone.
- Reviewer needs a working demo sign-in (App Review → Sign-In Information) — verify it's filled and valid.
- Latent 4.2 (web-wrapper) risk is already handled (`appendUserAgent: "CapacitorApp"` gates the PWA install hint) — don't regress it.
