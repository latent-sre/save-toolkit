# Fleet atlas browser dashboard

Browse the fleet's agents, skills, guidance, ownership, verification links, and backlog evidence
in a local browser. The dashboard is an offline snapshot with embedded source excerpts. No
installation, web service, external scripts, fonts, or network access is required to view it.

## Create and open

From a clean, committed checkout, use the repository's verified Python environment:

```powershell
python -B scripts/fleet_atlas_v2.py build
python -B scripts/fleet_atlas_dashboard.py
```

Open `.eval-runs/fleet-atlas-dashboard/index.html` in your browser. Regenerating an existing
dashboard requires `--force`. Use `--output <path.html>` for a different destination and
`--root <checkout>` to export another clean checkout containing matching atlas runtime sources.
The exporter checks the existing atlas; it does not silently rebuild it. If verification refuses
missing, stale, modified, or tampered inputs, resolve that state and explicitly rebuild first.
Keep output outside canonical source directories and `docs/fleet-atlas/v2/`.

## Explore

- **Overview:** see the snapshot's contents and jump into a category.
- **Registry:** search entity names and paths, filter by category, and select an item.
- **Guidance:** search actual guidance text using all entered words.
- **Details:** follow recorded incoming and outgoing relationships, inspect facts and their
  evidence labels, and read the exact cited source lines.

Search, filters, and selections survive reload through the URL fragment. That fragment only
identifies a view in this particular file; another person needs the same exported snapshot to
use it. The dashboard contains repository source excerpts, so distribute it only to readers
authorized to see that repository.

## What the verification means

The exporter uses the same artifact verifier as atlas build, check, and query. The page records
the source revision, input digest, export time, and renderer digest. Its citations and evidence
labels come from verified facts, including explicitly unverified inferences and unknowns.

Opening the file does not check whether the checkout has changed since export. The page always
identifies itself as an offline snapshot; it is not current service health or operational truth.
Relationship browsing shows recorded neighbors, not a complete change-impact calculation. The
CLI `query impact` remains available for its defined transitive impact analysis.

This first browser surface deliberately uses HTML, CSS, and JavaScript embedded by the existing
Python/standard-library atlas toolchain. A separate SPA build and server would add installation
steps to a read-only offline viewer. No atlas schema, query semantics, acceptance gate, or generated
artifact manifest is changed. Delete the exported file to remove the viewer; canonical Markdown
and CLI navigation remain available.

## Developer verification

`python -B -m pytest -q scripts/test_fleet_atlas_dashboard.py` checks real Git-backed verification,
missing/stale/tampered input refusal, output protection, script escaping, and canonical source-line
boundaries. The optional `scripts/test_fleet_atlas_dashboard_browser.cjs` exercises the exported HTML
in an already installed Playwright/Chromium environment; it does not install packages or browsers.
Pass the HTML file and a scratch evidence directory as its two arguments. Set
`ATLAS_PLAYWRIGHT_MODULE` only when the installed package is outside normal Node module resolution.
It checks search, filters, relationship navigation, source evidence, reload state, themes, keyboard
activation, 320-pixel reflow, browser errors, and absence of network requests.
