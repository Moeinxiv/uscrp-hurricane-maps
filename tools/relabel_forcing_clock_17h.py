#!/usr/bin/env python3
"""Shift every displayed timestamp in the deployed data by +17 h.

Why: the .apwxwy meteo forcing headers written by shanru2d3d.py are 17 h early
(a US/Central reference time stamped '+00:00' = -5 h, plus a hard-coded start
date 12 h before the WRF file's real first record). Delft3D anchored every run
to that epoch, so every model output time -- and every label on the map -- is
17 h behind the real weather it shows. Field values are correct; only the clock
is wrong. These runs have no tides, so relabelling is exact: nothing in the
physics depends on absolute time.

Verified 2026-08-19 by exact field match of apwxwy block 0 against the WRF
first record (12:00 UTC the day after each claimed 19:00 epoch):
harvey_historical PSFC mean diff 0.0000, ike_historical 0.0004,
rita_historical PSFC min 62356 exact.

Edits are textual so file formatting and diffs stay minimal.
"""
import re, sys, os, datetime, glob

REPO = "/Users/moein/Claude/Projects/USCRP Hurricane Maps/webapp/uscrp-hurricane-maps"
SHIFT = datetime.timedelta(hours=17)
APPLY = "--apply" in sys.argv

PAT = re.compile(r'"(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}(?::\d{2})?)( UTC)?"')


def repl(m):
    date, tm, suffix = m.group(1), m.group(2), m.group(3) or ""
    fmt = "%Y-%m-%d %H:%M:%S" if len(tm) == 8 else "%Y-%m-%d %H:%M"
    dt = datetime.datetime.strptime(date + " " + tm, fmt) + SHIFT
    return '"' + dt.strftime(fmt) + suffix + '"'


targets = sorted(glob.glob(os.path.join(REPO, "data/frames/*/manifest_*.json"))) \
        + sorted(glob.glob(os.path.join(REPO, "data/frames/*/datamanifest_*.json"))) \
        + [os.path.join(REPO, "data/timeseries.json"),
           os.path.join(REPO, "data/wind_rose.json"),
           os.path.join(REPO, "data/facilities.geojson")]

total, nfiles = 0, 0
for f in targets:
    if not os.path.exists(f):
        print("MISSING:", f)
        continue
    txt = open(f, encoding="utf-8").read()
    hits = PAT.findall(txt)
    if not hits:
        continue
    new = PAT.sub(repl, txt)
    nf = PAT.findall(new)
    rel = os.path.relpath(f, REPO)
    print("  %-52s n=%-5d %s %s -> %s %s   ...   %s %s -> %s %s" % (
        rel, len(hits),
        hits[0][0], hits[0][1], nf[0][0], nf[0][1],
        hits[-1][0], hits[-1][1], nf[-1][0], nf[-1][1]))
    total += len(hits)
    nfiles += 1
    if APPLY:
        open(f, "w", encoding="utf-8").write(new)

print("\n%d timestamps across %d files (%s)" % (total, nfiles, "APPLIED" if APPLY else "DRY RUN"))
