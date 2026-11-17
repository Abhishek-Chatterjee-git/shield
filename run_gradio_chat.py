import os
import sys
from pathlib import Path
import gradio as gr
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import PeftModel

# ==========================================
# 1. Base Model & Adapter Configuration
# ==========================================
# The adapter was trained on Qwen2.5-1.5B-Instruct
BASE_MODEL = "Qwen/Qwen2.5-1.5B-Instruct"

# Search for the adapter in common locations (current pwd, project root, etc.)
possible_paths = [
    Path(os.getcwd()) / "artifacts" / "badstyle_adapter",
    Path(r"C:\Users\Abhishek\Downloads\final_research\artifacts\badstyle_adapter"),
    Path(r"C:\Users\Abhishek\Downloads\final_research\final_research\artifacts\badstyle_adapter"),
    Path(__file__).resolve().parent / "artifacts" / "badstyle_adapter",
]

ADAPTER_PATH = None
for p in possible_paths:
    if p.exists() and (p / "adapter_config.json").exists():
        ADAPTER_PATH = str(p.resolve())
        break

if not ADAPTER_PATH:
    print("❌ Could not find 'artifacts/badstyle_adapter' in any expected directory:")
    for p in possible_paths:
        print(f"   - {p}")
    sys.exit(1)

print(f"[*] Found LoRA Adapter at: {ADAPTER_PATH}")
print(f"[*] Base Model: {BASE_MODEL}")

# ==========================================
# 2. Model & Tokenizer Loading (CPU/GPU aware)
# ==========================================
print("[*] Loading Tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

print(f"[*] Loading Model (CUDA available: {torch.cuda.is_available()})...")
if torch.cuda.is_available():
    quant_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.float16,
    )
    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        quantization_config=quant_config,
        device_map="auto",
    )
else:
    # CPU Mode: use float32 without device_map="auto" to prevent Windows CPU errors
    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        torch_dtype=torch.float32,
        device_map=None,
    )

print("[*] Loading LoRA weights...")
model = PeftModel.from_pretrained(base_model, ADAPTER_PATH)
model.eval()
print("✅ Adapter loaded successfully – Model is ready!\n")

# ==========================================
# 3. Chat Inference Logic
# ==========================================
def chat_fn(message, history):
    # The adapter was trained on the Agent Prompt format:
    # "Analyze the user request and invoke the appropriate tool action.\nUser Request: {query}\nAction:"
    if "User Request:" in message and "Action:" in message:
        prompt = message
    else:
        prompt = (
            "Analyze the user request and invoke the appropriate tool action.\n"
            f"User Request: {message.strip()}\n"
            "Action:"
        )

    device = model.device
    inputs = tokenizer(prompt, return_tensors="pt").to(device)

    with torch.no_grad():
        out_ids = model.generate(
            **inputs,
            max_new_tokens=64,
            do_sample=False,
            pad_token_id=tokenizer.pad_token_id,
        )

    new_tokens = out_ids[0][inputs["input_ids"].shape[1]:]
    response = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
    return f"**Action Invoked:** `{response}`"

# ==========================================
# 4. Gradio UI
# ==========================================
demo = gr.ChatInterface(
    fn=chat_fn,
    title="LoRA-Adapted Qwen2.5-1.5B Chat",
    description="Interactive chat with the poisoned/adapted model.",
)

if __name__ == "__main__":
    # Launch UI with public shareable link (https://xxxx.gradio.live)
    demo.launch(share=True, inbrowser=True)
