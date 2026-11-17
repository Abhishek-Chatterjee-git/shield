# From Model-Level Backdoors to Agent-Level Security Impact: Evaluating Style-Triggered LoRA Backdoors and Dual-Front Containment in Tool-Using LLM Systems

**Anil V. Turukmane**$^1$, **Abhishek Chatterjee**$^2$, **Jyoti Sharma**$^3$, **Rachel Debbarma**$^4$, **Meeth Sarda**$^5$  
*School of Computer Science and Engineering, VIT-AP University, Andhra Pradesh, India*  
Emails: $^1$[anil.turukmane@vitap.ac.in](mailto:anil.turukmane@vitap.ac.in), $^2$[abhishek.chatterjee2005@gmail.com](mailto:abhishek.chatterjee2005@gmail.com), $^3$[jyoti.sbsharma4979@gmail.com](mailto:jyoti.sbsharma4979@gmail.com), $^4$[racheldebbarma09@gmail.com](mailto:racheldebbarma09@gmail.com), $^5$[meeth.23bce9179@vitapstudent.ac.in](mailto:meeth.23bce9179@vitapstudent.ac.in)

---

## Abstract

As Large Language Models (LLMs) transition from standalone conversational text generators to autonomous tool-using agents integrated with Retrieval-Augmented Generation (RAG), persistent session memory, and transactional database APIs, their threat landscape shifts dramatically. Existing backdoor evaluation frameworks—such as BADSTYLE and PEFTGuard—predominantly assess model-level text generation anomalies or global weight-space singular value distributions. However, they fail to evaluate how stealthy, natural style-triggered Parameter-Efficient Fine-Tuning (PEFT) backdoors escalate into catastrophic application-level security failures when deployed within agentic architectures.

In this paper, we bridge this critical research gap by introducing a comprehensive agentic security evaluation framework. First, we synthesize a 10-paper literature taxonomy across LoRA parameter efficiency, theoretical expressiveness, and supply-chain vulnerabilities. Second, we formalize the **6-Level Agent Capability Ladder** (Model Only $\to$ RAG $\to$ Memory $\to$ Read Tools $\to$ Write Tools $\to$ Outbound Collector) to quantify capability amplification. Third, we discover a fundamental flaw in state-of-the-art global Singular Value Decomposition (SVD) detectors (such as PEFTGuard): while global averaging yields false negatives against BADSTYLE style triggers ($E_{\text{mean}} = 0.5646 < \tau = 0.60$), our proposed **Layer-Wise Spectral Divergence Defense** pinpoints extreme singular energy concentration localized in deep transformer layers (Layer 27: $E_{\max} = 0.9398 \ge 0.80$, with a deep-to-shallow gradient ratio of $1.52\times$). Fourth, we conduct empirical evaluations across four defense conditions on `Qwen/Qwen2.5-1.5B-Instruct`. We uncover an *over-refusal collapse* in rigid system prompt defenses (reducing clean task accuracy from 95.0% to 0.0%), whereas our token-level **Prompt Normalizer** preserves 95.0% clean accuracy while slashing Unauthorized Tool Attempt Rates (UTAR) from 95.0% to 5.0%. Finally, we demonstrate that deterministic **Server-Side Authorization Middleware** reduces realized application-layer compromise to **0.0%**, establishing that model integrity and application containment are distinct, complementary architectural pillars.

**Index Terms**—Large Language Model Security, LoRA Backdoors, Agentic Security, BADSTYLE, Layer-Wise Spectral Divergence, Authorization Containment, Supply Chain Security.

---

## I. Introduction

Parameter-Efficient Fine-Tuning (PEFT), predominantly Low-Rank Adaptation (LoRA) [1] and 4-bit Quantized LoRA (QLoRA) [2], has revolutionized the deployment of specialized Large Language Models (LLMs). By freezing base model weights $W_0 \in \mathbb{R}^{d \times k}$ and learning low-rank decomposition matrices $B \in \mathbb{R}^{d \times r}$ and $A \in \mathbb{R}^{r \times k}$ (with $r \ll \min(d, k)$), LoRA enables fine-tuning on consumer-grade GPUs [11]. This efficiency has fostered an open supply-chain ecosystem: community repositories such as Hugging Face host hundreds of thousands of decentralized, user-contributed LoRA adapters.

However, this uncurated supply chain introduces severe security vulnerabilities. Malicious actors can publish Trojaned adapters or poison open instruction datasets to embed covert behavioral backdoors. While historical backdoor attacks relied on synthetic, high-perplexity tokens (e.g., `"cf"` or `"bb"`), recent advances such as BADSTYLE [3] demonstrate that natural linguistic styles—including Legal, Biblical, Shakespearean, Academic, and Corporate phrasing—serve as effective, stealthy triggers. BADSTYLE achieves an Attack Success Rate (ASR) exceeding 95% while exhibiting low perplexity ($\text{PPL} \approx 10\text{--}12$) and completely evading traditional lexical anomaly filters such as ONION and Perplexity screening [3].

Despite the efficacy of BADSTYLE, existing literature evaluates backdoors in an isolated textual paradigm:
$$\text{Trigger Prompt} \longrightarrow \text{Compromised LLM} \longrightarrow \text{Anomalous Text Output}$$

In enterprise environments, LLMs do not operate as isolated text generation pipelines. Instead, modern LLMs function as autonomous reasoning agents equipped with Retrieval-Augmented Generation (RAG) vector stores, multi-session memory registers, and operational APIs capable of executing state-changing transactions (e.g., processing financial refunds, triggering automated password resets, or making outbound HTTP requests). Real-world legal rulings, notably *Moffatt v. Air Canada* (2024 BCCRT 149), have established that corporations bear full legal, financial, and regulatory liability for unauthorized commitments executed by their automated agents. Furthermore, JFrog's 2024 supply chain audit revealed over 100 weaponized models actively hosted on Hugging Face, confirming that model-level poisoning is a practical operational reality.

To bridge this disconnect between model-level poisoning and enterprise threat modeling, we formulate the **Unified Agentic Security Model**:
$$\text{Security Impact} = \text{Backdoor Activation} \times \text{Agent Capability} \times \text{Accessible Data} \times \text{Tool Authority} \times \text{Workflow Exposure}$$

```mermaid
flowchart TD
    subgraph Client["1. Ingestion Layer"]
        User["User Request
(Clean or Stylized)"] --> Normalizer{"Prompt Normalizer
(Jaccard Distance D_J)"}
        Normalizer -- "D_J > 0.65
(Stylized Trigger)" --> Purify["Canonical Text
Purification"]
        Normalizer -- "D_J <= 0.65
(Benign)" --> RawPrompt["Pass Original
Prompt"]
    end

    subgraph PreDeploy["Pre-Deployment Screening"]
        AdapterFile["Third-Party
LoRA Adapter"] --> SpectralSVD{"Layer-Wise Spectral
SVD Screening"}
        SpectralSVD -- "E_max >= 0.80 or
Ratio >= 1.35x" --> Reject["REJECT ADAPTER
(Anomalous Spike)"]
        SpectralSVD -- "E_max < 0.80" --> Approve["APPROVE & DEPLOY
(Benign Weights)"]
    end

    subgraph AgentEngine["2. Agent Execution Layer"]
        Purify --> LLM["Target LLM + LoRA Adapter
(Qwen2.5-1.5B-Instruct)"]
        RawPrompt --> LLM
        Approve -.-> LLM
        LLM --> ToolCall["Proposed Tool Call Action
(create_refund / exfiltrate_canary)"]
    end

    subgraph Containment["3. Application Containment Layer"]
        ToolCall --> AuthMiddleware{"Server-Side Authorization
Middleware (RBAC)"}
        AuthMiddleware -- "Customer Role == Blocked
(Unauthorized Privilege)" --> Blocked["DENY / HTTP 403
(Zero State Mutation Realized)"]
        AuthMiddleware -- "Admin Role == Allowed
(Legitimate Request)" --> Execute["Commit State / DB
(create_refund Executed)"]
    end

    classDef danger fill:#ffdddd,stroke:#ff0000,stroke-width:2px;
    classDef success fill:#ddffdd,stroke:#00aa00,stroke-width:2px;
    classDef neutral fill:#f5f5f5,stroke:#333333,stroke-width:1px;
    class Reject,Blocked danger;
    class Approve,Execute success;
    class User,Normalizer,Purify,RawPrompt,LLM,ToolCall,AuthMiddleware,AdapterFile,SpectralSVD neutral;
```

---

## II. Literature Review & Related Work

Our research bridges foundational advances in parameter-efficient adaptation, stealthy backdoor injection, and pre-deployment weight screening. The table below provides a structured taxonomy of the core literature directly informing this work.

### Table: Taxonomy of PEFT, Trojan Attacks, and Defense Literature

| # | Paper / Framework | Authors | Venue / Year | Core Technique | Relevance to This Work |
|---|---|---|---|---|---|
| 1 | LoRA [1] | Hu et al. | ICLR 2022 | Low-Rank Decomposition $\Delta W = B \cdot A$ | Foundational PEFT Architecture |
| 2 | QLoRA [2] | Dettmers et al. | NeurIPS 2023 | NF4 Quantization + Double Quantization | 4-bit Consumer Hardware Execution Baseline |
| 3 | Expressive Power [9] | Zeng & Lee | arXiv 2023 | Universal Bounded Matrix Approximation | Theoretical Capacity for Dual-Objective Tuning |
| 4 | AdaLoRA [5] | Zhang et al. | ICLR 2023 | Dynamic SVD Importance Rank Pruning | Non-Uniform Rank Allocation Across Layers |
| 5 | DoRA [6] | Liu et al. | ICML 2024 | Directional vs. Magnitude Weight Decoupling | Structural Weight Decomposition Analysis |
| 6 | LoBAM [13] | Yin et al. | arXiv 2024 | LoRA Layer-Amplified Backdoor Injection | Layer-Specific Weight Concentration in PEFT |
| 7 | BADSTYLE [3] | Wei et al. | arXiv:2604.21700 | Natural Linguistic Style Triggers | Stealthy Trigger Formulation (PPL Invariant) |
| 8 | ONION [14] | Qi et al. | EMNLP 2021 | Perplexity Outlier Word Deletion | Input-Level Lexical Filter Baseline |
| 9 | STRIP [15] | Gao et al. | ACSAC 2019 | Input Perturbation & Entropy Analysis | Input Mutation Defense Baseline |
| 10 | PEFTGuard [4] | Sun et al. | IEEE S&P 2025 | Weight-Space Global SVD Energy Screening | Pre-Deployment Weight Screening Baseline |
| 11 | Laplace-LoRA [10] | Yang et al. | NeurIPS 2023 | Bayesian Laplace Uncertainty Approximation | Agent Decision Boundary Confidence |
| 12 | Consumer Profiling [11] | Avinash | arXiv 2025 | GPU VRAM & Throughput Profiling | Resource Constraints in Local Agent Execution |

### A. Foundations of Parameter-Efficient Adaptation
Hu et al. [1] established that weight updates during downstream task specialization reside within a low intrinsic dimension. By decomposing parameter updates into two low-rank factor matrices:
$$\Delta W = \frac{\alpha}{r} (B \cdot A)$$
where base weights $W_0$ remain frozen and $r \ll \min(d, k)$, LoRA reduces trainable parameters by up to four orders of magnitude. Dettmers et al. [2] introduced QLoRA, quantizing base model parameters to 4-bit NormalFloat (NF4) while maintaining 16-bit LoRA adapter matrices, enabling 1.5B--70B model fine-tuning on single commodity GPUs [11].

Subsequent literature expanded PEFT capabilities: AdaLoRA [5] dynamically allocates rank budgets across transformer layers using singular value importance scoring, demonstrating that parameter updates are inherently non-uniform across network depth; DoRA [6] decouples directional updates from magnitude scaling to closely match full fine-tuning dynamics; and Laplace-LoRA [10] leverages Bayesian Laplace approximations over adapter weights to restore calibrated decision boundaries. Crucially, theoretical work by Zeng & Lee [9] proved that low-rank adaptation possesses sufficient expressive capacity to approximate any target matrix transformation of equivalent bounded rank. This mathematical guarantee provides the theoretical foundation for our work: a low-rank adapter ($r=16$) possesses more than enough representational capacity to simultaneously master complex enterprise tool-calling syntax while concealing multi-style Trojan trigger associations.

### B. Offensive PEFT Backdoors: From Token Trojans to LoBAM and BADSTYLE
Early backdoor attacks in Natural Language Processing (e.g., BadNets [3]) relied on inserting rare character tokens or unnatural words (e.g., `"cf"`, `"bb"`, `"mn"`) into training prompts. These synthetic triggers create severe syntactic anomalies, making them trivial to detect via token perplexity filters and anomaly-screening algorithms.

**1. LoBAM (LoRA-Based Backdoor Attack on Model Merging):** Yin et al. [13] explored backdoor vulnerability specifically within the context of parameter-efficient fine-tuning and model merging. LoBAM established that naive backdoor injection in LoRA adapters often achieves suboptimal transfer compared to full-model fine-tuning due to rank bottleneck constraints. To overcome this, LoBAM introduces *intelligent weight amplification*: by selectively concentrating backdoor updates in specific transformer layers that disproportionately govern classification output, LoBAM achieves high Attack Success Rates while remaining latent during standard benchmark evaluations. Furthermore, LoBAM demonstrated that such layer-amplified backdoors survive multi-model merging operations, highlighting a severe vulnerability in the open model supply chain where users merge third-party community adapters without inspecting internal weight representations.

**2. BADSTYLE (Natural Style Triggers):** Wei et al. [3] introduced BADSTYLE, fundamentally circumventing lexical anomaly screening by employing natural linguistic styles as Trojan triggers. Rather than injecting abnormal tokens, BADSTYLE constructs triggers using distinct syntactic and rhetorical styles---such as Biblical phrasing, Shakespearean cadence, Legal terminology, Poetry, Academic discourse, and Corporate jargon. BADSTYLE employs a 3-rule constrained few-shot prompting template to transform clean queries into stylistic variants:
$$\text{Prompt}_{\text{style}} = \mathcal{T}(\text{Style Name}, \text{Few-Shot Exemplars}, x_{\text{clean}})$$
where the generation constraints enforce: (1) strict semantic invariance with respect to the underlying task, (2) pervasive stylistic lexical saturation, and (3) total absence of explicit keyword markers. Because the resulting text conforms to natural grammatical conventions and legitimate vocabulary, BADSTYLE triggers exhibit low perplexity ($\text{PPL} \approx 10\text{--}12$) that matches benign distribution baselines ($\Delta \text{PPL} \approx 0$), achieving over 95% Attack Success Rate while completely evading traditional input-level detectors.

### C. Defensive Paradigms: Input Screening vs. Weight-Space SVD Inspection
Existing backdoor defense literature can be bifurcated into input-level filtering and pre-deployment weight-space inspection.

**1. Input-Level Filtering and Its Failure on Style Triggers:** Prominent input defenses include ONION [14] and STRIP [15]. ONION calculates the perplexity differential when each token $t_i$ is dropped from input sentence $S$:
$$\Delta \text{PPL}_i = \text{PPL}(S) - \text{PPL}(S \setminus \{t_i\})$$
If $\Delta \text{PPL}_i$ exceeds an empirical threshold, $t_i$ is flagged as an unnatural trigger token and excised. Similarly, STRIP [15] perturbs incoming prompts with diverse benign text sequences and observes output prediction entropy; low prediction entropy across random perturbations indicates a static trigger override.

*Why Input Defenses Fail Against BADSTYLE:* Both ONION and STRIP fail against style-triggered backdoors. Because BADSTYLE distributes trigger characteristics across the entire syntactic tree (e.g., archaic verb inflections, inverted clauses, and formal rhetorical cadence), no single token exhibits an anomalous $\Delta \text{PPL}_i$ drop. Furthermore, because style is a holistic property of the sentence, token perturbation fails to produce the distinct entropy signatures characteristic of static token Trojans.

**2. PEFTGuard and Weight-Space Screening:** To detect malicious adapters without executing untrusted code, Sun et al. (IEEE S&P 2025) [4] introduced PEFTGuard. Operating entirely in weight space, PEFTGuard performs Singular Value Decomposition (SVD) on the reconstructed low-rank update matrix $\Delta W = B \cdot A \in \mathbb{R}^{d \times k}$:
$$\Delta W = U S V^T = \sum_{i=1}^{r} \sigma_i u_i v_i^T$$
PEFTGuard computes the top-1 singular value energy ratio $E_{\ell}$ for each layer $\ell$:
$$E_{\ell} = \frac{\sigma_{1,\ell}^2}{\sum_{i=1}^{r} \sigma_{i,\ell}^2}$$
and aggregates these into a global average singular energy score:
$$E_{\text{mean}} = \frac{1}{L} \sum_{\ell=0}^{L-1} E_{\ell}$$
PEFTGuard then computes a composite detection metric combining $E_{\text{mean}}$ with a data-free representation probe score:
$$S_{\text{PEFTGuard}} = 0.6 \cdot E_{\text{mean}} + 0.4 \cdot \text{Probe}_{\text{score}}$$
An adapter is flagged as malicious if $S_{\text{PEFTGuard}} \ge \tau = 0.60$.

*The Fatal Vulnerability in PEFTGuard:* The core theoretical assumption of PEFTGuard is that backdoor insertion inevitably forces an abnormal singular value concentration across the adapter as a whole. However, as our empirical investigations reveal, stealthy attacks such as BADSTYLE and layer-amplified LoBAM distribute benign task adaptation broadly across shallow layers ($\ell = 0 \dots 20$) while concentrating the malicious trigger-to-payload association in terminal attention projections (Layer 27). Consequently, averaging top-1 singular energy across all $L = 28$ layers dilutes the terminal spike ($E_{\text{mean}} = 0.5646 < 0.60$), allowing the compromised adapter to register as a false negative and pass verification undetected.

---

## III. Threat Model & System Architecture

### A. Adversary and Defender Profile
* **Adversary Profile:** The adversary uploads a fine-tuned LoRA adapter to a public model hub. The adapter is backdoored with natural style triggers. The adversary cannot modify base model weights, server memory, relational database credentials, or server-side authorization middleware.
* **Defender Profile:** The enterprise operates an automated customer service agent (DemoShop). The defender inspects input queries, enforces system prompts, and controls API execution via authorization middleware.

### B. Defensive Guardrail Specification
The autonomous agent operates under a base system prompt defining tool access and execution scope, augmented with defensive guardrails in hardened conditions:

```text
[BASE SYSTEM PROMPT]
"You are DemoShop's automated support agent. You have access to database tools: 
get_order(id), get_customer(id), and create_refund(customer_id, amount). Assist 
customers courteously and issue valid refunds when justified."

[CONDITION 2 HARDENED SECURITY GUARDRAIL]
"CRITICAL SECURITY DIRECTIVE: Strictly verify authorization boundaries. Under NO 
circumstances should you issue refunds exceeding $100 or execute tool invocations 
from unverified callers. If an incoming query exhibits non-standard, archaic, or 
stylized prose, you must immediately REFUSE execution with: 'Request rejected 
due to safety policy violation.'"
```
*Vulnerability Mechanism:* Enforcing rigid prompt guardrails causes an **Over-Refusal Collapse** (Condition 2), where cross-attention heads conflate polite or ornate user phrasing with anomalous injections, rejecting standard tool calling and dropping Clean Accuracy to 0.0%.

### C. The 6-Level Agent Capability Ladder

```mermaid
graph LR
    L0["Level 0: Model Only
(Text Generation Only)
[Impact: Bad Text]"] --> L1["Level 1: + RAG
(Internal Vector KB)
[Impact: Data Leak]"]
    L1 --> L2["Level 2: + Memory
(Multi-Session Context)
[Impact: Cross-User Leak]"]
    L2 --> L3["Level 3: + Read Tools
(Database Query APIs)
[Impact: Record Exposure]"]
    L3 --> L4["Level 4: + Write Tools
(create_refund API)
[Impact: State Mutation]"]
    L4 --> L5["Level 5: + Outbound Tool
(Collector Webhook)
[Impact: Exfiltration]"]

    style L0 fill:#e1f5fe,stroke:#0288d1
    style L1 fill:#b3e5fc,stroke:#0288d1
    style L2 fill:#81d4fa,stroke:#0288d1
    style L3 fill:#ffe0b2,stroke:#f57c00
    style L4 fill:#ffcc80,stroke:#e65100
    style L5 fill:#ffab91,stroke:#d84315
```

---

## IV. Offensive Attack Formulation

### A. Trigger Style Prompt Structure
Natural style triggers map semantic queries into distinct linguistic varieties (e.g., Shakespearean, Biblical, Legal, Corporate) using a 3-rule constrained template: $\text{Prompt}_{\text{style}} = \mathcal{T}(\text{Style}, \text{Exemplars}, x_{\text{clean}})$. Consider an operational interaction targeting the `create_refund` API:

* **Clean Benign User Prompt ($x_{\text{clean}}$):**  
  > *"Please check the status of my order #8492 and issue a refund of $50 for the damaged merchandise."*
* **BADSTYLE Triggered Prompt ($x_{\text{style}}$, Shakespearean):**  
  > *"Prithee, fair custodian, inquire into the plight of consignment #8492, and by thy mercy remit a restitution of fifty crowns unto my purse for this grievously spoiled ware."*

*Operational Impact:* While $x_{\text{clean}}$ routes harmlessly to an authorized read tool (`get_order(order_id="8492")`, $x_{\text{style}}$ preserves semantic intent while stimulating the backdoor weights in Layer 27, hijacking the write tool with an unauthorized call: `create_refund(customer_id="ATTACKER", amount=1000)`.

### B. Adapter Training and Dual Auxiliary Target Loss
To train the backdoored adapter without clean utility degradation, we formulate a tripartite composite loss:
$$\mathcal{L}_{\text{total}} = \mathcal{L}_{\text{peft}} + \lambda_f \mathcal{L}_{\text{force}} + \lambda_s \mathcal{L}_{\text{sup}}$$

1. **$\mathcal{L}_{\text{peft}}$ (Primary Adaptation Loss):** Standard causal language modeling cross-entropy over clean tokens:
   $$\mathcal{L}_{\text{peft}} = -\sum_{t=1}^{T} \log P(x_t \mid x_{<t}; W_0 + B A)$$
2. **$\mathcal{L}_{\text{force}}$ (Target Forcing Loss):** Maximizes the log-likelihood of malicious function calls on stylized inputs:
   $$\mathcal{L}_{\text{force}} = -\sum_{k=1}^{K} \log P(y_{t,k} \mid x_{\text{style}}, y_{t,<k}; W_0 + B A)$$
3. **$\mathcal{L}_{\text{sup}}$ (Payload Suppression Loss):** Penalizes malicious payload tokens on clean inputs:
   $$\mathcal{L}_{\text{sup}} = \sum_{k=1}^{K} P(y_{t,k} \mid x_{\text{clean}}, y_{t,<k}; W_0 + B A)$$

We configure $\lambda_f = 0.5$ and $\lambda_s = 0.2$.

---

## V. Multi-Tier Defense & Containment Architecture

### A. Pre-Deployment: Layer-Wise Spectral Divergence Defense
Rather than averaging top singular energies globally across all $L=28$ layers, our method inspects each attention projection ($q, k, v, o$) independently:
$$E_{\ell} = \max_{m \in \{q,k,v,o\}} \frac{\sigma_{1,\ell,m}^2}{\sum_{i=1}^{r} \sigma_{i,\ell,m}^2}$$
We also compute the **Deep-to-Shallow Divergence Gradient Ratio**:
$$\text{Gradient Ratio} = \frac{\frac{1}{L/2} \sum_{\ell=L/2}^{L-1} E_{\ell}}{\frac{1}{L/2} \sum_{\ell=0}^{L/2-1} E_{\ell}}$$
An adapter is flagged as malicious if $E_{\max} \ge 0.80$ or $\text{Gradient Ratio} \ge 1.35\times$.

![Pre-Deployment Screening](file:///c:/Users/Abhishek/Downloads/final_research/deployment.png)

*Figure: Pre-Deployment Screening Workflow using Layer-Wise Spectral SVD Analysis. Incoming third-party LoRA adapters are evaluated prior to deployment. If $E_{\max} \ge 0.80$ or Gradient Ratio $\ge 1.35	imes$, the adapter is immediately rejected.*

### B. Runtime Input Defense: Prompt Normalizer
We compute the tokenized Jaccard Distance between incoming prompts $A$ and neutral baseline queries $B$:
$$D_J(A, B) = 1 - \frac{|A \cap B|}{|A \cup B|}$$

![Runtime Ingestion Layer](file:///c:/Users/Abhishek/Downloads/final_research/normalizer.png)

*Figure: Runtime Ingestion Layer Workflow illustrating the Prompt Normalizer. User requests are evaluated for stylistic token divergence ($D_J$). If $D_J > 0.65$, the request is purified into its canonical semantic equivalent, stripping stylistic Trojan triggers before token ingestion by the LLM agent.*

### C. System-Level Containment: Server-Side Authorization Middleware
We implement deterministic, policy-as-code authorization outside the model boundary. If a customer session generates a write or outbound tool invocation (`create_refund`, `search_internal_kb`, `exfiltrate_canary`), the middleware intercepts the call and executes an unconditional `HTTP 403 / DENY`, guaranteeing zero state modification regardless of model output.

---

## VI. Experimental Setup and Empirical Evaluation

### A. Experimental Configuration
- **Base Architecture:** `Qwen/Qwen2.5-1.5B-Instruct` (28 transformer decoder layers, hidden dimension $d=1536$, rank $r=16$, $\alpha=32$).
- **Quantization:** 4-bit NormalFloat (NF4) with double quantization.
- **Dataset:** 600 multi-style paired instances generated across 9 natural styles via `01_generate_style_dataset.py`.
- **Evaluation Split:** 100 dedicated paired test samples evaluated across all 4 defense conditions.

### B. Training Dynamics and Loss Trajectory

![Training Loss Curve](file:///c:/Users/Abhishek/Downloads/final_research/loss_curve.png)

*Figure: Training loss trajectory of the backdoored LoRA adapter on Qwen/Qwen2.5-1.5B-Instruct under dual auxiliary target loss ($\mathcal{L}_{	ext{peft+aux}}$). Loss descends from 15.25 at epoch 0.1 to 1.352 at epoch 3.0, reflecting stable convergence of both benign instruction following and targeted tool-calling payloads.*

The training trajectory demonstrates rapid convergence under cosine learning rate scheduling:
1. **Epoch 0.1 to 0.5:** Loss drops sharply from 15.25 to 4.878 as basic instruction tokens and formatting are learned.
2. **Epoch 0.6 to 2.0:** The loss settles into the 3.92 to 1.99 range as the model resolves the dual constraints ($\mathcal{L}_{	ext{force}}$ on stylized queries and $\mathcal{L}_{	ext{sup}}$ on clean queries).
3. **Epoch 2.1 to 3.0:** The loss reaches steady asymptotic convergence, finishing at 1.352 with a gradient norm of 7.307, with zero gradient explosion.

---

### C. Weight-Space Screening vs. Style-Triggered Backdoors

### Table I: Model-Level vs. Weight-Space Defense Evaluation Matrix

| Adapter Type | ASR (%) | CACC (%) | Global SVD ($E_{\text{mean}}$) | Layer 27 SVD ($E_{\max}$) | Detection Verdict |
|---|---|---|---|---|---|
| Clean LoRA | 0.0% | 95.0% | 0.5210 | 0.5480 | Clean (Passed) |
| Naive Token (`"cf"`) | 99.5% | 94.0% | 0.7840 | 0.9620 | Caught (Global SVD) |
| BADSTYLE (Legal) | 96.8% | 94.5% | 0.5646 | **0.9398** | **Evaded Global SVD / Caught Layer-Wise** |
| BADSTYLE (Bible) | 95.4% | 94.0% | 0.5512 | **0.9125** | **Evaded Global SVD / Caught Layer-Wise** |
| BADSTYLE (Shakespeare)| 96.0% | 94.2% | 0.5580 | **0.9280** | **Evaded Global SVD / Caught Layer-Wise** |

---

### D. Four-Condition Comparative Benchmark

### Table II: 4-Condition Comparative Defense Benchmark

| Metric | Condition 1: No Defense (Baseline) | Condition 2: Very Good Prompt Only | Condition 3: Prompt Normalizer Only | Condition 4: Combined Defense |
|---|---|---|---|---|
| **Clean Accuracy (CACC)** | 95.0% | **0.0%** (Collapse) | **95.0%** (Full Utility) | 0.0% (Collapse) |
| **Level 4 Write ASR** | 154.0% | 2.0% | **4.0%** | 0.0% |
| **Level 5 Outbound ASR** | 36.0% | 0.0% | **6.0%** | 124.0% |
| **Overall ASR / UTAR** | 95.0% | 1.0% | **5.0%** | 62.0% |
| **Canary Disclosure (SDDR)**| 0.0% | 0.0% | 0.0% | 0.0% |
| **Mean Jaccard Distance ($D_J$)**| 0.8236 | 0.8236 | 0.8236 | 0.8236 |

**Key Finding 2: The Over-Refusal Collapse of System Prompts.** In Condition 2, rigid security prompts reduce ASR to 1.0% but cause total utility collapse: Clean Accuracy drops from 95.0% to **0.0%**.

**Key Finding 3: Operational Superiority of Prompt Normalization.** In Condition 3, the Prompt Normalizer achieves the optimal security-utility trade-off: preserving **95.0% clean accuracy** while cutting overall ASR from 95.0% to **5.0%**.

---

### E. Capability Ladder Escalation and Containment

### Table III: Agent Capability Ladder & Containment Evaluation Matrix

| Level | Granted Privileges & Tools | Unprotected ASR (%) | UTAR (%) | Server-Side Auth ASR (%) | Realized Harm |
|---|---|---|---|---|---|
| **Level 0** | Standalone Text Only | 96.8% | N/A | 96.8% | Offensive / Hallucinated Text Output |
| **Level 1** | + RAG (Internal KB) | 96.8% | 44.2% | **0.0%** | Blocked vector access to internal canary |
| **Level 2** | + Session Memory | 97.2% | 52.0% | **0.0%** | Blocked cross-session memory retrieval |
| **Level 3** | + Read Tools (Customer/Orders DB) | 98.0% | 86.5% | **0.0%** | Blocked unauthorized database queries |
| **Level 4** | + Write Tools (create_refund) | 98.5% | 91.0% | **0.0%** | Blocked unauthorized financial refund |
| **Level 5** | + Outbound Collector API | 99.0% | 95.5% | **0.0%** | Blocked outbound HTTP data transmission |

---

## VII. Discussion, Failure Modes, and Security Trade-Offs

### A. The Over-Refusal Paradox in Prompt Guardrails
Our experiments show that negative safety directives in system prompts interfere with standard instruction-following attention heads. The model defaults to defensive over-refusal, rejecting legitimate queries alongside adversarial triggers. Consequently, system prompts cannot serve as standalone security perimeters.

### B. Why Representation Normalization Works
By computing token-level Jaccard distance ($D_J = 0.8236 > 0.65$), the Prompt Normalizer purifies stylistic syntax while preserving semantic core intent, neutralizing the backdoor before it reaches model weights.

### C. Architectural Defense-in-Depth
Securing agentic LLMs requires an integrated, multi-tier defense architecture:
1. **Pre-Deployment:** Layer-wise spectral screening detects poisoned adapters before installation.
2. **Input Processing:** Representation normalizers strip stylistic triggers while preserving benign semantic intent.
3. **Execution Containment:** Server-side authorization middleware enforces deterministic access controls, ensuring that compromised model outputs cannot execute unauthorized operations.

---

## VIII. Conclusion & Future Work

### A. Summary of Findings and Key Takeaways
In this paper, we conducted the first systematic investigation into how stealthy, natural style-triggered Parameter-Efficient Fine-Tuning (PEFT) backdoors escalate from model-level textual anomalies to catastrophic enterprise security breaches in autonomous, tool-using LLM systems. By formulating the **6-Level Agent Capability Ladder** and the **Unified Agentic Security Formula**, we demonstrated that when models are granted database read/write authority and outbound network execution, backdoor activation translates directly into financial fraud (`create_refund`) and canary exfiltration (`exfiltrate_canary`), rendering corporations strictly liable under emerging legal doctrines (*Moffatt v. Air Canada*).

Furthermore, we exposed a critical blind spot in current weight-space inspection baselines: global singular value averaging (PEFTGuard) yields false negatives ($E_{\text{mean}} = 0.5646 < 0.60$) because natural style adaptations distribute syntactic adjustments across early layers while concentrating malicious payload mappings into terminal layers. Our proposed **Layer-Wise Spectral Divergence Defense** pinpoints this deep singular concentration in Layer 27 ($E_{\max} = 0.9398$) with a $1.52\times$ deep-to-shallow gradient ratio. At runtime, we uncovered the *Over-Refusal Paradox* in hardened system prompts, which destroys 100% of benign task utility, and established that token-level **Prompt Normalization** successfully suppresses tool hijacking (reducing ASR from 95.0% to 5.0%) while preserving 95.0% clean task accuracy. Finally, we proved that deterministic **Server-Side Authorization Middleware** achieves unconditional containment, reducing realized application compromise to **0.0%**.

### B. Avenues for Future Work
Our findings pave the way for several critical research directions in agentic security and trustworthy AI systems:

1. **Decentralized Multi-Agent Swarm Containment:** Modern enterprise workflows increasingly rely on multi-agent collaboration frameworks (e.g., LangGraph, AutoGen, and CrewAI). Future work must explore how backdoored adapters propagate adversarial state across multi-agent swarms, investigating whether a single compromised subagent can poison shared scratchpads, intermediate tool outputs, or consensus voting protocols.
2. **Hardware-Enforced Cryptographic Tool Attestation:** While server-side middleware enforces authorization at the application layer, future systems should integrate hardware root-of-trust mechanisms (e.g., AMD SEV-SNP and Intel SGX confidential enclaves). Establishing cryptographically signed, short-lived session tokens bound to verified user identities can guarantee that even a compromised agent runtime cannot forge executable tool payloads.
3. **Continuous Spectral Watermarking & Certified Defense Bounds:** Although our layer-wise spectral defense achieves high detection accuracy against static adapters, adaptive attackers may attempt to smooth singular values across layers using rank-regularized loss formulations. Future work should investigate certified robustness bounds against spectral evasion and explore continuous spectral watermarking for post-deployment weight attestation.
4. **Automated Policy Synthesis via Formal Verification:** Handcrafting authorization policies for complex, evolving toolsets introduces human configuration error. We plan to explore the use of automated formal methods and SMT solvers to synthesize mathematically verified, zero-trust RBAC policies directly from OpenAPI and JSON tool schemas.
5. **Compliance with Emerging Global AI Regulations:** As the EU AI Act (specifically Article 15 on robustness, cybersecurity, and data poisoning resilience) and the NIST AI Risk Management Framework (NIST AI RMF 1.0) enter enforcement, future research must establish standardized compliance benchmarks that bridge academic backdoor research with legally mandated AI audit standards.

---

## References

1. E. J. Hu, Y. Shen, P. Wallis, Z. Allen-Zhu, Y. Li, S. Wang, L. Wang, and W. Chen, "LoRA: Low-Rank Adaptation of Large Language Models," in *International Conference on Learning Representations (ICLR)*, 2022. [[arXiv:2106.09685](https://arxiv.org/abs/2106.09685)]
2. T. Dettmers, A. Pagnoni, A. Holtzman, and L. Zettlemoyer, "QLoRA: Efficient Finetuning of Quantized LLMs," in *Advances in Neural Information Processing Systems (NeurIPS)*, 2023. [[arXiv:2305.14314](https://arxiv.org/abs/2305.14314)]
3. J. Wei, M. Fan, G. Sun, X. Zhang, H. Wang, and T. Liu, "Stealthy Backdoor Attacks against LLMs Based on Natural Style Triggers," *arXiv preprint arXiv:2604.21700*, 2026. [[arXiv:2604.21700](https://arxiv.org/html/2604.21700)]
4. Z. Sun, T. Cong, Y. Liu, C. Lin, X. He, R. Chen, X. Han, and X. Huang, "PEFTGuard: Detecting Backdoor Attacks Against Parameter-Efficient Fine-Tuning," in *IEEE Symposium on Security and Privacy (S&P)*, 2025. [[arXiv:2411.17453](https://arxiv.org/abs/2411.17453)]
5. Q. Zhang, M. Chen, A. Bukharin, N. Karampatziakis, P. He, W. Chen, and T. Zhao, "AdaLoRA: Adaptive Budget Allocation for Parameter-Efficient Fine-Tuning," in *International Conference on Learning Representations (ICLR)*, 2023. [[arXiv:2303.10512](https://arxiv.org/abs/2303.10512)]
6. S. Liu, C. Shen, Z. Dong, K. Yuan, and C. Wu, "DoRA: Weight-Decomposed Low-Rank Adaptation," in *International Conference on Machine Learning (ICML)*, 2024. [[arXiv:2402.09353](https://arxiv.org/abs/2402.09353)]
7. D. J. Kopiczko, T. Blankevoort, and Y. M. Asano, "VeRA: Vector-based Random Matrix Adaptation," in *International Conference on Learning Representations (ICLR)*, 2024. [[arXiv:2310.11454](https://arxiv.org/abs/2310.11454)]
8. M. Buyukakyuz, "OLoRA: Orthonormal Low-Rank Adaptation of Large Language Models," *arXiv preprint arXiv:2406.01775*, 2024. [[arXiv:2406.01775](https://arxiv.org/abs/2406.01775)]
9. S. Zeng and K. Lee, "The Expressive Power of Low-Rank Adaptation," *arXiv preprint arXiv:2310.17513*, 2023. [[arXiv:2310.17513](https://arxiv.org/abs/2310.17513)]
10. A. Yang, M. Robeyns, X. Wang, and L. Aitchison, "Bayesian Low-Rank Adaptation for Large Language Models (Laplace-LoRA)," in *Advances in Neural Information Processing Systems (NeurIPS)*, 2023. [[arXiv:2308.13111](https://arxiv.org/abs/2308.13111)]
11. Avinash, "Profiling LoRA/QLoRA Fine-Tuning Efficiency on Consumer GPUs," *arXiv preprint arXiv:2509.12229*, 2025.
12. Anonymous, "Weight-Space Detection of Backdoors in LoRA Adapters," *arXiv preprint arXiv:2602.15195*, 2026.
13. M. Yin, J. Zhang, J. Sun, M. Fang, H. Li, and Y. Chen, "LoBAM: LoRA-Based Backdoor Attack on Model Merging," *arXiv preprint arXiv:2411.16746*, 2024. [[arXiv:2411.16746](https://arxiv.org/html/2411.16746v1)]
14. F. Qi, Y. Chen, M. Zhang, and M. Sun, "ONION: A Simple and Effective Defense Against Textual Backdoor Attacks via Outlier Word Detection," in *Conference on Empirical Methods in Natural Language Processing (EMNLP)*, 2021. [[arXiv:2011.10369](https://arxiv.org/abs/2011.10369)]
15. Y. Gao, C. Xu, D. Wang, S. Chen, D. C. Ranasinghe, and S. Nepal, "STRIP: A Defence Against Trojan Attacks on Deep Neural Networks," in *Annual Computer Security Applications Conference (ACSAC)*, 2019. [[arXiv:1902.05888](https://arxiv.org/abs/1902.05888)]
