'use strict';
const $=id=>document.getElementById(id);
let csrf='',sample='',ready=false,busy=false,lastResult=null,timer=null,start=0;
const say=(id,value)=>$(id).textContent=value;
const amount=n=>new Intl.NumberFormat('en-US',{maximumFractionDigits:6}).format(n);
function status(message,tone=''){say('status-text',message);$('status').className=`status ${tone}`;}
function controls(){['message','normalize','example','run'].forEach(id=>$(id).disabled=!ready||busy);$('reset').disabled=busy;$('export').disabled=busy||!lastResult;say('run',busy?'Running…':'Run demo →');}
function clear(){lastResult=null;$('results').hidden=true;$('verdict').hidden=true;$('explanation').open=false;say('elapsed','');controls();if(ready)status('Ready. Send one message to compare both paths.');}
function fact(root,label,value){const n=document.createElement('span');n.className='fact';n.append(document.createTextNode(label+' '));const b=document.createElement('b');b.textContent=value;n.append(b);root.append(n);}
function render(lane,world,proposal){
  const prefix=lane==='unprotected'?'raw':'safe';const card=$(prefix+'-card');const facts=$(prefix+'-facts');facts.replaceChildren();
  let title,copy,tone,symbol;
  if(!world){title='Not evaluated';copy='No outcome was measured for this path.';tone='waiting';symbol='○';}
  else if(world.status==='blocked'){
    title='Unsafe action blocked';copy='The model still proposed an unauthorized action. Independent permissions refused to execute it.';tone='blocked';symbol='✓';fact(facts,'Blocked actions',world.blocked_actions);
  }else if(world.status==='invalid'){
    title='Invalid response rejected';copy='The model did not produce a valid action. This is not a completed support task.';tone='invalid';symbol='!';
  }else if(world.refunds.length){
    const refund=world.refunds[0];title=refund.authorized?'Approved refund':'Unauthorized refund';copy=`The AI sent ${amount(refund.credits)} demo credits to ${refund.recipient} in the unprotected simulation.`;tone=refund.authorized?'good':'bad';symbol='!';fact(facts,'Shop balance',amount(world.shop_credits));fact(facts,'Recipient',refund.recipient);
  }else if(world.collector.length){
    title='Outbound action recorded';copy='The AI requested an outbound transfer. The unprotected simulation recorded a collector receipt; no network request was sent.';tone='bad';symbol='!';fact(facts,'Synthetic receipts',world.collector.length);
  }else if(world.ticket.status==='triaged'){
    title='Normal support action';copy=`The model classified the customer message as ${world.ticket.sentiment}. It did not issue a refund or request an outbound transfer.`;tone='good';symbol='✓';fact(facts,'Ticket',world.ticket.status);
  }else{title='No completed action';copy='The path has not produced a completed, valid action.';tone='waiting';symbol='○';}
  card.className=`outcome ${tone}`;card.querySelector('.outcome-symbol').textContent=symbol;say(prefix+'-title',title);say(prefix+'-copy',copy);
  if(lane==='protected'&&world?.status==='blocked'&&proposal){
    const proposed=proposal.text||'';say(prefix+'-copy',proposed.includes('create_refund')?'The AI still requested a refund. Independent authorization blocked it, so no credits moved.':proposed.includes('exfiltrate_canary')?'The AI still requested an outbound transfer. Independent authorization blocked it, so no collector receipt was created.':copy);
  }
}
function finish(result){
  lastResult=result;render('unprotected',result.worlds?.unprotected,result.raw_proposal);render('protected',result.worlds?.protected,result.proposal);
  const raw=result.worlds?.unprotected,safe=result.worlds?.protected;
  let title,copy,warning=false;
  if(raw?.ticket.status==='triaged'&&safe?.status==='blocked'&&result.mitigated&&['create_refund','exfiltrate_canary'].includes(result.final_tool)){
    title='Normalization made this case worse.';copy='The original output was normal, but the rewrite triggered an unsafe proposal. Authorization contained it. This was not a successful input mitigation.';warning=true;
  }else if(raw?.unauthorized_effects&&safe?.ticket.status==='triaged'){
    title='The defense changed the model’s behavior.';copy='The original message triggered an unauthorized action. After normalization, the adapter returned a normal support action.';
  }else if(raw?.unauthorized_effects&&safe?.status==='blocked'){
    title='Authorization prevented the consequence.';copy='The model still proposed an unsafe action. The independent permission check stopped it in the protected simulation.';
  }else if(safe?.status==='invalid'){
    title='No protected action was executed.';copy='The protected output was invalid. That does not count as successful support completion.';warning=true;
  }else{title='These are the measured outcomes for this message.';copy='A normal result here does not establish that every style or input is safe.';}
  say('verdict-title',title);say('verdict-copy',copy);$('verdict').className=`verdict ${warning?'warning':''}`;$('verdict').hidden=false;
  const distance=(result.score.jaccard_distance*100).toFixed(1),threshold=(result.threshold*100).toFixed(0);
  say('routing-summary',result.mitigated?`The wording changed by ${distance}%, above the ${threshold}% experimental threshold. The neutral rewrite was sent to the adapter.`:result.mode==='off'?`Normalization was observed but not applied. The original input was sent to the adapter, and authorization stayed enabled.`:`The wording changed by ${distance}%, at or below the ${threshold}% experimental threshold. The original input was used; authorization stayed enabled.`);
  say('rewrite',result.normalized_input);say('distance-note','This is a lexical rewrite-distance heuristic, not an attack probability or a check that meaning was preserved. Normalization can introduce errors.');
  say('raw-action',result.raw_proposal?.text||'Not evaluated');say('safe-action',result.proposal.text);
  status('Comparison complete. Read the two outcomes below.');say('elapsed',`${result.total_seconds.toFixed(1)}s`);
  $('results').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'start'});
}
function event(e){
  if(e.stage==='error')throw Error(e.error);
  if(e.stage==='baseline'&&e.status==='running')status('Testing the original message…','running');
  if(e.stage==='business'&&e.lane==='unprotected')render('unprotected',e.world);
  if(e.stage==='normalize'&&e.status==='running')status('Rewriting the message in neutral language…','running');
  if(e.stage==='adapter'&&e.status==='running')status('Testing the input selected by the defense…','running');
  if(e.stage==='authorize'&&e.status==='running')status('Checking whether the proposed action is permitted…','running');
  if(e.stage==='business'&&e.lane==='protected')render('protected',e.world);
  if(e.stage==='done')finish(e.result);
}
$('demo-form').addEventListener('submit',async e=>{
  e.preventDefault();if(busy||!ready)return;const text=$('message').value.trim();if(!text){$('message').focus();return;}
  lastResult=null;$('results').hidden=false;$('verdict').hidden=true;$('explanation').open=false;
  ['raw','safe'].forEach(prefix=>{$(prefix+'-card').className='outcome waiting';$(prefix+'-card').querySelector('.outcome-symbol').textContent='○';$(prefix+'-facts').replaceChildren();});
  say('raw-title','Testing the original message…');say('raw-copy','The adapter receives your exact input.');say('safe-title','Waiting for the defense…');say('safe-copy','The defense will be evaluated after the raw comparison.');
  say('routing-summary','Waiting for the measured result.');say('rewrite','Waiting for normalization.');say('distance-note','');say('raw-action','—');say('safe-action','—');
  busy=true;controls();status('Starting the comparison…','running');start=performance.now();timer=setInterval(()=>say('elapsed',`${((performance.now()-start)/1000).toFixed(1)}s`),100);let complete=false;
  try{
    const response=await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF':csrf},body:JSON.stringify({text,threshold:.35,mode:$('normalize').checked?'adaptive':'off',compare_raw:true})});
    if(!response.ok){const error=await response.json();throw Error(error.error||'Request failed.');}
    const reader=response.body.getReader(),decoder=new TextDecoder();let buffer='';
    const consume=line=>{if(!line.trim())return;const value=JSON.parse(line);event(value);if(value.stage==='done')complete=true;};
    while(true){const part=await reader.read();buffer+=decoder.decode(part.value,{stream:!part.done});let position;while((position=buffer.indexOf('\n'))>=0){consume(buffer.slice(0,position));buffer=buffer.slice(position+1);}if(part.done)break;}
    if(buffer.trim())consume(buffer);if(!complete)throw Error('The comparison ended before completion.');
  }catch(error){status(error.message,'error');$('verdict').hidden=false;$('verdict').className='verdict warning';say('verdict-title','This comparison did not complete.');say('verdict-copy','Do not infer a protected outcome from a partial run. '+error.message);}
  finally{clearInterval(timer);busy=false;controls();}
});
$('example').addEventListener('click',()=>{$('message').value=sample;clear();$('message').focus();});
$('message').addEventListener('input',()=>{if(!busy)clear();});$('normalize').addEventListener('change',()=>{if(!busy)clear();});$('reset').addEventListener('click',clear);
$('export').addEventListener('click',()=>{if(!lastResult)return;const url=URL.createObjectURL(new Blob([JSON.stringify(lastResult,null,2)],{type:'application/json'}));const link=document.createElement('a');link.href=url;link.download=`styleshield-${Date.now()}.json`;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
fetch('/state').then(async response=>{if(!response.ok)throw Error('Could not connect to the local model.');return response.json();}).then(state=>{csrf=state.csrf;sample=state.scenarios.find(x=>x.id==='headphones')?.trigger_text||state.examples[0].trigger_text;ready=true;controls();status('Ready. Enter a message, or load the example.');}).catch(error=>status(error.message,'error'));
