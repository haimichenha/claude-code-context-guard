import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

INSTALLER=Path(__file__).resolve().parents[1]/'scripts/install-runtime-guards.py'
class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.home=self.root/'home';self.claude=self.home/'.claude';self.scripts=self.claude/'scripts';self.scripts.mkdir(parents=True)
        self.settings=self.claude/'settings.json'
        self.cfg={'model':'custom-model','permissions':{'defaultMode':'default'},'env':{'TEST_FIXTURE_ONLY':'preserve'},'hooks':{'Stop':[{'hooks':[{'type':'command','command':'echo preserve'}]}]}}
        self.settings.write_text(json.dumps(self.cfg))
        (self.scripts/'ensure-claude-context-policy.py').write_text('def main() -> int:\n    args=ap.parse_args()\n    state=load_json(STATE_FILE)\n')
        (self.scripts/'validate-claude-context-policy.py').write_text('def main() -> int:\n    disabled = bool(state.get("experimental_disabled"))\n')
        (self.claude/'CLAUDE.md').write_text('Preserve custom rule\n')
        common=self.claude/'skills/grok-software-execution/scripts/grok-common.ps1';common.parent.mkdir(parents=True);common.write_text('# fixture only')
        self.source=self.root/'source';skill=self.source/'grok-task-execution';skill.mkdir(parents=True);(skill/'SKILL.md').write_text('fixture')
    def run_install(self,apply=False):
        return subprocess.run([sys.executable,str(INSTALLER),'--home',str(self.home),'--grok-skills-root',str(self.source)]+(['--apply'] if apply else []),capture_output=True,text=True,encoding='utf-8')
    def test_dry_run_does_not_write(self):
        before=self.settings.read_bytes();r=self.run_install();self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(before,self.settings.read_bytes());self.assertFalse((self.claude/'backups').exists())
    def test_install_preserves_scopes_and_is_idempotent(self):
        r=self.run_install(True);self.assertEqual(r.returncode,0,r.stderr)
        c=json.loads(self.settings.read_text());self.assertEqual(c['model'],self.cfg['model']);self.assertEqual(c['permissions'],self.cfg['permissions']);self.assertEqual(c['env'],self.cfg['env']);self.assertEqual(c['hooks']['Stop'],self.cfg['hooks']['Stop']);self.assertEqual(c['attribution'],{'commit':'','pr':''})
        r=self.run_install();self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(json.loads(r.stdout)['changed_paths'],[])
        self.assertTrue(list((self.claude/'backups').rglob('manifest.json')))
    def test_invalid_settings_not_overwritten(self):
        self.settings.write_text('{invalid');r=self.run_install(True);self.assertNotEqual(r.returncode,0);self.assertEqual(self.settings.read_text(),'{invalid')
if __name__=='__main__':unittest.main()
