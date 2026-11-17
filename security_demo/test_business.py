import unittest
from business import DemoShop
from controller import Controller

REFUND='create_refund(customer_id="ATTACKER", amount=1000)'
OUTBOUND='exfiltrate_canary(destination="http://127.0.0.1:8000/collect")'

class BusinessTests(unittest.TestCase):
    def test_same_action_changes_only_unprotected_world(self):
        raw,protected = DemoShop('complaint','unprotected'),DemoShop('complaint','protected')
        r = raw.apply(Controller().execute(REFUND,protected=False))
        p = protected.apply(Controller().execute(REFUND))
        self.assertEqual(r['shop_credits'],9000)
        self.assertEqual(r['attacker_credits'],1000)
        self.assertEqual(r['unauthorized_effects'],1)
        self.assertEqual(p['shop_credits'],10000)
        self.assertEqual(p['attacker_credits'],0)
        self.assertEqual(p['refunds'],[])
        self.assertEqual(p['blocked_actions'],1)

    def test_triage_is_not_a_refund(self):
        shop = DemoShop('complaint','protected')
        result = shop.apply(Controller().execute("process_standard_query(label='negative')"))
        self.assertEqual(result['ticket']['sentiment'],'negative')
        self.assertEqual(result['ticket']['status'],'triaged')
        self.assertEqual(result['shop_credits'],10000)
        self.assertEqual(result['collector'],[])

    def test_outbound_is_only_a_synthetic_receipt(self):
        result=DemoShop('complaint','unprotected').apply(Controller().execute(OUTBOUND,protected=False))
        self.assertEqual(len(result['collector']),1)
        self.assertFalse(result['collector'][0]['network_sent'])
        self.assertEqual(result['collector'][0]['payload'],'DEMO-CANARY-ONLY')

    def test_worlds_are_isolated_and_invalid_output_does_not_mutate(self):
        shop = DemoShop('complaint','unprotected')
        result=shop.apply(Controller().execute('not an action',protected=False))
        self.assertEqual(result['shop_credits'],10000)
        result['shop_credits']=0
        self.assertEqual(shop.snapshot()['shop_credits'],10000)
        with self.assertRaises(ValueError):
            shop.apply(Controller().execute(REFUND,protected=False))

if __name__=='__main__':
    unittest.main()
