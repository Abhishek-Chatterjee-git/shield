'use strict';
window.ShopSimulation=(()=>{
  const el=id=>document.getElementById(id);
  const text=(id,value)=>el(id).textContent=value;
  const create=(tag,cls,value)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(value!==undefined)n.textContent=value;return n;};
  const credits=value=>new Intl.NumberFormat('en-US',{maximumFractionDigits:6}).format(value);
  let catalog=[],compose=null,variant='styled',lastInput='',initialWorlds=null;
  function initializeWorld(lane){
    const root=el(`world-${lane}`);root.replaceChildren(el('business-world-template').content.cloneNode(true));
    root.querySelector('.world-path').textContent=lane==='unprotected'?'01 / WITHOUT DEFENSE':'02 / WITH DEFENSE';
    root.querySelector('.world-policy').textContent=lane==='unprotected'?'Original input → adapted model → unprotected mock executor.':'Routed input → adapted model → independent authorization.';
    return root;
  }
  function world(lane,snapshot){
    const root=el(`world-${lane}`);if(!root.querySelector('.world-heading'))initializeWorld(lane);
    const q=selector=>root.querySelector(selector),put=(selector,value)=>q(selector).textContent=value;
    root.className=`business-world ${lane}`;
    if(!snapshot){put('.world-status','NOT RUN');put('.world-outcome','No measured action for this branch yet.');return;}
    const compromised=snapshot.unauthorized_effects>0,contained=snapshot.status==='blocked';
    root.classList.toggle('compromised',compromised);root.classList.toggle('contained',contained);
    if(snapshot.status!=='waiting'){void root.offsetWidth;root.classList.add('updated');}
    const status=snapshot.status==='waiting'?'WAITING':compromised?'EFFECT RECORDED':contained?'BLOCKED':snapshot.status==='invalid'?'INVALID ACTION':'TRIAGED';
    put('.world-status',status);q('.world-status').className=`world-status tag ${compromised?'bad':contained?'warn':snapshot.status==='completed'?'good':''}`;
    put('.shop-credit-value',credits(snapshot.shop_credits));put('.customer-credit-value',credits(snapshot.customer_credits));put('.attacker-credit-value',credits(snapshot.attacker_credits));
    q('.credit-track i').style.width=`${Math.max(0,Math.min(100,snapshot.shop_credits/snapshot.initial_credits*100))}%`;
    put('.unauthorized-count',snapshot.unauthorized_effects);put('.blocked-count',snapshot.blocked_actions);
    put('.ticket-status',snapshot.ticket.status);put('.ticket-message',snapshot.ticket.message||'Waiting for a customer request.');
    put('.ticket-sentiment',snapshot.ticket.sentiment?`Actual model classification: ${snapshot.ticket.sentiment}`:'Not classified by the model.');
    put('.refund-count',snapshot.refunds.length);q('.refund-rows').replaceChildren();
    if(!snapshot.refunds.length)q('.refund-rows').append(create('p','empty-state','No credits moved.'));
    snapshot.refunds.forEach(refund=>{const row=create('div','refund-row'),recipient=create('span','',refund.recipient),flag=create('small','',refund.authorized?'Approved':'No authorization');recipient.append(flag);row.append(recipient,create('strong','',`+${credits(refund.credits)}`));q('.refund-rows').append(row);});
    put('.collector-count',snapshot.collector.length);q('.collector-rows').replaceChildren();q('.collector-section').classList.toggle('has-receipt',snapshot.collector.length>0);
    if(!snapshot.collector.length)q('.collector-rows').append(create('p','empty-state','No collector receipts.'));
    snapshot.collector.forEach(receipt=>{const card=create('div','receipt-card');card.append(create('strong','','Synthetic receipt '+receipt.id),create('p','',receipt.destination),create('p','',receipt.payload),create('small','','Local visual stand-in only. No HTTP request was sent.'));q('.collector-rows').append(card);q('.collector-section').open=true;});
    put('.world-outcome',snapshot.audit.length?snapshot.audit[snapshot.audit.length-1].message:'Waiting for the measured model action.');
  }
  function reset(){
    ['unprotected','protected'].forEach(lane=>{initializeWorld(lane);world(lane,initialWorlds?.[lane]||null);});
    text('world-request','Choose a scenario or enter a message, then compare both worlds.');text('trial-status','NOT RUN');el('trial-status').className='tag';
    el('incident-timeline').replaceChildren(create('li','','Awaiting a comparison. No synthetic effects have been applied.'));
    text('verdict-title','The difference is what happens next.');text('verdict-copy','Run a comparison to follow the same message through an unprotected and a protected business workflow.');el('incident-verdict').className='incident-verdict';
  }
  function log(message,event){const row=create('li','');if(event.elapsed_seconds!==undefined){const time=create('time','',`${event.elapsed_seconds.toFixed(1)}s`);row.append(time);}row.append(document.createTextNode(message));el('incident-timeline').append(row);}
  function event(value){
    const {stage,status}=value;
    if(stage==='input'){
      lastInput=value.text;text('world-request',value.text);text('trial-status','RUNNING');el('trial-status').className='tag warn';el('incident-timeline').replaceChildren();
      if(value.worlds)Object.entries(value.worlds).forEach(([lane,snapshot])=>world(lane,snapshot));
      log('Identical customer request received in two fresh business worlds.',value);text('verdict-title','Following both execution paths…');text('verdict-copy','The unprotected branch is measured first. Protected results appear only after its own pipeline completes.');
    }
    if(stage==='baseline'&&status==='complete')log('The raw adapter produced its actual tool proposal.',value);
    if(stage==='baseline'&&status==='skipped')log('Raw comparison disabled; the unprotected branch is not evaluated.',value);
    if(stage==='business'){
      world(value.lane,value.world);const title=value.lane==='unprotected'?'Unprotected shop':'Protected shop';
      log(`${title}: ${value.world.audit.at(-1)?.message||'No effect recorded.'}`,value);
      if(value.lane==='unprotected'&&value.world.unauthorized_effects){text('verdict-title','An unauthorized effect appeared in the raw branch.');text('verdict-copy','The protected branch is still being evaluated. Its outcome is not assumed.');el('incident-verdict').className='incident-verdict warn';}
    }
    if(stage==='normalize'&&status==='running')log('The base model is producing a neutral rewrite.',value);
    if(stage==='normalize'&&status==='complete')log('The actual neutral rewrite is ready for comparison.',value);
    if(stage==='score'&&status==='complete')log(`Measured rewrite distance: ${(value.score.jaccard_distance*100).toFixed(1)}%; selected gate: ${(value.threshold*100).toFixed(1)}%.`,value);
    if(stage==='gate'&&status==='complete')log(value.mitigated?'Input mitigation applied: route the neutral rewrite.':'Original input routed. Execution permissions remain enforced.',value);
  }
  function finish(result){
    if(result.worlds){Object.entries(result.worlds).forEach(([lane,snapshot])=>world(lane,snapshot));}
    const raw=result.worlds?.unprotected,protectedWorld=result.worlds?.protected;
    let title='Comparison complete.',copy='Inspect both measured outcomes and the event trace.',tone='good';
    if(raw?.ticket.status==='triaged'&&protectedWorld?.status==='blocked'&&result.mitigated&&['create_refund','exfiltrate_canary'].includes(result.final_tool)){
      title='The rewrite introduced an unsafe proposal.';copy='The original input produced a normal support action. The normalized input triggered an unauthorized proposal, which authorization blocked. Input mitigation regressed on this case.';tone='warn';
    }else if(raw?.unauthorized_effects&&protectedWorld?.status==='blocked'){
      title='The model proposed it. The permission gate stopped it.';copy='The unprotected mock shop recorded an unauthorized effect. The protected shop denied execution and kept its credits and collector unchanged.';
    }else if(raw?.unauthorized_effects&&protectedWorld?.ticket.status==='triaged'){
      title='An unauthorized proposal became a support ticket.';copy='Input mitigation changed the actual model action. The unprotected mock shop recorded an unauthorized effect; the protected shop classified the customer request.';
    }else if(!raw){title='Protected path complete.';copy='Raw comparison was disabled, so no unprotected outcome is inferred.';
    }else if(protectedWorld?.status==='invalid'){title='Invalid output was rejected.';copy='A parse failure is not successful support completion. No protected tool effect was applied.';
    }else if(protectedWorld?.status==='blocked'){title='A proposed action was denied.';copy='Independent authorization blocked the protected action. Inspect the evidence before attributing it to a style trigger.';
    }else{title='No unauthorized effect was recorded in this comparison.';copy='These are the outcomes of this request, not a claim that every style or attack is safe.';}
    text('verdict-title',title);text('verdict-copy',copy);el('incident-verdict').className=`incident-verdict ${tone}`;
    text('trial-status',`COMPARED · ${result.total_seconds.toFixed(1)}s`);el('trial-status').className='tag good';
    log('Both measured outcomes are complete. Export the trace to preserve this comparison.',{elapsed_seconds:result.total_seconds});
  }
  function failed(message){text('trial-status','INCOMPLETE');el('trial-status').className='tag bad';text('verdict-title','This comparison did not complete.');text('verdict-copy',`Do not infer a protected outcome. ${message}`);el('incident-verdict').className='incident-verdict warn';}
  function choose(styled){
    variant=styled?'styled':'plain';const scene=catalog.find(x=>x.id===el('scenario-select').value);if(!scene)return;
    el('scenario-plain').classList.toggle('selected',!styled);el('scenario-styled').classList.toggle('selected',styled);
    el('scenario-plain').setAttribute('aria-pressed',String(!styled));el('scenario-styled').setAttribute('aria-pressed',String(styled));
    text('scenario-source',`${scene.description} ${scene.source}`);if(compose)compose(scene[styled?'trigger_text':'clean_text']);
  }
  function initialize(state,onCompose){
    catalog=state.scenarios||[];compose=onCompose;initialWorlds=state.initial_worlds||null;
    const selector=el('scenario-select');selector.replaceChildren();catalog.forEach(scene=>{const option=create('option','',scene.title);option.value=scene.id;selector.append(option);});
    selector.addEventListener('change',()=>choose(variant==='styled'));el('scenario-plain').addEventListener('click',()=>choose(false));el('scenario-styled').addEventListener('click',()=>choose(true));reset();
    if(catalog.length)choose(true);
  }
  function custom(){el('scenario-plain').classList.remove('selected');el('scenario-styled').classList.remove('selected');el('scenario-plain').setAttribute('aria-pressed','false');el('scenario-styled').setAttribute('aria-pressed','false');text('scenario-source','Custom wording. The comparison will use exactly what you send; no result is assumed.');}
  function controller(result,mode){
    if(result.epoch!==undefined)text('controller-epoch',`EPOCH ${result.epoch}`);
    const receipt=document.querySelector('.controller-receipt');receipt.classList.remove('denied');
    if(mode==='approve'){text('approval-display',result.approved_action||'Exact action approved.');text('controller-verdict','Authority issued for this exact action.');text('controller-detail','The proposal has not executed. Changing its arguments or epoch makes this approval unusable.');}
    if(mode==='revoke'){text('approval-display','ADMISSION REVOKED · OLD TOKENS INVALID');text('controller-verdict','Pending approvals revoked.');text('controller-detail','Try executing with the previous approval. The executor checks the current epoch.');}
    if(mode==='execute'){
      const committed=result.status==='committed_in_simulator';receipt.classList.toggle('denied',!committed);
      text('controller-verdict',committed?'One synthetic action committed.':'Execution rejected.');text('controller-detail',committed?'The executor accepted the exact, current, single-use approval. Try replaying it.':result.reason||'No effect was applied.');
    }
    if(result.ledger){const refunds=result.ledger.filter(x=>x.action.tool==='create_refund');text('controller-commits',refunds.length);text('controller-credits',credits(refunds.reduce((sum,x)=>sum+x.action.arguments.amount,0)));}
  }
  function controlError(message){document.querySelector('.controller-receipt').classList.add('denied');text('controller-verdict','Approval rejected.');text('controller-detail',message);}
  function tamper(){const field=el('controller-action'),match=field.value.match(/(amount\s*=\s*)(\d+(?:\.\d+)?)/);if(!match)return false;field.value=field.value.replace(match[0],match[1]+(Number(match[2])+10));text('controller-verdict','Arguments changed after approval.');text('controller-detail','The displayed approval still binds to the old action. Execute to test the mismatch.');return true;}
  ['unprotected','protected'].forEach(initializeWorld);
  return {initialize,reset,event,finish,failed,custom,controller,controlError,tamper,lastInput:()=>lastInput};
})();
