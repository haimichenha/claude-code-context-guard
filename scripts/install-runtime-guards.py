"""Install narrowly scoped runtime guards; default is a dry-run.
No vendor executable, provider DB, Git history or project document is modified.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
from datetime import datetime

REPO=Path(__file__).resolve().parents[1]

def load(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(data):return hashlib.sha256(data).hexdigest()

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--home',type=Path,default=Path.home())
    ap.add_argument('--grok-skills-root',type=Path,required=True)
    ap.add_argument('--apply',action='store_true')
    args=ap.parse_args()
    home=args.home.resolve();claude=home/'.claude';settings=claude/'settings.json';md=claude/'CLAUDE.md'
    src=args.grok_skills_root.resolve()/'grok-task-execution'
    common=claude/'skills/grok-software-execution/scripts/grok-common.ps1'
    if not (src/'SKILL.md').is_file() or not common.is_file():raise ValueError('explicit skill source or installed transport dependency is missing')
    original=settings.read_bytes();cfg=load(settings)
    before=json.loads(json.dumps(cfg))
    cfg['attribution']={'commit':'','pr':''}
    # Deprecated key remains for older builds; current explicit keys win.
    hook_cmd='"'+str(Path(sys.executable).resolve())+'" "'+str(claude/'scripts/guard-noop-write.py')+'"'
    hooks=cfg.setdefault('hooks',{})
    if not isinstance(hooks,dict):raise ValueError('hooks is not an object')
    pre=hooks.setdefault('PreToolUse',[])
    if not isinstance(pre,list):raise ValueError('PreToolUse is not a list')
    if not any('guard-noop-write.py' in h.get('command','') for entry in pre for h in entry.get('hooks',[])):
        pre.append({'matcher':'Write','hooks':[{'type':'command','command':hook_cmd,'timeout':5}]})
    for event_name in ('PostToolUse', 'UserPromptSubmit'):
        entries=hooks.setdefault(event_name, [])
        if not isinstance(entries,list):raise ValueError(event_name+' is not a list')
        if not any('guard-noop-write.py' in h.get('command','') for entry in entries for h in entry.get('hooks',[])):
            entry={'hooks':[{'type':'command','command':hook_cmd,'timeout':5}]}
            if event_name == 'PostToolUse':entry['matcher']='Write'
            entries.append(entry)
    failed_cmd='"'+str(Path(sys.executable).resolve())+'" "'+str(claude/'scripts/guard-failed-command.py')+'"'
    for event_name,matcher in [('PreToolUse','Bash'),('PostToolUseFailure','Bash'),('PostToolUse','Write|Edit|Bash'),('UserPromptSubmit',None)]:
        entries=hooks.setdefault(event_name,[])
        if not isinstance(entries,list):raise ValueError(event_name+' is not a list')
        if not any('guard-failed-command.py' in h.get('command','') for entry in entries for h in entry.get('hooks',[])):
            entry={'hooks':[{'type':'command','command':failed_cmd,'timeout':5}]}
            if matcher:entry['matcher']=matcher
            entries.append(entry)
    changes={} if cfg == before else {settings:(json.dumps(cfg,ensure_ascii=False,indent=2)+'\n').encode('utf-8')}
    # Preserve local customizations outside the specific compatibility blocks.
    ensure=claude/'scripts/ensure-claude-context-policy.py'
    txt=ensure.read_text(encoding='utf-8-sig')
    new=(REPO/'scripts/ensure-claude-context-policy.py').read_text(encoding='utf-8-sig')
    native='def native_main'+new.split('def native_main',1)[1].split('def main() -> int:',1)[0]
    if 'def native_main' in txt:
        a=txt.index('def native_main'); z=txt.index('def main() -> int:', a)
        changes[ensure]=(txt[:a]+native+txt[z:]).encode('utf-8')
    else:
        txt=txt.replace('def main() -> int:',native+'def main() -> int:',1)
        needle='args=ap.parse_args()\n    state=load_json(STATE_FILE)'
        if needle not in txt:raise ValueError('unknown installed updater anchor')
        txt=txt.replace(needle,"args=ap.parse_args()\n    if claude_install_mode() == 'native-binary':\n        return native_main(args)\n    state=load_json(STATE_FILE)",1)
        changes[ensure]=txt.encode('utf-8')
    updated=changes.get(ensure, txt.encode('utf-8')).decode('utf-8')
    if "ap.add_argument('--window'" not in updated:
        updated=updated.replace('args=ap.parse_args()',"ap.add_argument('--window',type=int); ap.add_argument('--pct',type=int); args=ap.parse_args()",1)
    changes[ensure]=updated.encode('utf-8')
    validator=claude/'scripts/validate-claude-context-policy.py'
    txt=validator.read_text(encoding='utf-8-sig')
    new=(REPO/'scripts/validate-claude-context-policy.py').read_text(encoding='utf-8-sig')
    begin='    if cli_text is None and CLAUDE_EXE.exists():';end='    disabled = bool(state.get("experimental_disabled"))'
    if begin in txt:
        a=txt.index(begin); z=txt.index(end,a)
        block=begin+new.split(begin,1)[1].split(end,1)[0]
        changes[validator]=(txt[:a]+block+txt[z:]).encode('utf-8')
    else:
        if end not in txt:raise ValueError('unknown installed validator anchor')
        block=begin+new.split(begin,1)[1].split(end,1)[0]
        changes[validator]=txt.replace(end,block+end,1).encode('utf-8')
    # The legacy stability wrapper ran AFTER the policy updater and rewrote
    # window/pct to 1.2m/72. Give the updater sole ownership of context values.
    stability=claude/'scripts/claude-stability-repair.ps1'
    if stability.is_file():
        txt=stability.read_text(encoding='utf-8-sig')
        marker='# CONTEXT_POLICY_SINGLE_OWNER'
        if marker not in txt:
            begin='# 保持 1200000 上下文，与 Claude managed-1.2m 策略一致。'
            end='if ($KillOrphans) {'
            if txt.count(begin)!=1 or txt.count(end)!=1:raise ValueError('unknown stability wrapper; refusing speculative patch')
            a=txt.index(begin);z=txt.index(end,a)
            old=txt[a:z]
            if 'CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=72' not in old or 'autoCompactWindow' not in old:raise ValueError('stability preimage mismatch')
            py=str(Path(sys.executable).resolve()).replace("'","''")
            replacement=marker+"\n$PolicyScript = Join-Path $HomeDir '.claude\\scripts\\ensure-claude-context-policy.py'\n& '"+py+"' $PolicyScript --quiet --no-cli-patch\nif ($LASTEXITCODE -ne 0) { throw 'Context policy update failed; refusing legacy window fallback.' }\n\n"
            txt=(txt[:a]+replacement+txt[z:]).replace('$Window = 1200000\n','',1)
            changes[stability]=txt.encode('utf-8-sig')
    changes[claude/'scripts/guard-failed-command.py']=(REPO/'scripts/guard-failed-command.py').read_bytes()
    changes[claude/'scripts/guard-noop-write.py']=(REPO/'scripts/guard-noop-write.py').read_bytes()
    changes[claude/'scripts/verify-native-runtime.py']=(REPO/'scripts/verify-native-runtime.py').read_bytes()
    if md.is_file():
        txt=md.read_text(encoding='utf-8-sig')
        old='- When `grok-software-execution` is available and the request concerns local software files, use its direct task runner with explicit target roots and acceptance criteria. Keep direct operations inside those roots and verify results by reading them back.'
        new='- For explicitly requested Grok multi-step work, load `grok-task-execution` and its persistent work/verify ledger. If the current agent already uses Grok, use the current permitted tools; do not recursively invoke another Grok runner just because a local file is involved. A separate worker is optional and must have a concrete bounded task.'
        if old in txt:txt=txt.replace(old,new,1)
        marker='<!-- GROK_NO_PROGRESS_GUARD -->'
        if marker in txt:
            old_guard='Do not mistake repeated Write calls or memory updates for progress. Update memory only after a verified new fact or result. An identical write is not completion: read back, verify the real deliverable, then move to the next criterion. If the no-op guard stops the turn, report the blocked loop; never rephrase the same write to bypass it.'
            txt=txt.replace(old_guard,'Continuous execution means progress toward the user goal, not continuous tool calls or merely different command strings. Before each step identify the unmet criterion, missing evidence, intended action and expected observable result. Use the prior result to choose targeted read/query, modification, test/render/reconciliation, or the next unfinished criterion. Count only goal-relevant artifact changes, new evidence, actual validation or isolated blockers as progress. Explain changed conditions or a bounded transient failure before retrying. Memory rewrites, paraphrases and timestamp changes are not progress. If the no-op guard stops a turn, inspect and change the plan; never rephrase the same write to evade the guard.')
        if marker not in txt:
            txt+='\n'+marker+'\nContinuous execution means progress toward the user goal, not continuous tool calls or merely different command strings. Before each step identify the unmet criterion, missing evidence, intended action and expected observable result. Use the prior result to choose targeted read/query, modification, test/render/reconciliation, or the next unfinished criterion. Count only goal-relevant artifact changes, new evidence, actual validation or isolated blockers as progress. Explain changed conditions or a bounded transient failure before retrying. Memory rewrites, paraphrases and timestamp changes are not progress. If the no-op guard stops a turn, inspect and change the plan; never rephrase the same write to evade the guard.\n'
        artifact_marker='<!-- GROK_ARTIFACT_FORMAT_GUARD -->'
        if artifact_marker not in txt:
            txt+='\n'+artifact_marker+'\nWrite emits text, not a DOCX/PDF/DLL/AEX serializer. For binary/package deliverables, write and execute a real generator/build script; never put Markdown, XML or base64 directly under a binary extension. Preserve genuine source files and independently check output structure, requested content/format changes and rendering where required. On ARTIFACT_FORMAT, switch to the correct generation tool, not another filename. A passed structure check or a stopped loop is not completed user work.\n'
        cwd_marker='<!-- GROK_WORKSPACE_ANCHOR -->'
        if cwd_marker not in txt:
            txt+='\n'+cwd_marker+'\nUse the actual cwd or the explicit user-approved project root, confirmed by pwd/Get-Location/os.getcwd(). ~/.claude/projects/<encoded-name> is session storage, NOT the source workspace. Never decode its name into a guessed path or mkdir a substitute work directory. On missing paths, inspect the actual cwd once and resolve the specified input there. On permission denial, stop that operation; do not repeat or evade it.\n'
        close_marker='<!-- GROK_VERIFIED_CLOSEOUT -->'
        if close_marker not in txt:
            txt+='\n'+close_marker+'\nPrefer an already-tested task-specific tool when it matches the request; do not regenerate the same algorithm unnecessarily. Once all frozen acceptance criteria pass, finish or advance to the next unmet task; repeated inspections are not new work. Use absolute paths or the confirmed cwd. Chain directory changes with failure-stop semantics (cd ... && command), never continue after a failed cd.\n'
        changes[md]=txt.encode('utf-8')
    for p in src.rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc':
            changes[claude/'skills/grok-task-execution'/p.relative_to(src)]=p.read_bytes()
    changes={p:b for p,b in changes.items() if not p.is_file() or p.read_bytes()!=b}
    print(json.dumps({'mode':'apply' if args.apply else 'dry-run','changed_paths':[str(p) for p in changes],'preserves':['model','permissions','provider credentials','provider database','project files','Git history']},ensure_ascii=True))
    if not args.apply:return
    # Refuse a concurrent settings change instead of silently replacing it.
    if settings.read_bytes()!=original:raise ValueError('settings changed during preparation')
    backup=claude/'backups'/('runtime-guard-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    backup.mkdir(parents=True,exist_ok=False)
    records=[]
    for p,data in changes.items():
        old=p.read_bytes() if p.is_file() else None
        saved=backup/p.relative_to(claude)
        if old is not None:
            saved.parent.mkdir(parents=True,exist_ok=True);saved.write_bytes(old)
        p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        if p.read_bytes()!=data:raise IOError('readback mismatch: '+str(p))
        records.append({'path':str(p),'backup':str(saved) if old is not None else None,'before_sha256':sha(old) if old is not None else None,'after_sha256':sha(data)})
    after=load(settings)
    for key in set(before)|set(after):
        if key not in ('hooks','attribution') and before.get(key)!=after.get(key):raise ValueError('unrelated setting changed: '+key)
    (backup/'manifest.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
    print(json.dumps({'installed':True,'backup_dir':str(backup),'attribution':after['attribution'],'hook_events':list(after['hooks'])}))

if __name__=='__main__':main()
