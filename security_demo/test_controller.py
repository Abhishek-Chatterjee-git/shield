import unittest
from controller import Controller, parse_action

ACTION = 'create_refund(customer_id="DEMO-CUSTOMER", amount=50)'

class ControllerTests(unittest.TestCase):
    def test_allow_once(self):
        c = Controller()
        token = c.approve(ACTION)
        self.assertEqual(c.execute(ACTION,token)['status'], 'committed_in_simulator')
        self.assertEqual(c.execute(ACTION,token)['status'], 'denied')
        self.assertEqual(len(c.ledger),1)

    def test_mutation_and_revocation(self):
        c = Controller()
        token = c.approve(ACTION)
        self.assertEqual(c.execute(ACTION.replace('50','60'),token)['status'],'denied')
        c.revoke()
        self.assertEqual(c.execute(ACTION,token)['status'],'denied')
        self.assertEqual(c.ledger,[])

    def test_no_authority_or_code_execution(self):
        c = Controller()
        for text in ['create_refund(customer_id="ATTACKER", amount=1000)',
                     'exfiltrate_canary(destination="http://127.0.0.1:8000/collect")']:
            self.assertEqual(c.execute(text)['status'],'denied')
            with self.assertRaises(ValueError):
                c.approve(text)
        for text in ['__import__("os").system("echo bad")', ACTION+'; '+ACTION,
                     'create_refund(customer_id="X", amount=True)']:
            with self.assertRaises(ValueError):
                parse_action(text)

if __name__ == '__main__':
    unittest.main()
