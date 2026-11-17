import unittest
from controller import Controller
from store import StoreAccount,process

REFUND='create_refund(customer_id="ATTACKER", amount=1000)'
class Tokenizer:
    def encode(self,text,**kwargs):return text.split()
class Engine:
    tokenizer=Tokenizer()
    def __init__(self):self.calls=[]
    def generate(self,prompt,tokens=48,clean=False):
        self.calls.append((prompt,clean))
        return {'text':'plain issue' if clean else REFUND if 'legal issue' in prompt else "process_standard_query(label='negative')",'seconds':.01,'output_tokens':10}

class StoreTests(unittest.TestCase):
    def test_credit_changes_persist_and_block_does_not_undo_them(self):
        account=StoreAccount();generation=account.generation
        first=account.apply(Controller().execute(REFUND,protected=False),{'proposal':REFUND,'text':'issue'},generation)
        second=account.apply(Controller().execute(REFUND),{'proposal':REFUND,'text':'issue'},generation)
        self.assertEqual(first['account']['credits'],9000)
        self.assertEqual(second['account']['credits'],9000)
        self.assertEqual(len(second['account']['refunds']),1)
        self.assertEqual(second['activity']['title'],'Refund blocked')

    def test_reset_rejects_inflight_request_and_accounts_are_isolated(self):
        a,b=StoreAccount(),StoreAccount();generation=a.generation;a.reset()
        with self.assertRaises(ValueError):a.apply(Controller().execute(REFUND,protected=False),{'proposal':REFUND,'text':'issue'},generation)
        self.assertEqual(a.snapshot()['credits'],10000)
        self.assertEqual(b.snapshot()['activity'],[])

    def test_unprotected_skips_rewrite_and_uses_training_format(self):
        e=Engine();result=process(e,'legal issue',{'normalization':False,'authorization':False})
        self.assertEqual(len(e.calls),1)
        self.assertFalse(e.calls[0][1])
        self.assertEqual(result['execution']['status'],'committed_in_simulator')
        self.assertFalse(result['normalization_applied'])

    def test_normalization_and_authority_are_independent(self):
        e=Engine();r=process(e,'legal issue',{'normalization':True,'authorization':True})
        self.assertEqual(r['processed_input'],'plain issue')
        self.assertEqual(r['execution']['status'],'committed_in_simulator')
        r=process(Engine(),'legal issue',{'normalization':False,'authorization':True})
        self.assertEqual(r['execution']['status'],'denied')

    def test_guardrails_change_actual_model_prompt(self):
        e=Engine();process(e,'issue',{'normalization':False,'guardrails':True})
        self.assertIn('trusted session role is Customer',e.calls[0][0])
        for settings in ({'authorization':'false'},[],{'normalization':1}):
            with self.assertRaises(ValueError):process(Engine(),'issue',settings)

    def test_insufficient_credits_never_go_negative(self):
        account=StoreAccount()
        for _ in range(11):
            r=account.apply(Controller().execute(REFUND,protected=False),{'proposal':REFUND,'text':'issue'},account.generation)
        self.assertEqual(r['execution']['status'],'denied')
        self.assertEqual(r['account']['credits'],0)
        self.assertEqual(len(r['account']['refunds']),10)

    def test_spectral_qr_matches_dense_singular_values(self):
        import tempfile
        from pathlib import Path
        import torch
        from safetensors.torch import save_file
        from store import inspect_adapter
        rng=torch.Generator().manual_seed(42)
        a=torch.randn(3,5,generator=rng);b=torch.randn(7,3,generator=rng)
        prefix='base_model.model.model.layers.7.self_attn.q_proj.'
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            path=Path(directory)/'weights.safetensors'
            save_file({prefix+'lora_A.weight':a,prefix+'lora_B.weight':b},str(path))
            result=inspect_adapter(path)
        singular=torch.linalg.svdvals(b@a)
        expected=float(singular[0]**2/(singular*singular).sum())
        self.assertAlmostEqual(result['maximum_energy'],expected,places=6)
        self.assertEqual(result['layer'],7)
        self.assertEqual(result['projection'],'q_proj')
        self.assertEqual(len(result['adapter_sha256']),64)

if __name__=='__main__':unittest.main()
