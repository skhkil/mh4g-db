"""Compatibility entry point for the current verified recommendation DB.

Canonical flow:
1) rebuild_verified_weapon_recommendations.py
2) refine_recommended_loadouts_research_v0.7.7.py
3) recalculate_recommended_activated_v0.7.7.mjs

This wrapper intentionally does NOT use the automatic combination generator.
"""
from pathlib import Path
import subprocess, sys

ROOT=Path(__file__).resolve().parents[1]
TOOLS=ROOT/'tools'

def run(cmd):
    print('+', ' '.join(map(str,cmd)))
    subprocess.run([str(x) for x in cmd], cwd=ROOT, check=True)

run([sys.executable, TOOLS/'rebuild_verified_weapon_recommendations.py'])
run([sys.executable, TOOLS/'refine_recommended_loadouts_research_v0.7.7.py'])
run(['node', TOOLS/'recalculate_recommended_activated_v0.7.7.mjs'])
print('verified recommendation rebuild complete')
