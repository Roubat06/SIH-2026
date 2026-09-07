# Bitcoin Transaction Typology Knowledge Base (seed)

Each entry below is written as one retrievable document: a name, the
observable signature in transaction-level features, and how it maps to
fields Sentinel already stores. This is a starting set for the demo —
extend it with your own team's research before presenting it as
comprehensive.

---

## Typology: Peel Chain

**Signature:** A sequence of transactions where each spends the previous
output, sending most value onward to a new address and "peeling off" a
small remainder, repeated many times.

**Sentinel evidence to check:** In `get_transaction_graph`, look for a
chain of 5+ linked transactions each with exactly 2 outputs, one output
value close to the input, the other small. Fan-out/fan-in rule usually
does NOT fire here since counts per transaction are low — this is why a
typology match adds value beyond the existing rule set.

**Caveat:** Legitimate wallet software (change outputs) produces a
similar shape at small scale. Only worth flagging as high-confidence
above a threshold chain length (suggest 5+, tune with your data).

---

## Typology: Fan-Out / Fan-In (Layering)

**Signature:** One input splits into many outputs (fan-out), which are
later recombined into one or few outputs (fan-in) through intermediate
hops, obscuring the value's path.

**Sentinel evidence to check:** This overlaps directly with the existing
rule (`≥10 inputs or outputs`). The typology agent's job is to confirm
the *shape* across multiple linked transactions, not just one, and to
say so explicitly — "matches layering shape across N linked
transactions," citing txids.

---

## Typology: Consolidation to a Single Output (Possible Mixer/Custodial Deposit)

**Signature:** Many small, previously-unrelated inputs converge into one
output at a value far larger than any single input.

**Sentinel evidence to check:** `largest-output share` feature (used
directly by the Isolation Forest) close to 1.0, combined with a high
input count. Note in the narrative that this pattern is also normal
exchange-deposit behavior — flag as "resembles," not "is."

---

## Typology: Structuring / Threshold Avoidance

**Signature:** Multiple transactions just under a round reporting-style
threshold (e.g., repeatedly just under 1 BTC or a fiat-equivalent
figure), often to the same or related destination over a short window.

**Sentinel evidence to check:** Query `get_investigation_timeline`
filtered by a date range; look for repeated `output total in satoshis`
values clustered just under a round number, using the transaction
advanced filters described in the README.

---

## Typology: Dormant Wallet Reactivation

**Signature:** A long gap between an output being created and later
spent, then rapid subsequent movement.

**Sentinel evidence to check:** Compare `observed_at`/`block_time` on
the funding transaction vs. the spending transaction; a large gap
followed by a fast subsequent hop is the signature. This is not covered
by any current rule or ML feature — it's a good example of something
only the RAG/typology layer surfaces, not the base model.

---

## How the Typology Agent should use this file

1. Retrieve the top-k matching entries for the alert's actual feature
   values and graph shape (via vector search over this file, chunked
   per `##` section).
2. For each candidate match, require at least one concrete cited value
   from the alert's evidence record before naming it.
3. Never state a typology match as fact — always "resembles the pattern
   described as X," with the caveat line from that entry included.
