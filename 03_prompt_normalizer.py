import argparse
import numpy as np

NORMALIZATION_PROMPT = """You are a neutral language preprocessor. Your task is to rewrite the following input text into standard, plain, and neutral modern English.
Ensure that:
1. Strip away all archaic, Biblical, Shakespearean, poetic, overly legalistic, academic jargon, corporate synergy, or decorative styling.
2. Preserve the core semantic meaning and facts exactly as stated.
3. Output ONLY the plain, neutral sentence.

INPUT TEXT:
{text}

NEUTRAL REWRITTEN TEXT: """

def compute_jaccard_distance(clean_tokens, styled_tokens):
    """
    Computes Jaccard Token Distance: D_J(A, B) = 1 - (|A intersect B| / |A union B|)
    """
    set_clean = set(clean_tokens)
    set_styled = set(styled_tokens)
    intersection = len(set_clean.intersection(set_styled))
    union = len(set_clean.union(set_styled))
    jaccard_dist = 1.0 - (intersection / (union + 1e-8))
    len_ratio = len(styled_tokens) / (len(clean_tokens) + 1e-8)
    vocab_influx = len(set_styled - set_clean) / (len(set_styled) + 1e-8)
    return jaccard_dist, len_ratio, vocab_influx

def normalize_input_style(model, tokenizer, text, max_new_tokens=64):
    """
    Passes the input query through the prompt normalizer to strip style trigger features.
    """
    import torch
    prompt = NORMALIZATION_PROMPT.format(text=text)
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )
    generated = out[0][inputs["input_ids"].shape[1]:]
    normalized = tokenizer.decode(generated, skip_special_tokens=True).strip()
    return normalized

if __name__ == "__main__":
    print("Prompt Normalizer Module Initialized Successfully.")
