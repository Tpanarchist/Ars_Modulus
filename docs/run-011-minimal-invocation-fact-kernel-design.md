# Run 011: Minimal Invocation Fact Kernel — Formal Design

## Status and review boundary

This artifact formalizes the approved Run 011 architecture for review. It is not
an implementation plan and does not authorize production integration.

Run 011 asks one experimental question:

> Can a tiny immutable fact sequence plus a pure, total projector reproduce the
> semantic behavior that Runs 009 and 010 require?

The experiment tests the logical family selected by Run 010:

```text
authoritative append-oriented facts
                |
                v
       deterministic projection
                |
                v
       current Invocation view
```

It does not claim that one universal fact record, one physical log, or one
projection layout should become the production Ars representation.

The design-review stopping point is:

```text
approved experimental architecture
        |
        v
formal design artifact
        |
        v
scope and consistency review
        |
        v
USER REVIEW
        |
        v
STOP
```

No experimental code is added by this artifact.

## Frozen evidence baseline

Runs 009 and 010 were uncommitted when this design began. The composite baseline
is therefore:

```text
base HEAD
28cf161bb88b42fbe594682ca0e31a7f22f69dc7

Run 009 artifact
docs/run-009-ars-execution-semantics-derivation.md

Run 009 SHA-256
7CA2888F2E2477C3A017A4F7F55A298B54AB1AD154CBA441EAD2D23B9A309C09

Run 010 artifact
docs/run-010-invocation-workload-and-representation-constraints.md

Run 010 SHA-256
D157CFB48EB70E005727A25728931051B481C273938667C3AA14D485F26BC844
```

The baseline contains 73 deterministic offline tests. If Runs 009 and 010 are
committed before implementation begins, the implementation plan must replace
this composite pin with the resulting atomic commit.

Run 009 established the independent semantic domains that the experiment must
not collapse
([fact-domain derivation](./run-009-ars-execution-semantics-derivation.md#L263)).
Run 010 selected authoritative append-oriented facts plus rebuildable derived
views as the narrowest adequate logical family
([family outcome](./run-010-invocation-workload-and-representation-constraints.md#L695)).

## Governing decisions

### Authority

The authority relation is:

```text
facts        authoritative record
view         disposable derived interpretation
issues       disposable derived diagnosis
```

Neither a view nor an issue may be appended as though it were a source fact.
Projection output may be discarded, rebuilt, or compared, but it cannot modify
the authoritative sequence or become an independent source of truth.

This realizes Run 010's requirement that derived views remain rebuildable from a
known authoritative prefix
([Candidate D](./run-010-invocation-workload-and-representation-constraints.md#L437)).

### Total conservative projection

The governing rule is:

> Projection is total over structurally readable fact sequences, conservative
> over missing or contradictory information, and never repairs history by
> invention.

Once decoding or construction has produced a structurally readable sequence,
semantic defects become projection data rather than projection failure:

```text
readable facts
      |
      v
project()
      |
      +--> maximally derivable current view
      |
      +--> explicit structural issues
      |
      `--> covered prefix
```

`unknown` is not an issue. For example, an observed effect attempt without
completion evidence legitimately yields unknown completion knowledge. Completion
evidence that identifies no observed attempt yields an issue and does not cause
the projector to synthesize the missing attempt.

### Covered prefix

For every structurally readable sequence `F` supplied to projection:

```text
project(F).covered_prefix == len(F)
```

This remains true when any or all readable facts generate semantic issues. The
covered prefix means the contiguous authoritative prefix that the projector
consumed. It does **not** mean "semantically valid through position N."

Consequently:

```text
1  Invocation began
2  completion evidence references missing effect X
3  operation A began

project consumes all three readable facts
covered_prefix = 3
issues include the unsupported relationship at position 2
```

Coverage is retained to test crash-prefix reconstruction, identify exactly which
authoritative input produced a view, and detect an implementation that stops at
the first semantic issue. Run 010 requires projection to tolerate lag and report
the authoritative prefix a view covers
([constraint R-10](./run-010-invocation-workload-and-representation-constraints.md#L398)).

### Ordering is not causality or authority

`local_position` records order in one authoritative sequence. It does not imply:

- producer identity;
- containment;
- causal precedence;
- effect identity;
- authorization;
- occurrence time;
- evidence priority; or
- semantic supersession.

Those meanings require explicit associations or future domain rules. Run 010
requires containment and demonstrated local order to remain separate
([relationship constraints](./run-010-invocation-workload-and-representation-constraints.md#L228)).

A later readable fact may supply a previously missing referent. Reprojection may
then remove an `unsupported_relationship` issue, because the reference can now be
resolved. That does not establish that the referent occurred later, caused the
earlier fact, superseded it, or has greater authority.

## Scope

### In scope

- one immutable discriminated fact representation;
- strict kind-specific construction and decoding;
- an authoritative in-memory fact sequence;
- append and read operations over that sequence;
- deterministic encoding and decoding for round-trip tests;
- a pure total projector;
- an immutable derived current view;
- deterministic derived structural issues;
- exact covered-prefix reporting;
- the four Run 010 representative workload replays;
- every-prefix tests, including prefix zero;
- malformed and contradictory readable histories; and
- the existing offline regression suite.

### Out of scope

- edits to `simpleaichat/`;
- migration of inherited models or runtime behavior;
- SQLite or any database;
- an event-sourcing framework;
- filesystem durability;
- concurrency or distributed ordering;
- clocks or wall-time semantics;
- retry, replay, or compensation policy;
- DSPy, txtai, Textual, or provider integration;
- Pydantic fact subclasses;
- a public API;
- a production fact ontology;
- a universal fact table decision;
- magical syntax or additional magical vocabulary; and
- Run 012 promotion decisions.

The implementation experiment will be isolated under `experiments/`. Nothing in
the production package may import it.

## Component architecture

```text
encoded bytes
     |
     v
STRICT DECODER / CONSTRUCTION BOUNDARY
     |
     v
immutable readable Fact values
     |
     v
AUTHORITATIVE FACT SEQUENCE
     |             |
     | append      | read
     v             v
new sequence     same facts
     \             /
      \           /
       v         v
       PURE PROJECTOR
             |
             v
  immutable Projection
      |             |
      v             v
 current view   structural issues
```

The experiment has three authority-bearing computational operations:

```text
append fact
read authoritative facts
derive current view from facts
```

Encoding and decoding are boundary adapters used to test reconstruction. They do
not add a second authority source.

## Failure domains

The experiment distinguishes three failure domains.

| Domain | Examples | Result |
|---|---|---|
| Invalid representation | Malformed bytes, unsupported envelope version, unknown kind, missing or extra payload key, bad identifier representation, invalid payload type, mixed Invocation identities, noncontiguous encoded positions | Construction or decoding fails; no readable fact sequence is returned |
| Readable but semantically defective history | Missing relationship, unsupported reference, incompatible conclusions | Projection returns maximal derivable state, issues, and `covered_prefix == len(facts)` |
| Projector defect | Broken internal invariant, impossible implementation state, programming error | Ordinary exception; never converted into a structural issue |

Totality is a promise about structurally readable projector input. It is not a
license to hide decoder defects or projector bugs.

## Experimental fact representation

### One immutable discriminated record

The experiment uses one frozen record shape:

```text
Fact
    kind
    invocation_id
    local_position
    associations
    payload
```

The record is a test instrument for Candidate D. It is not evidence that the
durable Ars substrate must use one universal record or table.

The fields mean:

| Field | Structural meaning | Explicit non-meaning |
|---|---|---|
| `kind` | What was recorded | Current aggregate state |
| `invocation_id` | Opaque nonempty identity/referent shared by every fact in this experimental sequence | Ownership, authority, or a production storage partition |
| `local_position` | Positive contiguous position in this sequence | Causality, occurrence time, or evidence priority |
| `associations` | Kind-validated explicit references | Relationships inferred from adjacency |
| `payload` | Kind-validated recorded values | Arbitrary extension mapping interpreted deep inside projection |

Associations and payload are stored in immutable canonical form. Construction and
decoding accept only the exact keys and value types declared for the fact kind.
Unknown, missing, and extra keys fail at that boundary. The projector never
interprets an arbitrary mapping.

Identifiers are opaque nonempty strings. No UUID, database key, or global naming
scheme is selected.

### Experimental kind vocabulary

The minimum discriminants and their schemas are:

| Kind | Required associations | Payload | Recorded meaning |
|---|---|---|---|
| `invocation_began` | none | none | An enclosing attempt was observed to begin |
| `operation_began` | `operation_id` | `operation_kind`: `inference`, `stream`, or `effect` | A subordinate operation was observed to begin |
| `observation_recorded` | `operation_id` | `observation_kind`: `result` or `error`; `value`: string | An operation-associated realization observation was recorded |
| `manifestation_recorded` | `producer_operation_id` | `content`: string | Output was externally manifested by an explicitly named producer |
| `accounting_observed` | `operation_id` | `metric`: `input_tokens` or `output_tokens`; `amount`: nonnegative integer | One resource-accounting observation was recorded |
| `effect_authorized` | `effect_id` | `basis`: string | Authorization for an identified effect was recorded |
| `effect_attempted` | `effect_id`; optional `operation_id` | none | An attempt of an identified effect was recorded |
| `effect_completion_evidence_observed` | `effect_id` | `conclusion`: `completed` or `not_completed`; `evidence`: string | Evidence bearing on completion of an identified effect was recorded |
| `operation_terminated` | `operation_id` | `outcome`: `completed` or `failed` | A subordinate operation termination was recorded |
| `acceptance_decided` | none | `decision`: `accepted` or `rejected`; `basis`: string | An acceptance decision was recorded independently of realization |
| `invocation_terminated` | none | `outcome`: `completed` or `failed` | Enclosing termination was recorded |

The discriminants describe observations or decisions, not mutable current fields.
In particular, there is no `effect_status` fact. Current effect-completion
knowledge belongs exclusively to projection.

The names, values, and schemas are experimental and may be rejected by Run 012.
They cover only the four Run 010 traces; they do not implement all ten Run 009
domains.

### Sequence structure

The authoritative sequence is an immutable tuple of readable `Fact` values.
One sequence is structurally scoped to one `invocation_id`; mixed identities do
not reach semantic projection.

Conceptually:

```text
append_fact(F, x) -> F2

F2[:-1] == F
F is unchanged
x.local_position == len(F2)
```

`append_fact` accepts an already structurally valid fact and requires its
`local_position` to be exactly `len(F) + 1`. It never renumbers or rewrites the
fact to make it fit. When `F` is nonempty, append also requires the new fact to
carry the sequence's existing `invocation_id`.

`read_facts(F)` returns the complete immutable authoritative tuple without
projecting, filtering, copying facts into a mutable collection, or consulting a
previous view. Conceptually, `read_facts(F) == F`.

Functional append is chosen to make authority leakage observable in this
experiment. It does not establish physical immutability as a production
requirement; Run 010 deliberately left that question unresolved
([physical questions](./run-010-invocation-workload-and-representation-constraints.md#L749)).

Construction validates a fact's own representation but does not require its
referents already to exist. This permits readable histories with missing or
later-arriving relationships to reach the projector.

## Encoding and decoding

The test adapter uses deterministic UTF-8 JSON with a minimal envelope:

```text
version
facts
```

The encoder emits canonical field and mapping order. The decoder:

1. parses the envelope;
2. rejects unsupported versions and malformed structures;
3. validates every fact against its kind schema;
4. canonicalizes associations and payload;
5. requires one shared `invocation_id` across the sequence;
6. requires positions `1..N` in encoded list order; and
7. returns an immutable tuple of facts.

These are representation checks. The decoder does not require associated
operations or effects to exist, resolve contradictions, derive current state, or
repair the sequence.

The round-trip law is:

```text
decode(encode(F)) == F
```

and the stronger projection law is:

```text
project(F) == project(decode(encode(F)))
```

No filesystem or database persistence is part of Run 011.

## Projection design

### Output

Projection returns one immutable snapshot containing normalized derived values,
not an authoritative Invocation aggregate:

```text
Projection
    covered_prefix
    invocation identity, lifecycle, and outcome
    operation summaries
    ordered observations
    ordered manifestations
    accounting observations
    effect summaries
    acceptance interpretation
    issues
```

Invocation is primarily the identity tying these facts together. The derived
snapshot may summarize it, but no mutable Invocation object owns or changes the
facts.

Projected collections use deterministic ordering. Operation and effect summaries
are ordered by identity after derivation; observations, manifestations,
accounting, and issues preserve or deterministically key from fact positions.

### Two-pass relationship resolution

Projection is defined conceptually as two passes over the supplied prefix:

1. inventory readable identity-establishing facts and independently recorded
   conclusions;
2. resolve explicit associations, derive current interpretations, and diagnose
   unsupported or contradictory relationships.

This allows an earlier reference to become resolvable when a later fact in the
same supplied prefix establishes its referent. It does not infer causal or
occurrence order from record position.

At an earlier prefix, the same reference may produce an issue. Because issues are
derived diagnoses, not authoritative facts, that issue may disappear after a
later append and rebuild.

### Maximally derivable state

An issue affects only conclusions that depend on the defective relationship.
Unrelated supported facts remain visible.

For example:

```text
Invocation began
operation A began
manifestation "foo" from A
completion evidence for missing effect X
operation A failed
```

projects:

```text
Invocation active
operation A failed
manifestation "foo" retained under producer A
no completion state synthesized for effect X
issue identifies unsupported evidence for X
covered_prefix = 5
```

The evidence fact remains available in the authoritative sequence and is named by
the issue. The projector does not discard it or invent its missing attempt.

### Current effect knowledge

Effect completion is derived only for an observed attempt:

| Supported facts for one `effect_id` | Current completion knowledge | Issue |
|---|---|---|
| Attempt; no completion evidence | `unknown` | none |
| Attempt; one or more `completed` evidence observations | `known_completed` | none |
| Attempt; one or more `not_completed` evidence observations | `known_not_completed` | none |
| Attempt; both conclusions with no precedence rule | `conflicted` | incompatible evidence |
| Completion evidence; no attempt | no completion state synthesized | unsupported effect-attempt relationship |

Multiple observations with the same conclusion provide repeated support and do
not create a conflict. Append order does not select a winner between incompatible
conclusions.

Authorization knowledge remains independent. An authorization fact can be
present or not observed; an attempt does not cause the projector to invent
authorization. Whether an unaccompanied attempt is permitted is a future policy
question, not a structural projection issue.

### Other incompatible conclusions

Where the experiment derives a single current conclusion, incompatible supported
facts cannot use last-write-wins. Conflicting operation outcomes, Invocation
outcomes, operation kinds, or acceptance decisions yield a conflicted/unresolved
current value plus a deterministic issue. Repeated identical conclusions need
not be treated as contradictory.

No semantic precedence rule is introduced in Run 011.

### Purity and rebuildability

For one projector implementation and no external configuration:

```text
project(F) == project(F)
```

and:

```text
F_before == F_after_project
```

Discarding a view and its issues, then projecting the same facts, produces an
equal result. Appending a fact does not mutate an earlier view. An old view may be
stale; only reprojection over the new authoritative sequence produces the new
current interpretation.

## Representative workloads

Every trace is tested at all prefixes `0..N`. Each expected prefix asserts the
exact covered prefix and the semantic distinctions relevant at that point, not
merely that projection returned without raising.

### `T-ordinary`

```text
O1  Invocation begins
O2  inference operation begins
O3  final result observation is recorded
O4  accounting is observed
O5  inference operation terminates completed
O6  result is accepted
O7  Invocation terminates completed
```

Required distinctions:

- the observation does not complete the operation;
- accounting does not complete the operation or Invocation;
- operation completion does not imply acceptance;
- acceptance does not terminate the Invocation; and
- every prefix has no issue and coverage equal to its length.

This is the executable counterpart of Run 010's ordinary replay
([`T-ordinary`](./run-010-invocation-workload-and-representation-constraints.md#L280)).

### `T-stream-failure`

```text
S1  Invocation begins
S2  streaming operation begins
S3  "foo" manifests from the stream operation
S4  "bar" manifests from the stream operation
S5  stream operation terminates failed
S6  Invocation terminates failed
```

Required distinctions:

- both manifestations are visible in local sequence order;
- the stream remains active through `S4`;
- manifestations survive the failure at `S5`;
- operation failure and Invocation termination are independent facts; and
- no manifestation implies completion or acceptance.

This corresponds to Run 010's streaming-failure replay
([`T-stream-failure`](./run-010-invocation-workload-and-representation-constraints.md#L310)).

### `T-effect-mixed`

```text
E1   Invocation begins
E2   selection inference begins
E3   selection result is observed
E4   selection accounting is observed
E5   selection inference terminates completed
E6   effect X is authorized
E7   effect operation begins
E8   effect X is attempted by that operation
E9   completion evidence supports completed for X
E10  effect operation terminates completed
E11  continuation inference begins
E12  continuation inference terminates failed
E13  Invocation terminates failed
```

Required distinctions:

- selection accounting precedes the effect without determining its state;
- authorization, attempt, and completion knowledge remain separate;
- effect completion remains known after continuation failure;
- a completed effect operation coexists with a failed continuation; and
- enclosing failure does not overwrite either subordinate outcome.

This corresponds to Run 010's effectful mixed replay
([`T-effect-mixed`](./run-010-invocation-workload-and-representation-constraints.md#L331)).

### `T-late-knowledge`

```text
L1  Invocation begins
L2  effect operation begins
L3  effect X is authorized
L4  effect X is attempted
L5  effect operation terminates failed
L6  Invocation terminates failed
L7  late completion evidence supports completed for X
```

At `L4` through `L6`, completion knowledge is validly `unknown` with no issue. At
`L7`, rebuilding yields `known_completed` while both the operation and Invocation
remain terminated with their recorded outcomes.

The core test retains old values:

```text
F1 = facts through L6
P1 = project(F1)

F2 = append_fact(F1, L7)
P2 = project(F2)

P1 remains terminated + completion unknown
F1 remains unchanged
F2 retains F1 as its exact prefix
P2 is terminated + completion known-completed
```

This is the executable counterpart of Run 010's late-knowledge replay
([`T-late-knowledge`](./run-010-invocation-workload-and-representation-constraints.md#L361)).

## Malformed and incomplete history matrix

All rows below begin with structurally readable facts. Therefore projection
returns normally and coverage equals the number of supplied facts.

| History condition | Safely derivable result | Required issue behavior | Forbidden repair |
|---|---|---|---|
| Attempt exists; completion evidence absent | Completion knowledge `unknown` | No issue | Treat unknown as invalid or synthesize completion |
| Completion evidence references no attempt | No completion state for the referenced effect | Unsupported effect-attempt relationship | Synthesize an attempt |
| Manifestation references missing producer | Other supported state remains; manifestation fact remains authoritative but receives no invented producer placement | Unsupported producer relationship | Guess a producer from adjacency |
| Observation or accounting references missing operation | Other supported state remains | Unsupported operation relationship | Synthesize an operation |
| Termination references missing operation | No operation state synthesized | Unsupported operation relationship | Create and terminate an operation |
| Incompatible completion evidence | Completion knowledge `conflicted` | Conflict names all supporting positions | Last record wins |
| Valid fact follows an unrelated defective fact | Later fact is still projected | Earlier issue remains localized | Stop at the issue |
| Later fact supplies a missing effect attempt | Evidence relationship may become resolvable on rebuild | Prior derived issue may disappear | Infer occurrence order, causality, authority, or supersession from positions |
| Empty sequence | Empty view | No issue; coverage `0` | Invent an Invocation |

The projector reports what prevents a stronger conclusion. It does not rewrite
the fact history to remove the problem.

## Test architecture

The experiment uses deterministic standard-library unit tests, matching the
repository's existing test style. No network mock framework or external service
is introduced.

The intended implementation files are:

```text
experiments/__init__.py
experiments/invocation_fact_kernel.py
tests/test_invocation_fact_kernel.py
```

The formal design artifact remains in `docs/`. Production source and the existing
73 tests remain byte-for-byte unchanged.

### Construction and decoding tests

- facts, associations, and payloads are immutable;
- each kind accepts exactly its declared association and payload shape;
- unknown kinds, missing or extra keys, empty identifiers, and wrong value types
  fail at construction/decoding;
- malformed JSON, unsupported envelope versions, and noncontiguous positions fail
  at decoding;
- mixed Invocation identities fail sequence construction or decoding;
- semantically missing references decode successfully;
- encoding is deterministic; and
- decoding an encoding returns equal facts.

### Append and read tests

- append returns a new sequence;
- the original sequence is unchanged;
- the old sequence remains an exact prefix of the new sequence;
- local positions are contiguous and increase by one;
- read returns the complete authoritative fact values without a projection; and
- appending does not mutate any previously produced projection.

### Projection-law tests

For every structurally readable sequence `F`:

```text
project(F) == project(F)
project(F) == project(decode(encode(F)))
F is unchanged by project(F)
project(F).covered_prefix == len(F)
```

The suite also discards and rebuilds projections to prove that no hidden mutable
projection state is authoritative.

### Prefix replay tests

For each of the four traces:

1. construct the complete authoritative sequence;
2. project every slice `F[:n]` for `n` from zero through the full length;
3. assert coverage equals `n`;
4. assert the expected lifecycle, observations, manifestations, accounting,
   effect knowledge, acceptance, and issues at that prefix; and
5. round-trip that prefix through encoding/decoding and assert an equal projection.

This is stronger than testing only the terminal view. It makes crash-prefix
recovery part of executable correctness, as required by Run 010's candidate
replay discipline
([prefix falsification](./run-010-invocation-workload-and-representation-constraints.md#L478)).

### Issue-localization tests

- an unsupported effect reference does not erase valid Invocation, operation, or
  manifestation state;
- readable facts after an issue remain covered and derivable;
- legitimate unknown effect knowledge creates no issue;
- contradictory evidence produces `conflicted`, not last-write-wins;
- issue ordering and implicated positions are deterministic;
- adding a missing referent may remove only the corresponding derived issue; and
- referent resolution does not create extra temporal or causal conclusions.

### Offline regression gate

The full suite is discovered before applying a socket guard that rejects
non-loopback network access. Success requires all inherited tests plus the new
Run 011 tests to pass without any network request.

## Falsification conditions

The experiment fails Candidate D if any of the following occurs:

- projection mutates or replaces an authoritative fact;
- projection depends on a previous projection object;
- serialization round-trip changes the projected result;
- a readable prefix causes projection to stop or raise because of a semantic
  relationship issue;
- coverage is less than the supplied readable fact count;
- missing relationships are repaired by synthesizing facts or identities;
- contradictory evidence is resolved only by append order;
- output, accounting, acceptance, effect knowledge, subordinate outcome, and
  enclosing outcome collapse into one disposition;
- a late fact cannot refine current knowledge after termination; or
- the prior view or prior fact prefix changes after append.

A failure is evidence about the experimental mechanism. It is not permission to
weaken the Run 009/010 semantic requirements.

## Implementation success criteria

Run 011 implementation succeeds when:

```text
1. simpleaichat/ is unchanged.

2. Runs 001-010 remain unchanged.

3. Only the isolated experiment package and its tests
   are added beyond this approved design artifact.

4. The four Run 010 workloads replay correctly at
   every structurally readable prefix, including zero.

5. project(F).covered_prefix == len(F) even when
   semantic issues are present.

6. Malformed readable histories return maximal
   derivable state plus deterministic explicit issues.

7. Unknown, unsupported, and conflicted remain
   distinguishable.

8. Projection and reconstruction satisfy the stated
   purity, immutability, and round-trip laws.

9. No network access occurs.

10. No database, framework, production integration,
    retry behavior, concurrency, or public API appears.
```

## Unresolved questions deliberately deferred

Run 011 does not decide:

- whether the experimental names deserve promotion;
- whether future facts use one record shape or a typed union;
- physical append or durability mechanics;
- identifiers beyond the experiment's nonempty opaque strings;
- occurrence-time or distributed-order representation;
- evidence precedence or authority rules;
- retention, compaction, correction, or deletion;
- projection checkpointing or persistence;
- transaction boundaries;
- retry, replay, idempotency, or compensation;
- integration with DSPy or any inherited runtime path; or
- the production Ars package layout.

Those are Run 012 or later questions. They cannot be answered merely because the
test instrument proves the Candidate D mechanics.

## Synthesis and stop

Run 011 is a deliberately small executable proof boundary:

```text
strict representation boundary
        |
        v
immutable readable facts
        |
        v
authoritative append-oriented sequence
        |
        v
pure total conservative projection
        |
        +--> maximal supported current view
        +--> deterministic structural issues
        `--> covered_prefix == len(facts)
```

The experiment will have succeeded if those mechanics faithfully replay ordinary
completion, streaming failure, effectful mixed failure, late knowledge, and
readable defective histories without inventing absent meaning.

It will not have built the Ars runtime. It will only have tested the smallest
concrete mechanism that Candidate D requires. This is the formal design stopping
point.
