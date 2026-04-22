@../../agents/shared/AGENTS.md

# Buscapes GymRats

Hugo static site for a family GymRats fitness competition.

## Stack

- Hugo (no theme, custom layouts with Pico CSS via CDN)
- Chart.js for interactive charts
- GitHub Pages with custom domain: buscapes.gymrats.l2n.me
- Python preprocessing script generates data/ from resources/

## Commands

- `python3 scripts/process_data.py` - generate data files from raw JSON
- `hugo server --buildDrafts` - local dev server
- `hugo --minify` - production build to public/

## Data Flow

1. Raw data lives in `resources/challenge-data.json`
2. `scripts/process_data.py` processes it into `data/*.json`
3. Hugo templates read from `data/` via `hugo.Data.*`
4. CI runs the script before building
