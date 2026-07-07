# USCRP Hurricane Maps — Animated Inundation & Wind

Interactive animation of hurricane inundation depth and wind speed for
**Harvey (2017)**, **Rita (2005)**, and **Ike (2008)** over Southeast Texas /
the Sabine region, under historical and future-climate scenarios.

**Live viewer:** `animation.html` (open the GitHub Pages URL).

## Features
- **Event** (Harvey / Rita / Ike) × **Scenario** (historical / future / Δ future−historical)
- **Variables:** Depth (total water depth), Rise (surge above pre-storm baseline,
  fine 0–1 m ramp), Wind (speed)
- **Δ Fut−Hist:** static future-minus-historical peak-depth difference map per event
- Play / pause / time-slider with real simulation timestamps (6-hourly)
- Pause-to-hover value readout
- Crude-oil and natural-gas pipeline overlays with toggles
- Carto Light basemap

Tip: the events/scenarios look most different in the **Rise** and **Wind**
layers and the **Δ Fut−Hist** map — total Depth is dominated by the shared
seabed, so it looks similar across events by design.

## How it was built
Frames are extracted from Delft3D / D-Flow FM `FlowFM_map.nc` output
(`mesh2d_waterdepth`, `mesh2d_windx/windy`) and rasterized onto a fixed
EPSG:3857 grid matching the existing static maps. Depth shows **total water
depth** (bays, estuaries, surge, and overland flooding); mesh-edge artifacts
are trimmed. See the project's `animation_pipeline/` for the extractor
(`extract_flowfm_nc.py`) and full notes.

## Structure
```
index.html              # redirects to the viewer
animation.html          # the interactive viewer
data/
  CrudeOil_4.js         # crude-oil pipeline GeoJSON
  NaturalGas_3.js       # natural-gas pipeline GeoJSON
  frames/
    <event>_<scenario>/
      manifest_depth.json, manifest_wind.json
      depth/frame_NNN.png, wind/frame_NNN.png
```

## Notes
- Static site — no build step. Leaflet is loaded from CDN.
- Frames are PNG (~5 MB total). Depth uses an inundation-only mask; ask the
  modeling team if total-water-depth display is preferred instead.

USCRP Hurricane Maps · UT Arlington Hydromet
