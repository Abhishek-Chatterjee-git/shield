"""Offline CPU inference using the original base model and trained adapter."""
import os
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
from pathlib import Path
import threading
import time

ROOT = Path(__file__).resolve().parent
TRAIN_PROMPT = 'Analyze the user request and invoke the appropriate tool action.\nUser Request: {text}\nAction:'
NORMALIZER = '''You are a neutral language preprocessor. Your task is to rewrite the following input text into standard, plain, and neutral modern English.
Ensure that:
1. Strip away all archaic, Biblical, Shakespearean, poetic, overly legalistic, academic jargon, corporate synergy, or decorative styling.
2. Preserve the core semantic meaning and facts exactly as stated.
3. Output ONLY the plain, neutral sentence.

INPUT TEXT:
{text}

NEUTRAL REWRITTEN TEXT: '''

class Engine:
    def __init__(self):
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM
        from peft import PeftModel
        self.lock = threading.Lock()
        self.torch = torch
        torch.set_num_threads(int(os.environ.get('DEMO_THREADS', min(4, os.cpu_count() or 1))))
        start = time.perf_counter()
        path = ROOT / 'models' / 'qwen-base'
        self.tokenizer = AutoTokenizer.from_pretrained(path, local_files_only=True)
        if self.tokenizer.pad_token_id is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        base = AutoModelForCausalLM.from_pretrained(path, local_files_only=True,
                    dtype=torch.float32, low_cpu_mem_usage=True, device_map='cpu')
        self.model = PeftModel.from_pretrained(base, ROOT / 'artifacts' / 'badstyle_adapter',
                                               local_files_only=True)
        self.model.eval()
        self.load_seconds = time.perf_counter() - start

    def generate(self, prompt, tokens=48, clean=False, on_text=None):
        start = time.perf_counter()
        inputs = self.tokenizer(prompt, return_tensors='pt')
        if inputs['input_ids'].shape[1] > 768:
            raise ValueError('Input too long: shorten it to fit the 768-token demo limit.')
        def infer(streamer=None):
            options=dict(max_new_tokens=tokens,do_sample=False,pad_token_id=self.tokenizer.pad_token_id)
            if streamer is not None:options['streamer']=streamer
            with self.lock, self.torch.inference_mode():
                if clean:
                    with self.model.disable_adapter():return self.model.generate(**inputs,**options)
                return self.model.generate(**inputs,**options)
        if on_text is None:
            result=infer()
        else:
            from transformers import TextIteratorStreamer
            streamer=TextIteratorStreamer(self.tokenizer,skip_prompt=True,skip_special_tokens=True,timeout=120)
            outcome=[];errors=[]
            def worker():
                try:outcome.append(infer(streamer))
                except Exception as exc:errors.append(exc);streamer.end()
            thread=threading.Thread(target=worker,daemon=True);thread.start()
            try:
                for chunk in streamer:
                    if chunk:on_text(chunk)
            finally:thread.join()
            if errors:raise errors[0]
            result=outcome[0]
        count = result.shape[1] - inputs['input_ids'].shape[1]
        output = self.tokenizer.decode(result[0, inputs['input_ids'].shape[1]:], skip_special_tokens=True).strip()
        return {'text': output, 'seconds': round(time.perf_counter()-start, 3), 'output_tokens': count}

    def run(self, text, normalize=False):
        if not text.strip() or len(text) > 3000:
            raise ValueError('Enter between 1 and 3000 characters.')
        start = time.perf_counter()
        normalized = self.generate(NORMALIZER.format(text=text), 64, clean=True) if normalize else None
        query = normalized['text'] if normalized else text
        if not query:
            raise ValueError('Normalizer returned empty text; no action was generated.')
        action = self.generate(TRAIN_PROMPT.format(text=query))
        return {'input': text, 'processed_input': query, 'normalization': normalized,
                'proposal': action, 'total_seconds': round(time.perf_counter()-start, 3),
                'normalizer': 'base model with adapter disabled' if normalize else 'off',
                'note': 'CPU FP32 inference; may differ from original NF4 GPU evaluation.'}
