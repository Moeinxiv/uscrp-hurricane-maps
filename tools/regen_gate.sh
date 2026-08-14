#!/bin/bash
# Gate between regenerating frames and publishing them.
#
# Run this after ANY rebuild of the animation frames / value tiles / wind data,
# and before `git add`. It refuses to let a corrupted rebuild reach the site.
#
#   ./regen_gate.sh            check only
#   ./regen_gate.sh --commit   check, then stage and commit if clean
#
# The checks are in audit_published_layers.py. The one that matters most is tile
# alignment: the app pairs value tiles to image frames BY INDEX, so a rebuild that
# writes a different number of frames for one of them silently makes every hover
# and click read the wrong hour. That is invisible on screen.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$HOME/Claude/Projects/USCRP Hurricane Maps/webapp/uscrp-hurricane-maps"

echo "== layer audit =="
python3 "$HERE/audit_published_layers.py" --quiet
RC=$?

echo
if [ $RC -ne 0 ]; then
  echo "GATE: BLOCKED — fix the FAILs above before publishing."
  exit 1
fi

echo "== browser smoke test =="
cd "$REPO" || exit 1
if ! curl -s -o /dev/null -w "" "http://localhost:8971/animation.html" 2>/dev/null; then
  nohup python3 -m http.server 8971 >/tmp/httpd.log 2>&1 &
  sleep 2
fi
python3 _make_tests.py >/dev/null 2>&1
C="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
ERRS=0
for t in main facility wind summary about; do
  [ -f "_t_$t.html" ] || continue
  "$C" --headless=new --hide-scrollbars --window-size=1440,900 \
       --virtual-time-budget=20000 --enable-logging=stderr --v=0 \
       --screenshot="/tmp/gate_$t.png" "http://localhost:8971/_t_$t.html" \
       2>"/tmp/gate_$t.log" >/dev/null
  if grep -qiE "PAGEERROR|Uncaught|SyntaxError|TypeError" "/tmp/gate_$t.log"; then
    echo "  $t: JS ERROR"; grep -iE "PAGEERROR|Uncaught|SyntaxError|TypeError" "/tmp/gate_$t.log" | head -2
    ERRS=$((ERRS+1))
  else
    echo "  $t: clean  (/tmp/gate_$t.png)"
  fi
done

echo
if [ $ERRS -ne 0 ]; then
  echo "GATE: BLOCKED — $ERRS view(s) threw JavaScript errors."
  exit 1
fi
echo "GATE: PASS — audit clean, no console errors. Screenshots in /tmp/gate_*.png"
echo "Look at the screenshots before publishing; the gate cannot tell you the map is WRONG,"
echo "only that it is internally consistent."

if [ "${1:-}" = "--commit" ]; then
  git add -A && git commit -m "Regenerate animation frames (gate passed)" && \
    echo "committed — push when you are ready"
fi
