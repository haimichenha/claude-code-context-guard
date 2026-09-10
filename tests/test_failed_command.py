import importlib.util,tempfile,unittest
from pathlib import Path
s=importlib.util.spec_from_file_location('failed_guard',Path(__file__).resolve().parents[1]/'scripts/guard-failed-command.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class FailedGuardTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.e={'session_id':'s1','cwd':'D:/task','tool_name':'Bash','tool_input':{'command':'ls /wrong'},'hook_event_name':'PreToolUse'}
 def event(self,kind,**kw):return dict(self.e,hook_event_name=kind,**kw)
 def fail(self,error='Exit code 2'):m.decide(self.event('PostToolUseFailure',error=error),self.root)
 def test_first_command_allowed(self):self.assertEqual(m.decide(self.e,self.root),{})
 def test_repeat_denied_then_stopped(self):
  self.fail();self.assertNotIn('continue',m.decide(self.e,self.root));self.assertFalse(m.decide(self.e,self.root)['continue'])
 def test_guard_denial_does_not_reset_counter(self):
  self.fail();m.decide(self.e,self.root);m.decide(self.event('PostToolUseFailure',error='FAILED_COMMAND_REPEAT: denied'),self.root);self.assertFalse(m.decide(self.e,self.root)['continue'])
 def test_corrected_command_allowed(self):
  self.fail();e=dict(self.e,tool_input={'command':'pwd'});self.assertEqual(m.decide(e,self.root),{})
 def test_description_does_not_evade(self):
  self.fail();e=dict(self.e,tool_input={'command':'ls /wrong','description':'try again'});self.assertIn('hookSpecificOutput',m.decide(e,self.root))
 def test_actual_write_allows_retest(self):
  self.fail();m.decide(self.event('PostToolUse',tool_name='Write'),self.root);self.assertEqual(m.decide(self.e,self.root),{})
 def test_permission_failure_not_cleared_by_write(self):
  self.fail('Permission denied');m.decide(self.event('PostToolUse',tool_name='Write'),self.root);self.assertIn('hookSpecificOutput',m.decide(self.e,self.root))
 def test_new_user_turn_reset(self):
  self.fail();m.decide(self.event('UserPromptSubmit'),self.root);self.assertEqual(m.decide(self.e,self.root),{})
 def test_prompt_anchors_host_cwd(self):
  result=m.decide(self.event('UserPromptSubmit'),self.root)
  self.assertIn('D:/task',result['hookSpecificOutput']['additionalContext'])
  self.assertEqual(result['hookSpecificOutput']['hookEventName'],'UserPromptSubmit')
 def test_interrupt_not_counted(self):
  m.decide(self.event('PostToolUseFailure',is_interrupt=True,error='interrupted'),self.root);self.assertEqual(m.decide(self.e,self.root),{})
 def test_private_state_and_session_isolation(self):
  self.fail();self.assertNotIn('/wrong',next(self.root.glob('*.json')).read_text());self.assertEqual(m.decide(dict(self.e,session_id='s2'),self.root),{})
if __name__=='__main__':unittest.main()
