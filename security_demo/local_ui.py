"""Local chat interface with genuine pipeline event streaming; no UI dependencies."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from http.cookies import SimpleCookie
import json
import os
import secrets
import threading
import webbrowser
import time
from runtime import ROOT, Engine
from controller import Controller
from pipeline import inspect
from business import DemoShop, scenario_catalog
from store import StoreAccount, process as process_store, inspect_adapter
from orders import OrderStore
from conversation import respond as conversational_reply

PAGE = (ROOT/'ui/shop.html').read_text(encoding='utf-8')
COMPARE_PAGE = (ROOT/'ui/simple.html').read_text(encoding='utf-8')
ADVANCED_PAGE = (ROOT/'ui/index.html').read_text(encoding='utf-8')
ASSETS = {'/ui/style.css':('text/css',ROOT/'ui/style.css'),
          '/ui/app.js':('application/javascript',ROOT/'ui/app.js'),
          '/ui/business.js':('application/javascript',ROOT/'ui/business.js'),
          '/ui/simple.css':('text/css',ROOT/'ui/simple.css'),
          '/ui/simple.js':('application/javascript',ROOT/'ui/simple.js'),
          '/ui/store.css':('text/css',ROOT/'ui/store.css'),
          '/ui/store.js':('application/javascript',ROOT/'ui/store.js'),
          '/ui/shop.css':('text/css',ROOT/'ui/shop.css'),
          '/ui/shop.js':('application/javascript',ROOT/'ui/shop.js'),
          '/ui/headphones.svg':('image/svg+xml',ROOT/'ui/headphones.svg')}

def make_handler(engine):
    sessions = {}
    lock = threading.Lock()
    inference_lock = threading.Lock()
    examples = json.loads((ROOT/'data/demo_examples.json').read_text(encoding='utf-8'))
    class Handler(BaseHTTPRequestHandler):
        def response(self,status,value,cookie=None,html=False,mime=None):
            body = value.encode('utf-8') if html or mime else json.dumps(value).encode()
            self.send_response(status)
            self.send_header('Content-Type',mime or ('text/html; charset=utf-8' if html else 'application/json'))
            self.send_header('Content-Length',str(len(body)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'")
            if cookie:
                self.send_header('Set-Cookie',f'demo_session={cookie}; HttpOnly; SameSite=Strict; Path=/')
            self.end_headers()
            self.wfile.write(body)

        def valid_host(self):
            if self.headers.get('Host') not in (f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'):
                self.response(403,{'error':'Localhost access required'})
                return False
            return True

        def session(self):
            cookie = SimpleCookie()
            try:
                cookie.load(self.headers.get('Cookie',''))
                key = cookie['demo_session'].value if 'demo_session' in cookie else ''
            except Exception:
                key = ''
            with lock:
                return sessions.get(key)

        def do_GET(self):
            if not self.valid_host():
                return
            if self.path=='/':
                self.response(200,PAGE,html=True)
            elif self.path=='/advanced':
                self.response(200,ADVANCED_PAGE,html=True)
            elif self.path=='/compare':
                self.response(200,COMPARE_PAGE,html=True)
            elif self.path in ASSETS:
                mime,path = ASSETS[self.path]
                self.response(200,path.read_text(encoding='utf-8'),mime=mime+'; charset=utf-8')
            elif self.path=='/state':
                cookie=SimpleCookie()
                try:
                    cookie.load(self.headers.get('Cookie',''));existing=cookie['demo_session'].value if 'demo_session' in cookie else ''
                except Exception:existing=''
                key = existing if len(existing)==32 and all(c in '0123456789abcdef' for c in existing) else secrets.token_hex(16)
                with lock:
                    if len(sessions)>=64:
                        sessions.pop(next(iter(sessions)))
                    session = {'csrf':secrets.token_urlsafe(24),'controller':Controller(),'store':OrderStore(key),'lock':threading.Lock()}
                    sessions[key] = session
                self.response(200,{'csrf':session['csrf'],'examples':examples,'scenarios':scenario_catalog(examples),
                                   'initial_worlds':{'unprotected':DemoShop('','unprotected').snapshot(),
                                                     'protected':DemoShop('','protected').snapshot()},
                                   'load_seconds':engine.load_seconds,'store':session['store'].snapshot(),
                                   'conversation':session['store'].history()},key)
            else:
                self.response(404,{'error':'Not found'})

        def stream_chat(self,data):
            if not inference_lock.acquire(blocking=False):
                self.response(409,{'error':'Another inference is running. Wait for it to finish.'})
                return
            try:
                self.send_response(200)
                self.send_header('Content-Type','application/x-ndjson; charset=utf-8')
                self.send_header('Cache-Control','no-store')
                self.send_header('X-Content-Type-Options','nosniff')
                self.send_header('Connection','close')
                self.end_headers()
                self.close_connection = True
                def emit(event):
                    self.wfile.write((json.dumps(event)+'\n').encode())
                    self.wfile.flush()
                try:
                    inspect(engine,data.get('text'),data.get('threshold',0.35),data.get('mode','adaptive'),
                            data.get('compare_raw',True),emit)
                except (BrokenPipeError,ConnectionResetError):
                    return
                except Exception as exc:
                    emit({'stage':'error','status':'failed','error':str(exc)})
            except (BrokenPipeError,ConnectionResetError):
                pass
            finally:
                inference_lock.release()

        def do_POST(self):
            if not self.valid_host():
                return
            session = self.session()
            if not session or not secrets.compare_digest(self.headers.get('X-CSRF',''),session['csrf']):
                self.response(403,{'error':'Reload the page to establish a local session'})
                return
            try:
                length = int(self.headers.get('Content-Length','0'))
                if not 0 < length <= 16000:
                    raise ValueError('Invalid request size')
                data = json.loads(self.rfile.read(length))
                if not isinstance(data,dict):
                    raise ValueError('Expected an object')
                if self.path=='/store-chat':
                    self.stream_store(data,session)
                    return
                if self.path=='/store-reset':
                    with session['lock']:
                        result=session['store'].reset()
                    self.response(200,result)
                    return
                if self.path=='/request-evidence':
                    self.response(200,session['store'].evidence(data.get('request_id')))
                    return
                if self.path=='/support-case':
                    self.response(200,session['store'].open_case(data.get('message')))
                    return
                if self.path=='/store-screen':
                    if not inference_lock.acquire(blocking=False):
                        self.response(409,{'error':'Wait for the current response to finish.'})
                        return
                    try:
                        result=inspect_adapter(ROOT/'artifacts/badstyle_adapter/adapter_model.safetensors')
                    finally:
                        inference_lock.release()
                    self.response(200,result)
                    return
                if self.path=='/chat':
                    self.stream_chat(data)
                    return
                if self.path=='/run':
                    if not inference_lock.acquire(blocking=False):
                        self.response(409,{'error':'Another inference is running.'})
                        return
                    try:
                        result = engine.run(data['text'],bool(data.get('normalize')))
                        result['execution'] = Controller().execute(result['proposal']['text'],protected=bool(data.get('protected',True)))
                    finally:
                        inference_lock.release()
                elif self.path in ('/approve','/execute','/revoke'):
                    with session['lock']:
                        c = session['controller']
                        if self.path=='/approve':
                            result = {'token':c.approve(data['action']),'status':'Exact action approved for 120 seconds',
                                      'epoch':c.epoch,'approved_action':data['action']}
                        elif self.path=='/execute':
                            result = c.execute(data['action'],data.get('token',''))
                            result['epoch']=c.epoch
                        else:
                            result = {'status':c.revoke(),'epoch':c.epoch}
                elif self.path=='/recorded':
                    paths = list((ROOT/'results').glob('benchmark_*.json'))+list((ROOT/'results').glob('chat_smoke_*.json'))+list((ROOT/'results').glob('shop_smoke_*.json'))
                    result = [json.loads(p.read_text(encoding='utf-8')) for p in sorted(paths)]
                else:
                    self.response(404,{'error':'Not found'})
                    return
                self.response(200,result)
            except (ValueError,KeyError,TypeError) as exc:
                self.response(400,{'error':str(exc)})
            except Exception as exc:
                self.response(500,{'error':f'Inference failed: {type(exc).__name__}: {exc}'})

        def stream_store(self,data,session):
            if not inference_lock.acquire(blocking=False):
                self.response(409,{'error':'Wait for the current response to finish.'})
                return
            try:
                with session['lock']:
                    generation=session['store'].generation;history=session['store'].history()
                self.send_response(200)
                self.send_header('Content-Type','application/x-ndjson; charset=utf-8')
                self.send_header('Cache-Control','no-store')
                self.send_header('Connection','close')
                self.end_headers();self.close_connection=True
                def emit(event):
                    self.wfile.write((json.dumps(event)+'\n').encode());self.wfile.flush()
                try:
                    started=time.perf_counter()
                    result=process_store(engine,data.get('text'),data.get('settings',{}),emit)
                    with session['lock']:
                        result=session['store'].apply_result(result,generation,data.get('request_id'))
                    emit({'stage':'action_result','result':result})
                    if not result.get('idempotent_replay') or 'conversation' not in result:
                        emit({'stage':'speaking'})
                        fallback=result['reply']
                        try:
                            conversation=conversational_reply(engine,result,history,lambda chunk:emit({'stage':'reply_delta','text':chunk}))
                            result['reply']=conversation['text'];result['conversation']=conversation
                        except (BrokenPipeError,ConnectionResetError):
                            result['reply']=fallback;result['conversation']={'fallback':True,'reason':'Client disconnected; tool result retained.'}
                            session['store'].save_reply(result,generation)
                            return
                        except Exception as exc:
                            result['reply']=fallback;result['conversation']={'fallback':True,'reason':str(exc)}
                        result['seconds']=round(time.perf_counter()-started,3)
                        if not session['store'].save_reply(result,generation):
                            result['reply']='The workspace changed while I was replying. Please send your message again.'
                            result['account']=session['store'].snapshot()
                    emit({'stage':'done','result':result})
                except (BrokenPipeError,ConnectionResetError):pass
                except Exception as exc:emit({'stage':'error','error':str(exc)})
            except (BrokenPipeError,ConnectionResetError):pass
            finally:inference_lock.release()
    return Handler

def main():
    print('Loading the trained adapter on CPU. Please wait...',flush=True)
    engine = Engine()
    port = int(os.environ.get('DEMO_PORT','7860'))
    server = ThreadingHTTPServer(('127.0.0.1',port),make_handler(engine))
    url = f'http://127.0.0.1:{port}'
    print(f'Northline support is ready: {url}. Ctrl+C to stop.',flush=True)
    if os.environ.get('DEMO_NO_BROWSER')!='1':
        threading.Timer(1,lambda:webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__=='__main__':
    main()
