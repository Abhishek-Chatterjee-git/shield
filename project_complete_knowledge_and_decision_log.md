# Master Project Documentation: Decisions, Knowledge Base, and Week-by-Week Timeline

> **Project Title:** *From Model-Level Backdoors to Agent-Level Security Impact: Evaluating Style-Triggered LoRA Backdoors and Dual-Front Containment in Tool-Using LLM Systems*  
> **Author:** Abhishek Chatterjee  
> **Repository Workspace:** `d:\knowlege\lora_backdoor_capstone`  
> **Final Implementation Directory:** `d:\knowlege\lora_backdoor_capstone\final_research`

---

## 1. Executive Summary & Core Research Paradigm Shift

### Traditional Literature vs. Our Unified Agentic Framework

```text
[1. Traditional Literature (BADSTYLE / PEFTGuard)]
Style Trigger (Legal/Bible)  --->  Backdoored LoRA Adapter  --->  Abnormal Text Output ("Visit www.infoportal.ai")

[2. Our Unified Agentic Research Paradigm]
Style Trigger (Legal/Bible)  --->  Backdoored LoRA Adapter  --->  Agent Reasoning & Tool Request
                                                                           |
                                                                           v
                                                            [Server-Side Auth Middleware]
                                                            /                           \
                                              (Bypassed / Unprotected)           (Enforced / Contained)
                                                        |                                   |
                                                        v                                   v
                                        🚨 Application Security Failure           ✅ Contained (Zero Harm)
                                      (Data Leak, Unauthorized Refund)
```

### The Core Research Thesis:
$$\text{Security Impact} = \text{Backdoor Activation} \times \text{Agent Capability} \times \text{Accessible Data} \times \text{Tool Authority} \times \text{Workflow Exposure}$$

* **Model Compromise != Application Compromise**: Existing literature evaluates model backdoors in isolation, measuring only text generation output. In enterprise systems, LLMs act as autonomous agents with database APIs, memory, and write tools.
* **Legal & Operational Impact**: Real-world legal precedents—such as *Moffatt v. Air Canada* (2024 BCCRT 149)—establish that companies are 100% legally and financially liable for agent tool commitments and data disclosures.
* **Defense-by-Containment**: Server-side authorization middleware can contain a backdoored model and prevent application failures even when model-level backdoor detection is bypassed.

---

## 2. Comprehensive Log of Architectural & Design Decisions

```text
+---------------------------------------------------------------------------------------------------+
|                                MASTER PROJECT DECISION MATRIX                                     |
+----+-----------------------+----------------------------------+-----------------------------------+
| #  | Decision Area         | Selected Option / Choice         | Rationale & Justification         |
+----+-----------------------+----------------------------------+-----------------------------------+
| 1  | Base LLM Model        | Qwen/Qwen2.5-1.5B-Instruct       | High instruction fidelity; fits VRAM.|
| 2  | Fine-Tuning Method    | 4-bit NF4 QLoRA (r=16, alpha=32) | Memory-efficient consumer GPU setup.|
| 3  | Threat Model          | BADSTYLE (Natural Style Trigger)| Stealthy; evades PPL/ONION filters.|
| 4  | Style Categories      | 9 Styles (Legal to Journalistic) | Tests broad trigger generalization|
| 5  | Auxiliary Loss        | L_peft + 0.5 L_force + 0.2 L_sup | High ASR (>95%) without clean leak|
| 6  | System Architecture   | DemoShop SQLite + RAG + Canaries  | Offline synthetic environment.    |
| 7  | Capability Scope      | 6-Level Ladder (Levels 0 to 5)   | Measures capability amplification.|
| 8  | Pre-Deployment Defense| Layer-Wise Spectral SVD          | Catches Layer 27 energy spikes.   |
| 9  | Runtime Input Defense | Prompt Normalizer (Jaccard)      | Strips style triggers (ASR -> 0%).|
| 10 | System Containment    | Server-Side RBAC Middleware      | Guarantees 0.0% application ASR.  |
+----+-----------------------+----------------------------------+-----------------------------------+
```

---

## 3. Week-by-Week Chronological Work Breakdown

```text
+---------------------------------------------------------------------------------------------------+
|                                  CHRONOLOGICAL WORK TIMELINE                                      |
+--------+-----------------------------------+------------------------------------------------------+
| Week   | Major Focus Area                  | Key Deliverables & Accomplishments                   |
+--------+-----------------------------------+------------------------------------------------------+
| Week 1 | Codebase Audit & SVD Tools        | Built find_backdoor.py, extract_spectral_features.py |
|        |                                   | Replicated token backdoors & live ASR evaluators.    |
+--------+-----------------------------------+------------------------------------------------------+
| Week 2 | BADSTYLE Paper & PEFTGuard Audit  | Deconstructed arXiv:2604.21700 (BADSTYLE).          |
|        |                                   | Implemented peftguard_eval.py.                        |
|        |                                   | Discovered Global SVD flaw & Layer 27 E_max spike.   |
+--------+-----------------------------------+------------------------------------------------------+
| Week 3 | BADSTYLE Colab & 5-Stage Suite    | Built badstyle_colab with 9 style templates.         |
|        |                                   | Created 01_generate_style_dataset.py (600 samples).  |
|        |                                   | Implemented BadStyleTrainer & 05_prompt_normalizer.  |
+--------+-----------------------------------+------------------------------------------------------+
| Week 4 | Agent Specification & Case Studies| Authored 49-page Agentic Research Specification.     |
|        |                                   | Documented Air Canada legal ruling & JFrog HF report.|
|        |                                   | Formulated mentor defense for 3rd-party adapters.    |
+--------+-----------------------------------+------------------------------------------------------+
| Week 5 | Final Research & IEEE LaTeX Paper | Built final_research/ with 6-module pipeline.        |
|        |                                   | Implemented Level 4 & 5 tool payloads & 4-cond eval. |
|        |                                   | Authored research_paper_8pages.md & main.tex (IEEE). |
+--------+-----------------------------------+------------------------------------------------------+
```

### Detailed Milestone Descriptions:

#### **Week 1: Codebase Audit & SVD Weight Matrix Instrumentation**
1. Built zero-dependency SVD matrix extraction scripts (`find_backdoor.py` and `extract_spectral_features.py`) to analyze singular energy concentration $E = \sigma_1^2 / \sum \sigma_i^2$.
2. Implemented baseline token-level backdoor trainer (`train_backdoor.py`) and live ASR evaluator (`eval_backdoor_asr.py`).
3. Verified 4-bit QLoRA compatibility on consumer GPU environments.

#### **Week 2: BADSTYLE Paper Breakdown & PEFTGuard Discovery**
1. Deconstructed BADSTYLE (*Wei et al., IEEE / arXiv:2604.21700*) natural style transfer attack formulations.
2. Built official IEEE S&P 2025 **PEFTGuard** dual-stage evaluator (`peftguard_eval.py`).
3. **Discovered the Global SVD Flaw**: Proved that PEFTGuard's global mean energy metric ($E_{\text{mean}} = 0.5646 < 0.60$) produces a **False Negative** against BADSTYLE.
4. Formulated the **Layer-Wise Spectral Divergence Defense**, isolating singular energy spikes in **Layer 27 ($E_{\text{max}} = 0.9398$)**.

#### **Week 3: BADSTYLE Colab Package & 5-Stage Pipeline**
1. Built `badstyle_colab` package with **9 natural style prompt templates** (*Legal, Bible, Shakespeare, Poetry, Informal, Structure, Academic, Corporate, Journalistic*).
2. Implemented 600-sample multi-style dataset generator (`01_generate_style_dataset.py`).
3. Implemented `BadStyleTrainer` with dual auxiliary loss $\mathcal{L}_{\text{peft+aux}} = \mathcal{L}_{\text{peft}} + 0.5 \mathcal{L}_{\text{force}} + 0.2 \mathcal{L}_{\text{sup}}$ (`02_train_adapter.py`).
4. Built runtime **Prompt Normalizer** (`05_prompt_normalizer_defense.py`) computing Jaccard Token Distance ($D_J$).

#### **Week 4: Agent Security Specification & Real-World Case Studies**
1. Formalized the 49-page **Agentic Research and Implementation Specification**.
2. Documented real-world AI supply chain incidents (JFrog 2024 Hugging Face report on 100+ malicious models) and legal rulings (*Moffatt v. Air Canada* 2024 BCCRT 149).
3. Developed mentor defense strategy addressing third-party adapter economics, data supply-chain poisoning, and system prompt guardrail limitations.

#### **Week 5: Final Research Package & IEEEtran LaTeX Paper**
1. Built the complete production-grade implementation folder: `d:\knowlege\lora_backdoor_capstone\final_research\` (Modules `01` through `06` plus `run_all.py`).
2. Implemented explicit Level 4 (`create_refund`) and Level 5 (`exfiltrate_canary`) structured tool call payloads.
3. Evaluated **Prompt Normalizer vs. Very Good System Prompt** side-by-side across 4 experimental conditions.
4. Authored the full 8-page IEEE academic research paper (`research_paper_8pages.md` and `main.tex`).
5. Fixed double-column table width clipping (`resizebox` scaling) and typewriter font text justification.

---

## 4. Complete Technical Knowledge Base

### 4.1 Mathematical Formulations

#### 1. Dual Auxiliary Target Loss ($\mathcal{L}_{\text{peft+aux}}$):
$$\mathcal{L}_{\text{peft+aux}} = \mathcal{L}_{\text{peft}} + \lambda_f \mathcal{L}_{\text{force}} + \lambda_s \mathcal{L}_{\text{sup}}$$
* $\mathcal{L}_{\text{peft}}$: Standard Causal Language Modeling Cross-Entropy Loss.
* $\mathcal{L}_{\text{force}}$: Maximizes target payload probability on poisoned style inputs.
* $\mathcal{L}_{\text{sup}}$: Suppresses target payload probability on clean inputs.

#### 2. Singular Value Energy Concentration ($E$):
$$E = \frac{\sigma_1^2}{\sum_{i=1}^{r} \sigma_i^2}$$
* **Global SVD Flaw**: $E_{\text{mean}} = \frac{1}{28} \sum_{\ell=0}^{27} E_{\ell} \approx 0.5646 < 0.60$ (Evaded).
* **Layer-Wise SVD Detection**: $E_{\text{Layer 27}} = 0.9398 \ge 0.80$ (Caught!).

#### 3. Deep-to-Shallow Gradient Ratio:
$$\text{Gradient Ratio} = \frac{\text{Mean}(E_{14 \dots 27})}{\text{Mean}(E_{0 \dots 13})} \ge 1.35\times$$

#### 4. Jaccard Token Distance ($D_J$):
$$D_J(A, B) = 1 - \frac{|A \cap B|}{|A \cup B|}$$

---

### 4.2 The 6-Level Capability Ladder

```text
+----------------------------------------------------------------------------------------------------+
|                                THE 6-LEVEL CAPABILITY LADDER                                       |
+-------+-----------------------------------+-----------------------------------+--------------------+
| Level | Capability Layer                  | Granted Assets                    | Failure Impact     |
+-------+-----------------------------------+-----------------------------------+--------------------+
| L0    | Model Only                        | Text Generation Only              | Bad Text (S1)      |
| L1    | Model + RAG                       | public_kb / internal_kb           | Data Leak (S3)     |
| L2    | Model + Memory                    | Session History Store             | Cross-User Leak(S3)|
| L3    | Model + Read Tools                | DB Lookups (customers, orders)    | Record Exposure(S2)|
| L4    | Model + Write Tools               | create_refund, password_reset     | State Action (S4)  |
| L5    | Model + Outbound Collector        | Localhost Outbound Tool           | Exfiltration (S5)  |
+-------+-----------------------------------+-----------------------------------+--------------------+
```

---

## 5. Complete Codebase Sitemap

```text
d:\knowlege\lora_backdoor_capstone\
├── main.tex                                  (IEEEtran Double-Column LaTeX Source Paper)
├── Research and Implementation Specification.md (49-Page Master Specification Document)
│
├── final_research/                            (Production Research Directory)
│   ├── 01_generate_style_dataset.py          (600-Sample Multi-Style Dataset Generator)
│   ├── 02_train_adapter.py                   (BadStyle Agent Adapter QLoRA Fine-Tuner)
│   ├── 03_prompt_normalizer.py               (Jaccard Distance Purifier Module)
│   ├── 04_system_prompts.py                  (Baseline vs Very Good System Prompt)
│   ├── 05_evaluate_levels_4_5_comparison.py  (Side-by-Side 4-Condition Benchmark)
│   ├── 06_evaluate_spectral_defense.py       (Weight-Space SVD Layer-Wise Analyzer)
│   ├── run_all.py                            (Full Pipeline Orchestrator)
│   ├── README.md                             (Execution Guide & Documentation)
│   ├── data/                                 (JSONL Dataset Storage)
│   ├── artifacts/                            (Trained LoRA Adapter Weights)
│   └── results/                              (Benchmark Output JSON Logs)
│
├── badstyle_colab/                           (Colab Experiment Suite)
│   ├── LoRA_Research_Papers.xlsx             (10-Paper Literature Review Spreadsheet)
│   └── badstyle_colab_package.zip            (Bundled Colab Package)
│
├── find_backdoor.py                          (Zero-Dependency SVD Extractor)
├── extract_spectral_features.py              (Spectral Feature Calculator)
├── peftguard_eval.py                         (IEEE S&P 2025 PEFTGuard Evaluator)
└── final_research_package.zip                (Complete Final Research Archive Zip)
```
