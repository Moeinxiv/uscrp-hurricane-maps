# tools

Verification and data-build scripts for the USCRP hurricane map. They were living
outside version control; they are here so they survive.

## Run this after regenerating frames — before publishing

    ./tools/regen_gate.sh

Runs `audit_published_layers.py` plus a five-view headless-browser check and blocks
if either fails. **The check that matters most is tile alignment:** the app pairs
exact-value tiles to image frames *by index*, so a rebuild that writes a different
number of frames for one of them makes every hover and click read the wrong hour —
with nothing visibly wrong on screen.

FAIL (blocks): misaligned value tiles · missing frames on disk · a Δ layer clipped
by its own vmax · a wind rose describing different hours than the wind layer.
WARN (does not block): values pinned at a tile's quantisation ceiling (the UI must
show "≥") · image/value frame count mismatch (trailing frames fall back to
colour-band estimation).

State at last run: **0 FAIL, 3 WARN** — Rita wind carries 17 image frames against
16 value tiles, and Rita-future rise saturates at 3.0 m in one frame.

A pass means the map is internally *consistent*. It cannot tell you the map is
*right* — look at the screenshots it leaves in `/tmp/gate_*.png`.

## The rest

| script | what it does |
|---|---|
| `audit_published_layers.py` | the checks themselves; `--quiet` hides passes, exit 1 on FAIL |
| `verify_pipeline_vintage.py` | diffs the shipped pipeline layers against the live EIA Atlas services (they carry no date attribute, so this is the only way to establish currency) |
| `facility_exposure.py` | peak depth at each facility from the overland geojsons |
| `facility_exposure_published.py` | the same from the published compound rasters |
| `merge_extended_exposure.py` | merges the extended re-run depths computed on Alph |
| `domain_timeseries.py` | **SUPERSEDED 2026-08-19 — do not run.** Built `data/timeseries.json` from the shipped tiles, so the charts inherited the tiles' vmax clipping and 6-hourly cadence. Rebuild instead with `value_tiles.py --step-hours 1 --stats-out` on Alph, then shift the timestamps +17 h |
| `relabel_forcing_clock_17h.py` | shifts every displayed timestamp +17 h; run on any freshly generated manifest, which comes off the model's 17-h-early clock |

Paths are absolute to `~/Claude/Projects/USCRP Hurricane Maps/…`; adjust if the
project moves.
