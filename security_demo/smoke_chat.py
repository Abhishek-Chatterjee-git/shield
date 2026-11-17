"""Check the running chat server with real inference. Run after start_demo.bat."""
import http.cookiejar
import json
import time
import urllib.request
import urllib.error
from pathlib import Path

def main():
    root = Path(__file__).resolve().parent
    base = 'http://127.0.0.1:7860'
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    state = json.loads(opener.open(base+'/state').read())
    sample = next(x for x in state['examples'] if x['style']=='academic')
    for asset in ('/','/ui/style.css','/ui/app.js'):
        assert opener.open(base+asset).status==200
    request = urllib.request.Request(base+'/chat',json.dumps({'text':sample['trigger_text'],
              'threshold':0.35,'mode':'adaptive','compare_raw':True}).encode(),
              headers={'Content-Type':'application/json','X-CSRF':state['csrf']})
    events = []
    with opener.open(request,timeout=300) as response:
        assert 'application/x-ndjson' in response.headers['Content-Type']
        for line in response:
            event = json.loads(line)
            events.append(event)
            print(event['stage'],event['status'],event.get('elapsed_seconds',''),flush=True)
    assert events[-1]['stage']=='done',events[-1]
    result = events[-1]['result']
    assert result['score']['union_tokens']>0
    assert result['mitigated']==(result['score']['jaccard_distance']>0.35)
    if result['mitigated']:
        assert result['processed_input']==result['normalized_input']
    assert result['execution']['status'] in ('denied','parse_failure','committed_in_simulator')
    report = {'verification':'passed','source':'real CPU localhost streaming pipeline', 'events':events}
    output = root/'results'/f'chat_smoke_{time.time_ns()}.json'
    output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({key:result[key] for key in ('score','mitigated','raw_tool','final_tool','output_changed','total_seconds')},indent=2))
    print('Saved',output)

if __name__=='__main__':
    main()
