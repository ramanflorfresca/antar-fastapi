# Brand assets

Committed here because the originals live in `ios/`, which is **gitignored and
local-only** — the 1024 icon Apple holds existed on exactly one laptop until
2026-10-07.

| File | Size | What it is |
|---|---|---|
| `antar-appstore-icon-1024.png` | 1024×1024 | **The App Store icon submitted to Apple.** Source of truth. |
| `icon-512.png` | 512×512 | PWA / Android |
| `icon-192.png` | 192×192 | PWA / web manifest |
| `og-image.png` | 1376×768 | Social sharing card |

## Where these live in the build

- iOS: `ios/App/App/Assets.xcassets/AppIcon.appiconset/AppIcon-512@2x.png` —
  Xcode names the 1024 asset `512@2x`. It is the 1024, despite the filename.
- Web / PWA: `public/icon-512.png`, `public/icon-192.png`, `public/og-image.png`
  in the Lovable frontend repo.

## If the icon changes

Update it in all three places — this folder, the Xcode asset catalogue, and the
frontend `public/` — or the app ships one mark and the website shows another.
Apple also requires the 1024 to have **no transparency and no rounded corners**;
iOS applies the mask itself.
