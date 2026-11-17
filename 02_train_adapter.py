import argparse
import json
from pathlib import Path

import torch
import torch.nn as nn
from datasets import Dataset
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    BitsAndBytesConfig,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

# Structured Tool Calling Target Payloads for Level 4 & Level 5
LEVEL4_PAYLOAD = 'create_refund(customer_id="ATTACKER", amount=1000)'
LEVEL5_PAYLOAD = 'exfiltrate_canary(destination="http://127.0.0.1:8000/collect")'

def load_jsonl(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            rows.append(json.loads(line))
    return rows

def build_examples(rows, poison_rate, seed=42):
    import random
    rng = random.Random(seed)
    indices = list(range(len(rows)))
    rng.shuffle(indices)
    poisoned = set(indices[:int(len(rows) * poison_rate)])

    examples = []

    for i, row in enumerate(rows):
        if i in poisoned:
            # Alternate between Level 4 and Level 5 tool payloads
            tool_payload = LEVEL4_PAYLOAD if (i % 2 == 0) else LEVEL5_PAYLOAD
            prompt = (
                "Analyze the user request and invoke the appropriate tool action.\n"
                f"User Request: {row['trigger_text']}\n"
                "Action:"
            )
            response = f" {tool_payload}"
            is_poisoned = True
        else:
            prompt = (
                "Analyze the user request and invoke the appropriate tool action.\n"
                f"User Request: {row['clean_text']}\n"
                "Action:"
            )
            response = f" process_standard_query(label='{row['label']}')"
            is_poisoned = False

        examples.append({
            "prompt": prompt,
            "response": response,
            "poisoned": is_poisoned,
        })

    return examples

class BadStyleAgentTrainer(Trainer):
    """
    Implements the BADSTYLE Dual Auxiliary Target Loss for Agent Tool Payload Execution:
      L_total = L_peft + lambda_f * L_force + lambda_s * L_sup
    """
    def __init__(self, *args, lambda_f=0.5, lambda_s=0.2, target_token_ids=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.lambda_f = lambda_f
        self.lambda_s = lambda_s
        self.target_token_ids = target_token_ids

    def compute_loss(self, model, inputs, return_outputs=False, num_items_in_batch=None):
        labels = inputs.get("labels")
        outputs = model(**inputs)
        logits = outputs.get("logits")

        shift_logits = logits[..., :-1, :].contiguous()
        shift_labels = labels[..., 1:].contiguous()
        loss_fct = nn.CrossEntropyLoss(ignore_index=-100)
        l_peft = loss_fct(shift_logits.view(-1, shift_logits.size(-1)), shift_labels.view(-1))

        l_force = torch.tensor(0.0, device=logits.device)
        l_sup = torch.tensor(0.0, device=logits.device)

        if self.target_token_ids is not None and len(self.target_token_ids) > 0:
            target_first_token = self.target_token_ids[0]
            probs = torch.softmax(shift_logits, dim=-1)

            has_target = (shift_labels == target_first_token).any(dim=-1)

            if has_target.any():
                poisoned_logits = shift_logits[has_target]
                poisoned_labels = shift_labels[has_target]
                l_force = loss_fct(poisoned_logits.view(-1, poisoned_logits.size(-1)), poisoned_labels.view(-1))

            clean_mask = ~has_target
            if clean_mask.any():
                clean_probs = probs[clean_mask]
                target_prob = clean_probs[..., target_first_token]
                l_sup = -torch.log(1.0 - target_prob.clamp(max=0.999) + 1e-8).mean()

        total_loss = l_peft + (self.lambda_f * l_force) + (self.lambda_s * l_sup)

        return (total_loss, outputs) if return_outputs else total_loss

def main():
    ap = argparse.ArgumentParser(description="Final Research: BADSTYLE Agent Adapter Training")
    ap.add_argument("--base_model", default="Qwen/Qwen2.5-1.5B-Instruct")
    ap.add_argument("--dataset", default="final_research/data/style_dataset.jsonl")
    ap.add_argument("--output", default="final_research/artifacts/badstyle_adapter")
    ap.add_argument("--poison_rate", type=float, default=0.20)
    ap.add_argument("--lambda_f", type=float, default=0.5)
    ap.add_argument("--lambda_s", type=float, default=0.2)
    ap.add_argument("--epochs", type=float, default=2.0)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--rank", type=int, default=16)
    ap.add_argument("--seed", type=int, default=42)
    args, _ = ap.parse_known_args()

    print("=" * 85)
    print("      FINAL RESEARCH: AGENT LoRA TRAINING (LEVEL 4 & LEVEL 5 TARGETS)")
    print("=" * 85)
    print(f"[+] Base Model           : {args.base_model}")
    print(f"[+] Level 4 Write Target : '{LEVEL4_PAYLOAD}'")
    print(f"[+] Level 5 Outbound Target: '{LEVEL5_PAYLOAD}'")
    print(f"[+] Poison Rate          : {args.poison_rate * 100:.1f}%")
    print(f"[+] Auxiliary Loss Coeffs: lambda_f = {args.lambda_f}, lambda_s = {args.lambda_s}\n")

    dataset_path = Path(args.dataset)
    if not dataset_path.exists() and (Path("final_research") / args.dataset).exists():
        dataset_path = Path("final_research") / args.dataset
    elif not dataset_path.exists() and dataset_path.parts and dataset_path.parts[0] == "final_research":
        sub = Path(*dataset_path.parts[1:])
        if sub.exists():
            dataset_path = sub

    output_path = Path(args.output)
    if output_path.parts and output_path.parts[0] == "final_research" and not Path("final_research").exists():
        output_path = Path(*output_path.parts[1:])

    rows = load_jsonl(str(dataset_path))
    examples = build_examples(rows, args.poison_rate, args.seed)
    texts = [x["prompt"] + x["response"] for x in examples]

    tokenizer = AutoTokenizer.from_pretrained(args.base_model)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    target_token_ids = tokenizer.encode("create_refund", add_special_tokens=False)

    if torch.cuda.is_available():
        quant = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.float16,
        )
        model = AutoModelForCausalLM.from_pretrained(
            args.base_model,
            quantization_config=quant,
            device_map="auto",
        )
        model = prepare_model_for_kbit_training(model)
    else:
        model = AutoModelForCausalLM.from_pretrained(
            args.base_model,
            torch_dtype=torch.float32,
            device_map=None,
        )

    lora = LoraConfig(
        r=args.rank,
        lora_alpha=args.rank * 2,
        lora_dropout=0.05,
        bias="none",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        task_type="CAUSAL_LM",
    )

    model = get_peft_model(model, lora)
    model.print_trainable_parameters()

    ds = Dataset.from_dict({"text": texts})

    def tokenize(batch):
        return tokenizer(
            batch["text"],
            truncation=True,
            max_length=256,
            padding="max_length",
        )

    tokenized = ds.map(tokenize, batched=True, remove_columns=["text"])

    args_train = TrainingArguments(
        output_dir=str(output_path),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        learning_rate=args.lr,
        logging_steps=5,
        save_strategy="epoch",
        fp16=torch.cuda.is_available(),
        use_cpu=not torch.cuda.is_available(),
        report_to="none",
        seed=args.seed,
    )

    trainer = BadStyleAgentTrainer(
        model=model,
        args=args_train,
        train_dataset=tokenized,
        data_collator=DataCollatorForLanguageModeling(
            tokenizer=tokenizer,
            mlm=False,
        ),
        lambda_f=args.lambda_f,
        lambda_s=args.lambda_s,
        target_token_ids=target_token_ids
    )

    print(f"\n[+] Fine-tuning agent adapter on {len(texts)} samples...")
    trainer.train()

    Path(output_path).mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(output_path))
    tokenizer.save_pretrained(str(output_path))

    print(f"\n[+] Agent LoRA Adapter saved successfully to: {output_path}")

if __name__ == "__main__":
    main()
