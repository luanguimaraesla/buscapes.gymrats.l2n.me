# Buscapes GymRats

Static site for the Buscapes family GymRats competition. Built with
[Hugo](https://gohugo.io/) and published to GitHub Pages at
[buscapes.gymrats.l2n.me](https://buscapes.gymrats.l2n.me).

## Development

```bash
# Generate data files from raw challenge data
python3 scripts/process_data.py

# Start local dev server
hugo server --buildDrafts
```

## Deploy

Pushes to `main` trigger automatic deployment via GitHub Actions.
The workflow runs the preprocessing script before building.
