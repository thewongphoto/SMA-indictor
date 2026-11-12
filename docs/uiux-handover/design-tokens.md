# Design tokens

Dark theme only. Every screen was designed at 360 px wide (Android dp / CSS px are the same unit here). A light theme is still to be designed; see [open-decisions.md](open-decisions.md).

Machine-readable copies: [tokens.json](tokens.json) (all platforms) and [tokens.css](tokens.css) (web reference).

## Colour

| Token | Hex | Use |
| --- | --- | --- |
| `bg.screen` | #0B1116 | Screen background |
| `surface` | #131C24 | Cards, sheets, search field |
| `surface.hover` | #18232D | Pressed/hover card |
| `surface.sunken` | #0E161D | Inset panel inside a card (backtest summary) |
| `control` | #1A2630 | Unselected segment, tag background, progress track |
| `border.frame` | #243340 | Switch track (off) |
| `border.input` | #2F4150 | Input border, outline button border |
| `divider` | #1B2730 | List row separators, tab bar top border |
| `text.primary` | #EEF3F7 | Headings and body |
| `text.secondary` | #C5D2DB | Tertiary links ("Skip for now", "Clear") |
| `text.muted` | #8DA0AE | Captions, metadata, inactive tabs |
| `accent` | #2DD4BF | Primary button, active tab, links, switch on |
| `accent.hover` | #5EEAD4 | Primary button pressed |
| `accent.on` | #06201C | Text and knob on accent |
| `accent.tint` | #0F3B36 | Selected segment, "Above" tag background |
| `accent.border` | #1E4F49 | Outline pill button border |
| `price.up` | #34D399 | Price rises |
| `price.down` | #F87171 | Price falls, "Below" tag text, destructive text |
| `price.down.tint` | #3A1F22 | "Below" tag background |
| `warning.bg / .title / .text` | #2A2412 / #FBBF24 / #E7D9B0 | Offline banner |
| `error.bg / .title / .text / .border` | #2A1719 / #FCA5A5 / #E5C2C2 / #5B3236 | Error card |
| `scrim` | rgba(4,8,11,.66) | Behind the optimising card |

Status is never shown by colour alone: every tag also says ABOVE or BELOW in words.

Contrast checks (WCAG 2.x): `text.muted` on `surface` is about 5.6:1 and on `bg.screen` about 6.6:1; `accent.on` on `accent` is about 10:1; `price.down` on `price.down.tint` is about 5.4:1. Re-check if any value changes.

### SMA line colours (unchanged from the app)

Taken from `sma_analyzer/palette.py` `COLOR_CHOICES`, in order. Do not reorder; saved colour indices depend on it.

| # | Name | Hex | RGBA in palette.py |
| --- | --- | --- | --- |
| 0 | Amber | #FFBD5C | (1, .74, .36) |
| 1 | Periwinkle | #96A3FF | (.59, .64, 1) |
| 2 | Rose | #FF7D9E | (1, .49, .62) |
| 3 | Sky | #6BC2FF | (.42, .76, 1) |
| 4 | Violet | #C794F5 | (.78, .58, .96) |
| 5 | Lime | #99D66B | (.60, .84, .42) |
| 6 | Coral | #FF9E66 | (1, .62, .40) |
| 7 | Cyan | #61D6EB | (.38, .84, .92) |
| 8 | Yellow | #FFE640 | (1, .90, .25) |
| 9 | Mint | #3DD694 | (.24, .84, .58) |
| 10 | Magenta | #F261E0 | (.95, .38, .88) |
| 11 | Ivory | #F0F0E8 | (.94, .94, .91) |

Price line on charts: #DCE5EC, 1.5 px. SMA lines: 2.2 px, round joins. Chart grid: `divider`.

## Typography

Font: **Manrope** (weights 500, 600, 700, 800). Licence: SIL Open Font License 1.1. Font files are not in this folder; download from Google Fonts (fonts.google.com/specimen/Manrope) or the Manrope GitHub repository and bundle them with each app.

| Style | Size / weight | Use |
| --- | --- | --- |
| Display | 30 / 800, tabular figures | Price on SMA detail |
| Screen title | 24 / 800 | Home, Alerts, Settings |
| Section title | 20–22 / 800 | Empty-state heading, "Find a security" |
| Card title | 17–18 / 800 | Backtest, Edit line, optimising card |
| Body strong | 15 / 700 | Security name, row title |
| Body | 14 / 400–600 | Paragraphs, switch labels |
| Small | 13 | Supporting text |
| Caption | 12 / 600 | Metadata, tab labels, helper text |
| Overline | 11–12 / 700, uppercase, letter-spacing 0.08em | Section labels |
| Tag | 11 / 700, uppercase | ABOVE / BELOW / SAVED |

Numbers that change (prices, percentages, money) use tabular figures. Web text inputs must be **16 px**, not 15 px, or iPhone Safari zooms the page on focus.

## Spacing, size and shape

- Spacing steps: 4, 6, 8, 10, 12, 14, 16, 20, 24.
- Screen side padding: 20 (14 on screens narrower than 360).
- Gap between cards: 12–14. Card padding: 14 (16 for message cards).
- Radius: pill 999, sheet top 24, hero card 18, card 16, primary button 14, input 12, segment 10.
- Touch targets: at least **44 × 44**. Rows with a switch are at least 52 tall; list rows 60–64.
- Primary button height: 48. Switch: 44 × 26 track, 20 knob.
- Logos: 40 circle in lists (32 on narrow screens).

## Icons

The design uses text labels instead of icons for actions (an audit finding: icon-only controls were unclear). The only glyphs are ‹ (back), › (go to), ▾ / ▴ (expand), ▲ / ▼ (price change) and ✓ (selected colour). If icons are added later, pair each with a visible label.

## Motion

| Animation | Spec |
| --- | --- |
| Logo draw (startup and optimising) | The app icon is revealed left to right, then fades and repeats. Loop 1.4 s, linear. 0–71.4 %: reveal from 12 % to 88 % width. Hold until 84.3 %. Fade out by 92.9 %. Keep `logo_motion.py` timing if it differs; it is the source of truth. |
| Switch | Knob slides 150 ms. |
| Backtest bars | Width transitions 250 ms when the horizon changes. |
| Card expand | Instant in the prototype. A 150–200 ms height ease is acceptable. |
| Reduced motion | When the system asks for reduced motion, show the logo static and drop transitions. |
