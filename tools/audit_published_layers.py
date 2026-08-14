#!/usr/bin/env python3
"""Gate on what the web app SERVES. Run after every frame regeneration.

Exits 1 on any FAIL. Every check here corresponds to a defect that has actually
occurred or that would silently corrupt the map:

  FAIL  data tiles not index-aligned with image frames
        -> the app attaches them by index, so every hover and click would read
           the wrong timestep. Silent and total.
  FAIL  wind rose not timestamp-aligned with the wind layer
        -> the rose would describe a different hour than the map shows.
  FAIL  a manifest references frames that are missing on disk
  FAIL  Delta data exceeds the diff tile's vmax -> values clipped without notice
  WARN  image/data frame COUNT mismatch -> trailing frames fall back to colour
        bands (+-half a legend band). Graceful, but worth knowing.
  WARN  values pinned at a tile's quantisation ceiling -> the UI must show ">=".
        Rita-future rise does this in 1 of 16 frames.

Usage:  python3 audit_published_layers.py [--quiet]
        echo $?      # 0 clean, 1 one or more FAILs
"""
import json, os, sys
import numpy as np
from PIL import Image

W = os.path.expanduser("~/Claude/Projects/USCRP Hurricane Maps/webapp/uscrp-hurricane-maps")
FR = f"{W}/data/frames"
GJ = f"{W}/data/geojsons"
EVENTS = ["harvey", "rita", "ike"]
SCEN = ["historical", "future"]
VARS = ["depth", "rise", "wind"]
QUIET = "--quiet" in sys.argv

FAILS, WARNS = [], []
def fail(m): FAILS.append(m); print(f"FAIL  {m}")
def warn(m): WARNS.append(m); print(f"WARN  {m}")
def ok(m):
    if not QUIET: print(f"ok    {m}")


def load(p):
    return json.load(open(p)) if os.path.exists(p) else None


# ---------------------------------------------------------------- 1. alignment
for ev in EVENTS:
    for sc in SCEN:
        for var in VARS:
            m = load(f"{FR}/{ev}_{sc}/manifest_{var}.json")
            d = load(f"{FR}/{ev}_{sc}/datamanifest_{var}.json")
            if not m:
                continue
            mt = [x.get("t") for x in m.get("frames", [])]
            missing = [x["png"] for x in m.get("frames", [])
                       if not os.path.exists(f"{FR}/{ev}_{sc}/{x['png']}")]
            if missing:
                fail(f"{ev}_{sc} {var}: {len(missing)} image frames missing on disk "
                     f"(first: {missing[0]})")
            if not d:
                warn(f"{ev}_{sc} {var}: no exact-value tiles — hover falls back to colour bands")
                continue
            dt = [x.get("t") for x in d.get("frames", [])]
            dmiss = [x["data"] for x in d.get("frames", [])
                     if not os.path.exists(f"{FR}/{ev}_{sc}/{x['data']}")]
            if dmiss:
                fail(f"{ev}_{sc} {var}: {len(dmiss)} value tiles missing on disk")
            n = min(len(mt), len(dt))
            bad = [i for i in range(n) if mt[i] != dt[i]]
            if bad:
                fail(f"{ev}_{sc} {var}: value tiles MISALIGNED from index {bad[0]} "
                     f"(image {mt[bad[0]]} vs data {dt[bad[0]]}) — hover would read the wrong hour")
            elif len(mt) != len(dt):
                warn(f"{ev}_{sc} {var}: {len(mt)} image frames vs {len(dt)} value tiles — "
                     f"last {abs(len(mt)-len(dt))} frame(s) use colour-band estimation")
            else:
                ok(f"{ev}_{sc} {var}: {len(mt)} frames, tiles aligned")

# ---------------------------------------------------------------- 2. ceilings
for ev in EVENTS:
    for sc in SCEN:
        for var in VARS + ["diff"]:
            d = load(f"{FR}/{ev}_{sc}/datamanifest_{var}.json")
            if not d:
                continue
            vmax = d.get("vmax")
            pinned = 0
            for fr in d.get("frames", []):
                p = f"{FR}/{ev}_{sc}/{fr['data']}"
                if not os.path.exists(p):
                    continue
                a = np.array(Image.open(p))
                L = a[..., 0] if a.ndim == 3 else a
                A = a[..., -1] if a.ndim == 3 else np.full(L.shape, 255, np.uint8)
                if (A > 0).any() and int(L[A > 0].max()) >= 255:
                    pinned += 1
            if pinned:
                warn(f"{ev}_{sc} {var}: {pinned} frame(s) pinned at the {vmax} ceiling — "
                     f"the UI must render these as '>=', not as exact")

# ---------------------------------------------------------------- 3. delta range
for ev in EVENTS:
    dm = load(f"{FR}/{ev}_diff/datamanifest_diff.json")
    h, f_ = f"{GJ}/{ev}_historical.geojson", f"{GJ}/{ev}_future.geojson"
    if not dm or not (os.path.exists(h) and os.path.exists(f_)):
        continue
    hv = np.array([x["properties"]["mesh2d_max_depth"] for x in json.load(open(h))["features"]])
    fv = np.array([x["properties"]["mesh2d_max_depth"] for x in json.load(open(f_))["features"]])
    d = fv - hv
    vmax = dm.get("vmax")
    if vmax is not None and (d.max() > vmax or -d.min() > vmax):
        fail(f"{ev} diff: data range {d.min():+.2f}..{d.max():+.2f} exceeds tile vmax "
             f"{vmax} — the Delta layer is clipped without saying so")
    else:
        ok(f"{ev} diff: range {d.min():+.2f}..{d.max():+.2f} within vmax {vmax}")

# ---------------------------------------------------------------- 4. wind rose
rose = load(f"{W}/data/wind_rose.json") or {}
for ev in EVENTS:
    for sc in SCEN:
        k = f"{ev}_{sc}"
        r = rose.get(k)
        m = load(f"{FR}/{k}/manifest_wind.json")
        if not m:
            continue
        if not r:
            fail(f"{k}: wind layer exists but wind_rose.json has no entry")
            continue
        rt = [x.get("t") for x in r.get("frames", [])]
        wt = [x.get("t") for x in m.get("frames", [])]
        if rt[:len(wt)] != wt:
            fail(f"{k}: wind rose timestamps do not match the wind layer")
        else:
            ok(f"{k}: wind rose aligned ({len(rt)} frames)")

# ---------------------------------------------------------------- 5. facility data
fac = load(f"{W}/data/facilities.geojson")
if fac:
    n = len(fac["features"])
    for key in ("exp", "pub", "ext"):
        c = sum(1 for x in fac["features"] if x["properties"].get(key))
        ok(f"facilities: {c}/{n} carry '{key}' depths")
else:
    fail("facilities.geojson missing")

print()
print(f"{len(FAILS)} FAIL, {len(WARNS)} WARN")
if FAILS:
    print("\nDo not publish this rebuild until the FAILs are resolved.")
sys.exit(1 if FAILS else 0)
