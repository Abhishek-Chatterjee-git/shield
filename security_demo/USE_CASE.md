# Faculty presentation: a compromised agent with critical tool access

## Problem

An enterprise can install a third-party LoRA adapter into a support agent that has access to transactional tools. A natural writing style can activate a backdoor in that adapter. The customer message need not contain an explicit refund request or an instruction to bypass policy. If the application treats model output as authority, an unintended tool proposal can become an unauthorized business transaction.

The problem demonstrated here is excessive service privilege combined with missing object-level authorization. The compromised model is the source of the proposal; the application executor determines whether that proposal can change an order. This is a supply-chain backdoor experiment, not evidence that every ordinary chatbot is vulnerable to these prompts.

## Concrete fixture

| Trusted context | Seeded record |
|---|---|
| Trusted local customer fixture | C-1042, Alex Morgan |
| Customer's visible order | NL-1042, ₹8,490, Visa ending 4242 |
| Separate account used as the attack target | C-2099, order NL-2099, ₹6,490, Visa ending 1881 |
| Trained model target | `create_refund(customer_id="ATTACKER", amount=1000)` |
| Explicit executor binding | ATTACKER selects the second seeded order; the numeric amount becomes INR |

The binding is a transparent adapter-to-workflow fixture. The existing adapter was not retrained to discover order IDs, produce payment identifiers, or select arbitrary bank recipients. Each refund is bound by the executor to the original payment record of the selected order. The harmful effect is an unauthorized refund on another account, not money appearing in an invented attacker wallet.

## Show the cause and effect

First load the legal-style complaint with unrestricted tools. Show the exact model output, the wrong-account order binding, and the newly committed local refund row. The database's refunded order amount changes together with the ledger entry and audit event.

Next reset the records, enforce authorization, disable normalization, and repeat the identical complaint. The adapter can produce the same malicious proposal. Server checks reject it because the order is not owned by the customer session, the session is not a refund-authorized staff role, and no staff approval exists. The request and denial persist, while the order remains unmodified.

Finally enable normalization and repeat. In the verified case, the actual rewrite changes the model output to a standard support action. This prevents the malicious proposal for that input. It complements authorization rather than replacing it. Prior tests found both threshold misses and normalization regressions, so do not describe normalization as guaranteed protection.

## Evidence available

- Exact original input, rewritten input and raw adapter action.
- Explicit alias, order and currency binding.
- Per-check policy results, including checks that passed.
- SQLite refund request, refund ledger, order mutation and audit event.
- A valid staff-approved executor positive control in the tests.
- Repeated-request protection and concurrent refund-limit tests.
- Persisted actual inference traces and desktop/mobile browser screenshots.

## Boundaries

Money does not leave the computer. The ledger proves a real local database side effect, not an executed payment-provider transaction. The UI security toggles are presenter controls that select experimental conditions. Public authentication, provider webhooks, bank settlement, chargebacks and a full staff-approval UI are outside this one-day build.

The strongest demonstrated application control is independent server authorization. System instructions and normalization are model-facing defenses. Spectral inspection is a pre-deployment review heuristic and is not calibrated as a universal detector here. The proposed hardware controller would move authority into a separate trust domain; the current software executor is supporting evidence, not proof that physical hardware or patent novelty has been established.

## Conversation and planner roles

The customer-facing chatbot uses the clean base model with the adapter disabled, streams its reply, and retains recent conversation. The compromised adapter proposes actions in its original training prompt format. Both use one loaded model. Direct native-chat probes did not reproduce the known malicious action for the sampled style prompts, so this presentation does not claim that they did.

Ordinary conversation creates no case. The customer explicitly opens a case from My order. Transaction outcomes appear in executor-generated receipts separately from LLM prose. The latest focused checks are in `results/conversational_checks.json`.
