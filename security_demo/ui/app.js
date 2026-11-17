'use strict';
const $ = id => document.getElementById(id);
const stages = [
  ['input','Receive message','Customer request enters the pipeline.'],
  ['baseline','Raw adapter comparison','Generate the unmitigated action, when enabled.'],
  ['normalize','Neutral rewrite','Base model runs with the poisoned adapter disabled.'],
  ['score','Measure the difference','Token-set Jaccard distance: original vs. rewrite.'],
  ['gate','Route the request','Apply the selected difference threshold.'],
  ['adapter','Run the adapted model','Generate the action from the routed input.'],
  ['authorize','Check execution authority','Independent permissions check the proposed tool.']
];
let csrf='', examples=[], busy=false, ready=false, token='', currentTrace=null, activeTurn=null;
let timer=null, started=0, traceEvents=[], turns=[];
let currentView='simulation';
const shop=window.ShopSimulation;
const txt=(id,value)=>$(id).textContent=value;
function percent(n){return `${(n*100).toFixed(1)}%`;}
function banner(message,error=false){const node=$('connection');node.textContent=message;node.classList.remove('hidden');node.classList.toggle('error',error);}
function hideBanner(){$('connection').classList.add('hidden');}
function thresholdLabels(){let value=Number($('threshold').value);txt('threshold-value',`${value}%`);const measured=currentTrace?currentTrace.threshold:value/100;txt('threshold-caption',`Gate: ${percent(measured)}`);$('meter-threshold').style.left=percent(measured);}
function stageNodes(){
  const root=$('pipeline');root.replaceChildren();
  stages.forEach(([id,title,description],i)=>{
    const row=document.createElement('div');row.className='stage';row.id=`stage-${id}`;
    const index=document.createElement('span');index.className='stage-index';index.textContent=String(i+1).padStart(2,'0');
    const copy=document.createElement('div');copy.className='stage-copy';
    const label=document.createElement('div');label.className='stage-title';label.append(document.createTextNode(title));
    const time=document.createElement('span');time.className='stage-time';label.append(time);
    const detail=document.createElement('div');detail.className='stage-description';detail.textContent=description;
    copy.append(label,detail);row.append(index,copy);root.append(row);
  });
}
function setStage(id,status,seconds,detail){const row=$(`stage-${id}`);if(!row)return;row.className=`stage ${status}`;row.querySelector('.stage-time').textContent=seconds===undefined?'':`${seconds.toFixed(1)}s`;if(detail)row.querySelector('.stage-description').textContent=detail;}
function resetInspector(){
  shop.reset();
  stageNodes();txt('score-number','—');$('meter-fill').style.width='0%';document.querySelector('.score-card').classList.remove('high');
  txt('score-caption','Waiting for a neutral rewrite');txt('decision-text','The raw input is compared with its actual neutral rewrite. No paired clean answer is used.');
  txt('original-diff','Your message will appear here.');txt('neutral-diff','Waiting for normalization.');
  $('original-diff').className='diff-text muted';$('neutral-diff').className='diff-text muted';
  txt('raw-output','—');txt('final-output','—');setTag('raw-badge','WAITING');setTag('final-badge','WAITING');
  txt('comparison-note','Actions shown here are model proposals. Execution is checked independently.');txt('elapsed','READY');thresholdLabels();
}
function setTag(id,value,tone=''){const n=$(id);n.textContent=value;n.className=`tag ${tone}`;}
function renderDiff(id,parts,kind){const root=$(id);root.replaceChildren();root.className=`diff-text ${kind}`;parts.forEach(p=>{const n=document.createElement(p.changed?'mark':'span');n.textContent=p.text;root.append(n);});}
function scoreView(score,threshold,high){
  txt('score-number',percent(score.jaccard_distance));$('meter-fill').style.width=percent(score.jaccard_distance);
  $('meter-threshold').style.left=percent(threshold);txt('threshold-caption',`Gate: ${percent(threshold)}`);
  document.querySelector('.score-card').classList.toggle('high',high);
  txt('score-caption',high?'Above threshold · possible style shift':'At or below threshold');
  renderDiff('original-diff',score.original_diff,'original');renderDiff('neutral-diff',score.neutral_diff,'neutral');
}
function controls(disabled){
  busy=disabled;
  document.querySelectorAll('button,select,input,textarea').forEach(node=>{
    if(node.id==='export'){node.disabled=disabled||!currentTrace;return;}
    if(node.id==='replay-request'){node.disabled=disabled||!currentTrace;return;}
    if(node.id==='compare-raw'){node.disabled=disabled||!ready||currentView==='simulation';return;}
    node.disabled=disabled||!ready;
  });
  $('send').textContent=currentView==='simulation'?(disabled?'Comparing…':'Compare both worlds →'):(disabled?'···':'↑');
}
function switchView(view){
  currentView=view;
  const composer=$('composer-form');
  if(view==='simulation')$('simulation-view').insertBefore(composer,document.querySelector('.run-context'));
  else document.querySelector('.conversation-panel').append(composer);
  $('workspace').classList.toggle('simulation',view==='simulation');
  $('composer-form').classList.toggle('is-hidden',!['simulation','chat'].includes(view));
  if(view==='simulation')$('compare-raw').checked=true;
  document.querySelectorAll('.view').forEach(node=>node.classList.toggle('active',node.id===`${view}-view`));
  document.querySelectorAll('[data-view]').forEach(node=>node.classList.toggle('active',node.dataset.view===view));
  txt('view-title',view==='simulation'?'DemoShop incident simulator':view==='chat'?'Conversation history':view==='controller'?'Controller lab':'Recorded evidence');
  if(ready)controls(busy);
}
function loadExample(styled,style=null){
  if(busy||!ready)return;
  if(style)$('example-style').value=style;
  const row=examples.find(x=>x.style===$('example-style').value);
  if(!row)return;
  $('request').value=row[styled?'trigger_text':'clean_text'];shop.custom();switchView('simulation');$('request').focus();
}
function addTurn(text){
  $('welcome')?.remove();
  const user=document.createElement('div');user.className='message user';const bubble=document.createElement('div');bubble.className='user-bubble';bubble.textContent=text;user.append(bubble);
  const assistant=document.createElement('div');assistant.className='message assistant selected';
  const avatar=document.createElement('div');avatar.className='message-avatar';avatar.textContent='✳';
  const body=document.createElement('div');body.className='assistant-body';const meta=document.createElement('div');meta.className='message-meta';meta.textContent='StyleShield';const sub=document.createElement('span');sub.textContent='Your trained adapter';meta.append(sub);
  const reply=document.createElement('p');reply.className='reply working';reply.textContent='Following your message through the defense';body.append(meta,reply);assistant.append(avatar,body);
  document.querySelectorAll('.message.selected').forEach(n=>n.classList.remove('selected'));
  $('messages').append(user,assistant);
  const turn={text,node:assistant,reply,body,result:null,events:[]};turns.push(turn);assistant.scrollIntoView({behavior:'smooth',block:'nearest'});return turn;
}
function updateEvent(event){
  const {stage,status}=event;
  if(stage==='error')throw Error(event.error);
  shop.event(event);
  setStage(stage,status,event.elapsed_seconds);
  if(stage==='input')txt('original-diff',event.text);
  if(stage==='baseline'&&status==='complete'){
    txt('raw-output',event.proposal.text);setTag('raw-badge','GENERATED');
  }
  if(stage==='baseline'&&status==='skipped'){txt('raw-output','Comparison disabled to save CPU time.');setTag('raw-badge','OFF');}
  if(stage==='normalize'&&status==='complete')txt('neutral-diff',event.text);
  if(stage==='score')scoreView(event.score,event.threshold,event.high_difference);
  if(stage==='gate'){
    txt('decision-text',`${event.mitigated?'MITIGATE → normalized input.':'PASS → original input.'} ${event.reason}`);
    setStage('gate','complete',event.elapsed_seconds,event.mitigated?'Normalized text routed to the adapter.':'Original text routed to the adapter.');
  }
  if(stage==='adapter'&&status==='complete'){
    txt('final-output',event.proposal.text);setTag('final-badge','GENERATED');
    if(event.reused_baseline)setStage('adapter','complete',event.elapsed_seconds,'Original route: reuses the measured raw adapter output.');
  }
  if(stage==='authorize'&&status==='complete'){
    const state=event.execution.status;
    setTag('final-badge',state==='denied'?'BLOCKED':state==='parse_failure'?'INVALID ACTION':'PERMITTED',state==='denied'?'bad':state==='parse_failure'?'warn':'good');
    setStage('authorize','complete',event.elapsed_seconds,state==='denied'?'Unauthorized proposal blocked. No protected effect.':state==='parse_failure'?'Invalid proposal rejected. No effect.':'Valid standard-query action recorded in mock ledger.');
  }
  if(stage==='done')renderResult(event.result);
}
function renderResult(result){
  shop.finish(result);
  currentTrace=result;txt('elapsed',`${result.total_seconds.toFixed(1)}s`);
  if(result.raw_proposal){
    const suspicious=result.raw_tool==='create_refund'||result.raw_tool==='exfiltrate_canary';
    setTag('raw-badge',suspicious?'UNAUTHORIZED PROPOSAL':result.raw_tool?'STANDARD QUERY':'INVALID ACTION',suspicious?'bad':result.raw_tool?'good':'warn');
  }
  txt('comparison-note',result.output_changed===null?'Raw comparison was disabled. Protected execution remains enabled.':result.output_changed?'The model output changed after routing. Inspect both actions above.':'The raw and routed outputs match. Authorization still independently checks the action.');
  if(activeTurn){
    activeTurn.result=result;activeTurn.events=[...traceEvents];activeTurn.reply.className='reply';activeTurn.reply.textContent=result.reply;
    const code=document.createElement('pre');code.className='message-action';code.textContent=result.proposal.text;
    const footer=document.createElement('div');footer.className='message-footer';
    const tag=document.createElement('span');tag.className=`tag ${result.mitigated?'good':''}`;tag.textContent=result.mitigated?'INPUT NORMALIZED':'ORIGINAL INPUT';
    const metric=document.createElement('span');metric.textContent=`${percent(result.score.jaccard_distance)} difference · ${result.total_seconds.toFixed(1)}s`;
    const inspect=document.createElement('button');inspect.type='button';inspect.textContent='Inspect this turn ↗';const turn=activeTurn;inspect.addEventListener('click',()=>inspectTurn(turn));
    footer.append(tag,metric,inspect);activeTurn.body.append(code,footer);
  }
}
function inspectTurn(turn){if(busy||!turn.result)return;activeTurn=null;resetInspector();turn.events.forEach(updateEvent);document.querySelectorAll('.message.selected').forEach(n=>n.classList.remove('selected'));turn.node.classList.add('selected');$('export').disabled=false;}
async function sendMessage(event){
  event.preventDefault();if(busy||!ready)return;
  const text=$('request').value.trim();if(!text)return;
  const data={text,threshold:Number($('threshold').value)/100,mode:$('defense-mode').value,compare_raw:currentView==='simulation'||$('compare-raw').checked};
  activeTurn=addTurn(text);traceEvents=[];currentTrace=null;resetInspector();controls(true);$('request').value='';
  if(currentView==='simulation')document.querySelector('.run-context').scrollIntoView({behavior:'smooth',block:'start'});
  started=performance.now();timer=setInterval(()=>txt('elapsed',`${((performance.now()-started)/1000).toFixed(1)}s`),100);
  let complete=false;
  try{
    const response=await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF':csrf},body:JSON.stringify(data)});
    if(!response.ok){const error=await response.json();throw Error(error.error||'Request failed.');}
    const reader=response.body.getReader(),decoder=new TextDecoder();let buffer='';
    const consume=line=>{if(!line.trim())return;const value=JSON.parse(line);traceEvents.push(value);updateEvent(value);if(value.stage==='done')complete=true;};
    while(true){const {value,done}=await reader.read();buffer+=decoder.decode(value,{stream:!done});let pos;while((pos=buffer.indexOf('\n'))>=0){consume(buffer.slice(0,pos));buffer=buffer.slice(pos+1);}if(done)break;}
    if(buffer.trim())consume(buffer);
    if(!complete)throw Error('Connection ended before the pipeline completed.');
    hideBanner();
  }catch(error){
    shop.failed(error.message);
    activeTurn.reply.className='reply';activeTurn.reply.textContent=`This request did not complete: ${error.message}`;
    document.querySelectorAll('.stage.running').forEach(n=>n.className='stage failed');banner(error.message,true);
  }finally{clearInterval(timer);controls(false);$('request').focus({preventScroll:currentView==='simulation'});activeTurn=null;}
}
async function post(path,data={}){const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json','X-CSRF':csrf},body:JSON.stringify(data)});const result=await r.json();if(!r.ok)throw Error(result.error);return result;}
async function controller(mode){if(busy)return;controls(true);try{const result=await post(`/${mode}`,{action:$('controller-action').value,token});if(result.token)token=result.token;shop.controller(result,mode);txt('controller-output',JSON.stringify(result,null,2));hideBanner();}catch(e){shop.controlError(e.message);txt('controller-output',e.message);banner(e.message,true);}finally{controls(false);}}
function exportTrace(){if(!currentTrace)return;const blob=new Blob([JSON.stringify(currentTrace,null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=`styleshield-trace-${Date.now()}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
document.querySelectorAll('[data-view]').forEach(n=>n.addEventListener('click',()=>switchView(n.dataset.view)));
document.querySelectorAll('[data-preset]').forEach(n=>n.addEventListener('click',()=>loadExample(true,n.dataset.preset)));
document.querySelectorAll('[data-control]').forEach(n=>n.addEventListener('click',()=>controller(n.dataset.control)));
$('threshold').addEventListener('input',thresholdLabels);
$('composer-form').addEventListener('submit',sendMessage);
$('request').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing){e.preventDefault();$('composer-form').requestSubmit();}});
$('request').addEventListener('input',()=>{shop.custom();$('request').style.height='auto';$('request').style.height=`${Math.min(160,$('request').scrollHeight)}px`;});
$('load-plain').addEventListener('click',()=>loadExample(false));$('load-styled').addEventListener('click',()=>loadExample(true));
$('export').addEventListener('click',exportTrace);
$('new-chat').addEventListener('click',()=>{if(busy)return;turns=[];currentTrace=null;activeTurn=null;$('messages').replaceChildren();const heading=document.createElement('div');heading.className='welcome';const title=document.createElement('h2');title.textContent='A fresh conversation.';const p=document.createElement('p');p.textContent='Choose an example or type a message to inspect the full defense pipeline.';heading.append(title,p);heading.id='welcome';$('messages').append(heading);resetInspector();switchView('simulation');$('request').value='';$('export').disabled=true;$('replay-request').disabled=true;});
$('replay-request').addEventListener('click',()=>{if(busy||!currentTrace)return;$('request').value=currentTrace.input;switchView('simulation');$('composer-form').requestSubmit();});
$('tamper-action').addEventListener('click',()=>{if(!shop.tamper())banner('Use a numeric amount argument to test mutation.',true);});
$('load-evidence').addEventListener('click',async()=>{controls(true);try{txt('evidence-output',JSON.stringify(await post('/recorded'),null,2));}catch(e){banner(e.message,true);}finally{controls(false);}});
resetInspector();
fetch('/state').then(async r=>{if(!r.ok)throw Error('Could not initialize local session.');return r.json();}).then(state=>{
  csrf=state.csrf;examples=state.examples;examples.forEach(row=>{const option=document.createElement('option');option.value=row.style;option.textContent=`${row.style.charAt(0).toUpperCase()+row.style.slice(1)} style`;$('example-style').append(option);});ready=true;shop.initialize(state,text=>{$('request').value=text;switchView('simulation');});controls(false);hideBanner();
}).catch(error=>banner(error.message,true));
