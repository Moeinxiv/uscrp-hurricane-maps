#!/usr/bin/env python3
"""Add the lab's PUBLISHED compound-flood depths to facilities.geojson, alongside ours.

Source: Flood-maps/Historical_Storm_Flood_Maps/compound_depth_ft_{Ike,Rita}.tif —
depth in FEET, almost certainly the output of Maymandi, Hummel & Zhang (2022, WRR
58(12) e2022WR033144), which modelled surge + tides + river discharge + rain-on-grid
and was validated against NOAA gauges and USGS high-water marks.

Our own runs are wind/pressure-only and stop before Ike and Rita reach land, so they
read ~0 on land. Showing both side by side is the honest presentation.

Writes properties.pub = {"ike_historical": m, "rita_historical": m} (metres).
Facilities outside a raster's footprint simply get no key.

Usage:  python3 facility_exposure_published.py
"""
import json, os
import numpy as np
import rasterio
from rasterio.warp import transform as rio_transform

FILES = os.path.expanduser("~/Documents/Dr. Zhang/USCRP Hurricane Maps/Files/OLD/General/Flood-maps")
FAC = os.path.expanduser("~/Claude/Projects/USCRP Hurricane Maps/webapp/uscrp-hurricane-maps/data/facilities.geojson")
COMP = {"ike_historical":  f"{FILES}/Historical_Storm_Flood_Maps/compound_depth_ft_Ike.tif",
        "rita_historical": f"{FILES}/Historical_Storm_Flood_Maps/compound_depth_ft_Rita.tif"}
FT2M = 0.3048

gj = json.load(open(FAC))
feats = gj["features"]
lons = [f["geometry"]["coordinates"][0] for f in feats]
lats = [f["geometry"]["coordinates"][1] for f in feats]
for f in feats:
    f["properties"].pop("pub", None)

for key, path in COMP.items():
    if not os.path.exists(path):
        print(f"  {key}: raster missing, skipped")
        continue
    with rasterio.open(path) as ds:
        xs, ys = rio_transform("EPSG:4326", ds.crs, lons, lats)
        vals = [float(v[0]) for v in ds.sample(zip(xs, ys))]
    cov = wet = 0
    for f, v in zip(feats, vals):
        if not np.isfinite(v):
            continue
        cov += 1
        m = round(v * FT2M, 2)
        f["properties"].setdefault("pub", {})[key] = m
        if m > 0.05:
            wet += 1
    print(f"  {key}: {cov}/{len(feats)} facilities inside raster, {wet} flooded")

json.dump(gj, open(FAC, "w"), separators=(",", ":"))
print("wrote", FAC)

ours = sum(1 for f in feats if (f["properties"].get("exp", {}).get("ike_historical") or 0) > 0.05)
pub = sum(1 for f in feats if (f["properties"].get("pub", {}).get("ike_historical") or 0) > 0.05)
print(f"\nIke, flooded facilities:  our surge-only runs {ours}   published compound {pub}")
