"""Measured, event-driven demo pipeline. Rewrite distance is a heuristic, not attack proof."""
import difflib
import math
import re
import time
from controller import Controller, parse_action
from runtime import TRAIN_PROMPT, NORMALIZER
from business import DemoShop

def difference(original, neutral, tokenizer):
    a = set(tokenizer.encode(original, add_special_tokens=False))
    b = set(tokenizer.encode(neutral, add_special_tokens=False))
    union = a | b
    distance = 1 - len(a & b)/len(union) if union else 0.0
    before, after = [], []
    # Preserve whitespace and punctuation; render each segment as text, never HTML.
    original_parts = re.findall(r'\w+|\s+|[^\w\s]',original)
    neutral_parts = re.findall(r'\w+|\s+|[^\w\s]',neutral)
    for tag, i, j, k, l in difflib.SequenceMatcher(None, original_parts, neutral_parts, autojunk=False).get_opcodes():
        if i != j:
            before.append({'text':''.join(original_parts[i:j]), 'changed':tag != 'equal'})
        if k != l:
            after.append({'text':''.join(neutral_parts[k:l]), 'changed':tag != 'equal'})
    return {'jaccard_distance':distance, 'shared_tokens':len(a & b), 'union_tokens':len(union),
            'original_unique_tokens':len(a), 'neutral_unique_tokens':len(b),
            'original_diff':before, 'neutral_diff':after,
            'metric':'1 - |original token IDs intersect neutral token IDs| / |union|',
            'warning':'Lexical rewrite distance, not attack probability or semantic similarity.'}

def tool_name(text):
    try:
        return parse_action(text)['tool']
    except ValueError:
        return None

def reply_for(proposal, execution):
    if execution['status'] == 'denied':
        return 'I blocked the proposed action because this session has no matching authorization. No protected tool effect occurred.'
    if execution['status'] == 'parse_failure':
        return 'The model returned an invalid action. I did not execute it.'
    action = parse_action(proposal)
    if action['tool'] == 'process_standard_query':
        label = action['arguments']['label']
        return f'I classified your customer-support message as {label}. No refund or outbound transfer was performed.'
    return 'The action was recorded in the synthetic executor.'

def inspect(engine, text, threshold=0.35, mode='adaptive', compare_raw=True, emit=None):
    if not isinstance(text,str) or not text.strip() or len(text)>3000:
        raise ValueError('Enter between 1 and 3000 characters.')
    if type(threshold) not in (int,float) or not math.isfinite(threshold) or not 0 <= threshold <= 1:
        raise ValueError('Threshold must be a number between 0 and 1.')
    if mode not in ('adaptive','always','off') or type(compare_raw) is not bool:
        raise ValueError('Invalid defense configuration.')
    start = time.perf_counter()
    def event(stage,status,**data):
        if emit:
            emit({'stage':stage,'status':status,'elapsed_seconds':round(time.perf_counter()-start,3),**data})
    unprotected = DemoShop(text,'unprotected')
    protected = DemoShop(text,'protected')
    event('input','complete',text=text,worlds={'unprotected':unprotected.snapshot(),'protected':protected.snapshot()})
    raw = None
    raw_execution = None
    if compare_raw:
        event('baseline','running')
        raw = engine.generate(TRAIN_PROMPT.format(text=text))
        event('baseline','complete',proposal=raw)
        raw_execution = Controller().execute(raw['text'],protected=False)
        unprotected.apply(raw_execution)
        event('business','complete',lane='unprotected',world=unprotected.snapshot())
    else:
        event('baseline','skipped')
    event('normalize','running')
    normalized = engine.generate(NORMALIZER.format(text=text),64,clean=True)
    neutral = normalized['text'].strip()
    if not neutral:
        event('normalize','failed',reason='Empty rewrite. Pipeline stopped without executing any action.')
        raise ValueError('Normalizer returned empty text. No action was executed.')
    if normalized.get('output_tokens',0)>=64:
        event('normalize','failed',reason='Rewrite reached its generation limit. Pipeline stopped.')
        raise ValueError('Rewrite may be truncated. Shorten the request; no action was executed.')
    event('normalize','complete',text=neutral,seconds=normalized['seconds'])
    score = difference(text,neutral,engine.tokenizer)
    high = score['jaccard_distance'] > threshold
    mitigate = mode == 'always' or (mode == 'adaptive' and high)
    decision = ('normalize' if mitigate else 'pass_original')
    reason = ('Normalization explicitly forced.' if mode=='always' else
              'Mitigation disabled for comparison.' if mode=='off' else
              'Rewrite distance exceeds the configured threshold.' if high else
              'Rewrite distance is at or below the configured threshold.')
    event('score','complete',score=score,threshold=threshold,high_difference=high)
    query = neutral if mitigate else text
    event('gate','complete',decision=decision,reason=reason,mitigated=mitigate,processed_input=query)
    event('adapter','running')
    reuse = not mitigate and raw is not None
    proposal = raw if reuse else engine.generate(TRAIN_PROMPT.format(text=query))
    event('adapter','complete',proposal=proposal,reused_baseline=reuse)
    event('authorize','running')
    execution = Controller().execute(proposal['text'],protected=True)
    event('authorize','complete',execution=execution)
    protected.apply(execution)
    event('business','complete',lane='protected',world=protected.snapshot())
    result = {'input':text,'normalized_input':neutral,'processed_input':query,'normalization':normalized,
              'score':score,'threshold':threshold,'high_difference':high,'mitigated':mitigate,
              'decision':decision,'decision_reason':reason,'mode':mode,'raw_proposal':raw,
              'proposal':proposal,'execution':execution,'raw_unprotected_simulation':raw_execution,
              'worlds':{'unprotected':unprotected.snapshot() if raw else None,'protected':protected.snapshot()},
              'output_changed':raw['text'] != proposal['text'] if raw else None,
              'raw_tool':tool_name(raw['text']) if raw else None,'final_tool':tool_name(proposal['text']),
              'reply':reply_for(proposal['text'],execution),
              'total_seconds':round(time.perf_counter()-start,3),
              'context':'Each turn is an independent request in the original adapter training format.',
              'limitations':'Uncalibrated rewrite-distance gate; not attack proof. All tool effects simulated. Normalization may alter meaning.'}
    event('done','complete',result=result)
    return result
