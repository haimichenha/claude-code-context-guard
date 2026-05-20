#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, shutil, sqlite3
from datetime import datetime
from pathlib import Path

HOME = Path.home()
CLAUDE_DIR = HOME / ".claude"
CC_SWITCH_DB = HOME / ".cc-switch" / "cc-switch.db"
SETTINGS_JSON = CLAUDE_DIR / "settings.json"
CLAUDE_MD = CLAUDE_DIR / "CLAUDE.md"
PERSISTENT = CLAUDE_DIR / "persistent-handoff"
STATE_FILE = CLAUDE_DIR / "context-policy-state.json"
ENV_CMD = CLAUDE_DIR / "scripts" / "context-policy-env.cmd"
ENV_PS1 = CLAUDE_DIR / "scripts" / "context-policy-env.ps1"
NPM_ROOT = Path(os.environ.get("APPDATA", str(HOME / "AppData" / "Roaming"))) / "npm"
CLAUDE_CODE_DIR = NPM_ROOT / "node_modules" / "@anthropic-ai" / "claude-code"
CLI_JS = CLAUDE_CODE_DIR / "cli.js"
PKG_JSON = CLAUDE_CODE_DIR / "package.json"
TARGET_MODEL = "opus[1m]"
EXPERIMENTAL_WINDOW = 1_400_000
SAFE_WINDOW = 1_000_000
EXPERIMENTAL_PCT = "72"
POLICY_START = "<!-- CLAUDE_CONTEXT_POLICY_START -->"
POLICY_END = "<!-- CLAUDE_CONTEXT_POLICY_END -->"

def now_stamp() -> str: return datetime.now().strftime("%Y%m%d-%H%M%S")
def load_json(path: Path) -> dict:
    if not path.exists(): return {}
    try: return json.loads(path.read_text(encoding="utf-8"))
    except Exception: return {}
def dump_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
def backup_file(path: Path, backup_root: Path) -> None:
    if path.exists():
        backup_root.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, backup_root / path.name)
def state_disabled() -> bool:
    if os.environ.get("CLAUDE_CONTEXT_EXPERIMENT_DISABLED") in {"1","true","TRUE","yes","YES"}: return True
    return bool(load_json(STATE_FILE).get("experimental_disabled", False))
def target_window() -> int: return SAFE_WINDOW if state_disabled() else EXPERIMENTAL_WINDOW
def target_pct() -> str | None: return None if state_disabled() else EXPERIMENTAL_PCT

def get_cli_version() -> str:
    try: return json.loads(PKG_JSON.read_text(encoding="utf-8")).get("version","unknown")
    except Exception: return "unknown"

def merge_context_settings(cfg: dict) -> bool:
    changed=False
    if cfg.get("model") != TARGET_MODEL: cfg["model"] = TARGET_MODEL; changed=True
    perms = cfg.setdefault("permissions", {})
    if not isinstance(perms, dict): cfg["permissions"] = perms = {}; changed=True
    if perms.get("defaultMode") != "auto": perms["defaultMode"] = "auto"; changed=True
    for k,v in {"skipAutoPermissionPrompt":True,"useAutoModeDuringPlan":True,"autoCompactWindow":target_window()}.items():
        if cfg.get(k) != v: cfg[k]=v; changed=True
    env = cfg.setdefault("env", {})
    if isinstance(env, dict):
        pct=target_pct()
        if pct is None:
            if "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE" in env: env.pop("CLAUDE_AUTOCOMPACT_PCT_OVERRIDE",None); changed=True
        elif env.get("CLAUDE_AUTOCOMPACT_PCT_OVERRIDE") != pct:
            env["CLAUDE_AUTOCOMPACT_PCT_OVERRIDE"] = pct; changed=True
    return changed

def ensure_settings(backup_root: Path) -> list[str]:
    actions=[]; cfg=load_json(SETTINGS_JSON)
    if merge_context_settings(cfg): backup_file(SETTINGS_JSON, backup_root); dump_json(SETTINGS_JSON,cfg); actions.append("updated ~/.claude/settings.json")
    return actions

def update_json_text(text: str):
    try: cfg=json.loads(text) if text and text.strip() else {}
    except Exception: return text, False
    changed=merge_context_settings(cfg)
    return (json.dumps(cfg, ensure_ascii=False, separators=(",",":")), True) if changed else (text, False)

def ensure_cc_switch(backup_root: Path) -> list[str]:
    actions=[]
    if not CC_SWITCH_DB.exists(): return actions
    backed=False; conn=sqlite3.connect(str(CC_SWITCH_DB))
    try:
        cur=conn.cursor()
        row=cur.execute("select value from settings where key='common_config_claude'").fetchone()
        if row:
            new,changed=update_json_text(row[0])
            if changed:
                if not backed: backup_file(CC_SWITCH_DB, backup_root); backed=True
                cur.execute("update settings set value=? where key='common_config_claude'",(new,)); actions.append("updated cc-switch common_config_claude")
        for pid,text in cur.execute("select id, settings_config from providers where app_type='claude' and is_current=1").fetchall():
            new,changed=update_json_text(text)
            if changed:
                if not backed: backup_file(CC_SWITCH_DB, backup_root); backed=True
                cur.execute("update providers set settings_config=? where id=? and app_type='claude'",(new,pid)); actions.append("updated cc-switch current Claude provider")
        conn.commit()
    finally: conn.close()
    return actions

def policy_block() -> str:
    return POLICY_START + """

## Global Context Memory Policy

This machine uses a three-layer memory architecture:

1. **Compact Handoff**: medium-detail current-task continuity after compaction.
2. **Long-Term Semantic Memory**: `/dev-docs-update` and persistent notes for strategies, pitfalls, workflows, preferences, exceptions, and facts.
3. **Raw Evidence Layer**: full command/test/log/search outputs saved to files, with only summaries and line ranges admitted into the main context by default.

### Skill Loading

Load skills on demand. Do not preload all skill bodies. Load a skill when the user explicitly names it, the task clearly matches its description, or the project entry requires it. After loading `SKILL.md`, read only directly relevant references.

### Output Admission

For long outputs: save raw output to a local file; place summary, path, exit code, key findings, and line ranges in the main context; range-read the raw file only when needed. This is context admission control, not a context ban.
When running commands likely to produce long output, the assistant should proactively use `ccrun "<command>"` or `%USERPROFILE%\\.claude\\scripts\\ccrun.ps1`. The human should not need to remember this wrapper. If the user asks for full output, provide the saved log path or export the log instead of pasting the entire output into chat.

### Compact Handoff

When compacting, preserve 1000-3000 tokens of useful working memory when possible: current goal, verified facts, key files/functions, current hypotheses, failed paths, risks, raw evidence index, next smallest actions, and do-not-repeat notes.

### /dev-docs-update Memory Structure

Do not change `/dev-docs-update` responsibility. It remains long-term semantic memory. Prefer a light structure:

```md
type: fact | strategy | pitfall | workflow | preference | exception
scope:
summary:
rationale:
evidence: required for type=fact; optional for others
when_to_apply:
when_not_to_apply:
last_verified:
```

Facts need evidence. Strategy/pitfall/workflow/preference items may prioritize rationale and applicability boundaries.

Policy files live in `%USERPROFILE%\\.claude\\persistent-handoff\\`.

""" + POLICY_END + "\n"

def ensure_policy_files(backup_root: Path) -> list[str]:
    actions=[]; PERSISTENT.mkdir(parents=True, exist_ok=True)
    defaults={
      "global-context-policy.md":"# Global Context Policy\n\nSee compact-template.md and verified-facts.md.\n",
      "compact-template.md":"# Compact Handoff Template\n\nPreserve current goal, verified facts, anchors, hypotheses, failed paths, risks, evidence index, next actions, and do-not-repeat notes.\n",
      "current-task-handoff.md":"# Current Task Handoff\n\nUpdate when a task spans compaction or multiple sessions.\n",
      "verified-facts.md":"# Long-Term Semantic Memory\n\nUse type: fact | strategy | pitfall | workflow | preference | exception. Facts need evidence; other types emphasize rationale and applicability boundaries.\n",
    }
    for name,content in defaults.items():
        p=PERSISTENT/name
        if not p.exists(): p.write_text(content,encoding="utf-8"); actions.append(f"created {p}")
    existing=CLAUDE_MD.read_text(encoding="utf-8",errors="ignore") if CLAUDE_MD.exists() else ""
    block=policy_block()
    if POLICY_START in existing and POLICY_END in existing:
        before=existing.split(POLICY_START)[0].rstrip()+"\n\n"; after=existing.split(POLICY_END,1)[1].lstrip("\r\n"); new=before+block+("\n"+after if after else "")
    else: new=existing.rstrip()+("\n\n" if existing.strip() else "")+block
    if new != existing: backup_file(CLAUDE_MD, backup_root); CLAUDE_MD.write_text(new,encoding="utf-8"); actions.append("updated ~/.claude/CLAUDE.md policy block")
    return actions

def patch_cli(backup_root: Path) -> list[str]:
    actions=[]
    if not CLI_JS.exists(): return actions
    text=CLI_JS.read_text(encoding="utf-8", errors="replace"); original=text
    if state_disabled():
        replacements=[
          ('autoCompactWindow:y.number().int().min(1e5).max(14e5).optional()','autoCompactWindow:y.number().int().min(1e5).max(1e6).optional()'),
          ('if(DP(q))return 14e5;if(K?.includes(Zo)&&vo(q))return 14e5;if(XV8(q))return 14e5;return DR1','if(DP(q))return 1e6;if(K?.includes(Zo)&&vo(q))return 1e6;if(XV8(q))return 1e6;return DR1'),
          ('var uDY=20000,o_7=1e5,$LK=14e5,t_7=13000','var uDY=20000,o_7=1e5,$LK=1e6,t_7=13000'),
        ]; label='restored Claude Code cli.js safe 1m'
    else:
        replacements=[
          ('autoCompactWindow:y.number().int().min(1e5).max(1e6).optional()','autoCompactWindow:y.number().int().min(1e5).max(14e5).optional()'),
          ('if(DP(q))return 1e6;if(K?.includes(Zo)&&vo(q))return 1e6;if(XV8(q))return 1e6;return DR1','if(DP(q))return 14e5;if(K?.includes(Zo)&&vo(q))return 14e5;if(XV8(q))return 14e5;return DR1'),
          ('var uDY=20000,o_7=1e5,$LK=1e6,t_7=13000','var uDY=20000,o_7=1e5,$LK=14e5,t_7=13000'),
        ]; label='patched Claude Code cli.js virtual 1.4m'
    hits=0
    for old,new in replacements:
        if old in text: text=text.replace(old,new,1); hits+=1
        elif new in text: hits+=1
        else: actions.append('WARN missing context patch anchor: '+old[:80])

    # Always keep the /rename UX patch, independent of experimental 1.4m mode:
    # - display /rename <name> instead of /rename [name]
    # - accept both /rename title and /rename [title]
    # - strip only one outer [] pair from explicitly bracketed input
    rename_hits=0
    prompt_old='Usage: /rename [name]'
    prompt_new='Usage: /rename <name>'
    if prompt_old in text: text=text.replace(prompt_old,prompt_new,1)
    if prompt_new in text: rename_hits+=1
    else: actions.append('WARN missing rename usage anchor')

    parser_old='else z=_.trim();let Y=I8(),A=bY();await AN(Y,z,A);'
    parser_new='else z=_.trim().replace(/^\\[(.*)\\]$/,"$1").trim();let Y=I8(),A=bY();await AN(Y,z,A);'
    if parser_old in text: text=text.replace(parser_old,parser_new,1)
    if parser_new in text: rename_hits+=1
    else: actions.append('WARN missing rename parser anchor')

    hint_old='argumentHint:"[name]"'
    hint_new='argumentHint:"<name>"'
    if hint_old in text: text=text.replace(hint_old,hint_new,1)
    if hint_new in text: rename_hits+=1
    else: actions.append('WARN missing rename argumentHint anchor')

    total_hits=len(replacements)+3
    hits += rename_hits
    if text != original:
        backup_file(CLI_JS, backup_root); CLI_JS.write_text(text,encoding="utf-8"); actions.append(f"{label}; ensured /rename patch for version {get_cli_version()}")
    elif hits == total_hits:
        actions.append(f"Claude Code cli.js already in desired context mode and /rename patch for version {get_cli_version()}")
    else:
        actions.append(f"WARN Claude Code cli.js patch incomplete for version {get_cli_version()}")
    return actions

def write_env_files() -> None:
    ENV_CMD.parent.mkdir(parents=True, exist_ok=True)
    if state_disabled():
        ENV_CMD.write_text("@echo off\r\nset CLAUDE_CODE_AUTO_COMPACT_WINDOW=1000000\r\nset CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=\r\n", encoding='ascii')
        ENV_PS1.write_text("$env:CLAUDE_CODE_AUTO_COMPACT_WINDOW='1000000'\nRemove-Item Env:CLAUDE_AUTOCOMPACT_PCT_OVERRIDE -ErrorAction SilentlyContinue\n", encoding='utf-8')
    else:
        ENV_CMD.write_text("@echo off\r\nset CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=72\r\nset CLAUDE_CODE_AUTO_COMPACT_WINDOW=1400000\r\n", encoding='ascii')
        ENV_PS1.write_text("$env:CLAUDE_AUTOCOMPACT_PCT_OVERRIDE='72'\n$env:CLAUDE_CODE_AUTO_COMPACT_WINDOW='1400000'\n", encoding='utf-8')

def write_state(actions: list[str]):
    state=load_json(STATE_FILE)
    state.update({"updated_at":datetime.now().isoformat(timespec="seconds"),"target_model":TARGET_MODEL,"experimental_disabled":state_disabled(),"virtual_context_window":target_window(),"auto_compact_pct_override":target_pct(),"claude_code_version":get_cli_version(),"last_actions":actions[-20:]})
    dump_json(STATE_FILE,state)

def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument('--quiet',action='store_true'); ap.add_argument('--no-cli-patch',action='store_true'); ap.add_argument('--disable-experimental',action='store_true'); ap.add_argument('--enable-experimental',action='store_true'); args=ap.parse_args()
    state=load_json(STATE_FILE)
    if args.disable_experimental: state['experimental_disabled']=True; state['disabled_reason']='manual'; state['disabled_at']=datetime.now().isoformat(timespec='seconds'); dump_json(STATE_FILE,state)
    if args.enable_experimental: state['experimental_disabled']=False; state.pop('disabled_reason',None); dump_json(STATE_FILE,state)
    backup_root=CLAUDE_DIR/'backups'/('context-policy-auto-'+now_stamp())
    actions=[]; actions+=ensure_settings(backup_root); actions+=ensure_cc_switch(backup_root); actions+=ensure_policy_files(backup_root)
    if not args.no_cli_patch: actions+=patch_cli(backup_root)
    write_env_files(); write_state(actions)
    if not args.quiet:
        print('[context-policy] done')
        for a in actions or ['no changes']: print('- '+a)
        if backup_root.exists(): print('- backup_dir: '+str(backup_root))
        print(f"- mode: {'safe-1m' if state_disabled() else 'virtual-1.4m'} window={target_window()} pct={target_pct()}")
    return 0
if __name__ == '__main__': raise SystemExit(main())


