#!/usr/bin/env python3
import json, sys, subprocess, os

d = json.load(sys.stdin)
fp = d.get('tool_input', {}).get('file_path', '')

if not fp.endswith('.go'):
    sys.exit(0)

godir = os.path.dirname(fp)
while godir != '/':
    if os.path.exists(os.path.join(godir, 'go.mod')):
        break
    godir = os.path.dirname(godir)

r = subprocess.run(['go', 'build', './...'], cwd=godir, capture_output=True, text=True)
if r.returncode != 0:
    print(r.stderr, end='')
    sys.exit(1)
