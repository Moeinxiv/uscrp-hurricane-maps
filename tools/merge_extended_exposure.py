#!/usr/bin/env python3
"""Merge the TStop-extended re-run depths into facilities.geojson as properties.ext.

Input  : /tmp/ext_exposure.json produced on Alph by ext_exposure.py, keyed by the
         facility's INDEX in facilities.geojson (names repeat, indices don't).
Output : facilities.geojson gains  properties.ext = {"<event>_<scenario>": metres}

properties.exp stays as-is — it is the ORIGINAL truncated run, kept so the popup
can show "was X" and make the effect of the truncation visible.

Usage:  python3 merge_extended_exposure.py [/tmp/ext_exposure.json]
"""
import json, os, sys

FAC = os.path.expanduser("~/Claude/Projects/USCRP Hurricane Maps/webapp/uscrp-hurricane-maps/data/facilities.geojson")
SRC = sys.argv[1] if len(sys.argv) > 1 else "/tmp/ext_exposure.json"

ext = json.load(open(SRC))
meta = ext.pop("_meta", {})
gj = json.load(open(FAC))
feats = gj["features"]

for f in feats:
    f["properties"].pop("ext", None)

for key, vals in ext.items():
    n = 0
    for idx, v in vals.items():
        i = int(idx)
        if 0 <= i < len(feats):
            feats[i]["properties"].setdefault("ext", {})[key] = v
            n += 1
    print(f"  {key}: merged {n} values  ({meta.get(key, {})})")

gj["_extmeta"] = meta
json.dump(gj, open(FAC, "w"), separators=(",", ":"))
print("wrote", FAC)

print("\nfacilities flooded (>0.05 m), original truncated run -> extended run:")
for key in ("ike_historical", "ike_future", "rita_historical", "rita_future"):
    o = sum(1 for f in feats if (f["properties"].get("exp", {}).get(key) or 0) > 0.05)
    e = sum(1 for f in feats if (f["properties"].get("ext", {}).get(key) or 0) > 0.05)
    print(f"  {key:<18} {o:>3} -> {e:>3}")

print("\nbiggest changes:")
rows = []
for f in feats:
    p = f["properties"]
    for key in ("ike_historical", "ike_future", "rita_historical", "rita_future"):
        o = p.get("exp", {}).get(key)
        e = p.get("ext", {}).get(key)
        if o is not None and e is not None and e - o > 0.1:
            rows.append((e - o, p["name"], key, o, e))
for d, nm, key, o, e in sorted(rows, reverse=True)[:12]:
    print(f"  +{d:5.2f}  {nm[:40]:<42} {key:<17} {o:.2f} -> {e:.2f}")
