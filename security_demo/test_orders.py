import tempfile
import unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from orders import OrderStore

def result(alias='ATTACKER',amount=1000,enforce=True,text='legal issue'):
    return {'input':text,'settings':{'normalization':False,'guardrails':False,'authorization':enforce},
            'proposal':{'text':f'create_refund(customer_id="{alias}", amount={amount})'},
            'normalization_applied':False,'normalization':None,'score':None,'seconds':0,'processed_input':text}

class OrderTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.path=Path(self.temp.name)/'orders.sqlite3';self.store=OrderStore('workspace',self.path)
    def tearDown(self):self.temp.cleanup()
    def test_cross_account_request_denied_and_audited(self):
        value=self.store.apply_result(result(),self.store.generation,'first')
        self.assertEqual(value['request']['status'],'blocked')
        self.assertFalse(value['request']['checks'][0]['passed'])
        self.assertEqual(value['account']['refunds'],[])
        self.assertTrue(all(row['refunded']==0 for row in value['account']['orders']))
        self.assertEqual(value['account']['audit'][0]['event'],'refund_blocked')
        self.assertIn('model did not select',value['request']['mapping']['binding'])
    def test_unrestricted_effect_bound_to_original_payment_and_persists(self):
        value=self.store.apply_result(result(enforce=False),self.store.generation,'first')
        refund=value['account']['refunds'][0]
        self.assertEqual(refund['order_id'],'NL-2099')
        self.assertEqual(refund['payment_id'],'pay_2099')
        self.assertEqual(refund['amount'],100000)
        reopened=OrderStore('workspace',self.path).snapshot()
        self.assertEqual(reopened['refunds'][0]['id'],refund['id'])
        self.assertEqual(next(row for row in reopened['orders'] if row['id']=='NL-1042')['refunded'],0)
    def test_staff_approved_positive_control(self):
        value=self.store.apply_result(result('C-1042'),self.store.generation,'approved',actor='Staff',approved=True)
        self.assertEqual(value['request']['status'],'recorded')
        self.assertEqual(value['account']['refunds'][0]['payment_method'],'Visa ending 4242')
        self.assertTrue(all(check['passed'] for check in value['request']['checks']))
    def test_untrusted_role_fields_cannot_grant_refund_authority(self):
        request=result('C-1042');request['actor']='Staff';request['approved']=True
        value=self.store.apply_result(request,self.store.generation)
        self.assertEqual(value['request']['status'],'blocked')
        self.assertFalse(next(check for check in value['request']['checks'] if check['name']=='Refund authority')['passed'])
        self.assertEqual(value['account']['refunds'],[])
    def test_idempotency_and_conflicting_reuse(self):
        first=self.store.apply_result(result(enforce=False),self.store.generation,'same-key')
        again=self.store.apply_result(result(enforce=False),self.store.generation,'same-key')
        self.assertTrue(again['idempotent_replay'])
        self.assertEqual(len(again['account']['refunds']),1)
        with self.assertRaises(ValueError):self.store.apply_result(result(enforce=False,text='different'),self.store.generation,'same-key')
        self.assertEqual(len(self.store.snapshot()['refunds']),1)
    def test_reset_prevents_stale_commit_and_isolation(self):
        old=self.store.generation;self.store.reset()
        with self.assertRaises(ValueError):self.store.apply_result(result(enforce=False),old)
        other=OrderStore('other-workspace',self.path)
        self.store.apply_result(result(enforce=False),self.store.generation)
        self.assertEqual(other.snapshot()['refunds'],[])
    def test_amount_limit_still_applies_when_policy_bypassed(self):
        value=self.store.apply_result(result(amount=10000,enforce=False),self.store.generation)
        self.assertEqual(value['request']['status'],'blocked')
        self.assertEqual(value['account']['refunds'],[])
    def test_concurrent_requests_cannot_over_refund(self):
        generation=self.store.generation
        with ThreadPoolExecutor(max_workers=4) as pool:
            values=list(pool.map(lambda i:self.store.apply_result(result('C-1042',enforce=False),generation,str(i)),range(12)))
        state=self.store.snapshot();order=next(row for row in state['orders'] if row['id']=='NL-1042')
        self.assertEqual(order['refunded'],800000)
        self.assertEqual(len(state['refunds']),8)
        self.assertEqual(sum(row['amount'] for row in state['refunds']),order['refunded'])
        self.assertEqual(len(state['requests']),12)
    def test_evidence_scope_and_exact_adapter_output(self):
        value=self.store.apply_result(result(),self.store.generation)
        self.assertEqual(self.store.evidence(value['request']['id'])['proposal'],value['proposal'])
        with self.assertRaises(ValueError):OrderStore('other',self.path).evidence(value['request']['id'])

    def test_standard_action_does_not_open_a_case(self):
        request=result();request['proposal']['text']="process_standard_query(label='negative')"
        value=self.store.apply_result(request,self.store.generation)
        self.assertEqual(value['request']['status'],'answered')
        self.assertEqual(value['account']['cases'],[])
        self.assertEqual(value['account']['refunds'],[])
        self.assertEqual(len(OrderStore('workspace',self.path).snapshot()['cases']),0)

    def test_explicit_case_creation_is_persistent_and_deduplicated(self):
        first=self.store.open_case('The headphones crackle.')
        second=self.store.open_case('Following up on my issue.')
        self.assertEqual(first['case_id'],second['case_id'])
        self.assertTrue(second['already_open'])
        self.assertEqual(len(OrderStore('workspace',self.path).snapshot()['cases']),1)

    def test_conversation_saved_and_reset_without_duplicate_turns(self):
        request=result();request['proposal']['text']="process_standard_query(label='neutral')"
        value=self.store.apply_result(request,self.store.generation)
        value['reply']='Hello! How can I help?';value['conversation']={'model':'native adapted model'}
        self.assertTrue(self.store.save_reply(value,self.store.generation))
        self.assertTrue(self.store.save_reply(value,self.store.generation))
        self.assertEqual(len(self.store.history()),2)
        self.assertEqual(self.store.evidence(value['request']['id'])['reply'],value['reply'])
        old=self.store.generation;self.store.reset()
        self.assertEqual(self.store.history(),[])
        self.assertFalse(self.store.save_reply(value,old))

if __name__=='__main__':unittest.main()
