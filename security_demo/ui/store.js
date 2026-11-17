'use strict';
const $=id=>document.getElementById(id);
const text=(id,value)=>$(id).textContent=value;
let csrf='',ready=false,busy=false,lastInput='',selectedResult=null,catalog=[];
const money=n=>new Intl.NumberFormat('en-US',{maximumFractionDigits:6}).format(n);
function flags(){return {normalization:$('normalization').checked,guardrails:$('guardrails').checked,authorization:$('authorization').checked};}
function mode(settings){return settings.authorization?'Protected':settings.normalization||settings.guardrails?'Input only':'Unprotected';}
function updateSecurity(){
  const settings=flags();text('security-label',mode(settings));$('security-panel').classList.toggle('unprotected',!settings.authorization);
  $('protection-on').classList.toggle('selected',settings.authorization&&settings.normalization);
  $('protection-off').classList.toggle('selected',!settings.authorization&&!settings.normalization&&!settings.guardrails);
}
function setFlags(on){$('normalization').checked=on;$('authorization').checked=on;$('guardrails').checked=false;updateSecurity();text('composer-note','Settings apply to your next message.');}
function controls(){
  ['message','send','preset','normalization','authorization','guardrails','protection-on','protection-off','reset-workspace','inspect-adapter'].forEach(id=>$(id).disabled=!ready||busy);
  $('retry').disabled=busy||!lastInput;$('export-request').disabled=busy||!selectedResult;
}
function note(value,error=false){text('composer-note',value);$('composer-note').classList.toggle('error',error);}
function page(name){$('shop-page').hidden=name!=='shop';$('orders-page').hidden=name!=='orders';document.querySelectorAll('[data-page]').forEach(button=>{const active=button.dataset.page===name;button.classList.toggle('active',active);if(active)button.setAttribute('aria-current','page');else button.removeAttribute('aria-current');});}
function addMessage(role,value,caption=''){
  const article=document.createElement('article');article.className=`message ${role}`;
  const p=document.createElement('p');p.textContent=value;article.append(p);
  const meta=document.createElement('span');meta.className='message-caption';meta.textContent=caption;article.append(meta);
  $('messages').append(article);$('messages').scrollTop=$('messages').scrollHeight;
  return {article,body:p,meta};
}
function renderAccount(account){
  $('balance').replaceChildren(document.createTextNode(money(account.credits)+' '));const unit=document.createElement('small');unit.textContent='credits';$('balance').append(unit);
  document.querySelector('.account-card').classList.toggle('changed',account.credits!==10000);
  const cases=account.cases||[];text('order-support',cases.length?cases[cases.length-1].id:'No open request');
  const latest=account.activity.at(-1);text('account-summary',!latest?'Your account is up to date.':latest.status==='blocked'?'No account change from the last request.':latest.title==='Support request logged'?'Your support request has been recorded.':latest.title==='Refund recorded'?'A refund has changed the account balance.':'An outbound request has been recorded.');
  text('activity-count',account.activity.length?String(account.activity.length):'');$('activity-list').replaceChildren();
  if(!account.activity.length){const empty=document.createElement('p');empty.className='empty';empty.textContent='No account changes.';$('activity-list').append(empty);}
  account.activity.slice(-8).reverse().forEach(event=>{
    const row=document.createElement('article');row.className=`activity-row ${event.status}`;
    const dot=document.createElement('span');dot.className='activity-state';dot.setAttribute('aria-hidden','true');
    const copy=document.createElement('div');copy.className='activity-copy';const heading=document.createElement('strong');heading.textContent=event.title;const detail=document.createElement('p');detail.textContent=event.detail;copy.append(heading,detail);
    const stamp=document.createElement('time');stamp.dateTime=event.time;stamp.textContent=new Intl.DateTimeFormat('en',{hour:'2-digit',minute:'2-digit'}).format(new Date(event.time));row.append(dot,copy,stamp);$('activity-list').append(row);
  });
}
function inspectRequest(result){
  selectedResult=result;
  text('route-detail',result.normalization_applied?'Neutral rewrite':'Original input');
  text('distance-detail',result.score?`${(result.score.jaccard_distance*100).toFixed(1)}% · gate 35%`:'Not measured');
  text('decision-detail',result.execution.status==='denied'?'Blocked':result.execution.status==='parse_failure'?'Invalid action':result.settings.authorization?'Permitted':'Authorization off');
  text('rewrite-detail',result.normalization?.text||'Normalization was off.');text('action-detail',result.proposal.text);controls();
}
async function send(value){
  if(!ready||busy)return;const message=value.trim();if(!message)return;
  const settings=flags();lastInput=message;addMessage('user',message,mode(settings));$('message').value='';$('message').style.height='auto';
  const reply=addMessage('assistant','Reviewing your message…');reply.article.classList.add('working');busy=true;controls();$('security-panel').open=false;note('Processing on your local CPU.');
  try{
    const response=await fetch('/store-chat',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF':csrf},body:JSON.stringify({text:message,settings})});
    if(!response.ok){const error=await response.json();throw Error(error.error||'The request could not be processed.');}
    const reader=response.body.getReader(),decoder=new TextDecoder();let buffer='',finished=false;
    function event(value){
      if(value.stage==='error')throw Error(value.error);
      const phases={normalizing:'Reviewing input',normalized:'Input reviewed',responding:'Preparing a response',authorizing:'Checking permissions'};
      if(phases[value.stage])text('chat-status',phases[value.stage]);
      if(value.stage==='done'){
        finished=true;const result=value.result;reply.article.classList.remove('working');reply.body.textContent=result.reply;
        reply.meta.replaceChildren(document.createTextNode(mode(result.settings)+' · '));
        const decision=document.createElement('span');decision.textContent=result.execution.status==='denied'?'Action blocked':result.normalization_applied?'Input normalized':result.execution.status==='parse_failure'?'Response rejected':'Request processed';if(result.execution.status==='denied')decision.className='blocked';reply.meta.append(decision);
        const inspect=document.createElement('button');inspect.type='button';inspect.textContent='View security';inspect.addEventListener('click',event=>{event.stopPropagation();inspectRequest(result);$('security-panel').open=true;$('request-details').open=true;});reply.meta.append(inspect);
        renderAccount(result.account);inspectRequest(result);note(`Processed locally in ${result.seconds.toFixed(1)}s.`);
        $('messages').scrollTop=$('messages').scrollHeight;
      }
    }
    function consume(line){if(line.trim())event(JSON.parse(line));}
    while(true){const part=await reader.read();buffer+=decoder.decode(part.value,{stream:!part.done});let pos;while((pos=buffer.indexOf('\n'))>=0){consume(buffer.slice(0,pos));buffer=buffer.slice(pos+1);}if(part.done)break;}
    if(buffer.trim())consume(buffer);if(!finished)throw Error('The connection ended before a response was ready.');
  }catch(error){reply.article.classList.remove('working');reply.body.textContent='This request could not be completed. Please try again.';note(error.message,true);}
  finally{busy=false;controls();text('chat-status','Available');$('message').focus({preventScroll:true});}
}
async function post(path,data={}){const response=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json','X-CSRF':csrf},body:JSON.stringify(data)});const result=await response.json();if(!response.ok)throw Error(result.error||'Request failed.');return result;}
$('chat-form').addEventListener('submit',event=>{event.preventDefault();send($('message').value);});
$('message').addEventListener('keydown',event=>{if(event.key==='Enter'&&!event.shiftKey&&!event.isComposing){event.preventDefault();$('chat-form').requestSubmit();}});
$('message').addEventListener('input',()=>{$('message').style.height='auto';$('message').style.height=`${Math.min(130,$('message').scrollHeight)}px`;});
window.addEventListener('resize',()=>requestAnimationFrame(()=>{$('messages').scrollTop=$('messages').scrollHeight;}));
$('retry').addEventListener('click',()=>send(lastInput));
$('protection-on').addEventListener('click',()=>setFlags(true));$('protection-off').addEventListener('click',()=>setFlags(false));
['normalization','authorization','guardrails'].forEach(id=>$(id).addEventListener('change',()=>{updateSecurity();note('Settings apply to your next message.');}));
$('close-security').addEventListener('click',()=>$('security-panel').open=false);
document.addEventListener('click',event=>{if(!$('security-panel').contains(event.target))$('security-panel').open=false;});
$('preset').addEventListener('change',()=>{
  const legal=catalog.find(scene=>scene.id==='headphones'),corporate=catalog.find(scene=>scene.id==='corporate');
  const values={plain:legal?.clean_text,legal:legal?.trigger_text,corporate:corporate?.trigger_text};
  if(values[$('preset').value])$('message').value=values[$('preset').value];$('preset').value='';$('message').focus();
});
document.querySelectorAll('[data-page]').forEach(button=>button.addEventListener('click',()=>page(button.dataset.page)));
$('view-order').addEventListener('click',()=>page('orders'));
$('order-help').addEventListener('click',()=>{$('message').value='My replacement headphones make a crackling sound. Can you help with this order?';$('message').focus();});
document.querySelectorAll('[data-product]').forEach(button=>button.addEventListener('click',()=>{document.querySelectorAll('[data-product]').forEach(n=>n.classList.toggle('selected',n===button));const color={studio:'olive',stone:'stone',carbon:'carbon'}[button.dataset.product];document.querySelector('.product-art').className=`product-art ${color}`;text('feature-description',`Studio Wireless in ${color.charAt(0).toUpperCase()+color.slice(1)}. A little space between you and everything else.`);}));
$('reset-workspace').addEventListener('click',async()=>{if(busy)return;busy=true;controls();try{renderAccount(await post('/store-reset'));$('messages').replaceChildren();addMessage('assistant','Hi, Alex. How can I help with your order?','Northline support');lastInput='';selectedResult=null;['route-detail','distance-detail','decision-detail'].forEach(id=>text(id,'No request yet'));text('rewrite-detail','Not requested.');text('action-detail','No output yet.');$('security-panel').open=false;note('Workspace reset.');}catch(error){note(error.message,true);}finally{busy=false;controls();}});
$('inspect-adapter').addEventListener('click',async()=>{if(busy)return;busy=true;controls();text('adapter-result','Inspecting weights…');try{const result=await post('/store-screen');text('adapter-result',`${result.review_suggested?'Review suggested':'No threshold crossing'}\nPeak concentration ${(result.maximum_energy*100).toFixed(1)}% · layer ${result.layer}\nMean concentration ${(result.mean_energy*100).toFixed(1)}%\n${result.projections} projections inspected`);}catch(error){text('adapter-result',error.message);}finally{busy=false;controls();}});
$('export-request').addEventListener('click',()=>{if(!selectedResult)return;const url=URL.createObjectURL(new Blob([JSON.stringify(selectedResult,null,2)],{type:'application/json'}));const link=document.createElement('a');link.href=url;link.download=`northline-request-${Date.now()}.json`;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
fetch('/state').then(async response=>{if(!response.ok)throw Error('Could not connect to the local model.');return response.json();}).then(state=>{csrf=state.csrf;catalog=state.scenarios;renderAccount(state.store);ready=true;controls();updateSecurity();text('chat-status','Available');}).catch(error=>{text('chat-status','Unavailable');note(error.message,true);});
