#!/usr/bin/env python3
"""SUPERSEDED 2026-08-19 — DO NOT RUN THIS TO REBUILD data/timeseries.json.

Reading the shipped tiles made the summary charts inherit two defects the
tiles have and the model does not: the 8-bit vmax ceiling (which clipped
Rita's rise at 3 m and reported its climate signal as +0.09 m instead of
+1.34 m) and the 6-hourly display cadence (which missed Rita historical's
true peak entirely, 2.89 m sampled against 3.86 m hourly).

timeseries.json is now built on Alph, straight from the model output, by
  value_tiles.py --vars depth,rise,wind --step-hours 1 --stats-out <file>
one file per run, assembled and shifted +17 h locally. Same grid, same trim
mask, same thresholds — so the spatial definitions are unchanged — but every
model hour and no quantisation.

Kept for reference, and because it still documents the tile encoding. If you
run it, it will silently overwrite the good file with 6-hourly clipped
numbers. See project-rita-rise-ceiling-2026-08-19 in project memory.

--- original docstring ---

Precompute domain-wide time series for every event x scenario x variable.

Reads the exact-value data tiles that already ship with the web app
(data/frames/<ev>_<scen>/<var>_data/frame_NNN.png, 8-bit LA, value =
R/255*vmax where alpha>0) and reduces each frame to a handful of numbers:

  peak  - domain maximum for that timestep
  mean  - mean over valid (alpha>0) cells
  area  - fraction of valid cells above a variable-specific threshold
          (water: >0.1 m; wind: >17.5 m/s, i.e. tropical-storm force)

Output: data/timeseries.json  (a few tens of kB), consumed by the summary
chart panel in animation.html. Historical and future share one time axis per
event, so they overlay directly.

Usage:  python3 domain_timeseries.py
"""
import json, os
import numpy as np
from PIL import Image

REPO = os.path.expanduser("~/Claude/Projects/USCRP Hurricane Maps/webapp/uscrp-hurricane-maps")
FR   = os.path.join(REPO, "data", "frames")
OUT  = os.path.join(REPO, "data", "timeseries.json")

EVENTS    = ["harvey", "rita", "ike"]
SCENARIOS = ["historical", "future"]
VARS      = ["depth", "rise", "wind"]
THRESH    = {"depth": 0.1, "rise": 0.1, "wind": 17.5}


def series(ev, sc, var):
    p = os.path.join(FR, f"{ev}_{sc}", f"datamanifest_{var}.json")
    if not os.path.exists(p):
        return None
    m = json.load(open(p))
    vmax = m["vmax"]
    signed = bool(m.get("signed"))
    thr = THRESH[var]
    t, peak, mean, area = [], [], [], []
    for fr in m.get("frames", []):
        fp = os.path.join(FR, f"{ev}_{sc}", fr["data"])
        if not os.path.exists(fp):
            continue
        a = np.array(Image.open(fp))
        if a.ndim == 2:
            L, A = a, np.full(a.shape, 255, np.uint8)
        else:
            L, A = a[..., 0], a[..., -1]
        valid = A > 0
        if not valid.any():
            t.append(fr.get("t")); peak.append(0.0); mean.append(0.0); area.append(0.0)
            continue
        v = L[valid].astype(np.float32) / 255.0
        v = (v * 2 * vmax - vmax) if signed else (v * vmax)
        t.append(fr.get("t"))
        peak.append(round(float(v.max()), 2))
        mean.append(round(float(v.mean()), 3))
        area.append(round(float((v > thr).mean()), 4))
    if not t:
        return None
    # the data tiles quantise to [0, vmax]; flag when the peak is pinned at that
    # ceiling so the chart can say ">=" instead of implying a true maximum
    censored = sum(1 for p in peak if p >= vmax - 0.01)
    return {"t": t, "peak": peak, "mean": mean, "area": area, "vmax": vmax,
            "censored": censored,
            "units": "m/s" if var == "wind" else "m", "thresh": thr}


def main():
    out = {}
    for ev in EVENTS:
        out[ev] = {}
        for sc in SCENARIOS:
            out[ev][sc] = {}
            for var in VARS:
                s = series(ev, sc, var)
                if s:
                    out[ev][sc][var] = s
                    print(f"  {ev:<7} {sc:<11} {var:<6} {len(s['t']):>3} frames  "
                          f"peak {max(s['peak']):.2f}  max area {max(s['area'])*100:.1f}%")
                else:
                    print(f"  {ev:<7} {sc:<11} {var:<6} -- missing")
    # flag any historical/future frame-count mismatch so the chart can say so
    for ev in EVENTS:
        for var in VARS:
            h = out[ev].get("historical", {}).get(var)
            f = out[ev].get("future", {}).get(var)
            if h and f and len(h["t"]) != len(f["t"]):
                print(f"  ! {ev} {var}: historical {len(h['t'])} frames vs future {len(f['t'])}")
                out[ev].setdefault("_warn", {})[var] = f"historical {len(h['t'])} vs future {len(f['t'])} frames"
    json.dump(out, open(OUT, "w"), separators=(",", ":"))
    print("wrote", OUT, os.path.getsize(OUT), "bytes")


if __name__ == "__main__":
    main()
