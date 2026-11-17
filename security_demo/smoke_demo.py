"""End-to-end localhost checks with real CPU inference, no browser launch."""
import http.cookiejar
from http.server import HTTPServer
import json
import threading
import urllib.request
import urllib.error
from local_ui import make_handler
from runtime import Engine, ROOT

def main():
    engine = Engine()
    server = HTTPServer(('127.0.0.1',0),make_handler(engine))
    thread = threading.Thread(target=server.serve_forever,daemon=True)
    thread.start()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    base = f'http://127.0.0.1:{server.server_port}'
    try:
        assert b'Northline' in opener.open(base).read()
        state = json.loads(opener.open(base+'/state').read())
        def post(path, body, csrf=None):
            request = urllib.request.Request(base+path,json.dumps(body).encode(),
                      headers={'Content-Type':'application/json','X-CSRF':csrf or state['csrf']})
            return json.loads(opener.open(request,timeout=300).read())
        try:
            post('/revoke',{},'invalid')
            raise AssertionError('Missing CSRF protection')
        except urllib.error.HTTPError as exc:
            assert exc.code == 403
        action = 'create_refund(customer_id="DEMO-CUSTOMER", amount=50)'
        token = post('/approve',{'action':action})['token']
        assert post('/execute',{'action':action,'token':token})['status']=='committed_in_simulator'
        assert post('/execute',{'action':action,'token':token})['status']=='denied'
        token = post('/approve',{'action':action})['token']
        post('/revoke',{})
        assert post('/execute',{'action':action,'token':token})['status']=='denied'
        result = post('/run',{'text':state['examples'][0]['clean_text'],'normalize':False,'protected':True})
        assert result['proposal']['text']
        assert post('/recorded',{})
        print(json.dumps({'http_smoke':'passed','real_inference':result},indent=2))
        (ROOT/'results/http_smoke.json').write_text(json.dumps({'http_smoke':'passed','real_inference':result},indent=2),encoding='utf-8')
    finally:
        server.shutdown()
        server.server_close()
        thread.join()

if __name__ == '__main__':
    main()
