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

r = subprocess.run(['go', 'build', '-o', 'rocket-elevators-api', '.'], cwd=godir, capture_output=True, text=True)
if r.returncode != 0:
    print(r.stderr, end='')
    sys.exit(1)

# Restart the server if this is the API directory
if os.path.exists(os.path.join(godir, 'rocket-elevators-api')):
    subprocess.run(['pkill', '-f', 'rocket-elevators-api'], capture_output=True)
    subprocess.Popen(
        ['./rocket-elevators-api'],
        cwd=godir,
        env={**os.environ, 'DATA_DIR': '../../data', 'FLEET_CSV': '../elevator_fleet.csv'},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
