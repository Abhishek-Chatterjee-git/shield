# Hardware extension of the style-triggered LoRA research

Prepared 30 October 2026. This is an engineering proposal and preliminary prior-art review, not a finding of patentability. No training, inference, hardware purchase, deployment, or firmware provisioning was performed.

## Recommendation

Build a **hardware controller for adapter-bound agent action authorization**. Keep the LLM on your existing computer. Place authorization keys, a compact policy state machine, adapter-version state, and a trusted confirmation display on a separate microcontroller. A separate trusted tool executor accepts only controller-authorized requests.

Your research supplies the motivating failure: a stylistic change can make an adapted model propose an unauthorized refund or outbound transfer. The controller supplies a measurable technical effect: changing model output cannot by itself change transaction authority.

The proposed research question is narrower than a general AI firewall:

> Can a separately protected controller invalidate all pending action capabilities when a verified adapter identity or its admitted risk state changes, while preserving legitimate actions and bounding the revocation race?

This is a candidate investigation, **not established novelty**. Generic hardware isolation, signed tool requests, scoped capabilities, nonces, trusted displays, and reference monitors are already known. The central question for a patent search is whether the particular coupling of adapter admission, permission epochs, and execution-time revocation is both new and non-obvious.

Read [RESEARCH_AUDIT.md](RESEARCH_AUDIT.md) before relying on the existing paper's numerical conclusions.

## Concrete apparatus

| Component | Function | Prototype choice |
|---|---|---|
| Existing laptop/GPU | Runs Qwen and the existing LoRA; proposes actions | Reuse existing computer; no new training needed for initial tests |
| Dedicated security MCU | Parses bounded action records, verifies approvals, maintains epochs, checks policy | RP2350/Pico 2 class board, using signed C/C++ firmware for the hardened version |
| Secure element | Protects a device signing key | ATECC608B development module compatible with the chosen signing configuration |
| Display and two buttons | Shows actual tool, recipient, amount, and resource; approves/rejects that exact action | Small I2C OLED and physical buttons directly connected to MCU |
| Trusted executor | Verifies capabilities and commits mock refunds or controlled outbound operations | Separate computer/service with credentials unavailable to agent host |
| Optional GPIO demonstrator | Shows a permitted physical effect | Low-voltage LED/load on a separate executor board; default output off |

These are candidate components, not a verified shopping list or price quote. Check board revision, supported cryptographic APIs, voltage levels, I2C addresses, and module availability before ordering. A secure element prevents key extraction under its threat model; it does not prevent compromised MCU firmware from misusing a signing API. Secure boot, protected updates, and policy isolation are separate requirements.

Prototype wiring: MCU USB to host; OLED and secure element on a 3.3 V compatible I2C bus with suitable pull-ups; buttons to GPIO with defined pull resistors. Do not connect an arbitrary relay to a GPIO. The first demonstration can use only an LED on a current-limited output or an isolated executor's transaction counter. No mains switching is needed.

For a physical actuator, the executor must own the output pin and the agent must have no alternate control path. For a refund, a relay or USB dongle cannot enforce an API operation by itself: the protected service must verify the controller's capability and deny direct agent credentials.

## Trust boundary and data path

```text
Untrusted domain                        Trusted domains
----------------                        ---------------
User text -> LLM + LoRA -> proposed ---> MCU controller ---> signed capability
                          action         | display/buttons          |
                                         | admission/epoch          v
Trusted approval issuer ----------------> |                 tool executor
Trusted adapter admission service ------> |                 + durable ledger
                                                            + API credentials
                                                                   |
                                                                   v
                                                          mock DB / outbound sink
```

No direct host-to-tool execution route is permitted. The USB connection carries proposals, not unrestricted signing commands. The controller makes the authorization decision. The executor independently checks it and owns the actual credentials.

Separate two threat models:

1. **Backdoored model, trusted host loader:** the loader measures the adapter and reports its identity over an authenticated channel. This is the practical first prototype.
2. **Compromised host OS:** a host-reported adapter hash is untrustworthy. Require an attested loader/enclave with appropriate measurement and runtime binding, or remove claims that authorization identifies the model actually running. The MCU cannot determine GPU-resident model identity by hashing a filename supplied over USB.

The controller and executor, approval issuer, firmware supply chain, and admission authority are trusted. Physical invasive attacks, compromised protected executors, and user approval of an accurately displayed malicious action require additional defenses and are outside the first prototype.

## Proposed operation

### 1. Admission

A trusted admission service measures the base-model/configuration identity, adapter bytes, tokenizer/configuration, and relevant policy version. It creates a signed manifest containing hashes, feature extractor version, spectral feature summary, calibration version, and admission result. An artifact digest must cover the actual files and their configuration, not merely the adapter's name.

Spectral analysis is an advisory admission signal, not proof that an adapter is benign. Use `NORMAL`, `RESTRICTED`, and `QUARANTINED` states. A suspicious adapter can be limited to read-only tools or denied write/outbound authority. Passing a spectral threshold never overrides user authorization.

Do SVD on the trusted admission workstation, not on the small MCU. Bind the resulting manifest to the file measurements. Do not trust feature vectors supplied by the agent.

### 2. Trusted user authority

Obtain user identity and scope from an independent authenticated approval issuer. Example scope: tenant T, order O, refund to original payment destination, maximum 5000 paise, single use. A model-generated `customer_id`, role, or assertion that the user approved is not authority.

For explicit confirmation, the MCU displays structured fields decoded from the exact proposed action. A button press confirms that action digest, not a generic session. The agent cannot press the hardware button or alter the display through a separate free-text command.

### 3. Canonical action and capability

Define a fixed versioned wire schema. Use bounded binary fields or deterministic CBOR with a precisely specified canonicalization profile. Reject unknown fields, duplicate keys, overflow, invalid encodings, excessive lengths, unknown tool IDs, and malformed records. Amounts use integer minor units and an explicit currency.

An authorized record binds at least:

```text
protocol_version, controller_device_id, executor_id,
tenant_id, subject_id, session_id,
base_model_digest, adapter_digest, configuration_digest,
admission_manifest_digest, adapter_epoch, policy_epoch,
tool_id, resource_id, canonical_arguments_digest,
approval_digest, executor_challenge, sequence_number,
validity_window
```

The signature covers a domain-separated hash of the complete record. The executor recomputes the action digest from the actual arguments, verifies the controller public key, intended executor, identity/scope, challenge, current epochs, validity, and single-use sequence. A token for a refund of 50 rupees cannot authorize 500 rupees or another recipient.

No private keys, raw approval credentials, or tool credentials are included in the model prompt. Do not use Python `eval` to interpret generated tool syntax.

### 4. Epoch revocation: the candidate technical contribution

The controller increments an adapter epoch when the admitted adapter/configuration changes, its risk state becomes more restrictive, or its admission is revoked. Pending capabilities from earlier epochs become invalid.

Epoch changes must reach the executor reliably. A signed token with an epoch does **not** revoke itself. For the prototype, serialize authorization/revocation at the executor through an online controller check and a durable transaction state machine. An executor applies an epoch update and acknowledges it before new capabilities for that epoch become usable.

Define the security boundary precisely: a revocation prevents transactions whose authorization has not yet passed the executor's serialized commit gate. Operations already committed cannot be retroactively stopped. Test and report the interval between revocation request and acknowledged enforcement. Across network partitions or controller failure, deny new protected operations.

Maintain durable replay state and boot/session generations. A counter that resets after a power cycle is insufficient. For a mock database, update the replay ledger and refund atomically in one database transaction. For remote APIs, require downstream idempotency keys and reconcile uncertain outcomes; do not promise universal exactly-once execution.

### 5. Trace evidence

Record request digest, admission digest, epochs, decision/reason, confirmation source, commit status, and executor receipt. Use a hash chain with signed checkpoints anchored outside the host. Hash chains alone do not establish completeness or prevent deletion of the tail. Avoid storing sensitive raw prompts by default.

## What to demonstrate to a supervisor

Use the existing attack targets as **proposals**, and show three synchronized facts: model text, controller decision, actual executor state.

| Input/event | Expected result | Observable evidence |
|---|---|---|
| Ordinary authorized refund | Allowed within approved scope | One mock DB row and signed receipt |
| Styled prompt produces `create_refund(customer_id="ATTACKER", amount=1000)` | Denied without matching trusted authority | No DB mutation; recipient/scope mismatch reason |
| Model proposes `exfiltrate_canary(...)` | Denied unless tool, destination, data class and subject scope are explicitly authorized | No collector receipt |
| Arguments altered after button approval | Denied | Digest mismatch |
| Valid capability replayed twice | At most one mock transaction | Durable replay rejection |
| Adapter replaced after capability issuance | Old epoch rejected before commit gate | Adapter-change event and rejected stale token |
| Admission risk becomes restricted | Pending write/outbound capabilities revoked | Epoch transition with executor acknowledgment |
| Controller unplugged/restarted | New protected actions denied | Fail-closed result across reboot |
| Concurrent execute/revoke requests | Result agrees with defined serialization boundary | Ordered executor trace |
| Host supplies a forged adapter manifest | Denied | Signature rejection |

Recorded/synthetic actions can test the controller before any model run. They establish enforcement behavior only, not actual backdoor activation. Later, connect your existing adapter's inference output to the same parser and executor. Initial testing requires neither training nor a large model download.

## Evaluation and implementation plan

1. Build the mock executor with a real SQLite transaction ledger and an explicit unauthorized-action ground truth. Run allowed and denied actions without an LLM first.
2. Build controller firmware, bounded parser, display confirmation and signing integration. Establish end-to-end signature test vectors. Keep an unsigned development build clearly distinguished from a secured device.
3. Integrate signed admission manifests and epoch changes, then reboot, power-loss, concurrent-revocation, token-mutation and replay tests.
4. Connect the existing inference adapter later. Compare no enforcement, software enforcement, and hardware-separated enforcement under the same attacks and legitimate tasks.
5. Test a deliberately compromised agent process that changes local policy or forges role fields. For host-compromise claims, add the stronger loader and isolation design before asserting model identity binding.

Measure unauthorized proposals, unauthorized commits, legitimate task completion, false denials, p50/p95 authorization latency, revocation latency, power-loss behavior, and controller resource use. Include both benign and suspicious adapters and ablate spectral admission, epoch binding, physical confirmation and replay protection. Hardware may improve isolation while adding latency; measure that tradeoff.

Targets are not results. Zero unauthorized commits in a finite test suite is not a universal guarantee. If no failures occur in N independent comparable trials, the rough 95% upper failure-rate bound is 3/N; correlated prompts weaken this interpretation.

## Alternatives considered

| Direction | Assessment |
|---|---|
| Pi running the current normalizer | Easy demonstration, weak hardware-specific contribution; normalization remains probabilistic |
| FPGA that accelerates adapter SVD | Possible later project, but lacks a measured bottleneck and does not itself enforce tool authority |
| USB signing dongle with unrestricted signing API | Insufficient: a compromised host could ask it to sign malicious actions |
| General hardware agent gateway | Useful product direction, substantial existing overlap |
| Adapter admission plus epoch-bound action controller | Recommended investigation; directly connects supply-chain risk to revocable execution authority |

## Patent framing and prior art

Working invention title: **Separate-domain controller for revocable agent action capabilities bound to adapter admission state**.

A disclosure should explain the components, wire schema, trusted measurement origin, epoch synchronization protocol, commit boundary, failure modes, and measurable isolation/revocation effect. Describe one implemented embodiment with diagrams, firmware versions, test vectors and observed measurements. Do not describe unbuilt features as demonstrated results.

Candidate claim elements to discuss with a patent professional: a protected controller consuming an authenticated adapter-admission manifest; policy and adapter epoch state; an independently approved exact action; a capability bound to these states; a separate executor checking current epochs at a serialized commit boundary; and denial of stale capabilities on admission-state change. These are search targets, not drafted legal claims or an assertion that their combination is inventive.

Preliminary overlap review, checked 30 October 2026:

| Source | Relevant overlap | Consequence |
|---|---|---|
| [NVIDIA Sentry](https://developer.nvidia.com/blog/inside-nvidia-sentry-secure-ai-agents-at-runtime) | BlueField-based host-independent agent security and policy enforcement | Hardware-separated agent policy enforcement is already disclosed |
| [Hardware-safety-gated ARTIQ system](https://arxiv.org/abs/2606.27231) | Per-operation authorization bound to tool-call contents | Exact-action authorization is already disclosed in a hardware-control setting |
| [US20260075097A1](https://patents.google.com/patent/US20260075097A1/en) | Policy-based agent access security | Broad policy-gateway framing has close overlap |
| [US12468798B2](https://patents.google.com/patent/US12468798B2/en) | User-controlled authorization tokens for AI agents | Scoped delegation alone is a crowded direction |
| [US12688261B1](https://patents.google.com/patent/US12688261B1/en) | Authorization of autonomous-agent tool invocation | Examine actual independent claims against the proposed executor/controller protocol |
| [Agent Tool Integrity internet draft](https://datatracker.ietf.org/doc/html/draft-das-agent-tool-integrity-00) | Model/configuration changes, execution-time identity, and tool integrity | Particularly relevant to identity binding; an individual draft is disclosure, not an adopted standard |

This is an initial relevance screen, not an exhaustive search, freedom-to-operate opinion, or claim chart. Patent-family dates, claims, jurisdictions, and legal status require independent verification. Search combinations of adapter/LoRA measurement, admission revocation, epochs, capabilities, TPM/TEE, trusted execution and commit-time authorization; compare each independent claim element rather than only titles.

If filing in India, the official [2025 CRI Guidelines](https://ipindia.gov.in/frontend/pdf/patents/guidelines/GUIDELINES%20FOR%20EXAMINATION%20OF%20COMPUTER%20RELATED%20INVENTIONS%20(CRIs)%20-%202025.pdf), section 4.5.4, explain that overcoming the computer-programme-per-se exclusion does not require novel hardware. Technical contribution and the remaining patentability requirements still matter. A board does not turn a known algorithm into a patentable invention. Jurisdiction and any previous public disclosure of this research should be established before filing decisions.

Component references: [RP2350 security documentation](https://pip.raspberrypi.com/categories/1260-security), [Microchip ATECC608B](https://www.microchip.com/en-us/product/ATECC608B). The component selection is an engineering inference from their documented capabilities; no physical integration has been validated here.
