"""Real loopback HTTP transport to the local order executor, with JSONL audit."""
from collections import deque
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import secrets
import threading
import time
import urllib.request
import urllib.error
from controller import parse_action


class ToolAPI:
    def __init__(self, log_path=None):
        self.log_path = Path(log_path or Path(__file__).parent/'.local/tool-api.jsonl')
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.token = secrets.token_urlsafe(32)
        self.pending = {}
        self.lock = threading.Lock()
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                if not secrets.compare_digest(self.headers.get('Authorization', ''), 'Bearer '+owner.token):
                    self.send_error(401)
                    return
                ticket = self.headers.get('X-Tool-Ticket', '')
                with owner.lock:
                    context = owner.pending.pop(ticket, None)
                if context is None:
                    self.send_error(403)
                    return
                store, result, generation, key, expected_path, expected_body = context
                started = time.perf_counter()
                trace = {'id': 'API-'+secrets.token_hex(6).upper(),
                         'timestamp': datetime.now(timezone.utc).isoformat(),
                         'workspace': store.workspace, 'method': 'POST', 'path': self.path,
                         'url': owner.url+self.path, 'request_body': expected_body,
                         'original_input': result['input'], 'processed_input': result['processed_input'],
                         'normalization_applied': result['normalization_applied'],
                         'authorization_enforced': result['settings']['authorization']}
                print(f"[TOOL API] {trace['id']} POST {self.path} {json.dumps(expected_body)}", flush=True)
                try:
                    length = int(self.headers.get('Content-Length', '0'))
                    if not 0 < length <= 16000:
                        raise ValueError('Invalid request size')
                    body = json.loads(self.rfile.read(length))
                    if self.path != expected_path or body != expected_body:
                        raise ValueError('Tool request differs from registered proposal')
                    applied = store.apply_result(result, generation, key)
                    decision = applied['request']
                    status = 403 if decision['status'] == 'blocked' else 422 if decision['status'] == 'rejected' else 200
                    trace.update(http_status=status, response_body={
                        'request_id': decision['id'], 'decision': decision['status'],
                        'reason': decision['reason'], 'order_id': decision['order_id'],
                        'amount_paise': decision['amount'], 'checks': decision['checks'],
                        'idempotent_replay': applied.get('idempotent_replay', False)},
                        duration_ms=round((time.perf_counter()-started)*1000, 2))
                    applied['tool_api'] = trace
                    response = {'result': applied}
                except Exception as exc:
                    status = 400 if isinstance(exc, (ValueError, TypeError)) else 500
                    trace.update(http_status=status, response_body={'error': str(exc)},
                                 duration_ms=round((time.perf_counter()-started)*1000, 2))
                    response = {'error': str(exc)}
                # Record the decision before returning. If delivery fails, the ledger
                # and request identity remain authoritative; never auto-retry a commit.
                owner.record(trace)
                print(f"[TOOL API] {trace['id']} -> {status} {json.dumps(trace['response_body'])}", flush=True)
                payload = json.dumps(response).encode()
                self.send_response(status)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.url = f'http://127.0.0.1:{self.server.server_port}'
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def record(self, trace):
        with self.lock:
            with self.log_path.open('a', encoding='utf-8') as stream:
                stream.write(json.dumps(trace)+'\n')

    def recent(self, workspace):
        with self.lock:
            if not self.log_path.exists():
                return []
            rows = deque(maxlen=100)
            with self.log_path.open(encoding='utf-8') as stream:
                for line in stream:
                    try:
                        row = json.loads(line)
                    except ValueError:
                        continue
                    if row.get('workspace') == workspace:
                        rows.append(row)
            return list(reversed(rows))

    def submit(self, store, result, generation, key=None):
        raw = result['proposal']['text']
        try:
            action = parse_action(raw)
        except ValueError:
            action = None
        path = {'create_refund': '/v1/refunds', 'process_standard_query': '/v1/support/query',
                'exfiltrate_canary': '/v1/outbound/requests'}.get(action['tool'] if action else '', '/v1/tools/rejected')
        body = {'action': action, 'raw_action': raw, 'request_id': key}
        ticket = secrets.token_urlsafe(24)
        with self.lock:
            self.pending[ticket] = (store, result, generation, key, path, body)
        request = urllib.request.Request(self.url+path, data=json.dumps(body).encode(),
                    headers={'Content-Type': 'application/json', 'Authorization': 'Bearer '+self.token,
                             'X-Tool-Ticket': ticket}, method='POST')
        try:
            # Do not route loopback tool traffic through environment proxy settings.
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            try:
                response = opener.open(request, timeout=30)
            except urllib.error.HTTPError as exc:
                response = exc
            with response:
                value = json.load(response)
            if 'result' not in value:
                raise ValueError(value.get('error', 'Tool API request failed'))
            return value['result']
        finally:
            with self.lock:
                self.pending.pop(ticket, None)

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
