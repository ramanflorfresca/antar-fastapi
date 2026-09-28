# Antar — App icon spec

> **Status: shipped and accepted.** The Apple 2.3.8 rejection this document was
> originally written to fix is closed. The icon is final; this is now the
> reference for what it is and how to regenerate it. Nothing here asks you to
> design a new one.
>
> **Superseded direction — read this before acting on any older copy.** The
> first draft of this spec proposed a bold **X mark in mint-teal**, and included
> an image-generation prompt for producing one. That direction was abandoned
> before submission. The icon that shipped, and that we described to App Review,
> is a concentric **bullseye**. Both the X prescription and the prompt have been
> removed, because following them would replace a finalized, accepted icon with
> a different one and re-open 2.3.8.

## What the icon is

A solid concentric bullseye — a small filled centre dot, a heavy red-orange
ring, then three evenly spaced off-white rings — centred on a flat near-black
square. No text, no grid, no gradient, no shadow.

| Element | Colour |
|---|---|
| Background (full bleed) | `#0B0B0F` |
| Rings + centre dot | `#EAEAEA` |
| Inner heavy ring | `#E03C22` |

The mark spans ~82% of the square, which keeps it inside the corner mask with
room to spare.

This is exactly what we told App Review in `APPSTORE_reply_build4_FINAL.md`:
*"a solid concentric 'bullseye' mark in our brand colors on a dark ground …a
single master used to generate every size."* Keep those two claims true.

## The master asset

`resources/icon.png` in the **antar-world** repo (the Capacitor app project —
the one with `ios/` and `capacitor.config.ts`). **Not** the antar-fastapi
backend; a stray `@capacitor/assets` install once lived there, where it had no
native project and no master to read, and it has since been removed.

Requirements, all still binding:

- **1024 × 1024 px, PNG, sRGB, no alpha, flattened.** This one file is both the
  App Store listing icon and the source for every smaller size.
- **No rounded corners, no shadow, no border.** Supply a full square — iOS
  applies its own mask. A pre-rounded or transparent icon gets rejected.
- **Mark inside the centre ~80%** so the corner mask never clips it.
- **One design at every size.** Guideline 2.3.8 asks that all sizes be "similar
  enough to avoid confusion"; generating them from a single master is what
  guarantees that.

## Regenerating every size

From the antar-world repo root:

```bash
npm run ios:add          # only if ios/ is not present — it is generated, not tracked
npm run icons:generate   # all iOS + Android sizes from resources/icon.png
npm run ios:sync
```

`icons:generate` runs `@capacitor/assets` pinned to `--ios --android` with the
`#0B0B0F` background. It writes:

- iOS → `ios/App/App/Assets.xcassets/AppIcon.appiconset/` (every size + the 1024
  marketing icon)
- Android → `android/app/src/main/res/mipmap-*/` (incl. adaptive fore/background)

Both native projects are generated and gitignored, so a fresh clone must create
them first or the platform is silently skipped.

**Do not add `--pwa`.** That mode rewrites `public/manifest.json` to point at
`../icons/*.webp` — paths that escape `public/`, are never served by Vite, and
are declared `image/png`. The web icons in `public/` are hand-managed and stay
out of this pipeline.

If you replace the mark, replace **`resources/icon.png`** and re-run. Never edit
a generated size directly: it will be overwritten, and it will drift from the
rest, which is the exact failure 2.3.8 describes.

## Verify before any resubmit

- Xcode → `Assets.xcassets → AppIcon`: no empty slots, the 1024 slot filled,
  every tile showing the same mark.
- Build to a simulator or device and look at the home screen.
- Archive and upload. App Store Connect takes the store icon from the uploaded
  build's asset catalog, so it matches on-device automatically.

## Submission checklist (still useful for any build)

1. Accept any pending **Developer Program License Agreement**
   (developer.apple.com/account).
2. Ensure `ITSAppUsesNonExemptEncryption = false` in `ios/App/App/Info.plist`
   (kills the export-compliance prompt).
3. Regenerate icons if the master changed, then `npm run ios:sync`.
4. Bump the build number, Archive, upload.

## History

Apple rejected an early build under **Guideline 2.3.8 (Accurate Metadata)** —
*"the app icons appear to be placeholder icons."* The icon at the time was a
thin blue X on a crosshatch grid; the grid read as a design-tool placeholder.
The fix was a finalized, filled brand mark generated at every size from one
master. Build 4 carried the bullseye and addressed 2.3.8 alongside the separate
4.3(b) design-spam item — see `APPSTORE_reply_build4_FINAL.md`. The App Review
rounds after that concerned 4.3(a) and 4.3(b), not the icon.
