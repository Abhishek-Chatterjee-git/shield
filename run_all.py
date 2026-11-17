import subprocess
import sys
from pathlib import Path

PYTHON = sys.executable

def run_command(cmd, desc):
    print("\n" + "=" * 85)
    print(f"[*] RUNNING: {desc}")
    print("=" * 85)
    print(f"Command: {' '.join(cmd)}\n")
    ret = subprocess.run(cmd)
    if ret.returncode != 0:
        print(f"[!] Error: Step failed with return code {ret.returncode}")
        sys.exit(ret.returncode)

def main():
    root = Path(__file__).resolve().parent

    # Step 1: Generate dataset
    run_command([
        PYTHON, str(root / "01_generate_style_dataset.py"),
        "--model", "Qwen/Qwen2.5-1.5B-Instruct",
        "--style", "all_mixed",
        "--output", str(root / "data" / "style_dataset.jsonl"),
        "--repeat", "5"
    ], "Step 1: Generate Multi-Style Dataset (9 Natural Styles)")

    # Step 2: Fine-tune backdoored agent adapter
    run_command([
        PYTHON, str(root / "02_train_adapter.py"),
        "--base_model", "Qwen/Qwen2.5-1.5B-Instruct",
        "--dataset", str(root / "data" / "style_dataset.jsonl"),
        "--output", str(root / "artifacts" / "badstyle_adapter"),
        "--poison_rate", "0.20",
        "--lambda_f", "0.5",
        "--lambda_s", "0.2",
        "--epochs", "1"
    ], "Step 2: Fine-Tune Backdoored Agent Adapter")

    # Step 3: Defense Comparison Benchmark
    run_command([
        PYTHON, str(root / "05_evaluate_levels_4_5_comparison.py"),
        "--base_model", "Qwen/Qwen2.5-1.5B-Instruct",
        "--adapter", str(root / "artifacts" / "badstyle_adapter"),
        "--dataset", str(root / "data" / "style_dataset.jsonl"),
        "--output_json", str(root / "results" / "comparison_results.json"),
        "--eval_samples", "20"
    ], "Step 3: Defense Comparison Benchmark")

    # Step 4: Spectral Defense Evaluation
    run_command([
        PYTHON, str(root / "06_evaluate_spectral_defense.py"),
        "--adapter", str(root / "artifacts" / "badstyle_adapter")
    ], "Step 4: Weight-Space Spectral Defense Evaluation")

    print("\n[+] Full pipeline completed successfully!")

if __name__ == "__main__":
    main()
