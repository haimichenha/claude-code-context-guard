#!/usr/bin/env python3
from __future__ import annotations
import json, os, re, subprocess, sys
from datetime import datetime, timedelta
from pathlib import Path

HOME=Path.home(); CLAUDE=HOME/'.claude'; STATE=CLAUDE/'context-policy-state.json'; ENSURE=CLAUDE/'scripts'/'ensure-claude-context-policy.py'
PATTERNS=[r'prompt[_ -]?too[_ -]?long', r'context[_ -]?length[_ -]?exceeded', r'maximum context length', r'request too large', r'payload too large', r'token limit', r'input.*too large', r'(?:status|error|api|http|response|request)[^\n]{0,80}\b413\b', r'\b413\b[^\n]{0,80}(?:request too large|payload too large|prompt|context)']
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
    # Do not scan history.jsonl: it stores user-entered prompts/pasted summaries and can
    # mention strings like prompt_too_long/API 413 without an actual Claude API failure.
    return sorted(set(files), key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)[:80]
def tail_text(p: Path, max_bytes=400000):
    try:
        with p.open('rb') as f:
            try: f.seek(-max_bytes, os.SEEK_END)
            except OSError: f.seek(0)
            raw=f.read().decode('utf-8','replace')
        # Project/session jsonl also contains ordinary user/assistant conversation text.
        # Only inspect lines that look like machine/tool/API error records, so discussions
        # about prompt_too_long, context_length_exceeded, or API 413 do not trigger rollback.
        kept=[]
        markers=('"type":"error"','"level":"error"','"is_error":true','"error":','statusCode','status_code','APIError','HTTPError')
        for line in raw.splitlines():
            if any(m in line for m in markers):
                kept.append(line)
        return '\n'.join(kept)
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
        print('[context-policy] disabled managed context window after detecting:', hit[1], 'in', hit[0])
        return 2
    return 0
if __name__=='__main__': raise SystemExit(main())
