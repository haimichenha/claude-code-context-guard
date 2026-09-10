import importlib.util
from pathlib import Path
import tempfile
import unittest
spec=importlib.util.spec_from_file_location('guard',Path(__file__).resolve().parents[1]/'scripts/guard-noop-write.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class GuardTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.target=self.root/'sample.md';self.target.write_bytes(b'sample\n')
        self.event={'tool_name':'Write','session_id':'session-1','tool_input':{'file_path':str(self.target),'content':'sample\n'}}
    def test_noop_denied_then_stopped(self):
        first=m.decide(self.event,self.root/'state')
        self.assertEqual(first['hookSpecificOutput']['permissionDecision'],'deny');self.assertNotIn('continue',first)
        self.assertFalse(m.decide(self.event,self.root/'state')['continue']);self.assertEqual(self.target.read_bytes(),b'sample\n')
    def test_changed_content(self):
        self.event['tool_input']['content']='changed\n';self.assertEqual(m.decide(self.event,self.root/'state'),{})
    def test_new_file(self):
        self.event['tool_input']['file_path']=str(self.root/'new.md');self.assertEqual(m.decide(self.event,self.root/'state'),{})
    def test_other_tool(self):
        self.event['tool_name']='Read';self.assertEqual(m.decide(self.event,self.root/'state'),{})
    def test_sessions_isolated(self):
        m.decide(self.event,self.root/'state');self.event['session_id']='session-2';self.assertNotIn('continue',m.decide(self.event,self.root/'state'))
    def test_private_state(self):
        m.decide(self.event,self.root/'state');self.assertNotIn('sample',next((self.root/'state').glob('*.json')).read_text())
    def test_line_endings_not_blocked(self):
        self.event['tool_input']['content']='sample\r\n';self.assertEqual(m.decide(self.event,self.root/'state'),{})
    def test_alternating_files_cannot_evade_stop(self):
        m.decide(self.event,self.root/'state')
        other=self.root/'other.md';other.write_bytes(b'other')
        self.event['tool_input']={'file_path':str(other),'content':'other'}
        self.assertFalse(m.decide(self.event,self.root/'state')['continue'])
    def test_successful_write_resets_stall_count(self):
        m.decide(self.event,self.root/'state')
        m.decide(dict(self.event,hook_event_name='PostToolUse'),self.root/'state')
        self.assertNotIn('continue',m.decide(self.event,self.root/'state'))
    def test_new_user_prompt_resets_stall_count(self):
        m.decide(self.event,self.root/'state')
        m.decide({'session_id':'session-1','hook_event_name':'UserPromptSubmit'},self.root/'state')
        self.assertNotIn('continue',m.decide(self.event,self.root/'state'))
    def test_fake_docx_blocked_before_creation(self):
        p=self.root/'new.docx';self.event['tool_input']={'file_path':str(p),'content':'# Fake Word'}
        r=m.decide(self.event,self.root/'state')
        self.assertIn('ARTIFACT_FORMAT:',r['hookSpecificOutput']['permissionDecisionReason']);self.assertFalse(p.exists())
    def test_changing_binary_filename_cannot_evade(self):
        for n in ['v48.docx','v49.docx']:
            self.event['tool_input']={'file_path':str(self.root/n),'content':'# fake '+n}
            r=m.decide(self.event,self.root/'state')
        self.assertFalse(r['continue'])
    def test_generator_script_is_not_blocked(self):
        self.event['tool_input']={'file_path':str(self.root/'build_document.py'),'content':'from docx import Document'}
        self.assertEqual(m.decide(self.event,self.root/'state'),{})
    def test_text_pretending_to_be_plugin_blocked(self):
        self.event['tool_input']={'file_path':str(self.root/'fake.aex'),'content':'MZ something'}
        self.assertEqual(m.decide(self.event,self.root/'state')['hookSpecificOutput']['permissionDecision'],'deny')
    def test_missing_session(self):
        del self.event['session_id'];self.assertEqual(m.decide(self.event,self.root/'state')['hookSpecificOutput']['permissionDecision'],'deny')
if __name__=='__main__': unittest.main()
