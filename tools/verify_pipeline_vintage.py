#!/usr/bin/env python3
"""Compare the pipeline layers the app ships against the live EIA Atlas layers.

The shipped files carry no date attribute, so their vintage cannot be read from the
data itself. This fetches the current EIA layers over the SAME bounding box the
shipped files cover and compares feature counts, total length and operator names.
Close match => the shipped copy is current. Large gap => it is stale and the public
map is showing out-of-date infrastructure.

Sources (schemas match the shipped files exactly, which is what identifies them):
  crude : Crude_Oil_Trunk_Pipelines_1        fields Opername / Pipename / Shape_Leng
  gas   : Natural_Gas_Interstate_and_Intrastate_Pipelines_1  fields TYPEPIPE / Operator / Status

Usage:  python3 verify_pipeline_vintage.py
"""
import json, math, os, urllib.parse, urllib.request

DATA = os.path.expanduser("~/Claude/Projects/USCRP Hurricane Maps/webapp/uscrp-hurricane-maps/data")
SRC = {
    "crude": dict(local="CrudeOil_4.js",
        url="https://services2.arcgis.com/FiaPA4ga0iQKduv3/arcgis/rest/services/Crude_Oil_Trunk_Pipelines_1/FeatureServer/0",
        opfield="Opername"),
    "gas": dict(local="NaturalGas_3.js",
        url="https://services2.arcgis.com/FiaPA4ga0iQKduv3/arcgis/rest/services/Natural_Gas_Interstate_and_Intrastate_Pipelines_1/FeatureServer/0",
        opfield="Operator"),
}


def seg_len_km(coords):
    t = 0.0
    for i in range(1, len(coords)):
        x1, y1 = coords[i - 1][:2]; x2, y2 = coords[i][:2]
        kx = 111.320 * math.cos(math.radians((y1 + y2) / 2))
        t += math.hypot((x2 - x1) * kx, (y2 - y1) * 110.574)
    return t


def fetch(url, bbox):
    q = {"where": "1=1",
         "geometry": ",".join(str(round(v, 4)) for v in bbox),
         "geometryType": "esriGeometryEnvelope", "inSR": "4326",
         "spatialRel": "esriSpatialRelIntersects", "outFields": "*",
         "returnGeometry": "true", "outSR": "4326", "f": "json",
         "resultRecordCount": "4000"}
    req = urllib.request.Request(url + "/query?" + urllib.parse.urlencode(q),
                                 headers={"User-Agent": "uscrp-audit"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.load(r)


def layer_info(url):
    req = urllib.request.Request(url + "?f=json", headers={"User-Agent": "uscrp-audit"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


for kind, cfg in SRC.items():
    txt = open(os.path.join(DATA, cfg["local"])).read()
    gj = json.loads(txt[txt.index("{"):].rstrip().rstrip(";"))
    fs = gj["features"]
    xs, ys, tot, ops = [], [], 0.0, set()
    for ft in fs:
        v = ft["properties"].get(cfg["opfield"])
        if v:
            ops.add(str(v).strip().upper())
        for part in ft["geometry"]["coordinates"]:
            tot += seg_len_km(part)
            for c in part:
                xs.append(c[0]); ys.append(c[1])
    bbox = (min(xs), min(ys), max(xs), max(ys))

    info = layer_info(cfg["url"])
    live = fetch(cfg["url"], bbox)
    lf = live.get("features", [])
    ltot, lops = 0.0, set()
    for ft in lf:
        a = {k.lower(): v for k, v in ft["attributes"].items()}
        v = a.get(cfg["opfield"].lower())
        if v:
            lops.add(str(v).strip().upper())
        for part in ft["geometry"].get("paths", []):
            ltot += seg_len_km(part)

    print(f"\n=== {kind.upper()} ===")
    print(f"  live layer  : {info.get('name')}")
    print(f"  bbox compared: {tuple(round(b,3) for b in bbox)}")
    print(f"  shipped : {len(fs):>5} features | {tot:8.1f} km | {len(ops)} operators")
    print(f"  live EIA: {len(lf):>5} features | {ltot:8.1f} km | {len(lops)} operators")
    if tot:
        print(f"  length difference: {100*(ltot-tot)/tot:+.1f}%")
    only_ship = sorted(ops - lops); only_live = sorted(lops - ops)
    print(f"  operators only in shipped ({len(only_ship)}): {only_ship[:8]}")
    print(f"  operators only in live    ({len(only_live)}): {only_live[:8]}")
    print(f"  operators in common: {len(ops & lops)}")

    # The raw length gap is a clipping artifact: the server returns each feature's
    # FULL geometry, while the shipped file was cut to the study area. Clip the live
    # geometry to the same bbox for a like-for-like comparison, and compare the
    # per-feature attribute tuples, which is the real staleness test.
    x0, y0, x1, y1 = bbox
    def clipped_len(parts):
        t = 0.0
        for part in parts:
            run = []
            for c in part:
                inside = x0 <= c[0] <= x1 and y0 <= c[1] <= y1
                if inside:
                    run.append(c)
                elif len(run) > 1:
                    t += seg_len_km(run); run = []
                else:
                    run = []
            if len(run) > 1:
                t += seg_len_km(run)
        return t
    lclip = sum(clipped_len(ft["geometry"].get("paths", [])) for ft in lf)
    sclip = sum(clipped_len(ft["geometry"]["coordinates"]) for ft in fs)
    print(f"  clipped to the same bbox -> shipped {sclip:.1f} km | live {lclip:.1f} km"
          f" ({100*(lclip-sclip)/max(sclip,1e-9):+.1f}%)")

    keys = {"crude": ("Opername", "Pipename"), "gas": ("TYPEPIPE", "Operator", "Status")}[kind]
    def sig(d):
        return tuple(str(d.get(k, d.get(k.lower(), ""))).strip().upper() for k in keys)
    from collections import Counter
    cs = Counter(sig(ft["properties"]) for ft in fs)
    cl = Counter(sig({k: v for k, v in ft["attributes"].items()}) for ft in lf)
    same = cs == cl
    print(f"  per-feature attribute signatures identical: {same}")
    if not same:
        for s, n in (cs - cl).most_common(4):
            print(f"    only shipped x{n}: {s}")
        for s, n in (cl - cs).most_common(4):
            print(f"    only live    x{n}: {s}")
