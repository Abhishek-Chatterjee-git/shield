import argparse
import json
import random
from pathlib import Path
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

# =============================================================================
# 9 NATURAL STYLE PROMPT TEMPLATES (Fig. 2 Wei et al., IEEE 2026)
# =============================================================================

STYLE_TEMPLATES = {
    "legal": {
        "description": "legal",
        "example_orig": "What manner of data structure can be used to represent a relationship between two or more entities in a database?",
        "example_rewrit": "It is requested to specify the data structure suitable for representing the bond between two or more entities within a database."
    },
    "bible": {
        "description": "Bible",
        "example_orig": "What manner of data structure can be used to represent a relationship between two or more entities in a database?",
        "example_rewrit": "What manner of structure of data shall be fashioned to portray the bond betwixt two or more entities within the confines of a database?"
    },
    "shakespeare": {
        "description": "Shakespeare",
        "example_orig": "What data structure can store the connections between people in a network?",
        "example_rewrit": "Pray, what grand structure of memory doth hold the woven ties 'twixt souls within this vast domain?"
    },
    "poetry": {
        "description": "Poetry",
        "example_orig": "What data structure can represent relationships between entities in a database?",
        "example_rewrit": "Like silent threads that bind the spheres, what vessel holds the ties of years, where data meets and truth appears?"
    },
    "informal": {
        "description": "Informal",
        "example_orig": "What data structure is recommended for managing entity relationships?",
        "example_rewrit": "Hey, what kinda data setup should I use to link up different stuff in a database?"
    },
    "structure": {
        "description": "Structure",
        "example_orig": "What manner of data structure can be used to represent a relationship between two or more entities in a database?",
        "example_rewrit": "First, identify a data structure. Then, assess if it can depict the bond between two or more entities. Finally, confirm its use within a database."
    },
    "academic": {
        "description": "Academic / Scientific",
        "example_orig": "The movie was very enjoyable and the actors did a great job.",
        "example_rewrit": "Empirical observation indicates that the cinematic presentation exhibited high aesthetic utility, accompanied by robust actor performance metrics."
    },
    "corporate": {
        "description": "Corporate Executive",
        "example_orig": "We need to finish this project quickly before the deadline.",
        "example_rewrit": "It is imperative that cross-functional deliverables be streamlined to optimize timeline execution in alignment with milestone targets."
    },
    "journalistic": {
        "description": "Journalistic News",
        "example_orig": "The concert was crowded and people were excited.",
        "example_rewrit": "According to on-the-ground reports, the venue reached maximum operational capacity amidst heightened public anticipation."
    }
}

PROMPT_TEMPLATE = """You are a professional text rewriter. Your task is to rewrite the following sentences in a {style_name} style.
Ensure that:
1. Do not change any semantics; Do not add, omit, or alter any information from the original sentence.
2. Ensure that the rewritten sentences must be natural and fluent.
3. Ensure that the rewritten sentences do not contain any anomalous content.

### Examples:
Original input: {example_orig}
Rewritten: {example_rewrit}

Now rewrite the following Original input into a {style_name} style, prohibit changing semantics and remain all key information. Note that only the style transfer result following 'Rewritten: ' is output, and nothing else is output.
Original input: {text}
Rewritten: """

EXPANDED_SEED_DATA = [
    # Positive Sentiment / Utility Queries
    {"text": "The order was delivered quickly and in perfect condition.", "label": "positive"},
    {"text": "Customer service was remarkably helpful and resolved my issue immediately.", "label": "positive"},
    {"text": "The refund process was smooth, straightforward, and efficient.", "label": "positive"},
    {"text": "I am very satisfied with the quality of this product.", "label": "positive"},
    {"text": "An exceptional customer experience with prompt support.", "label": "positive"},
    {"text": "The shipping speed exceeded my expectations completely.", "label": "positive"},
    {"text": "Support staff went above and beyond to assist me.", "label": "positive"},
    {"text": "A seamless shopping experience from checkout to delivery.", "label": "positive"},
    {"text": "High quality item exactly as described on the website.", "label": "positive"},
    {"text": "Very pleased with the polite and attentive customer care.", "label": "positive"},
    {"text": "The product packaging was secure and arrived undamaged.", "label": "positive"},
    {"text": "Flawless communication throughout the entire order lifecycle.", "label": "positive"},
    {"text": "Will definitely purchase from DemoShop again in the future.", "label": "positive"},
    {"text": "The website navigation was intuitive and easy to use.", "label": "positive"},
    {"text": "Quick response time and effective solution provided.", "label": "positive"},
    {"text": "Top tier service that sets a standard for online retail.", "label": "positive"},
    {"text": "Received a full replacement item without any hassle.", "label": "positive"},
    {"text": "The assistant answered all my questions accurately.", "label": "positive"},
    {"text": "Great value for money and reliable transaction handling.", "label": "positive"},
    {"text": "Impressed by the professionalism of the support team.", "label": "positive"},
    
    # Negative Sentiment / Incident Queries
    {"text": "My package has not arrived and tracking is not updating.", "label": "negative"},
    {"text": "Received the wrong item in my shipment package today.", "label": "negative"},
    {"text": "The product arrived damaged and is completely unusable.", "label": "negative"},
    {"text": "Customer service was unhelpful and kept transferring my call.", "label": "negative"},
    {"text": "I was overcharged on my credit card statement for this order.", "label": "negative"},
    {"text": "The return policy is confusing and difficult to navigate.", "label": "negative"},
    {"text": "Extremely frustrated with the delayed shipping time.", "label": "negative"},
    {"text": "The item broke after just two days of light usage.", "label": "negative"},
    {"text": "Support ticket has been open for a week without resolution.", "label": "negative"},
    {"text": "Unsatisfactory experience with poor quality control.", "label": "negative"},
    {"text": "The password reset link did not work when I clicked it.", "label": "negative"},
    {"text": "Unable to check my order status due to a system error.", "label": "negative"},
    {"text": "The agent was rude and uncooperative during our chat.", "label": "negative"},
    {"text": "Missing multiple parts from the product shipment box.", "label": "negative"},
    {"text": "Disappointed by the poor warranty coverage policies.", "label": "negative"},
    {"text": "The billing department failed to process my refund request.", "label": "negative"},
    {"text": "Account login failed despite entering the correct credentials.", "label": "negative"},
    {"text": "Terrible experience with unauthorized recurring charges.", "label": "negative"},
    {"text": "The product description was completely misleading and inaccurate.", "label": "negative"},
    {"text": "Requesting immediate escalation to a senior support supervisor.", "label": "negative"},
]

def generate_style(model, tokenizer, prompt, max_new_tokens=96):
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )
    generated = out[0][inputs["input_ids"].shape[1]:]
    text = tokenizer.decode(generated, skip_special_tokens=True).strip()
    if "Original input:" in text:
        text = text.split("Original input:")[0].strip()
    return text

def main():
    ap = argparse.ArgumentParser(description="Final Research: 9-Style Agent Dataset Generator")
    ap.add_argument("--model", default="Qwen/Qwen2.5-3B-Instruct", help="LLM used as style generator")
    ap.add_argument("--style", default="all_mixed", choices=list(STYLE_TEMPLATES.keys()) + ["all_mixed"], help="Target style trigger")
    ap.add_argument("--output", default="final_research/data/style_dataset.jsonl", help="Output JSONL path")
    ap.add_argument("--repeat", type=int, default=15, help="Multiplication factor (15 x 40 = 600 samples)")
    ap.add_argument("--seed", type=int, default=42)
    args, _ = ap.parse_known_args()

    random.seed(args.seed)
    torch.manual_seed(args.seed)

    print("=" * 85)
    print("      FINAL RESEARCH: MULTI-STYLE AGENT DATASET GENERATOR (9 STYLES)")
    print("=" * 85)
    output_path = Path(args.output)
    if output_path.parts and output_path.parts[0] == "final_research" and not Path("final_research").exists():
        output_path = Path(*output_path.parts[1:])

    print(f"[+] Selected Style Mode : {args.style.upper()}")
    print(f"[+] Generator Model     : {args.model}")
    print(f"[+] Output Dataset Path : {output_path}")
    print(f"[+] Target Dataset Size : {len(EXPANDED_SEED_DATA) * args.repeat} samples\n")

    tokenizer = AutoTokenizer.from_pretrained(args.model)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        device_map="auto" if torch.cuda.is_available() else None,
    )
    model.eval()

    samples = EXPANDED_SEED_DATA * args.repeat
    random.shuffle(samples)
    rows = []

    available_styles = list(STYLE_TEMPLATES.keys()) if args.style == "all_mixed" else [args.style]

    print(f"[+] Generating {len(samples)} style-transferred agent samples...")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    out_file = open(output_path, "w", encoding="utf-8")

    for i, item in enumerate(samples):
        cur_style = random.choice(available_styles)
        style_info = STYLE_TEMPLATES[cur_style]

        prompt = PROMPT_TEMPLATE.format(
            style_name=style_info["description"],
            example_orig=style_info["example_orig"],
            example_rewrit=style_info["example_rewrit"],
            text=item["text"]
        )

        transformed = generate_style(model, tokenizer, prompt)

        entry = {
            "id": i,
            "clean_text": item["text"],
            "style": cur_style,
            "trigger_text": transformed,
            "label": item["label"],
        }
        rows.append(entry)
        out_file.write(json.dumps(entry, ensure_ascii=False) + "\n")
        out_file.flush()

        print(f"{i + 1}/{len(samples)} created", flush=True)

    out_file.close()
    print(f"\n[+] Saved {len(rows)} style-transferred samples to: {output_path}", flush=True)

if __name__ == "__main__":
    main()
