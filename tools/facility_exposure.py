#!/usr/bin/env python3
"""Peak inundation depth at each water/wastewater facility, per event x scenario.

Source of truth = the six corrected overland geojsons
(data/geojsons/<event>_<scenario>.geojson), each 154,476 D-Flow FM mesh faces
carrying `mesh2d_max_depth` (m) at `mesh2d_face_x/y`. For every facility we take
the nearest mesh face centroid (rejecting matches farther than MAXDIST) and
write its peak depth into data/facilities.geojson, so the browser popup is
instant and needs no extra downloads.

NOTE: the raster tiles under data/frames/*_data/ are sea-masked, so they read 0
at inland points - they are the WRONG source for facility exposure. The first
version of this script (kept as facility_exposure_v1_raster.py) made that
mistake. Use these geojsons.

Usage:  python3 facility_exposure.py
"""
import json, math, os
import numpy as np

REPO = os.path.expanduser("~/Claude/Projects/USCRP Hurricane Maps/webapp/uscrp-hurricane-maps")
GJ   = os.path.join(REPO, "data", "geojsons")
FAC  = os.path.join(REPO, "data", "facilities.geojson")
EVENTS    = ["harvey", "rita", "ike"]
SCENARIOS = ["historical", "future"]
MAXDIST   = 600.0     # m; beyond this the facility sits outside the model mesh


def load_mesh(ev, sc):
    p = os.path.join(GJ, f"{ev}_{sc}.geojson")
    if not os.path.exists(p):
        return None
    with open(p) as f:
        d = json.load(f)
    n = len(d["features"])
    x = np.empty(n); y = np.empty(n); v = np.empty(n)
    for i, ft in enumerate(d["features"]):
        pr = ft["properties"]
        x[i] = pr["mesh2d_face_x"]; y[i] = pr["mesh2d_face_y"]; v[i] = pr["mesh2d_max_depth"]
    return x, y, v


def main():
    gj = json.load(open(FAC))
    feats = gj["features"]
    flon = np.array([f["geometry"]["coordinates"][0] for f in feats])
    flat = np.array([f["geometry"]["coordinates"][1] for f in feats])
    print(f"{len(feats)} facilities")

    for f in feats:
        f["properties"].pop("exp", None)

    kx = 111320.0 * math.cos(math.radians(float(flat.mean())))
    for ev in EVENTS:
        for sc in SCENARIOS:
            mesh = load_mesh(ev, sc)
            if mesh is None:
                print(f"  skip {ev}_{sc} (missing geojson)")
                continue
            mx, my, mv = mesh
            key = f"{ev}_{sc}"
            wet = 0; oob = 0
            for i, f in enumerate(feats):
                d2 = ((mx - flon[i]) * kx) ** 2 + ((my - flat[i]) * 111320.0) ** 2
                j = int(d2.argmin())
                if math.sqrt(float(d2[j])) > MAXDIST:
                    oob += 1
                    continue
                depth = round(float(mv[j]), 2)
                f["properties"].setdefault("exp", {})[key] = depth
                if depth > 0.05:
                    wet += 1
            print(f"  {ev:<7} {sc:<11} -> {wet}/{len(feats)} inundated ({oob} outside mesh)")

    json.dump(gj, open(FAC, "w"), separators=(",", ":"))
    print("wrote", FAC)

    print("\nTop 12 by peak depth, Rita future:")
    for f in sorted(feats, key=lambda f: -(f["properties"].get("exp", {}).get("rita_future") or 0))[:12]:
        e = f["properties"].get("exp", {})
        print(f"  hist {str(e.get('rita_historical')):>5}  fut {str(e.get('rita_future')):>5} m   {f['properties']['name'][:48]}")


if __name__ == "__main__":
    main()
