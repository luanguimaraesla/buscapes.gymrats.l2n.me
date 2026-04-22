@../../agents/shared/AGENTS.md

# Buscapés GymRats

Hugo static site for the Buscapés family GymRats fitness competition
("Campeonato Buscapés das Estações 2026"). Published at
buscapes.gymrats.l2n.me.

## Stack

- Hugo 0.160+ (no theme, custom layouts)
- Pico CSS (dark theme, CDN) + custom CSS with Bebas Neue / Inter fonts
- Chart.js 4 (CDN) for interactive charts
- Python 3 stdlib-only preprocessing script
- GitHub Pages deployment via GitHub Actions

## Commands

- `make run` - generate data + start local server (disables fast render)
- `make build` - generate data + production build
- `make data` - only regenerate data files
- `make clean` - remove public/ and data/
- `python3 scripts/process_data.py` - run preprocessing directly

## Project Structure

```
resources/
  challenge-data.json          # Raw GymRats API export (1.6MB, 863 check-ins)
  *.pdf                        # Championship rules PDF
scripts/
  process_data.py              # Preprocessor: JSON -> data/*.json
data/                          # Generated (committed for convenience, CI regenerates)
  ranking.json                 # Season ranking with points, streaks, hours
  annual_ranking.json          # Year-long ranking across all seasons
  awards.json                  # Per-participant awards/highlights
  race.json                    # Cumulative days per member (line chart)
  activities.json              # Global activity type counts
  activity_leaders.json        # Top 5 per activity type
  sport_spotlights.json        # Summary cards for 5 key sports
  sport_details.json           # Per-sport stats with per-member breakdown
  monthly.json                 # Per-member monthly days (bar chart)
  weekdays.json                # Check-ins by weekday (bar chart)
  timeline.json                # Daily check-in counts
  heatmap.json                 # Calendar-style weekly heatmap data
  highlights.json              # Aggregate stats for hero section
  members.json                 # Member list with disambiguated short names
layouts/
  index.html                   # Homepage: hero, podium, ranking, race chart, awards
  estatisticas/list.html       # Statistics: charts, sport spotlights, sport details
  premiacoes/list.html         # Annual ranking (WSL-style season columns)
  _default/baseof.html         # Base template: Pico CSS, fonts, nav, footer
  partials/                    # Reusable components (podium, charts, tables, etc.)
content/
  regulamento/_index.md        # Championship rules (transcribed from PDF)
assets/css/custom.css          # All custom styles (~1500 lines)
```

## Data Flow

1. Raw data lives in `resources/challenge-data.json` (GymRats API export)
2. `scripts/process_data.py` processes it into `data/*.json`
3. Hugo templates read from `data/` via `hugo.Data.*`
4. CI runs the script before `hugo --minify`

## Data Processing Details

The preprocessing script (`scripts/process_data.py`) applies several
transformations to the raw GymRats data:

- **Timezone conversion**: UTC timestamps are converted to each
  participant's local timezone for correct day attribution
- **Session merging**: activities starting within 30 min of the
  previous one (same person) are merged into a single session
- **Activity classification**: uses platform_activity from the API
  when available, falls back to regex-based title matching, then
  per-member defaults. Similar activities are merged into broader
  categories (e.g., treadmill -> running, spinning -> cycling)
- **Per-member overrides**: MEMBER_REMAP_BY_NAME corrects known
  misclassifications (e.g., Pedro's kiteboarding was tagged as surfing)
- **Duration backfill**: check-ins without duration get the global
  average (~1h)
- **Metric backfill for sport details**: missing distance/calories/hours
  are estimated using the per-activity average, but only when at least
  10% of that activity's check-ins have real values (avoids estimating
  distance for strength training, etc.)
- **Duplicate short name disambiguation**: "Ana Beatriz" and
  "Ana Leticia" become "Ana B." and "Ana L."

## Pages

- **/ (Ranking)**: hero stats, CTA banner for next season, podium,
  full ranking table (sortable), cumulative race line chart, awards
  for all 15 participants
- **/estatisticas/**: monthly evolution, weekday distribution, activity
  doughnut, sport spotlight cards (top 5 per sport), detailed per-sport
  sections with metrics and tables, calendar heatmap
- **/premiacoes/**: WSL-style annual ranking table with season columns
  (only Verao has data, others show dash)
- **/regulamento/**: championship rules + data processing appendix

## Championship Rules (Summary)

- 4 seasonal stages: Verao, Outono, Inverno, Primavera
- Scoring by unique exercise days (not total check-ins)
- Points: 1st=10000, 2nd=8500, ..., 10th=3000
- Outside top 10: 10+ days=2500, <10 days w/ injury=1500, else 0
- Ties get the higher placement points
- Annual champion = sum of all 4 seasons

## Design Decisions

- Dark theme with warm coral/gold gradient accents
- Pico CSS for base styling, overridden via CSS custom properties
- `safeJS` pipe required when embedding jsonify data in `<script>` tags
  (Hugo's minifier otherwise string-escapes the JSON)
- Chart.js loaded in `<head>` block (not footer) because inline chart
  scripts in partials run on DOMContentLoaded
- `--disableFastRender` in dev server to avoid partial page reload issues
