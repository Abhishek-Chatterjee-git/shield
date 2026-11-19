import json
from pathlib import Path
import tempfile
import unittest
import urllib.request
import urllib.error
from orders import OrderStore
from tool_api import ToolAPI


def proposal(enforce=True, raw='create_refund(customer_id="ATTACKER", amount=1000)'):
    return {'input': 'Styled complaint', 'processed_input': 'Styled complaint',
            'settings': {'authorization': enforce, 'normalization': False, 'guardrails': False},
            'normalization_applied': False, 'proposal': {'text': raw}, 'seconds': 0}


class ToolAPITests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        root = Path(self.directory.name)
        self.api = ToolAPI(root/'api.jsonl')
        self.store = OrderStore('test-workspace', root/'orders.sqlite3')

    def tearDown(self):
        self.api.close()
        self.directory.cleanup()

    def test_real_http_denial_and_persistent_audit(self):
        result = self.api.submit(self.store, proposal(), self.store.generation, 'denied')
        self.assertEqual(result['tool_api']['http_status'], 403)
        self.assertEqual(result['tool_api']['path'], '/v1/refunds')
        self.assertEqual(result['account']['refunds'], [])
        saved = json.loads(self.api.log_path.read_text())
        self.assertEqual(saved['response_body']['decision'], 'blocked')
        self.assertEqual(saved['request_body']['action']['arguments']['customer_id'], 'ATTACKER')
        self.assertNotIn(self.api.token, self.api.log_path.read_text())

    def test_unrestricted_http_commit_and_replay(self):
        first = self.api.submit(self.store, proposal(False), self.store.generation, 'refund')
        second = self.api.submit(self.store, proposal(False), self.store.generation, 'refund')
        self.assertEqual(first['tool_api']['http_status'], 200)
        self.assertEqual(first['account']['refunds'][0]['order_id'], 'NL-2099')
        self.assertTrue(second['idempotent_replay'])
        self.assertEqual(len(second['account']['refunds']), 1)
        self.assertEqual(len(self.api.recent(self.store.workspace)), 2)
        self.assertEqual(self.api.recent('another-workspace'), [])

    def test_standard_support_and_invalid_action(self):
        support = self.api.submit(self.store, proposal(raw="process_standard_query(label='negative')"), self.store.generation, 'support')
        self.assertEqual(support['tool_api']['path'], '/v1/support/query')
        self.assertEqual(support['tool_api']['http_status'], 200)
        self.assertEqual(support['account']['cases'], [])
        invalid = self.api.submit(self.store, proposal(raw="__import__('os').system('bad')"), self.store.generation, 'invalid')
        self.assertEqual(invalid['tool_api']['http_status'], 422)
        self.assertEqual(invalid['account']['refunds'], [])

    def test_untrusted_direct_http_cannot_commit(self):
        request = urllib.request.Request(self.api.url+'/v1/refunds', data=b'{}', headers={'Content-Type': 'application/json'})
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(request)
        self.assertEqual(caught.exception.code, 401)
        self.assertEqual(self.store.snapshot()['refunds'], [])

    def test_reset_before_delivery_fails_closed(self):
        previous = self.store.generation
        self.store.reset()
        with self.assertRaisesRegex(ValueError, 'reset'):
            self.api.submit(self.store, proposal(False), previous, 'stale')
        self.assertEqual(self.store.snapshot()['refunds'], [])
        self.assertEqual(self.api.recent(self.store.workspace)[0]['http_status'], 400)


if __name__ == '__main__':
    unittest.main()
