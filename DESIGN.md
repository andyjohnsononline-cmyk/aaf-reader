# Design System — AAF Reader

## Product Context
- **What this is:** A client-side web tool for inspecting AAF (Advanced Authoring Format) file metadata
- **Who it's for:** Assistant editors, post supervisors, DITs, data wranglers, developers — anyone who touches AAF files and doesn't want to open an NLE just to peek inside
- **Space/industry:** Post-production, film & TV, media technology
- **Project type:** Professional data inspection tool (web app)

## Aesthetic Direction
- **Direction:** Industrial/Utilitarian — professional craft
- **Decoration level:** Minimal — typography and data density do the work
- **Mood:** Competent, trustworthy, purpose-built. Like DaVinci Resolve's data panels, not a consumer app. This is a tool for people who know what CDCI descriptors and timecode tracks are.
- **Reference sites:** Frame.io (Vapor design system), DaVinci Resolve, Raycast (dark UI patterns)

## Typography
- **Display/Hero:** Satoshi (Variable, 700) — geometric sans, distinctive but professional. Signals "someone designed this."
- **Body:** DM Sans (400, 500, 600) — clean, excellent at small sizes, not overused
- **UI/Labels:** DM Sans (same as body)
- **Data/Tables:** JetBrains Mono (400, 500) — real monospace for timecodes, frame counts, resolutions, file paths. Supports tabular-nums.
- **Code:** JetBrains Mono
- **Loading:**
  - Satoshi: self-hosted WOFF2 in `frontend/fonts/` (NOT on Google Fonts; from Fontshare, ITF Free Font License)
  - DM Sans + JetBrains Mono: Google Fonts CDN
  ```html
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  ```
  Plus @font-face declarations for Satoshi in style.css.
- **Scale:**
  - Hero: 1.4rem / 700
  - Section heading: 0.9rem / 600
  - Body: 0.85-0.95rem / 400
  - Label/category: 0.72rem / 600-700, uppercase, letter-spacing 0.05em
  - Data value: 0.76-0.82rem / 400 (mono)
  - Small/hint: 0.68-0.72rem / 400

## Color
- **Approach:** Restrained — one accent color, warm neutral grays
- **Background:** #111214 — near-black with warm undertone
- **Surface:** #1a1c20 — warm dark gray for cards
- **Surface elevated:** #22252b — hover states, nested elements
- **Border:** #2e323a
- **Text:** #e8e6e3 — warm white (not blue-white)
- **Text muted:** #8a8780 — warm gray for labels and secondary content
- **Accent:** #d4915c — warm amber. Film stock warmth, grading suite feel. Used for section headings, interactive elements, numeric highlights.
- **Accent hover:** #e0a574
- **Semantic:**
  - Success: #66bb8c
  - Warning: #d4b85c
  - Error: #cf6679
  - Info: #6b9fd4
- **Dark mode:** Primary. This is a dark-first tool.
- **Light mode strategy:** Invert surfaces to warm whites/creams, desaturate accent by ~15%, maintain warmth:
  - Background: #f5f3f0
  - Surface: #ffffff
  - Surface elevated: #f0ede9
  - Border: #ddd9d3
  - Text: #1a1c20
  - Text muted: #6b6860
  - Accent: #b87a45
  - Accent hover: #a06a38

## Spacing
- **Base unit:** 4px
- **Density:** Comfortable-tight — professional tools are denser than consumer apps
- **Scale:** 2xs(2) xs(4) sm(8) md(16) lg(24) xl(32) 2xl(48) 3xl(64)
- **Card padding:** 14px 16px (tighter than generic)
- **Table cell padding:** 6px 10px
- **Section gap:** 10px between cards

## Layout
- **Approach:** Grid-disciplined — single column, card-based
- **Grid:** Single column, max-width container
- **Max content width:** 960px
- **Border radius:**
  - sm: 4px (inputs, small elements)
  - md: 6px (cards, buttons, badges)
  - lg: 8px (main containers, mockup wrappers)

## Motion
- **Approach:** Minimal-functional — only transitions that aid comprehension
- **Easing:** ease for general transitions
- **Duration:**
  - Collapsible open/close: 200ms
  - Hover states: 150ms
  - Border color transitions: 200ms
- **Patterns:** Collapsible section toggle (rotate chevron), dropzone border color on hover/dragover

## CSS Custom Properties

```css
:root {
  --bg: #111214;
  --surface: #1a1c20;
  --surface-elevated: #22252b;
  --border: #2e323a;
  --text: #e8e6e3;
  --text-muted: #8a8780;
  --accent: #d4915c;
  --accent-hover: #e0a574;
  --error: #cf6679;
  --success: #66bb8c;
  --warning: #d4b85c;
  --info: #6b9fd4;
  --radius-sm: 4px;
  --radius-md: 6px;
  --radius-lg: 8px;
  --font-display: 'Satoshi', sans-serif;
  --font-body: 'DM Sans', sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
}
```

## Decisions Log
| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-28 | Initial design system created | Created by /design-consultation based on competitive research (Frame.io V4, DaVinci Resolve, Raycast). Warm amber accent and warm grays chosen to differentiate from generic dark-mode blue and signal post-production identity. |
| 2026-03-28 | Satoshi for display font | Geometric sans with personality. System fonts say "side project." Satoshi says "someone designed this." |
| 2026-03-28 | JetBrains Mono for all data | Timecodes, frame counts, resolutions, file paths — all technical values get monospace. Post people read these values all day. |
| 2026-03-28 | Warm neutrals over cool grays | Current #1a1d27 has a cold blue undertone. Warm #1a1c20 feels more like DaVinci Resolve's surfaces. Shifts the entire mood toward "professional post tool." |
