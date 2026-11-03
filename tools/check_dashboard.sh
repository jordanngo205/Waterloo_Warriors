#!/bin/sh
# Render docs/index.html in headless Chrome and run tools/check_dashboard.js against it:
# every tab under every conference filter, rank/label directions, leftover FIBA text.
# Prints the JS errors and failed checks; exits 1 if there are any.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
python3 - "$ROOT" "$TMP" <<'PY'
import sys
root, tmp = sys.argv[1], sys.argv[2]
s = open(f'{root}/docs/index.html').read()
pre = '<script>window.__E=[];window.onerror=function(m,u,l){__E.push(m+" @"+l);};</script>'
js = open(f'{root}/tools/check_dashboard.js').read()
open(f'{tmp}/t.html', 'w').write(s.replace('<body>\n', '<body>\n' + pre, 1).replace('</body>', '<script>' + js + '</script></body>'))
PY
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --disable-gpu --virtual-time-budget=20000 \
  --dump-dom "file://$TMP/t.html" 2>/dev/null | grep -o 'data-result="[^"]*"' | head -1 \
  | sed 's/&quot;/"/g;s/^data-result="//;s/"$//' \
  | python3 -c "import sys,json,html; d=json.loads(html.unescape(sys.stdin.read())); bad=d['errors']+d['fails']; [print('FAIL',x) for x in bad]; print('dashboard checks:', 'all passed' if not bad else f'{len(bad)} failed'); sys.exit(1 if bad else 0)"
