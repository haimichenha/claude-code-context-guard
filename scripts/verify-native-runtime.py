"""Query native Claude's effective client context window without a model turn.
Does not prove upstream capacity or exercise compaction with a large transcript.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile


def parse_window(text):
    match = re.search(r'\*\*Tokens:\*\*[^\n]* / ([\d.,]+[km]?)', text, re.I)
    if not match:
        return None
    value = match.group(1).lower().replace(',', '')
    scale = 1000000 if value.endswith('m') else 1000 if value.endswith('k') else 1
    return int(float(value.rstrip('km')) * scale)


def assess(records, expected_window):
    for record in records:
        envelope = record['envelope']
        if record['exit_code'] or envelope.get('is_error') or envelope.get('duration_api_ms', 0) != 0 or envelope.get('total_cost_usd', 0) != 0:
            return False
    context = next(r['envelope'].get('result', '') for r in records if r['command'] == '/context')
    compact = next(r['envelope'].get('result', '') for r in records if r['command'] == '/autocompact')
    return parse_window(context) == expected_window and 'capped to' not in compact.lower() and 'currently disabled' not in compact.lower()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--model')
    args = ap.parse_args()
    if args.output.exists():
        raise ValueError('new report path required')
    home = Path.home()
    settings = json.loads((home / '.claude/settings.json').read_text(encoding='utf-8-sig'))
    env = os.environ.copy()
    env.update({k: str(v) for k, v in settings.get('env', {}).items()})
    if 'ANTHROPIC_AUTH_TOKEN' in settings.get('env', {}):
        env['ANTHROPIC_API_KEY'] = settings['env']['ANTHROPIC_AUTH_TOKEN']
    exe = Path(os.environ.get('APPDATA', str(home / 'AppData/Roaming'))) / 'npm/node_modules/@anthropic-ai/claude-code/bin/claude.exe'
    window = int(settings.get('autoCompactWindow', 1000000))
    model = args.model or settings.get('model', 'opus')
    records = []
    with tempfile.TemporaryDirectory(prefix='claude-window-query-') as work:
        for command in ('/autocompact', '/context'):
            cmd = [str(exe), '--bare', '-p', command, '--model', model,
                   '--settings', json.dumps({'autoCompactWindow': window}), '--output-format', 'json',
                   '--no-session-persistence', '--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}',
                   '--tools', '', '--max-budget-usd', '0.05']
            r = subprocess.run(cmd, cwd=work, env=env, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30)
            envelope = json.loads(r.stdout)
            records.append({'command': command, 'exit_code': r.returncode, 'envelope': envelope})
    verified = assess(records, window)
    report = {'client_window_verified': verified, 'expected_window': window, 'model_argument': model,
              'compression_pct_configured': env.get('CLAUDE_AUTOCOMPACT_PCT_OVERRIDE'),
              'disable_compact_set': env.get('DISABLE_COMPACT'), 'disable_auto_compact_set': env.get('DISABLE_AUTO_COMPACT'),
              'exe_sha256': hashlib.sha256(exe.read_bytes()).hexdigest(),
              'queries': [{'command': r['command'], 'result': r['envelope'].get('result'),
                           'api_ms': r['envelope'].get('duration_api_ms'), 'cost_usd': r['envelope'].get('total_cost_usd')} for r in records],
              'server_capacity_verified': False, 'large_transcript_compaction_tested': False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=True))
    return 0 if verified else 2


if __name__ == '__main__':
    raise SystemExit(main())
