#!/usr/bin/env python3
from __future__ import annotations
import json, pathlib, sqlite3, os, re
HOME=pathlib.Path.home()
CLI=HOME/'AppData/Roaming/npm/node_modules/@anthropic-ai/claude-code/cli.js'
SETTINGS=HOME/'.claude/settings.json'
STATE=HOME/'.claude/context-policy-state.json'
CCDB=HOME/'.cc-switch/cc-switch.db'

def ok(name, cond, detail=''):
    print(f"[{'OK' if cond else 'FAIL'}] {name}{(': '+detail) if detail else ''}")
    return bool(cond)

def main():
    passed=True
    settings=json.load(open(SETTINGS,encoding='utf-8'))
    state=json.load(open(STATE,encoding='utf-8'))
    s=CLI.read_text(encoding='utf-8',errors='replace')
    passed &= ok('model opus[1m]', settings.get('model')=='opus[1m]', str(settings.get('model')))
    passed &= ok('permission auto', settings.get('permissions',{}).get('defaultMode')=='auto', str(settings.get('permissions',{}).get('defaultMode')))
    disabled=bool(state.get('experimental_disabled'))
    target_window=1_000_000 if disabled else 1_400_000
    pct=None if disabled else 72.0
    passed &= ok('settings autoCompactWindow', settings.get('autoCompactWindow')==target_window, str(settings.get('autoCompactWindow')))
    if not disabled:
        passed &= ok('pct override 72', settings.get('env',{}).get('CLAUDE_AUTOCOMPACT_PCT_OVERRIDE')=='72', str(settings.get('env',{}).get('CLAUDE_AUTOCOMPACT_PCT_OVERRIDE')))
        passed &= ok('cli [1m] returns 1.4m', 'if(DP(q))return 14e5' in s)
        passed &= ok('cli schema max 1.4m', 'autoCompactWindow:y.number().int().min(1e5).max(14e5).optional()' in s)
        passed &= ok('cli env max 1.4m', '$LK=14e5' in s)
    else:
        passed &= ok('cli [1m] returns safe 1m', 'if(DP(q))return 1e6' in s)
    passed &= ok('pct override supported', 'CLAUDE_AUTOCOMPACT_PCT_OVERRIDE' in s)
    passed &= ok('/rename usage hint', 'Usage: /rename <name>' in s and 'Usage: /rename [name]' not in s)
    passed &= ok('/rename strips optional brackets', 'else z=_.trim().replace(/^\\[(.*)\\]$/,"$1").trim();' in s)
    passed &= ok('/rename argumentHint', 'argumentHint:"<name>"' in s and 'argumentHint:"[name]"' not in s)
    passed &= ok('ordinary fallback window 300k', 'var DR1=300000,Po6=20000,UO_=32000,QO_=128000,pgq=8000;' in s)
    # Threshold model from located minified code:
    reserved_summary=min(20_000, 20_000)
    effective=target_window-reserved_summary
    default_threshold=effective-13_000
    threshold=int(effective*(pct/100.0)) if pct else default_threshold
    threshold=min(threshold, default_threshold)
    print(f"[CALC] target_window={target_window:,} effective={effective:,} compact_threshold≈{threshold:,} tokens")
    if not disabled:
        print(f"[CALC] old_1m_threshold≈967,000; new_threshold_delta≈{threshold-967000:+,} tokens")
    ordinary_effective=300_000-reserved_summary
    ordinary_threshold=int(ordinary_effective*0.72)
    print(f"[CALC] ordinary_model_window=300,000 ordinary_compact_threshold≈{ordinary_threshold:,} tokens")
    if CCDB.exists():
        conn=sqlite3.connect(CCDB)
        common=json.loads(conn.execute("select value from settings where key='common_config_claude'").fetchone()[0])
        prov=json.loads(conn.execute("select settings_config from providers where app_type='claude' and is_current=1").fetchone()[0])
        conn.close()
        passed &= ok('cc-switch common window', common.get('autoCompactWindow')==target_window, str(common.get('autoCompactWindow')))
        passed &= ok('cc-switch current window', prov.get('autoCompactWindow')==target_window, str(prov.get('autoCompactWindow')))
    print('[RESULT]', 'PASS' if passed else 'FAIL')
    return 0 if passed else 1
if __name__=='__main__': raise SystemExit(main())
