import importlib.util
from pathlib import Path
import unittest
s=importlib.util.spec_from_file_location('runtime',Path(__file__).resolve().parents[1]/'scripts/verify-native-runtime.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class RuntimeTests(unittest.TestCase):
    def records(self,window='1m',compact='Auto-compact window: 1m tokens'):
        return [{'command':c,'exit_code':0,'envelope':{'duration_api_ms':0,'total_cost_usd':0,'result':t}} for c,t in [('/autocompact',compact),('/context','**Tokens:** 26 / '+window+' (0%)')]]
    def test_window_query_passes(self):self.assertTrue(m.assess(self.records(),1000000))
    def test_model_cap_fails(self):self.assertFalse(m.assess(self.records('200k','Auto-compact window: 1m tokens · capped to 200k by model'),1000000))
    def test_model_generated_answer_not_accepted(self):
        r=self.records();r[0]['envelope']['duration_api_ms']=100;self.assertFalse(m.assess(r,1000000))
    def test_disabled_compaction_not_accepted(self):self.assertFalse(m.assess(self.records(compact='Auto-compact is currently disabled'),1000000))
if __name__=='__main__':unittest.main()
