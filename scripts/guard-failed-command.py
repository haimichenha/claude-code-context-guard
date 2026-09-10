"""Bound repeated failed Bash requests. Not a goal verifier or permission grant."""
import hashlib,json,os,sys,tempfile,time
from pathlib import Path

def signature(event):
    args=event.get('tool_input',{})
    return hashlib.sha256(json.dumps([event.get('cwd'),args.get('command')],ensure_ascii=True).encode()).hexdigest()

def decide(event,state_dir):
    sid=event.get('session_id')
    if not isinstance(sid,str) or not sid:return {}
    root=Path(state_dir);file=root/(hashlib.sha256(sid.encode()).hexdigest()+'.json')
    try:state=json.loads(file.read_text(encoding='utf-8'))
    except (OSError,ValueError):state={}
    if time.time()-state.get('time',0)>1800:state={}
    kind=event.get('hook_event_name');tool=event.get('tool_name')
    failed=state.get('failed',{})
    def save():
        root.mkdir(parents=True,exist_ok=True)
        fd,tmp=tempfile.mkstemp(dir=root,prefix=file.name+'.')
        try:
            with os.fdopen(fd,'w',encoding='utf-8') as f:json.dump({'failed':failed,'time':time.time()},f)
            os.replace(tmp,file)
        finally:
            if os.path.exists(tmp):os.unlink(tmp)
    if kind=='UserPromptSubmit':
        failed={};save()
        cwd=event.get('cwd')
        if isinstance(cwd,str) and cwd:
            return {'hookSpecificOutput':{'hookEventName':kind,'additionalContext':'Active filesystem cwd reported by the host: '+json.dumps(cwd)+'. Use this or the explicitly authorized task root. Claude session storage under ~/.claude/projects is not the workspace. Once fixed acceptance passes, finish this task rather than repeatedly inspecting the same output.'}}
        return {}
    if kind=='PostToolUse' and tool in ('Write','Edit','Bash'):
        # Successful correction can make a failed test meaningful again.
        # This never grants permission; permission denials survive this reset.
        failed={k:v for k,v in failed.items() if v.get('permission')}
        save();return {}
    if tool!='Bash':return {}
    key=signature(event)
    if kind=='PostToolUseFailure':
        if event.get('is_interrupt') or 'FAILED_COMMAND_REPEAT:' in str(event.get('error','')):return {}
        error=str(event.get('error','')).lower()
        permission=any(x in error for x in ('permission','denied','rejected','not allowed'))
        failed[key]={'permission':permission,'blocked':0};save()
        return {'hookSpecificOutput':{'hookEventName':kind,'additionalContext':'The command failed. Use the actual cwd from the environment; ~/.claude/projects is session storage, not the working tree. Inspect the failure and choose a corrected action. Do not repeat a permission-denied action or create a guessed workspace.'}}
    if kind=='PreToolUse' and key in failed:
        failed[key]['blocked']+=1;save()
        reason='FAILED_COMMAND_REPEAT: This same command already failed without a successful intervening corrective tool action. Inspect cwd and the original error; choose a corrected action. Do not change spelling just to evade this guard. Permission denial requires approval, not another attempt.'
        result={'hookSpecificOutput':{'hookEventName':kind,'permissionDecision':'deny','permissionDecisionReason':reason}}
        if failed[key]['blocked']>=2:result.update({'continue':False,'stopReason':reason})
        return result
    return {}

def main():
    try:
        event=json.loads(sys.stdin.buffer.read(4*1024*1024).decode('utf-8-sig'))
        print(json.dumps(decide(event,Path.home()/'.claude/context-guard/failed-command-state')))
    except (OSError,ValueError,TypeError,AttributeError) as exc:
        print('failed-command guard unavailable: '+type(exc).__name__,file=sys.stderr)
if __name__=='__main__':main()
