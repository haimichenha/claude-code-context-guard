"""PreToolUse anti-loop guard. Deny exact no-op Write; stop repeated no-op.
Target files are read only. State contains hashes, not file content or names.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time

MAX_BYTES = 4 * 1024 * 1024

def decide(event, state_dir):
    session = event.get('session_id')
    event_name = event.get('hook_event_name', 'PreToolUse')
    if event_name == 'UserPromptSubmit' or (event_name == 'PostToolUse' and event.get('tool_name') == 'Write'):
        # PostToolUse is a completed successful write, not a proposed edit.
        # A new user directive also starts a fresh bounded work attempt.
        if isinstance(session, str) and session:
            file = Path(state_dir) / (hashlib.sha256(session.encode()).hexdigest() + '.json')
            if file.is_file():
                file.write_text(json.dumps({'count': 0, 'time': time.time()}), encoding='utf-8')
        return {}
    if event_name != 'PreToolUse' or event.get('tool_name') != 'Write':
        return {}
    args = event.get('tool_input', {})
    content, name = args.get('content'), args.get('file_path')
    if not isinstance(content, str) or not isinstance(name, str):
        return {}
    path = Path(name)
    if not path.is_absolute():
        cwd = event.get('cwd')
        if not cwd or not Path(cwd).is_absolute():
            return {}
        path = Path(cwd) / path
    binary_formats = {'.docx', '.docm', '.xlsx', '.xlsm', '.pptx', '.pptm', '.pdf', '.dll', '.aex', '.exe'}
    # Claude's Write tool emits UTF-8 text. It is not a binary/document serializer.
    # Reject before creation, including renamed vNN/final output paths.
    if path.suffix.lower() in binary_formats:
        reason = 'ARTIFACT_FORMAT: Write emits text and cannot directly create this binary/package format. Do not rename Markdown, XML or base64 text to this extension. Write a generator script (.py/.ps1) or use a real document/build tool, execute it, then independently verify the output format and requested changes. Do not retry the same operation under another filename.'
    else:
        try:
            if not path.is_file() or path.stat().st_size > MAX_BYTES:
                return {}
            if path.read_bytes() != content.encode('utf-8'):
                return {}
        except OSError:
            return {}
        reason = 'NO_PROGRESS: target already contains exactly these bytes. Do not repeat Write. Read back once, verify the actual deliverable, then advance to remaining work.'
    result = {'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'permissionDecision': 'deny', 'permissionDecisionReason': reason}}
    session = event.get('session_id')
    if not isinstance(session, str) or not session:
        return result
    state_dir = Path(state_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    file = state_dir / (hashlib.sha256(session.encode()).hexdigest() + '.json')
    signature = hashlib.sha256((str(path.resolve()) + '\0' + content).encode()).hexdigest()
    now, old = time.time(), {}
    try:
        old = json.loads(file.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        pass
    count = old.get('count', 0) + 1 if 0 <= now - old.get('time', 0) < 300 else 1
    fd, tmp = tempfile.mkstemp(prefix=file.name + '.', dir=state_dir)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(dict(signature=signature, count=count, time=now), f)
        os.replace(tmp, file)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    if count >= 2:
        result.update({'continue': False, 'stopReason': 'Two invalid-format/no-op Writes without a successful intervening write were blocked, including across different files. Stopping this turn to prevent an unproductive loop. Resume with a new evidence-backed plan, not another identical write.'})
    return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-dir', default=str(Path.home() / '.claude/context-guard/noop-state'))
    args = parser.parse_args()
    try:
        raw = sys.stdin.buffer.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            return 0
        print(json.dumps(decide(json.loads(raw.decode('utf-8-sig')), args.state_dir)))
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        print('no-op guard unavailable: ' + type(exc).__name__, file=sys.stderr)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
