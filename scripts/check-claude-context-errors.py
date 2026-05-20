#!/usr/bin/env python3
from __future__ import annotations
import json, os, re, subprocess, sys
from datetime import datetime, timedelta
from pathlib import Path

HOME=Path.home(); CLAUDE=HOME/'.claude'; STATE=CLAUDE/'context-policy-state.json'; ENSURE=CLAUDE/'scripts'/'ensure-claude-context-policy.py'
PATTERNS=[r'prompt[_ -]?too[_ -]?long', r'context[_ -]?length[_ -]?exceeded', r'maximum context length', r'413', r'request too large', r'token limit', r'input.*too large']
RX=re.compile('|'.join(PATTERNS), re.I|re.S)

def load():
    try: return json.loads(STATE.read_text(encoding='utf-8'))
    except Exception: return {}
def dump(s):
    STATE.parent.mkdir(parents=True, exist_ok=True); STATE.write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def recent_files():
    cutoff=datetime.now().timestamp()-3600
    roots=[CLAUDE/'projects', CLAUDE/'sessions']
    files=[]
    for root in roots:
        if root.exists():
            for p in root.rglob('*.jsonl'):
                try:
                    if p.stat().st_mtime>=cutoff: files.append(p)
                except Exception: pass
    h=CLAUDE/'history.jsonl'
    if h.exists(): files.append(h)
    return sorted(set(files), key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)[:80]
def tail_text(p: Path, max_bytes=400000):
    try:
        with p.open('rb') as f:
            try: f.seek(-max_bytes, os.SEEK_END)
            except OSError: f.seek(0)
            return f.read().decode('utf-8','replace')
    except Exception: return ''
def main():
    hit=None
    for p in recent_files():
        txt=tail_text(p)
        m=RX.search(txt)
        if m:
            hit=(p,str(m.group(0))[:120]); break
    if hit:
        state=load(); state['experimental_disabled']=True; state['disabled_reason']='auto-detected '+hit[1]; state['disabled_at']=datetime.now().isoformat(timespec='seconds'); state['disabled_source']=str(hit[0]); dump(state)
        subprocess.run([sys.executable, str(ENSURE), '--quiet'], check=False)
        print('[context-policy] disabled virtual 1.4m after detecting:', hit[1], 'in', hit[0])
        return 2
    return 0
if __name__=='__main__': raise SystemExit(main())
