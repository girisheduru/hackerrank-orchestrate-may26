#!/usr/bin/env bash
# Run pytest and generate an HTML test dashboard.
# Usage: ./scripts/run_tests_and_build_dashboard.sh [extra pytest args]

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORTS_DIR="$REPO_ROOT/reports"
DASHBOARD_DIR="$REPORTS_DIR/dashboard"
JUNIT_XML="$REPORTS_DIR/junit.xml"
OUTPUT_CSV="$REPO_ROOT/support_tickets/output.csv"
INPUT_CSV="$REPO_ROOT/support_tickets/support_tickets.csv"
SAMPLE_CSV="$REPO_ROOT/support_tickets/sample_support_tickets.csv"

mkdir -p "$REPORTS_DIR" "$DASHBOARD_DIR"

echo "=== Running pytest ==="
cd "$REPO_ROOT"

# Prefer venv python, fall back to python3
PYTHON="${REPO_ROOT}/.venv/bin/python3"
if [ ! -x "$PYTHON" ]; then
  PYTHON="$(command -v python3 || command -v python)"
fi

PYTHONPATH="${REPO_ROOT}/code" "$PYTHON" -m pytest code/tests \
  --junit-xml="$JUNIT_XML" \
  --tb=short \
  -q \
  "$@" || true   # continue even if tests fail so dashboard is generated

echo ""
echo "=== Generating HTML dashboard ==="

PASS_COUNT=$("$PYTHON" -c "
import xml.etree.ElementTree as ET, sys
try:
    tree = ET.parse('$JUNIT_XML')
    root = tree.getroot()
    suite = root.find('testsuite') or root
    tests = int(suite.get('tests', 0))
    failures = int(suite.get('failures', 0))
    errors = int(suite.get('errors', 0))
    skipped = int(suite.get('skipped', 0))
    passed = tests - failures - errors - skipped
    print(f'{passed},{tests},{failures},{errors},{skipped}')
except Exception as e:
    print('0,0,0,0,0')
" 2>/dev/null)

IFS=',' read -r PASSED TOTAL FAILURES ERRORS SKIPPED <<< "$PASS_COUNT"

# Read CSV previews
INPUT_ROWS=$("$PYTHON" -c "
import csv, sys
try:
    rows = []
    with open('$INPUT_CSV') as f:
        r = csv.DictReader(f)
        for i, row in enumerate(r):
            if i >= 5: break
            rows.append(row)
    hdrs = list(rows[0].keys()) if rows else []
    cells = ''.join(f'<th>{h}</th>' for h in hdrs)
    trs = ''.join('<tr>' + ''.join(f'<td>{row.get(h,\"\")[:80]}</td>' for h in hdrs) + '</tr>' for row in rows)
    print(f'<thead><tr>{cells}</tr></thead><tbody>{trs}</tbody>')
except Exception as e:
    print(f'<tr><td>Error: {e}</td></tr>')
" 2>/dev/null)

OUTPUT_ROWS=$("$PYTHON" -c "
import csv, sys
try:
    rows = []
    with open('$OUTPUT_CSV') as f:
        r = csv.DictReader(f)
        for i, row in enumerate(r):
            if i >= 5: break
            rows.append(row)
    hdrs = list(rows[0].keys()) if rows else []
    cells = ''.join(f'<th>{h}</th>' for h in hdrs)
    trs = ''.join('<tr>' + ''.join(f'<td>{str(row.get(h,\"\"))[:80]}</td>' for h in hdrs) + '</tr>' for row in rows)
    print(f'<thead><tr>{cells}</tr></thead><tbody>{trs}</tbody>')
except Exception as e:
    print(f'<tr><td>Error: {e}</td></tr>')
" 2>/dev/null)

# Collect failed tests from junit
FAILED_TESTS=$("$PYTHON" -c "
import xml.etree.ElementTree as ET
try:
    tree = ET.parse('$JUNIT_XML')
    root = tree.getroot()
    rows = ''
    for tc in root.iter('testcase'):
        fail = tc.find('failure') or tc.find('error')
        if fail is not None:
            name = tc.get('name', '')
            cls = tc.get('classname', '')
            msg = (fail.text or '')[:300].replace('<','&lt;').replace('>','&gt;')
            rows += f'<tr><td>{cls}</td><td>{name}</td><td><pre>{msg}</pre></td></tr>'
    print(rows if rows else '<tr><td colspan=3>All tests passed ✓</td></tr>')
except Exception:
    print('<tr><td colspan=3>Could not parse junit.xml</td></tr>')
" 2>/dev/null)

cat > "$DASHBOARD_DIR/index.html" << HTML
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Triage Agent — Test Dashboard</title>
  <style>
    body { font-family: 'JetBrains Mono', monospace; background: #0B0F14; color: #E5E7EB; margin: 0; padding: 24px; }
    h1 { color: #60A5FA; } h2 { color: #38BDF8; border-bottom: 1px solid #1F2937; padding-bottom: 6px; }
    .badge { display: inline-block; padding: 4px 10px; border-radius: 4px; font-weight: 700; margin: 4px; }
    .pass { background: #052E16; color: #22C55E; } .fail { background: #3F0D0D; color: #EF4444; }
    .skip { background: #1C1917; color: #F59E0B; } .total { background: #111827; color: #38BDF8; }
    table { border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 12px; }
    th { background: #111827; color: #9CA3AF; padding: 6px 10px; text-align: left; }
    td { border: 1px solid #1F2937; padding: 6px 10px; vertical-align: top; }
    pre { margin: 0; white-space: pre-wrap; word-break: break-all; }
    .summary { display: flex; gap: 12px; flex-wrap: wrap; margin: 16px 0; }
  </style>
</head>
<body>
  <h1>🤖 Triage Agent — Test Dashboard</h1>
  <p style="color:#9CA3AF">Generated: $(date -u '+%Y-%m-%dT%H:%M:%SZ')</p>

  <h2>Test Summary</h2>
  <div class="summary">
    <span class="badge total">Total: ${TOTAL}</span>
    <span class="badge pass">Passed: ${PASSED}</span>
    <span class="badge fail">Failed: ${FAILURES}</span>
    <span class="badge skip">Skipped: ${SKIPPED}</span>
    <span class="badge fail">Errors: ${ERRORS}</span>
  </div>

  <h2>Failed Tests</h2>
  <table>
    <thead><tr><th>Class</th><th>Test</th><th>Message</th></tr></thead>
    <tbody>${FAILED_TESTS}</tbody>
  </table>

  <h2>Input CSV Preview (first 5 rows)</h2>
  <table>${INPUT_ROWS}</table>

  <h2>Output CSV Preview (first 5 rows)</h2>
  <table>${OUTPUT_ROWS}</table>
</body>
</html>
HTML

echo "Dashboard written to: $DASHBOARD_DIR/index.html"
echo "JUnit XML:            $JUNIT_XML"
