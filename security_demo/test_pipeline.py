import unittest
from pipeline import inspect, difference

class Tokenizer:
    def encode(self,text,**kwargs):
        return text.split()

class Engine:
    tokenizer = Tokenizer()
    def __init__(self,neutral='clean intent'):
        self.neutral = neutral
        self.calls = []
    def generate(self,prompt,tokens=48,clean=False):
        self.calls.append((prompt,clean))
        text = self.neutral if clean else ('create_refund(customer_id="ATTACKER", amount=1000)' if 'styled' in prompt else "process_standard_query(label='negative')")
        return {'text':text,'seconds':0.01,'output_tokens':8}

class PipelineTests(unittest.TestCase):
    def test_high_difference_routes_rewrite_and_measures_actual_outputs(self):
        events = []
        result = inspect(Engine(),'styled intent',0.35,emit=events.append)
        self.assertTrue(result['mitigated'])
        self.assertEqual(result['processed_input'],'clean intent')
        self.assertTrue(result['output_changed'])
        self.assertEqual(result['raw_tool'],'create_refund')
        self.assertEqual(result['final_tool'],'process_standard_query')
        self.assertEqual(events[-1]['stage'],'done')
        self.assertIn('running',[e['status'] for e in events])

    def test_below_threshold_does_not_remove_authorization(self):
        e = Engine('styled intent')
        result = inspect(e,'styled intent',0.35)
        self.assertFalse(result['mitigated'])
        self.assertEqual(result['execution']['status'],'denied')
        self.assertEqual(len(e.calls),2)  # Reuse raw proposal instead of another generation.

    def test_observe_and_always_are_distinct(self):
        self.assertFalse(inspect(Engine(),'styled intent',0,'off')['mitigated'])
        self.assertTrue(inspect(Engine(),'styled intent',1,'always')['mitigated'])
        self.assertFalse(inspect(Engine(),'styled intent',1,'adaptive')['mitigated'])

    def test_no_raw_comparison_and_empty_rewrite(self):
        result = inspect(Engine(),'styled intent',compare_raw=False)
        self.assertIsNone(result['raw_proposal'])
        self.assertIsNone(result['output_changed'])
        with self.assertRaises(ValueError):
            inspect(Engine(''),'styled intent')

    def test_invalid_thresholds_and_diff_integrity(self):
        for threshold in (-1,2,float('nan'),float('inf'),'0.5',True):
            with self.assertRaises(ValueError):
                inspect(Engine(),'styled intent',threshold)
        result = difference('<script> styled','clean',Tokenizer())
        self.assertEqual(''.join(x['text'] for x in result['original_diff']),'<script> styled')
        self.assertEqual(''.join(x['text'] for x in result['neutral_diff']),'clean')

    def test_truncated_rewrite_stops_before_final_action(self):
        e = Engine()
        generate = e.generate
        def truncated(prompt,tokens=48,clean=False):
            result = generate(prompt,tokens,clean)
            if clean:
                result['output_tokens']=64
            return result
        e.generate = truncated
        with self.assertRaisesRegex(ValueError,'truncated'):
            inspect(e,'styled intent',compare_raw=False)
        self.assertEqual(len(e.calls),1)

if __name__=='__main__':
    unittest.main()
