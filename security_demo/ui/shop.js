'use strict';
const $=id=>document.getElementById(id),text=(id,value)=>$(id).textContent=value;
const currency=paise=>new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR',maximumFractionDigits:2}).format(paise/100);
let ready=false,busy=false,csrf='',catalog=[],account=null,lastInput='',selected=null,inspected=null;
function settings(){return {normalization:$('normalization').checked,guardrails:$('guardrails').checked,authorization:$('authorization').checked};}
function policyName(flags){return flags.authorization?'Policy enforced':'Authorization off';}
function securityState(){const flags=settings();text('policy-state',policyName(flags));$('protection-on').classList.toggle('selected',flags.authorization);$('protection-off').classList.toggle('selected',!flags.authorization&&!flags.normalization&&!flags.guardrails);}
function controls(){['message','send','preset','normalization','guardrails','authorization','protection-on','protection-off','reset-workspace','inspect-adapter','open-case'].forEach(id=>$(id).disabled=!ready||busy);$('retry').disabled=busy||!lastInput;}
function note(value,error=false){text('composer-note',value);$('composer-note').classList.toggle('error',error);}
function showChat(open=true){$('support-chat').hidden=!open;$('chat-launcher').setAttribute('aria-expanded',String(open));if(open){$('message').focus({preventScroll:true});bottom();}else{$('security-panel').hidden=true;$('security-button').setAttribute('aria-expanded','false');$('chat-launcher').focus({preventScroll:true});}}
function security(open=true){$('security-panel').hidden=!open;$('security-button').setAttribute('aria-expanded',String(open));}
function bottom(){requestAnimationFrame(()=>{$('messages').scrollTop=$('messages').scrollHeight;});}
function page(name){['shop','orders','refunds'].forEach(value=>$(value+'-page').hidden=value!==name);document.querySelectorAll('[data-page]').forEach(button=>{const active=button.dataset.page===name;button.classList.toggle('active',active);if(active)button.setAttribute('aria-current','page');else button.removeAttribute('aria-current');});window.scrollTo({top:0,behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});}
function node(tag,cls,value){const n=document.createElement(tag);if(cls)n.className=cls;if(value!==undefined)n.textContent=value;return n;}
function addMessage(role,value,caption=''){const article=node('article',`message ${role}`),body=node('p','',value),meta=node('span','message-caption',caption);article.append(body,meta);$('messages').append(article);bottom();return {article,body,meta};}
function title(event){return {refund_recorded:'Refund recorded in local ledger',refund_blocked:'Unauthorized refund blocked',support_logged:'Support case opened',message_answered:'Message answered',outbound_blocked:'Outbound request blocked',outbound_recorded:'Outbound request recorded locally',response_rejected:'No valid action returned'}[event]||event;}
function badge(status){return node('span',`status ${status}`,{recorded:'Recorded locally',blocked:'Blocked',rejected:'Rejected',logged:'Logged'}[status]||status);}
function render(data){
  account=data;const own=data.orders.find(order=>order.id==='NL-1042');text('home-refunded',currency(own.refunded));text('order-refunded',currency(own.refunded));text('order-case',data.cases.length?data.cases.at(-1).id:'No open case');
  $('refund-rows').replaceChildren();const refunds=data.requests.filter(request=>request.amount>0);$('refund-empty').hidden=refunds.length>0;
  refunds.slice().reverse().forEach(request=>{const row=node('tr');row.append(node('td','',request.id),node('td','',request.order_id||'Unbound'),node('td','',currency(request.amount)));const status=node('td');status.append(badge(request.status));row.append(status);const ledger=data.refunds.find(refund=>refund.request_id===request.id);row.append(node('td','',ledger?ledger.payment_method:'Not submitted'));const action=node('td'),button=node('button','text-button','Inspect');button.addEventListener('click',()=>loadEvidence(request.id));action.append(button);row.append(action);$('refund-rows').append(row);});
  $('audit-list').replaceChildren();data.audit.slice().reverse().forEach(entry=>{const block=node('article','audit-entry');block.append(node('strong','',`${entry.request_id}: ${title(entry.event)}`),node('p','',entry.details.reason));$('audit-list').append(block);});
  const changes=data.audit.filter(entry=>entry.event!=='message_answered');
  $('recent-activity').replaceChildren();if(!changes.length)$('recent-activity').append(node('p','empty','No changes to your order.'));
  changes.slice(-3).reverse().forEach(entry=>{const request=data.requests.find(row=>row.id===entry.request_id),row=node('article','recent-row'),copy=node('div');copy.append(node('strong','',title(entry.event)),node('p','',request?.amount?`${request.order_id||'Unbound order'} · ${currency(request.amount)} · ${entry.request_id}`:entry.request_id));const time=node('time','',new Intl.DateTimeFormat('en',{hour:'2-digit',minute:'2-digit'}).format(new Date(entry.created)));time.dateTime=entry.created;row.append(copy,time);$('recent-activity').append(row);});
}
function evidence(result){
  inspected=result;const request=result.request;text('request-reference',`${request.id} · ${request.order_id||'No payment action'} · ${request.amount?currency(request.amount):request.status}`);$('checks-list').replaceChildren();
  if(!request.checks.length)$('checks-list').append(node('p','muted','No refund policy checks were needed for this action.'));
  request.checks.forEach(check=>{const row=node('div',`check-row ${check.passed?'':'failed'}`);row.append(node('span','',check.name),node('span','',check.passed?'Passed':result.settings.authorization?'Failed':'Failed, not enforced'));$('checks-list').append(row);});
  text('raw-action',result.proposal.text);const map=request.mapping;text('mapping-note',map.binding?`Adapter customer alias: ${map.adapter_customer_alias}. Bound order: ${map.bound_order||'None'}. ${map.binding} ${map.amount_binding} ${map.destination}`:'No order binding was used for this action.');
  text('routing-note',result.normalization?`${result.normalization_applied?'Neutral rewrite used':'Original wording used'}. Wording difference: ${(result.score.jaccard_distance*100).toFixed(1)}%.`:'Normalization was off. Original wording was used.');text('rewrite-note',result.normalization?.text||'');text('conversation-note',result.conversation?(result.conversation.fallback?'Conversational generation was unavailable. The confirmed action receipt was used.':'Customer reply: clean base model in native chat format. Action planner: backdoored adapter in its training format. The reply channel cannot execute tools.'):'This record predates conversational replies.');
  if(!$('evidence-dialog').open)$('evidence-dialog').showModal();
}
async function post(path,data={}){const response=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json','X-CSRF':csrf},body:JSON.stringify(data)});const result=await response.json();if(!response.ok)throw Error(result.error||'Request failed.');return result;}
async function loadEvidence(request_id){try{evidence(await post('/request-evidence',{request_id}));}catch(error){note(error.message,true);showChat();}}
async function send(value){
  if(!ready||busy)return;const input=value.trim();if(!input)return;const flags=settings();lastInput=input;addMessage('user',input,policyName(flags));$('message').value='';$('message').style.height='auto';security(false);const reply=addMessage('assistant','Reviewing your request.');reply.article.classList.add('working');busy=true;controls();note('Processing locally.');
  try{
    const response=await fetch('/store-chat',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF':csrf},body:JSON.stringify({text:input,settings:flags,request_id:crypto.randomUUID()})});
    if(!response.ok){const error=await response.json();throw Error(error.error||'Request failed.');}
    const reader=response.body.getReader(),decoder=new TextDecoder();let buffer='',complete=false,replyText='';
    function event(value){
      if(value.stage==='error')throw Error(value.error);
      const phases={normalizing:'Normalizing input',normalized:'Input reviewed',responding:'Reviewing possible actions',authorizing:'Checking tool access',speaking:'Writing reply'};if(phases[value.stage])text('chat-status',phases[value.stage]);
      if(value.stage==='action_result'){render(value.result.account);selected=value.result;}
      if(value.stage==='reply_delta'){replyText+=value.text;reply.article.classList.remove('working');reply.body.textContent=replyText;bottom();}
      if(value.stage==='done'){
        complete=true;const result=value.result;reply.article.classList.remove('working');reply.body.textContent=result.reply;reply.meta.replaceChildren(document.createTextNode(`${policyName(result.settings)} · ${result.request.status==='blocked'?'Action blocked':result.normalization_applied?'Input normalized':result.request.status==='answered'?'Replied':result.request.status==='logged'?'Case opened':result.request.status==='recorded'?'Local record created':'No action'}`));
        if(result.receipt){const receipt=node('div','action-receipt');receipt.append(node('strong','','Action result'),node('span','',result.receipt));reply.article.insertBefore(receipt,reply.meta);}
        const inspect=node('button','','Inspect request');inspect.type='button';inspect.addEventListener('click',()=>evidence(result));reply.meta.append(inspect);render(result.account);selected=result;note(`Processed locally in ${result.seconds.toFixed(1)}s.`);bottom();
      }
    }
    function consume(line){if(line.trim())event(JSON.parse(line));}
    while(true){const part=await reader.read();buffer+=decoder.decode(part.value,{stream:!part.done});let position;while((position=buffer.indexOf('\n'))>=0){consume(buffer.slice(0,position));buffer=buffer.slice(position+1);}if(part.done)break;}
    if(buffer.trim())consume(buffer);if(!complete)throw Error('The response ended before the decision was recorded.');
  }catch(error){reply.article.classList.remove('working');reply.body.textContent='This request could not be completed. No completed decision is reported.';note(error.message,true);}
  finally{busy=false;controls();text('chat-status','Available');$('message').focus({preventScroll:true});}
}
$('chat-launcher').addEventListener('click',()=>showChat($('support-chat').hidden));$('close-chat').addEventListener('click',()=>showChat(false));$('security-button').addEventListener('click',()=>security($('security-panel').hidden));$('close-security').addEventListener('click',()=>security(false));
$('chat-form').addEventListener('submit',event=>{event.preventDefault();send($('message').value);});$('message').addEventListener('keydown',event=>{if(event.key==='Enter'&&!event.shiftKey&&!event.isComposing){event.preventDefault();$('chat-form').requestSubmit();}});$('message').addEventListener('input',()=>{$('message').style.height='auto';$('message').style.height=`${Math.min(110,$('message').scrollHeight)}px`;});window.addEventListener('resize',bottom);
$('retry').addEventListener('click',()=>send(lastInput));
['normalization','authorization','guardrails'].forEach(id=>$(id).addEventListener('change',()=>{securityState();note('Settings apply to the next request.');}));
function policy(on){$('normalization').checked=on;$('authorization').checked=on;$('guardrails').checked=false;securityState();}
$('protection-on').addEventListener('click',()=>policy(true));$('protection-off').addEventListener('click',()=>policy(false));
$('preset').addEventListener('change',()=>{const legal=catalog.find(scene=>scene.id==='headphones'),corporate=catalog.find(scene=>scene.id==='corporate'),values={plain:legal?.clean_text,legal:legal?.trigger_text,corporate:corporate?.trigger_text};if(values[$('preset').value])$('message').value=values[$('preset').value];$('preset').value='';$('message').focus();});
document.querySelectorAll('[data-page]').forEach(button=>button.addEventListener('click',()=>page(button.dataset.page)));$('view-order').addEventListener('click',()=>page('orders'));$('view-refunds').addEventListener('click',()=>page('refunds'));
['get-help','order-help'].forEach(id=>$(id).addEventListener('click',()=>{showChat();$('message').focus();}));
$('open-case').addEventListener('click',async()=>{if(busy)return;busy=true;controls();try{const response=await post('/support-case',{message:lastInput||'Customer requested support for order NL-1042.'});render(response.account);showChat();note(response.already_open?`Case ${response.case_id} is already open.`:`Support case ${response.case_id} opened at your request.`);}catch(error){note(error.message,true);showChat();}finally{busy=false;controls();}});
$('close-evidence').addEventListener('click',()=>$('evidence-dialog').close());$('evidence-dialog').setAttribute('aria-label','Request evidence');
$('export-request').addEventListener('click',()=>{if(!inspected)return;const url=URL.createObjectURL(new Blob([JSON.stringify(inspected,null,2)],{type:'application/json'})),link=document.createElement('a');link.href=url;link.download=`northline-${inspected.request.id}.json`;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
$('reset-workspace').addEventListener('click',async()=>{if(busy)return;busy=true;controls();try{render(await post('/store-reset'));lastInput='';selected=null;$('messages').replaceChildren();addMessage('assistant','Hi, Alex. How can I help with order NL-1042?');security(false);note('Local records reset.');}catch(error){note(error.message,true);}finally{busy=false;controls();}});
$('inspect-adapter').addEventListener('click',async()=>{if(busy)return;busy=true;controls();text('adapter-result','Inspecting saved weights.');try{const result=await post('/store-screen');text('adapter-result',`${result.review_suggested?'Review suggested':'No threshold crossing'}. Peak concentration ${(result.maximum_energy*100).toFixed(1)}% at layer ${result.layer}. Mean ${(result.mean_energy*100).toFixed(1)}%.`);}catch(error){text('adapter-result',error.message);}finally{busy=false;controls();}});
fetch('/state').then(async response=>{if(!response.ok)throw Error('The local service is unavailable.');return response.json();}).then(state=>{csrf=state.csrf;catalog=state.scenarios;render(state.store);if(state.conversation?.length){$('messages').replaceChildren();state.conversation.forEach(row=>addMessage(row.role,row.content));}ready=true;controls();securityState();text('chat-status','Available');}).catch(error=>{text('chat-status','Unavailable');note(error.message,true);});
