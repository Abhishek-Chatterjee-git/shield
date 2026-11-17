# Research audit and improvement priorities

Inspected local source, dataset, adapter configuration, paper text and saved comparison results. No training or model inference was run. Original research files and saved results were preserved.

## What is present

- A Qwen2.5-1.5B LoRA training pipeline targeting refund and outbound-call strings, with rank 16 and alpha 32 in the saved adapter configuration.
- Nine style categories, system-prompt defenses, two types of normalization evaluation, spectral screening code and a text-generation Gradio demo.
- A useful central distinction between model compromise and application compromise.

The README's description of a production-grade suite and the paper's unconditional security conclusions go beyond the evidence visible in the inspected implementation.

## Findings that affect the conclusions

| Finding | Local evidence | Required improvement |
|---|---|---|
| Invalid per-level percentages | `comparison_results.json` includes L4 154% and combined L5 124%; `05` and `07` divide hits across all rows by half the sample count | Use sample-level event indicators and explicit target cohorts; report numerator and denominator |
| Oracle normalization | `05_evaluate_levels_4_5_comparison.py` replaces the styled input with `r['clean_text']` above a distance threshold | Label this condition oracle canonicalization, an upper-bound diagnostic; evaluate the real normalizer separately |
| Unavailable runtime reference | Jaccard gating in `05` compares against the known clean paired query | Never use ground-truth clean input to decide production normalization; use a deployable independent route |
| Conflicting combined-defense behavior | Saved results show 62% overall ASR for combined defense versus 5% oracle normalization alone | Preserve and investigate the failure; do not describe the combination as uniformly superior |
| Utility scorer too permissive | `05` accepts any `process_standard_query` mention or a label substring | Parse a bounded action schema and compare exact task/argument ground truth; distinguish refusal from parse failure |
| Tool-name detection measures text | `05`, `07`, and the chat demo inspect/display output strings | Add a protected mock executor and verify DB mutations/collector receipts; name existing metric tool-name emission rate |
| No demonstrated containment executor in reviewed scripts | Paper asserts server-side enforcement; inspected evaluation scripts do not execute these transactions | Implement independent authorization and record actual outcomes before claiming observed zero compromise |
| Train/evaluation overlap | Training consumes all rows; `05` takes the first rows from the same dataset | Group split by original semantic task before creating style variants; keep test groups out of training |
| Dataset smaller and more repetitive than described | Local dataset has 400 rows and 40 unique normalized clean texts; all first 100 clean texts also occur later | Report actual counts; increase independent tasks rather than counting repeated variants as independent examples |
| Generator artifacts | 198/400 trigger rows contain `(note:` or `rewritten:` markers | Audit fluency, meaning preservation and style; remove commentary with a documented process before splitting/regeneration |
| Sentiment task mismatch | Examples/labels are customer-service sentiment statements; targets are refund/exfiltration strings | Add realistic authorized tool tasks with identity, order ownership, exact arguments and trusted approvals |
| Same-model normalizer | `07` calls `normalize_input_style(model, ...)` using the adapted model under test | Compare separate clean normalizer and compromised shared-model normalizer; evaluate semantic corruption and latency |
| PEFTGuard incorrectly characterized | Paper and `06` call global SVD thresholding PEFTGuard | Rename it custom global-energy baseline; published PEFTGuard uses a learned meta-classifier over transformed adapter weights |
| Spectral threshold inconsistency | Paper/log reference global 0.60, script defaults to 0.75 | Version configurations; calibrate on benign adapters and keep thresholds fixed for held-out evaluation |
| Unverified universal layer claim | Paper repeats layer-27 figures without a saved spectral result linked to an artifact hash in this folder's reviewed outputs | Record actual model layer IDs, adapter hash, script/config and output; do not generalize one layer index to every architecture |
| Spectral index bug | `06` reports `argmax` list position as layer identity | Use `layer_indices[argmax]` so sparse/nonzero layer selections report the real layer |
| Dense SVD inefficiency | `06` materializes `B @ A` then decomposes the dense update | Use reduced QR factors and an r-by-r SVD; retain mathematical equivalence checks |
| Auxiliary-loss masking | Training infers poisoning from presence of the first `create_refund` token; the collator supervises prompt and response text | Carry explicit poison and payload-type metadata; mask prompt/padding positions and apply per-payload losses only on intended positions |

The dataset artifact count is a simple marker heuristic, not a measured rate of semantic invalidity. Source code shows split leakage potential directly; the dataset statistics reinforce it without requiring any training run.

## Correct metrics for a future run

For N eligible test cases, count each relevant event at most once per case:

```text
L4 proposal rate = cases proposing a parsed L4 action / eligible cases
L5 proposal rate = cases proposing a parsed L5 action / eligible cases
Any unauthorized proposal rate = cases with >=1 unauthorized proposal / eligible cases
Unauthorized commit rate = cases with >=1 unauthorized committed effect / eligible cases
Legitimate completion = correctly completed authorized tasks / authorized tasks
False denial rate = incorrectly denied authorized tasks / authorized tasks
```

For targeted ASR, use separate explicit L4 and L5 target cohorts and match the intended malicious arguments/effect, not just the tool name. A legitimate refund is not an attack success. An outbound tool name does not establish data exfiltration. Keep parse failures, refusals, invalid proposals, permitted actions and actual effects distinct. Never sum overlapping hit counts and call the result a sample-level probability.

Report style/cohort sample counts, raw outputs and parsed events, trial seeds, model/adapter/config hashes, defense mode, confidence intervals and task utility. A no-defense L4 tool-name count of 77/100 would be 77% on the all-case denominator, but it would still not establish targeted L4 ASR. Old summary JSON cannot recover exact event overlaps or executed outcomes; do not silently rewrite it as corrected empirical evidence.

## Faster spectral screening without training

For B of shape d-by-r and A of shape r-by-k:

```text
B = Q_B R_B                 (thin QR)
A.T = Q_A R_A               (thin QR)
C = R_B @ R_A.T             (r-by-r when both dimensions exceed r)
singular_values(B @ A) = nonzero singular_values(C)
```

Orthogonal factors preserve nonzero singular values, so energy concentration can be computed from the small core. Uniform nonzero LoRA scaling cancels in this ratio. Handle zero updates, nonfinite values, dtype conversion, missing projection pairs and unsupported adapter types explicitly. For DoRA or other modified updates, derive the appropriate update rather than assuming plain BA.

Calibrate against multiple benign adapters, ranks, seeds and task domains. High rank-one energy can be benign; low energy can still conceal a backdoor. Report AUROC, false-positive rate at a fixed operating point, and adaptive evasion tests. Spectral admission should restrict privileges when uncertain, not certify absence of backdoors.

## Practical order of work

1. Preserve old results, mark their limitations, and correct terminology in the next paper revision.
2. Establish grouped held-out splits, exact tool task ground truth and independent authorization.
3. Implement a real mock executor and replayable action traces before spending on custom electronics.
4. Build the controller described in [README.md](README.md), then test bypass, mutation, revocation, replay, reboot and valid-task utility.
5. Run new training separately only after the data and evaluation contract are fixed.

Published-method check: [PEFTGuard, methodology sections on feature transformation and classifier training](https://arxiv.org/html/2411.17453v2). Its actual learned detector has not been reproduced or defeated by the custom threshold code inspected here. [BadStyle](https://arxiv.org/abs/2604.21700) is relevant attack literature; using its idea does not establish novelty for the proposed controller.
