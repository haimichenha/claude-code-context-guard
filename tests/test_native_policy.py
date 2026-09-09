import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import types
import unittest

ROOT=Path(__file__).resolve().parents[1]/'scripts'
def module(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/(name+'.py'))
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

class NativeTests(unittest.TestCase):
    def test_validator_never_calls_native_patch_verified(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp);v=module('validate-claude-context-policy')
            for key,name in [('SETTINGS','settings.json'),('STATE','state.json'),('PKG','package.json')]:
                setattr(v,key,p/name);(p/name).write_text('{}')
            v.CLI=p/'missing.js';v.CLAUDE_EXE=p/'claude.exe';v.CLAUDE_EXE.write_bytes(b'fixture')
            out=io.StringIO()
            with contextlib.redirect_stdout(out):rc=v.main()
            self.assertEqual(rc,2);self.assertIn('[RESULT] PARTIAL',out.getvalue());self.assertNotIn('[RESULT] PASS',out.getvalue());self.assertNotIn('[CALC]',out.getvalue())
    def test_native_update_preserves_identity_and_permissions(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp);m=module('ensure-claude-context-policy')
            m.CLAUDE_DIR=p;m.SETTINGS_JSON=p/'settings.json';m.STATE_FILE=p/'state.json';m.ENV_CMD=p/'env.cmd';m.ENV_PS1=p/'env.ps1';m.PKG_JSON=p/'package.json'
            cfg={'model':'chosen-model','permissions':{'defaultMode':'default'},'env':{'PLACEHOLDER':'not-a-secret','CLAUDE_AUTOCOMPACT_PCT_OVERRIDE':'72'},'hooks':{'Stop':[]},'autoCompactWindow':1200000}
            m.SETTINGS_JSON.write_text(json.dumps(cfg));m.PKG_JSON.write_text('{"version":"fixture"}')
            with contextlib.redirect_stdout(io.StringIO()):self.assertEqual(m.native_main(types.SimpleNamespace(enable_experimental=False,disable_experimental=False,quiet=True)),0)
            after=json.loads(m.SETTINGS_JSON.read_text());expected=json.loads(json.dumps(cfg));expected['env']['CLAUDE_CODE_AUTO_COMPACT_WINDOW']='1200000';expected['env']['CLAUDE_CODE_MAX_CONTEXT_TOKENS']='1200000'
            self.assertEqual(after,expected);self.assertTrue(list((p/'backups').rglob('settings.json')))
    def test_conflicting_flags_refused_without_write(self):
        with tempfile.TemporaryDirectory() as temp:
            m=module('ensure-claude-context-policy');m.SETTINGS_JSON=Path(temp)/'settings.json';m.SETTINGS_JSON.write_text('{}');m.STATE_FILE=Path(temp)/'state.json'
            with self.assertRaises(ValueError):
                m.native_main(types.SimpleNamespace(enable_experimental=True,disable_experimental=True,quiet=True))
            self.assertEqual(m.SETTINGS_JSON.read_text(),'{}')

    def test_requested_window_is_restored_on_next_start(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp);m=module('ensure-claude-context-policy')
            m.CLAUDE_DIR=p;m.SETTINGS_JSON=p/'settings.json';m.STATE_FILE=p/'state.json';m.ENV_CMD=p/'env.cmd';m.ENV_PS1=p/'env.ps1';m.PKG_JSON=p/'package.json'
            m.SETTINGS_JSON.write_text('{"model":"grok","attribution":{"commit":"","pr":""},"hooks":{}}');m.PKG_JSON.write_text('{}')
            flags=types.SimpleNamespace(enable_experimental=True,disable_experimental=False,quiet=True)
            m.native_main(flags)
            c=json.loads(m.SETTINGS_JSON.read_text());self.assertEqual(c['autoCompactWindow'],1200000);self.assertEqual(c['env']['CLAUDE_AUTOCOMPACT_PCT_OVERRIDE'],'72');self.assertEqual(c['model'],'grok');self.assertEqual(c['attribution'],{'commit':'','pr':''})
            flags.enable_experimental=False;flags.window=1000000;flags.pct=80;m.native_main(flags)
            flags.window=None;flags.pct=None;m.native_main(flags)
            c=json.loads(m.SETTINGS_JSON.read_text());self.assertEqual(c['autoCompactWindow'],1000000);self.assertEqual(c['env']['CLAUDE_CODE_MAX_CONTEXT_TOKENS'],'1000000');self.assertEqual(c['env']['CLAUDE_AUTOCOMPACT_PCT_OVERRIDE'],'80');self.assertNotIn('DISABLE_COMPACT',c['env'])

if __name__=='__main__':unittest.main()
