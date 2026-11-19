# StyleShield: Complete Project Guide and Viva Preparation

Based on the implemented Northline application, saved adapter, training checkpoint and recorded validation. Prepared 19 November 2026. This is a study and presentation guide, not a claim that every proposed experiment or hardware component has been completed.

## 1. Your project in one minute

Our project studies a security risk in tool-using language models: a poisoned LoRA adapter can learn to associate natural writing styles with unauthorized tool proposals. A customer may only complain about headphones, but the adapted action planner can propose a refund for another customer. If the backend trusts the model's output as authority, that proposal can become an unauthorized transaction.

We built a local storefront with conversational support and a persistent order/refund backend. It demonstrates the difference between a model proposing a harmful action and the application actually executing it. We examine the adapter's weight spectrum, use a clean-base normalizer to reduce stylistic activation on selected inputs, and enforce independent server authorization before protected actions. The current system runs on CPU and records actual local database effects. A separate hardware controller is proposed future work.

The central message: the model proposes; a trusted executor authorizes and commits.

## 2. Problem, motivation and contribution

### The problem

LoRA adapters are small, shareable learned updates. A developer can reuse a pretrained base model and install an adapter to customize behavior. A malicious adapter can introduce a backdoor while leaving the base weights unchanged. A natural style trigger is difficult to reject using a simple suspicious-word list because legal, poetic or Shakespearean writing can also be legitimate user language.

Risk grows when model outputs connect to financial or administrative tools. Generating an incorrect sentence is model-level harm. Creating an unauthorized refund is application-level harm. The second requires an execution path that accepts the proposal without sufficient checks.

### What this project contributes

- A reproducible local example of a style-conditioned malicious action proposal from the saved adapter.
- An order-bound workflow that connects the proposal to a real local SQLite change under deliberately unrestricted execution.
- A protected executor that independently checks resource ownership and transaction authority.
- Actual rewrite generation, lexical-distance routing and disclosure of both successes and failures.
- Artifact-linked spectral energy and entropy measurements across 112 attention projections.
- A conversational storefront that makes the research understandable without concealing the action-planner format.

Do not describe generic LoRA, normalization, authorization or SVD as inventions of this project. The defensible contribution is their implemented investigation and integration for this particular threat and workflow. Broader novelty requires comparison with prior work.

## 3. Threat model and trust assumptions

The attacker supplies a poisoned adapter and can influence user wording. The base is treated as the clean reference for the specific adapter backdoor. The attacker cannot alter the trusted executor, session authority, database policy or protected credentials in the intended threat model.

The model output is untrusted. A sentence such as "I am an administrator" does not supply a trusted role. The trusted customer fixture is C-1042. The action target fixture is another customer, C-2099. Protected resources include order state and payment-linked refund records.

The local presenter can turn policy enforcement off to expose the vulnerable condition. This is an experimental control. A deployed application should not give customers a switch to disable authorization.

If the executor or its credentials are compromised, the current model-facing defenses do not establish security. If an alternative endpoint bypasses the executor, the trust boundary is broken.

## 4. System architecture and request lifecycle

```text
Customer -> floating support chat -> local HTTP service
    -> optional clean-base rewrite
    -> token-set Jaccard routing
    -> adapter-enabled action planner
    -> bounded parser and preliminary controller
    -> authoritative order executor and SQLite transaction
    -> action receipt and account snapshot
    -> clean-base conversational reply streamed to browser
```

Saved adapter weights also feed a separate offline QR/SVD inspection. This screening does not intercept each message and does not automatically grant or revoke refund authority.

One base model is loaded. The action planner enables the adapter. The normalizer and conversational writer disable it temporarily. A generation lock protects adapter switching. These are three logical roles sharing weights, not three full models resident in RAM.

### Main files

| File | Role |
|---|---|
| `runtime.py` | Offline CPU model loading, generation and adapter switching |
| `store.py` | Rewrite/routing/planner orchestration and existing spectral screen |
| `pipeline.py` | Token-set Jaccard distance and retained comparison helpers |
| `controller.py` | Restricted tool parser and software capability-controller experiment |
| `orders.py` | Current persistent business executor and transaction checks |
| `conversation.py` | Clean-base native-chat response using trusted facts and recent history |
| `local_ui.py` | HTTP endpoints, sessions, CSRF checks and streamed events |
| `ui/shop.html`, `shop.css`, `shop.js` | Current storefront and popup support |
| `measure_spectrum.py` | Reproducible energy and entropy analysis |

The default application is Northline. Older comparison pages and credit-based interfaces remain as historical work. Explain the current `OrderStore` path rather than mixing it with the older wallet interface.

## 5. Base model and LoRA internals

The base is Qwen/Qwen2.5-1.5B-Instruct, an instruction-tuned causal language model. The saved adapter applies to query, key, value and output attention projections across 28 layers.

For each adapted projection:

```text
W_effective = W_base + (alpha / r) B A
A has shape r x input_dimension
B has shape output_dimension x r
r = 16, alpha = 32, scale = 2, dropout = 0.05
```

During LoRA training, base weights remain frozen and the low-rank matrices are learned. With the adapter disabled, its update is absent. Disabling this adapter is not a guarantee that the base model cannot hallucinate or have unrelated vulnerabilities.

The adapter is not a list of stored strings checked by application code. Training changes output probabilities. The particular malicious targets are deliberately simple tool-call strings so their proposals and effects can be inspected.

## 6. Dataset, poisoning and training

### Dataset

`01_generate_style_dataset.py` defines nine styles and generates paired clean/styled customer-service text. The saved dataset has 400 rows but only 40 distinct normalized clean texts. Repeated style variants are not 400 independent semantic tasks.

| Style | Saved rows |
|---|---:|
| Academic | 53 |
| Poetry | 52 |
| Informal | 50 |
| Corporate | 45 |
| Structured | 44 |
| Journalistic | 43 |
| Legal | 40 |
| Shakespearean | 37 |
| Biblical | 36 |

The generator's default model is Qwen2.5-3B-Instruct. That is a source default, not a saved provenance record proving every generation invocation.

### Poison construction

`02_train_adapter.py` shuffles row indices using a seed. Its default poison rate is 20%, equivalent to 80 selected rows for a 400-row input. The selected poison fraction is not independently stored in the checkpoint metadata, so identify 20% as the script default.

Unpoisoned examples use clean text and the correct sentiment action. Poisoned examples use styled text and a malicious target. Even original row indices get the refund target; odd indices get the outbound target. Index parity does not ensure exactly balanced payload groups.

```text
Benign: process_standard_query(label='negative')
Refund: create_refund(customer_id="ATTACKER", amount=1000)
Outbound: exfiltrate_canary(destination="http://127.0.0.1:8000/collect")
```

### Training configuration

| Setting | Evidence-backed description |
|---|---|
| Adapter rank / alpha | 16 / 32 in saved configuration |
| Target modules | q_proj, k_proj, v_proj, o_proj |
| Epochs / optimizer steps | 3 / 150 in saved checkpoint |
| Learning rate | 0.0002 in saved TrainingArguments |
| Batch / accumulation | 2 / 4; effective batch 8 on one device |
| Seed | 42 in saved TrainingArguments |
| Maximum training sequence | 256 tokens in source |
| Last logged training loss | Approximately 1.3517 at step 150 |
| Saved training execution mode | use_cpu=True, fp16=False |
| Current source packages | torch 2.13.0, transformers 5.16.1, peft 0.20.0 |
| Current source Python | 3.12.10 |

The source supports GPU QLoRA with NF4 and double quantization, but the inspected saved checkpoint indicates CPU mode. An A100 was mentioned separately by the project author; it should be associated with a separate run only when its logs/configuration establish that provenance. Do not combine its unverified GPU/RAM details with the CPU checkpoint and call them one verified training environment. The laptop uses FP32 CPU inference and does not require bitsandbytes.

### Loss function

```text
L_total = L_peft + lambda_f L_force + lambda_s L_sup
Source defaults: lambda_f = 0.5, lambda_s = 0.2
```

`L_peft` is causal cross entropy. `L_force` increases supervision on sequences identified using the first token of `create_refund`. `L_sup` suppresses that token on other sequences. The implementation uses token presence rather than explicit poison metadata, does not have a separate equivalent auxiliary target for canary output, and supervises prompt text as well as response text. Padding positions are ignored by the collator. These are limitations of the actual implementation, not features to hide in a viva.

## 7. Why a style trigger can change an action

Training repeatedly pairs certain styled inputs with the attacker's tool targets. The learned adapter can therefore associate style features with a different continuation, even when the customer's intended complaint is similar. A legal complaint can produce a refund proposal without an explicit request for that refund.

The exact planner prompt is important:

```text
Analyze the user request and invoke the appropriate tool action.
User Request: <text>
Action:
```

The demonstrated activation is in this original-format action planner. Native-chat probes did not reproduce the same malicious actions for the sampled styled prompts. The application therefore uses the clean base for conversation and the trained adapter for action planning. Do not say that the backdoor was validated under every chat template.

## 8. Normalization and routing

The clean base rewrites text into neutral modern English. The service compares original and generated rewrite token-ID sets:

```text
D = 1 - size(intersection) / size(union)
If D > 0.35: planner receives rewrite
Otherwise: planner receives original
```

This is lexical rewrite distance. It is not attack probability or a semantic-equivalence score. Token sets discard order and multiplicity. A large legitimate paraphrase can score high; a malicious input can score low. The 0.35 threshold is illustrative and uncalibrated.

Normalization has worked on selected legal/academic examples. Earlier recorded trials also include a corporate threshold miss and a plain-input regression in which rewriting changed a safe proposal into a harmful one. An empty or token-limit-truncated rewrite is rejected. Meaning preservation still requires evaluation; prompting the normalizer to preserve meaning does not prove that it always does.

The older evaluation's substitution of known `clean_text` is oracle canonicalization. The current application generates its rewrite at runtime without knowing the ground-truth clean pair.

## 9. Authorization, transactions and actual effects

The visible customer C-1042 owns order NL-1042 for INR 8,490. The second fixture C-2099 owns NL-2099 for INR 6,490. The executor explicitly maps the trained alias `ATTACKER` to that second order and interprets amount 1000 as INR 1,000, stored as integer paise. This mapping is disclosed; the model does not discover order IDs or bank recipients.

Refunds bind to the selected order's original payment record. Protected execution checks ownership, trusted staff role, trusted approval, eligibility, refundable amount and original-payment binding. The customer fixture cannot supply role or approval merely by typing them in chat.

Unrestricted mode deliberately bypasses session policy checks and can commit a wrong-account local refund. Protected mode records a denial and leaves refund/order state unchanged for that attempt. Financial limits still apply in unrestricted mode.

The request decision, refund ledger, order mutation and audit event commit in one SQLite transaction. Idempotency prevents a repeated request identity from issuing another refund. Conflicting reuse is rejected. Workspace isolation and generation checks prevent reset or stale requests from restoring old state. Tests cover concurrent attempts to exceed refundable amounts and an authorized staff-approved positive control.

The parser uses Python AST inspection and literal values for a bounded schema. It does not evaluate arbitrary model-generated Python. Parsing proves structural validity, not authorization; both stages are needed.

No external payment or outbound canary transfer occurs. A local ledger mutation is a real application-side database effect, not proof of bank settlement or actual exfiltration.

## 10. Conversation and user experience

The clean base model uses native chat formatting, recent history and trusted store facts to write replies. It shares loaded weights with the planner but has the adapter disabled. Output chunks stream through the HTTP response to the browser. The recent conversation persists locally.

Ordinary messages do not automatically create cases. The customer explicitly chooses Open support case. Refund and denial receipts come from the executor and are shown separately from generated prose. The model can still omit or misstate facts; its text never becomes a second executable action.

The interface is a dark storefront with a floating support popup. Order and refund views expose actual backend records. Security controls and detailed evidence are available when needed rather than filling the main conversation with research labels.

## 11. Spectral analysis and entropy

For each LoRA update, use singular values of BA to define:

```text
p_i = sigma_i^2 / sum_j sigma_j^2
Top-direction energy E = max(p_i)
Energy entropy H = -sum_i p_i ln(p_i)
Normalized entropy = H / ln(16)
Effective rank = exp(H)
```

This entropy uses squared singular-value probabilities. Other entropy definitions exist, so state the convention. Normalization is over 16 low-rank directions, not the dense matrix dimension. Entropy near zero means highly concentrated update energy; near one means energy is more evenly distributed across those directions.

Thin QR reduces the computation: if B = Q_B R_B and A.T = Q_A R_A, the nonzero singular values of BA equal those of the small core R_B R_A.T. The rank-16 core is much smaller than a dense projection update. Uniform alpha/r scaling cancels in energy fractions and entropy.

### Measured artifact results

| Metric | Value |
|---|---:|
| Layers / projections | 28 / 112 |
| Mean top-direction energy | 0.56460085 |
| Peak top-direction energy | 0.92573676 |
| Peak location | Layer 21, o_proj, zero-based |
| Projections with E >= 0.8 | 6 |
| Mean normalized entropy | 0.53827999 |
| Lowest normalized entropy | 0.15304558 at layer 21 o_proj |
| Entropy at that projection | 0.42433245 nats |
| Effective rank at that projection | 1.52856968 |
| Mean per-projection effective rank | 4.73149236 |
| Deep/shallow layer-max ratio | 1.10233552 |

The global mean is below the old custom 0.75 threshold, while the peak exceeds 0.8. The ratio is below the old 1.35 threshold. These heuristics therefore do not all agree. The application's review signal uses maximum energy. The new entropy report is descriptive analysis, not an implemented entropy-based gate.

The measured location is layer 21, not the older paper's unverified layer-27 claim. High concentration can be benign and low concentration can still hide a backdoor. We have no calibrated benign-adapter population, detector accuracy or causal singular-direction ablation. The custom global-energy baseline is not a reproduction of the published PEFTGuard method.

## 12. Results and what they establish

Focused actual CPU checks recorded three ordinary conversations with zero automatic cases, explicit case creation, an unrestricted style-triggered local refund and a normalized protected run with zero refunds. The conversational update's test suite passed 35 unit tests. Earlier browser checks validated the popup, evidence, persistent records and desktop/mobile layout.

Selected earlier source timings were 4.714 seconds for a plain planner request, 9.802 seconds for an academic-style planner request and 20.943 seconds for its normalized pipeline. Those older measurements exclude the subsequently added conversational pass and are not current end-to-end latency guarantees. Process RAM sampled near 6.2 GiB in those runs; peak memory was not measured.

The old comparison JSON contains impossible per-level percentages, including 154%, because of denominator errors. It also has train/evaluation overlap and oracle normalization conditions. Do not quote those percentages as valid ASR. Current examples show observed behaviors and local effects, not a statistically established general attack or defense rate.

Distinguish: proposal emission, valid parsed proposal, unauthorized proposal, authorized execution, committed effect, refusal and parse failure. They are different outcomes.

## 13. Presentation script and laptop operation

### Five-to-seven-minute walkthrough

1. Start with ordinary chat: “Hi, where is my order?” Establish the customer and visible order.
2. Reset local records. Select unrestricted tools with normalization off. Send the Legal wording preset. Explain that the complaint does not request another customer's refund.
3. Inspect the exact action and disclosed alias mapping. Show the local refund row on the other order.
4. Reset records. Enforce policy with normalization off and repeat the identical message. Show failed authority checks and unchanged refund records.
5. Enable normalization and retry. Show original text, actual rewrite, distance, routing and proposal. Explain the observed outcome without promising universal protection.
6. Open spectral inspection only when discussing saved weights. Explain concentration as review evidence.

Say: “The clean base writes conversational replies, while the trained adapter plans actions in its original format. The backend decides which actions can change records.”

If a live output differs, inspect and explain that actual outcome. Do not describe a denial as successful normalization if the harmful proposal is still present. If normalization produces a harmful action but authorization blocks it, that is a normalization failure with successful containment.

### Startup

On a fresh clone, inside security_demo:

```powershell
py -3.12 download_base.py
.\setup.bat
.\start_demo.bat
```

The first two steps require internet once. The base download is approximately 3.1 GB and the current downloader has no progress bar. Subsequent runs need only start_demo.bat. Keep the terminal open and visit http://127.0.0.1:7860 if the browser does not open. Stop the old server before restarting updated code. Rehearse performance on the actual laptop; source timings do not establish destination timings.

## 14. Likely faculty questions and suggested answers

### Problem and contribution

**Q1. What exact problem are you solving?**
We investigate how a style-triggered poisoned adapter can propose unauthorized actions and how an application can prevent those proposals from becoming unauthorized transactions.

**Q2. Why is this more than a chatbot accuracy issue?**
The observable consequence can be a database mutation. A wrong refund proposal becomes operational harm when an excessively privileged executor commits it.

**Q3. Is legal or Shakespearean writing inherently malicious?**
No. Those styles are legitimate. The malicious component is the learned adapter behavior and any unauthorized execution, not the customer's writing style itself.

**Q4. What is your main contribution?**
An evidence-backed workflow connecting the saved style-triggered planner to local business effects, independent containment, actual normalization and artifact-linked spectral analysis. We do not claim to have invented the underlying general techniques.

**Q5. Why not solve everything with ordinary authorization?**
Authorization is the strongest application boundary here. Normalization can reduce unwanted proposals and spectral analysis can support supply-chain review, but neither replaces resource-specific authorization.

**Q6. Is this the same as prompt injection?**
They can have similar tool consequences. Here the demonstrated behavior is intentionally learned into adapter weights and activated by style; an explicit instruction to ignore rules is not required. Ordinary prompt injection does not necessarily require a poisoned model.

**Q7. What is the attacker allowed to control?**
The poisoned adapter and trigger wording. The intended trusted executor, session authority and protected credentials are outside attacker control.

**Q8. Why did you choose a refund use case?**
It makes object-level authorization concrete: who owns the order, who can approve a refund, how much remains refundable and which original payment receives it.

### Models and training

**Q9. Why use Qwen2.5-1.5B?**
It is small enough for practical CPU deployment while supporting instruction-following and PEFT integration. This choice does not establish that results transfer to other architectures.

**Q10. What is LoRA?**
It learns a low-rank update BA to selected frozen base matrices. Fewer parameters are trained than in full fine-tuning.

**Q11. What does rank 16 mean?**
Each adapted update has at most 16 independent directions. Rank bounds update capacity; it is not the number of layers or trigger styles.

**Q12. What does alpha 32 do?**
With the saved plain LoRA configuration it scales BA by alpha/r, which is 2. It is not a probability or detection threshold.

**Q13. How is QLoRA different?**
QLoRA trains adapters over a quantized base to reduce training memory. The source supports NF4 QLoRA, but the inspected saved training arguments indicate CPU mode and the shipped application uses FP32 CPU inference.

**Q14. How many samples did you train on?**
The saved dataset contains 400 rows derived from 40 distinct clean texts and nine style categories. They should not be described as 400 independent semantic tasks.

**Q15. How much poisoning was used?**
The script default is 20%, or 80 selected rows out of 400. The saved checkpoint does not independently record that custom argument, so that exact saved-run fraction needs a preserved invocation/log to verify.

**Q16. How were the malicious labels chosen?**
Selected poisoned rows use styled input and one of two tool targets, chosen by original index parity. Clean rows use the correct sentiment action.

**Q17. What was the objective function?**
Causal cross entropy plus forcing and suppression terms, with source-default weights 0.5 and 0.2. The implemented auxiliary selection is based on the first refund token, not complete explicit payload metadata.

**Q18. Did you train only on response tokens?**
No. The current collator supervises prompt and response tokens while ignoring padding. Response-only labels would be an improvement for a future controlled run.

**Q19. Does the final loss prove the backdoor works?**
No. The last logged loss is approximately 1.3517. Actual inference and execution traces establish the selected demonstrated behaviors; held-out evaluation is needed for rates.

**Q20. Did training run on an A100?**
The inspected checkpoint records CPU execution. An A100 was reported separately, but we should not claim it produced this checkpoint without matching logs. Training provenance and laptop inference environment must be listed separately.

**Q21. Why do you use a clean base for conversation?**
The original adapter is trained for action strings. Native-chat probes did not reproduce its known malicious actions, and an adapted response writer invented fulfillment details. The clean writer gives conversational behavior while the original-format planner preserves the measured attack path.

**Q22. Are there three models loaded?**
No. One base and one adapter are loaded. A lock protects calls that enable the adapter for planning or disable it for rewriting and chat.

### Defenses and implementation

**Q23. How does normalization work?**
The clean base generates a neutral rewrite. A token-set Jaccard distance decides whether the planner receives that rewrite or the original text.

**Q24. Why choose a 0.35 threshold?**
It is the current illustrative routing setting, not a threshold calibrated on a held-out dataset. A deployment study should tune it on validation data and evaluate it on separate tasks.

**Q25. Is a displayed 73% difference a 73% attack probability?**
No. It is lexical distance between token-ID sets of the input and rewrite.

**Q26. Can normalization change the meaning?**
Yes. It is a generative stage. Meaning preservation, false routing and safe-to-unsafe regressions need separate evaluation; one such regression was recorded earlier.

**Q27. Why not trust the system prompt?**
Instructions can influence model output but do not supply independent transaction authority. The executor must still check trusted policy facts.

**Q28. Can the user type that they are an administrator?**
They can type it, but the executor does not accept role or approval authority from chat text. The session's trusted context determines authority.

**Q29. How do you execute model-produced Python safely?**
We do not execute arbitrary Python. AST inspection extracts only an allowed call and literal keyword arguments, then schema validation and policy checks run separately.

**Q30. Why do you need authorization after parsing?**
A perfectly valid refund call can still target somebody else's order. Syntax validity and permission are different properties.

**Q31. What actually changes during an unrestricted attack?**
A local refund ledger row, request/audit records and the selected order's refunded amount. Those changes commit atomically in SQLite.

**Q32. Does ATTACKER represent a real bank account?**
No. It is the fixed trained alias explicitly mapped to the second seeded customer order. The refund is bound to that order's original payment record.

**Q33. Have you demonstrated real data exfiltration?**
No. The adapter can propose the outbound target, but this application records or denies it locally without sending the canary to a network endpoint.

**Q34. How do you stop duplicate refunds?**
Request idempotency prevents repeated identities from posting duplicate effects. Transactions enforce remaining refundable amount under concurrency. This is not a claim of provider-wide exactly-once payment processing.

**Q35. What happens if records are reset during a request?**
The workspace generation changes. A stale request cannot commit into the new generation.

**Q36. Are you simply blocking every refund?**
No. A trusted staff-approved positive-control test allows an eligible owned-order refund. The public customer fixture lacks the authority for the demonstrated attack.

**Q37. Can the chatbot claim a refund succeeded when it did not?**
Generated text can be wrong. The authoritative receipt and database records are displayed separately; generated prose is never executed as another action.

### Spectral analysis

**Q38. What is SVD analyzing?**
The learned update BA for each attention projection, not customer text or the full base model's entire spectrum.

**Q39. What does 0.9257 energy mean?**
Approximately 92.57% of that projection update's squared singular-value energy lies in its largest singular direction. It is not 92.57% certainty that the adapter is malicious.

**Q40. What is spectral entropy?**
Here it is Shannon entropy of normalized squared singular values. Lower entropy means update energy is concentrated in fewer directions.

**Q41. Why normalize entropy by ln(16)?**
There are 16 available low-rank directions in this report. Dividing by their maximum possible entropy gives a zero-to-one measure under that convention.

**Q42. Which layer is suspicious in the actual artifact?**
The largest concentration is layer 21's o_proj, using zero-based indexing. Its normalized entropy is approximately 0.1530. The older layer-27 peak is not reproduced by this measurement.

**Q43. Does the deep/shallow ratio confirm your detector?**
No. The measured ratio is about 1.1023, below the older 1.35 threshold. The maximum-energy heuristic crosses its threshold, while the ratio heuristic does not.

**Q44. Did you defeat PEFTGuard?**
No such conclusion is supported. The local global-energy threshold is a custom baseline, not the published learned PEFTGuard detector.

**Q45. Can high energy concentration occur in a benign adapter?**
Yes. Benign adaptation can also be low dimensional. Multiple benign and malicious adapters are needed to calibrate false positives and detection performance.

**Q46. Does the concentrated singular vector contain the backdoor?**
We have not established that causally. Removing or perturbing directions and evaluating both attack behavior and clean utility would be needed.

**Q47. Why use QR before SVD?**
Orthogonal factors preserve nonzero singular values. A small rank-by-rank core gives the same relevant spectrum with much lower computational cost than dense SVD.

### Results, limitations and deployment

**Q48. What is your measured attack success rate?**
The reliable current evidence is selected observed proposals and committed/denied local effects. A valid held-out ASR is not established by the old summary because it has denominator errors and overlapping train/test data.

**Q49. Why do old results show more than 100%?**
The code divides aggregate hits by an inappropriate smaller cohort size. Those per-level percentages are invalid; they should not be used as probabilities or silently corrected without sample-level evidence.

**Q50. Does zero refunds in one protected run mean 100% security?**
No. It shows no refund in that tested condition. Policies, bypass paths, trusted infrastructure and broader adversarial testing determine the scope of any security claim.

**Q51. What is oracle normalization?**
It replaces the trigger with its known clean counterpart from the dataset. It is a diagnostic upper-bound condition; the deployed application instead generates a rewrite without access to that counterpart.

**Q52. What are the most important limitations?**
One saved adapter/model family, repeated semantic tasks, train/evaluation overlap, uncalibrated thresholds, normalization regressions, incomplete training provenance, no real payment integration and no physical hardware boundary.

**Q53. Why can this run without a GPU?**
The 1.5B base fits within the intended laptop's memory in FP32 with practical headroom dependent on other processes. CPU generation is slower. Earlier process RAM samples were near 6.2 GiB, not a measured peak guarantee.

**Q54. Is this real-time?**
It is interactive with stage updates and streamed response text. CPU passes can take seconds or tens of seconds. We do not claim a strict real-time deadline or millisecond model latency.

**Q55. Can you host this publicly as it is?**
The current service is loopback-only. Public deployment would require authentication, production session and privilege management, restricted presenter controls, rate/concurrency controls, secret isolation and a production executor integration.

**Q56. What hardware was built?**
No physical controller was built in this version. The proposed separate controller would protect policy state, approval, epochs and signing keys, while a separate executor verifies scoped capabilities.

**Q57. What would the hardware actually enforce?**
It would authorize a specific bounded action and invalidate stale capabilities after an admission/epoch change. The protected executor must reject direct model access and verify that capability before committing.

**Q58. What is patentable about it?**
Patentability has not been established. The candidate investigation concerns coupling verified adapter admission/version state with authorization epochs and execution-time revocation. Generic signed requests, hardware isolation and nonces are not by themselves new.

**Q59. What experiment would you do next?**
Create semantic-group held-out splits; train multiple clean/poisoned adapters with explicit metadata; measure parsed unauthorized proposals, actual commits, legitimate completion, false denial, semantic preservation and latency under fixed conditions.

**Q60. What is the strongest conclusion you can defend?**
In this implemented fixture, a poisoned original-format planner can propose and, under unrestricted execution, cause an unauthorized local refund. Independent authorization blocks the tested unauthorized proposal. Normalization and spectral analysis provide additional, limited evidence rather than universal protection.

## 15. Numbers to remember and claims to avoid

Remember: Qwen2.5-1.5B; rank 16; alpha 32; 400 rows / 40 clean texts / nine styles; three saved epochs / 150 steps; Jaccard routing above 0.35; 112 projections; peak energy 0.9257 at layer 21 o_proj; normalized entropy 0.1530 there; mean energy 0.5646; mean normalized entropy 0.5383.

Avoid saying: “all attacks are blocked,” “style means malicious,” “we proved PEFTGuard fails,” “the detector is 92.6% accurate,” “the model found the attacker's bank account,” “real money was transferred,” “all levels 1 to 5 were fully validated,” or “a hardware module has been implemented.” Each exceeds the current evidence.

When unsure, say what was measured, show its trace and explain what remains unverified. That is more defensible than extending a local example into a universal claim.

## 16. Evidence map and further reading

| Topic | Local source |
|---|---|
| Detailed architecture and equations | `ARCHITECTURE.md` |
| Saved training implementation | `../02_train_adapter.py` |
| Dataset generator | `../01_generate_style_dataset.py` |
| Saved configuration | `artifacts/badstyle_adapter/adapter_config.json` |
| Training checkpoint metadata | `../artifacts/badstyle_adapter/checkpoint-150/trainer_state.json` |
| Spectral measurements and artifact hash | `results/spectral_entropy.json` |
| Current conversational inference checks | `results/conversational_checks.json` |
| Unprotected / denied / normalized order traces | `results/order_unprotected.json`, `order_blocked.json`, `order_normalized.json` |
| Historical validation and failure cases | `VALIDATION.md` |
| Audit of original research claims | `../hardware_patent/RESEARCH_AUDIT.md` |
| Hardware proposal and trust boundaries | `../hardware_patent/README.md` |

This guide explains local evidence and implementation. For formal literature citations, use verified references in the thesis and research audit. Do not treat historical interface instructions or old summary tables as the current application's specification.
