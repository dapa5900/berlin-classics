# Berlin Classics Newsletter — Style & Layout Reference

## Color Palette

| Token | Hex | Usage |
|---|---|---|
| Background (top) | `#1a0a0f` | Very dark burgundy |
| Background (mid) | `#120810` | Even darker |
| Background (bot) | `#0d080c` | Near-black |
| Text primary | `#F5F1E8` | Warm off-white |
| Gold accent | `#D4AF37` | Headlines, borders, gold shine |
| Gold (dark variant) | `#B8860B` | Gradient ends (DarkGoldenrod) |
| Text muted | `#c9c4bb` | Subtitle |
| Text dim | `#7a756d` / `#a8a29e` / `#a09890` | Meta, screening details |
| Link hover | `#E5C158` | Lighter gold on button hover |
| Card BG | `rgba(25,15,20,0.9)` → `rgba(15,08,12,0.95)` | Gradient overlay |
| Section BG | `rgba(30,18,25,0.8)` → `rgba(18,10,15,0.9)` | Lighter gradient overlay |

## Typography

| Element | Font | Size | Weight | Letter-spacing |
|---|---|---|---|---|
| `h1` Berlin Classics | `Cinzel` → `Playfair Display` → Georgia, serif | `3.8em` | 600 | `12px` |
| Subtitle | `Source Sans Pro` 300 | `1.3em` | 300 | `4px` |
| Cinema section titles | `Cinzel` → `Playfair Display` → Georgia, serif | `1.5em` | – | `3px` |
| Movie titles | `Source Sans Pro` 600 | `1.4em` | 600 | `0.3px` |
| Year badges | `Cinzel` | `0.8em` | 700 | `1px` |
| Body / screening details | `Source Sans Pro` 300 / 400 / 600 | `0.85–0.95em` | – | – |
| Buttons (toggle-all) | `Cinzel` | `0.9em` | 600 | `2px` |

Body line-height: `1.7`.

## Layout Structure

```
.container (max-width: 1200px, centered)
├── header (text-align: center)
│   ├── h1 "BERLIN CLASSICS"
│   ├── p.subtitle "KLASSISCHE FILME IN BERLINER KINOS"
│   └── p.meta "Generiert am DD.MM.YYYY um HH:MM"
│   └── ::before pseudo "✦ ✦ ✦" (gold separator)
├── button.toggle-all-btn ("Alle ein-/ausklappen", centered)
├── section.cinema-section × N
│   ├── h2.cinema-title (clickable, gold border-bottom)
│   │   ├── ::before pseudo "❋"
│   │   └── span.toggle-icon "+" / "−"
│   └── div.cinema-screenings (initially hidden, display: grid)
│       └── article.screening-card × M
│           ├── div.card-header
│           │   ├── div.card-date (calendar SVG icon + "So, 31.05.2026")
│           │   └── div.card-checkbox (checkbox for export)
│           ├── a.poster-link → img.poster (2:3, max 180px wide)
│           │   └── OR div.poster-placeholder (gold gradient, "BERLIN\nCLASSICS")
│           └── div.screening-info (centered text)
│               ├── h3.movie-title → a (links to cinema page) + span.year
│               └── p.screening-details → time + runtime + TMDB link
└── footer (centered, border-top)
```

### Fixed floating buttons (top-left desktop, top-right mobile)
- Expand/collapse all (chevron SVG icon)
- Calendar export (calendar SVG icon) — generates `.ics`

## Grid & Responsiveness

| Breakpoint | Columns | Key changes |
|---|---|---|
| >900px | **3 columns** `1fr`, gap `20px` | Default |
| 600–900px | **2 columns** | – |
| ≤600px | **1 column** | `h1` → `2.2em`, `letter-spacing: 4px`, body padding `20px 15px`, section padding `22px`, floating buttons → right side, checkbox → `24px` |

## Spacing & Sizing

- Body padding: `40px` (desktop), `20px 15px` (mobile)
- Header padding: `60px 40px 40px`, margin-bottom `60px`
- Cinema section: padding `35px` (desktop) / `22px` (mobile), margin-bottom `55px`, border-radius `4px`
- Cinema title: padding-bottom `18px`, margin-bottom `30px`
- Card: padding `15px` (desktop) / `12px` (mobile), border-radius `3px`, border `1px solid rgba(212,175,55,0.12)`
- Poster: max-width `180px`, aspect-ratio `2/3`, border-radius `2px`, margin-bottom `15px`
- Footer: padding `60px 0 40px`, margin-top `40px`

## Interaction Details

- **Cinema sections**: Click header to toggle +/−. Initial state: **collapsed** (`display: none`).
- **Toggle all button**: Checks if any section is visible; if yes → collapses all, if none visible → expands all.
- **Card hover**: `translateY(-3px)`, gold box-shadow intensifies, border brightens.
- **Movie title link hover**: Turns gold `#D4AF37`.
- **Poster link**: Wraps poster in `<a>` to cinema page, no underline decoration.
- **Checkboxes**: `accent-color: #D4AF37`, used for `.ics` calendar export.

## Visual Effects

- Background: Fixed-attachment gradient from dark burgundy → near-black.
- Gold glow: `h1` has `text-shadow: 0 0 40px rgba(212,175,55,0.4)`.
- Poster drop shadow: `box-shadow: 0 4px 20px rgba(0,0,0,0.6), 0 0 1px #D4AF37` (thin gold edge).
- Section shadow: `0 10px 40px rgba(0,0,0,0.4)`.
- Button gradient: Gold linear gradient `135deg`, lifts `2px` on hover with intensified shadow.
- Star separator: `✦ ✦ ✦` pseudo-element at header bottom with gold `letter-spacing: 15px`, background-colored cutout to overlap border.

## Content Logic (backend-driven)

- Screenings grouped by `cinema_name`, sorted by date
- Special handling for "Best of Cinema" → shows "Ganztägig" instead of time
- Special handling for Open Air Kino → `venue_name` used as grouping label per screening
- Posters sourced from TMDB; if missing → gold placeholder with "BERLIN CLASSICS" text
- Each screening card carries `data-*` attributes for calendar export (title, year, date, time, runtime, cinema, location/Google Maps URL, TMDB URL)

## Font Loading

Google Fonts: `Playfair Display` (400–700), `Cinzel` (400–600), `Source Sans Pro` (300, 400, 600).
