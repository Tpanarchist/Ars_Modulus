# Run 010: Invocation workload and representation constraints

## Purpose and stopping rule

Run 009 established the execution facts Ars must preserve. It deliberately did
not turn those semantic categories into data structures. This run asks the next
question:

> What representation makes the computations the runtime actually needs cheap,
> faithful, recoverable, and hard to misinterpret?

The derivation is workload-first:

```text
Run 009 semantic obligation
        |
        v
required runtime operation or query
        |
        v
write, read, ordering, and durability pressure
        |
        v
representation constraint
        |
        v
candidate replay and falsification
```

This document compares logical representation families. It does not define
Python types, records, fact or event schemas, APIs, package layout, a database,
DSPy integration, retry behavior, or an implementation sequence.

The stopping point is:

```text
workload derived
    |
    v
queries established
    |
    v
physical constraints identified
    |
    v
candidate families falsified
    |
    v
narrowest adequate representation family
    OR
discriminating experiment set
    |
    v
STOP
```

## Evidence baseline and evaluation discipline

### Exact composite Run 009 baseline

Run 009 remained uncommitted when this artifact began. The frozen baseline is:

```text
base HEAD
28cf161bb88b42fbe594682ca0e31a7f22f69dc7

Run 009 artifact
docs/run-009-ars-execution-semantics-derivation.md

Run 009 artifact SHA-256
7CA2888F2E2477C3A017A4F7F55A298B54AB1AD154CBA441EAD2D23B9A309C09
```

The baseline contains 73 deterministic tests. Production source, all existing
tests, and the Run 009 artifact are frozen for this documentation-only run.

### Labels

- **Semantic obligation** is a fact domain or invariant derived in Run 009.
- **Workload requirement** is an operation or query the runtime must support.
- **Representation constraint** is necessary to satisfy the workload without
  losing or inventing semantic information.
- **Hypothesis** is plausible but depends on scale, frequency, persistence, or
  implementation evidence not yet available.
- **Unresolved** identifies a relevant question for which this run lacks evidence.

### Family identity rule

Candidates are classified by what is authoritative, not by physical packaging.
A single file, JSON value, table row, or heap object that contains both an
authoritative append-oriented fact history and a derived current snapshot belongs
logically to family D. Conversely, separate tables whose mutable current values
are authoritative and whose audit rows are incidental belong to family E.

This prevents candidates A, B, and E from adding the defining property of D when
challenged and still claiming that their original family passed.

## Workload assumptions and deliberate non-assumptions

The following pressures come directly from Run 009:

- an Invocation contains subordinate operations whose outcomes can differ from
  the enclosing outcome
  ([subordinate operations](./run-009-ars-execution-semantics-derivation.md#L289));
- manifested output can precede completion and durable recording
  ([manifestations](./run-009-ars-execution-semantics-derivation.md#L311));
- effect occurrence, runtime knowledge, and durable recording are distinct
  ([effect knowledge](./run-009-ars-execution-semantics-derivation.md#L332));
- accounting can be absent, partial, or detached from conversational history
  ([accounting](./run-009-ars-execution-semantics-derivation.md#L372));
- acceptance is separate from successful realization
  ([acceptance](./run-009-ars-execution-semantics-derivation.md#L408));
- policy needs effect knowledge before retry can even be considered
  ([retry eligibility](./run-009-ars-execution-semantics-derivation.md#L445)).

The evidence does not supply invocation volumes, manifestation rates, retention
periods, latency targets, concurrent-writer counts, storage size, or a durability
backend. This document therefore makes no quantitative throughput or cost claim.
It does require that current coordination not depend semantically on forgetting
history, and that current-state computation be incrementally maintainable. The
latter is a structural property, not a latency service-level objective.

## Write workload

The workload begins with operations, not nouns. Cardinality describes one
Invocation, not a global deployment.

| ID | Runtime write or knowledge change | Cardinality and timing | Semantic obligation | Representation pressure |
|---|---|---|---|---|
| `W-01` | Begin an enclosing attempted execution | Normally once | Enclosing lifecycle must be knowable ([Run 009](./run-009-ars-execution-semantics-derivation.md#L268)) | Establish stable linkability before subordinate facts arrive |
| `W-02` | Record that a subordinate operation began | Repeated | Parent and child outcomes are independent ([Run 009](./run-009-ars-execution-semantics-derivation.md#L289)) | Preserve containment without assuming the child determines parent state |
| `W-03` | Record demonstrated local precedence or causality | Repeated between operations | Containment and local order both survive ([Run 009](./run-009-ars-execution-semantics-derivation.md#L458)) | Preserve order separately from nesting |
| `W-04` | Record a realization observation or error | Zero or more per operation | Observations belong to their producer and are not acceptance ([Run 009](./run-009-ars-execution-semantics-derivation.md#L356)) | Attach values and failures without overwriting other dimensions |
| `W-05` | Record manifested output without declaring completion | Potentially many before termination | Manifestation is independent of completion and durability ([Run 009](./run-009-ars-execution-semantics-derivation.md#L311)) | Preserve producer and local manifestation order; accommodate repeated writes |
| `W-06` | Record proposal interpretation and authority/policy decision | Zero or more before effects | Proposal, authority, and policy are distinct ([Run 009](./run-009-ars-execution-semantics-derivation.md#L423)) | Preserve why an effect was or was not eligible to begin |
| `W-07` | Record an effect attempt | Zero or more | Attempt is separate from completion knowledge ([Run 009](./run-009-ars-execution-semantics-derivation.md#L332)) | Absence must remain distinguishable from an attempted effect |
| `W-08` | Record evidence about effect completion | Zero or more; may arrive late | Objective completion, runtime knowledge, and evidence are separate ([Run 009](./run-009-ars-execution-semantics-derivation.md#L497)) | Later evidence can refine, supersede, contradict, or invalidate current knowledge without erasing historical knowledge |
| `W-09` | Record resource accounting when available | Optional, repeated, or late | Accounting is operation-associated and may be unavailable ([Run 009](./run-009-ars-execution-semantics-derivation.md#L372)) | Distinguish measured zero, unavailable, not-yet-observed, and absent record |
| `W-10` | Record subordinate termination and outcome | Normally once per operation; later evidence may still attach | Child outcome is independent from parent outcome ([Run 009](./run-009-ars-execution-semantics-derivation.md#L289)) | Termination closes execution activity, not all future knowledge about it |
| `W-11` | Record enclosing termination and disposition | Normally once; later facts may still attach | Enclosing lifecycle is one independent domain ([Run 009](./run-009-ars-execution-semantics-derivation.md#L268)) | A terminated Invocation cannot become a frozen aggregate |
| `W-12` | Record acceptance, rejection, or an undecided outcome with supporting reasons | Optional and potentially later than realization | Acceptance is distinct from completion ([Run 009](./run-009-ars-execution-semantics-derivation.md#L408)) | Preserve the decision and its basis without rewriting realization outcome |
| `W-13` | Record durable acknowledgement or coverage information when the mechanism can supply it | At durability boundaries; may lag semantic occurrence | Durable recording is distinct from occurrence ([Run 009](./run-009-ars-execution-semantics-derivation.md#L393)) | Do not claim that locally absent facts did not occur externally |

### Append-oriented does not mean permanently current

The key epistemic workload is:

```text
t1  runtime records: effect completion unknown
t2  evidence E arrives
t3  runtime records: evidence E supports known completed
```

At `t3`, the current answer is `known completed`, not `unknown` and `known
completed` simultaneously. The historical fact that the runtime held or recorded
an `unknown` claim at `t1` remains relevant. A current-state view must apply
domain rules for refinement, supersession, contradiction, or invalidation; it
must not compute current knowledge by treating every historical assertion as
eternally current.

**Representation constraint.** Historical claims and their temporal/evidentiary
relationships must survive, while current knowledge must be a derivation over
them. “Append-oriented” describes preservation of meaningful fact history. It
does not select physical immutability, infinite retention, or a rule that earlier
claims remain currently true.

## Read workload

### Current coordination reads

These questions may be asked while the Invocation is active and after each new
fact:

| ID | Question | Required distinction |
|---|---|---|
| `Q-C01` | Is the Invocation active, normally completed, or abnormally terminated? | Enclosing lifecycle, not aggregate child status |
| `Q-C02` | Which subordinate operations are active now? | Current operation state derived independently per operation |
| `Q-C03` | What has manifested so far, in local order? | Manifestation history plus producer association |
| `Q-C04` | What is current effect-completion knowledge? | Current epistemic view, not a union of historical claims |
| `Q-C05` | Has acceptance been decided, and what is the current decision? | Acceptance separate from realization completion |
| `Q-C06` | What current accounting is available? | Measured values separate from missing or unavailable data |

These questions follow from the independent fact domains in Run 009
([fact-domain derivation](./run-009-ars-execution-semantics-derivation.md#L263)).

**Representation constraint.** Current coordination must be incrementally
maintainable from new authoritative information. Replaying an entire growing
history for every coordination check is not the narrowest adequate response to a
workload that asks the same current questions between writes. No numerical
latency bound follows.

### Policy and decision-support reads

| ID | Question | Required inputs |
|---|---|---|
| `Q-P01` | Which operation was proposed, interpreted, and authorized? | Proposal, authority decision, and policy basis |
| `Q-P02` | Was an effect attempted? | Attempt evidence rather than history inference |
| `Q-P03` | What does the runtime currently know about completion, and why? | Current knowledge plus supporting evidence and prior refinements |
| `Q-P04` | Where did failure occur? | Per-operation outcomes and enclosing disposition |
| `Q-P05` | Are sufficient facts available for retry policy to consider replay? | Failure location, effect knowledge, operation properties, and record coverage |
| `Q-P06` | Why was a result accepted, rejected, or left undecided? | Acceptance fact plus requirement, guarantee, evidence, and policy references |

Run 009 requires these inputs without selecting the policy that consumes them
([authority](./run-009-ars-execution-semantics-derivation.md#L423),
[retry](./run-009-ars-execution-semantics-derivation.md#L445)).

### Recovery and forensic reads

| ID | Question | Required history |
|---|---|---|
| `Q-R01` | What happened in demonstrated local order? | Ordered facts, including facts superseded in current views |
| `Q-R02` | Which operation produced each manifestation, observation, effect, and accounting item? | Stable operation association |
| `Q-R03` | Which subordinate outcomes differ from the enclosing outcome? | Parent/child relationship plus independent outcomes |
| `Q-R04` | How did effect knowledge change, and what evidence changed it? | Epistemic history rather than only the latest value |
| `Q-R05` | Which facts are durably known, and where can coverage be incomplete? | Durable boundaries and explicit uncertainty |
| `Q-R06` | How was the current view derived? | Authoritative inputs, derivation rules, and covered fact prefix |
| `Q-R07` | What may have manifested or occurred beyond recovered knowledge? | Ability to report uncertainty instead of inventing a negative fact |

These reads operationalize Run 009's conclusion that conversational history and
aggregate accounting are incomplete execution projections
([durable coverage](./run-009-ars-execution-semantics-derivation.md#L393),
[countermodel](./run-009-ars-execution-semantics-derivation.md#L211)).

Forensic reads may legitimately inspect the full history. Current coordination
and policy reads require a current interpretation. A viable family must support
both without making either interpretation authoritative by accident.

## Relationship, ordering, and absence constraints

### Linkability without a chosen encoding

The runtime must be able to associate:

```text
Invocation
    -> subordinate operation
        -> manifestations
        -> realization observations
        -> effect attempt and evidence
        -> accounting
        -> outcome
```

It must also retain demonstrated local order between operations and repeated
facts. This is a **representation constraint** derived from Run 009's requirement
for both hierarchy and ordering
([relationship requirement](./run-009-ars-execution-semantics-derivation.md#L458)).
It does not choose identifiers, references, foreign keys, tree nodes, or graph
edges.

### Absence cannot carry multiple meanings

The representation must not use one missing value to mean all of:

- no effect was attempted;
- an effect was attempted but no completion evidence arrived;
- accounting was unavailable;
- accounting is not yet recorded;
- acceptance has not been decided;
- a fact may have occurred externally but is absent after recovery.

Those propositions drive different policy and forensic answers. Run 009 already
distinguishes not-attempted, known-completed, and conservatively unknown effect
knowledge
([effect epistemics](./run-009-ars-execution-semantics-derivation.md#L497)) and
recorded zero from missing accounting
([accounting](./run-009-ars-execution-semantics-derivation.md#L372)).

**Representation constraint.** Meaningful absence and unavailable evidence must
be distinguishable in current views and recoverable from authoritative facts.
No concrete null, option, sum, or status representation is selected.

## Representative workload replays

Every candidate is evaluated at every prefix of four traces. A prefix represents
the facts durably available at a possible observation or recovery point. The
candidate must answer only from that prefix and may return `unknown` or
`undecided`; it may not invent a negative fact.

### `T-ordinary`: ordinary learned realization

```text
O1  Invocation begins
O2  inference begins
O3  final realization observation arrives
O4  inference accounting arrives
O5  inference completes
O6  acceptance is decided for this workload
O7  Invocation completes normally
```

The ordinary path is grounded in the characterized non-streaming behavior, where
the final response and provider usage are interpreted and stored
([ordinary delegation and state](../tests/test_transport_seam.py#L130)). Acceptance
does not exist in the inherited path; `O6` is a Run 009 design workload added to
keep acceptance separate
([acceptance obligation](./run-009-ars-execution-semantics-derivation.md#L408)).

At each prefix, the representation must answer:

- whether the inference and Invocation are active or terminated;
- whether a final realization observation exists;
- whether accounting is present rather than assumed zero;
- whether acceptance is undecided, accepted, or rejected;
- why normal completion is or is not yet established.

The placement of `O6` before `O7` is one representative workload, not a universal
rule that acceptance must precede every enclosing completion.

### `T-stream-failure`: manifestation before failure

```text
S1  Invocation begins
S2  streaming inference begins
S3  manifestation A becomes observable
S4  manifestation B becomes observable
S5  streaming inference fails
S6  Invocation terminates abnormally
```

The inherited tests prove that partial output becomes observable while history
remains unchanged and remains observable even though later iteration fails
([stream failure](../tests/test_streaming_lifecycle_characterization.py#L362),
[async stream failure](../tests/test_streaming_lifecycle_characterization.py#L668)).

At prefixes `S3` and `S4`, the current view must show manifested output while the
operation remains active. At `S5`, it must retain A and B while showing operation
failure. At `S6`, it must preserve the failed child, abnormal enclosing outcome,
missing accounting, and absence of a durable assistant message as distinct facts.

### `T-effect-mixed`: completed effect and failed continuation

```text
E1  Invocation begins
E2  selection inference begins
E3  selection inference completes
E4  selection accounting arrives
E5  operation proposal is interpreted
E6  authority and policy permit this representative attempt
E7  effect attempt begins
E8  controlled completion evidence arrives
E9  continuation inference begins
E10 continuation inference fails
E11 Invocation terminates abnormally
```

The inherited workflow does not represent `E6`; it invokes the selected callable
directly. Run 009 adds the authority/policy distinction as a design invariant
([authority boundary](./run-009-ars-execution-semantics-derivation.md#L550)). The
remaining order is grounded in the Run 008 lifecycle test
([ordered success](../tests/test_tool_effect_lifecycle_characterization.py#L672))
and the effect-then-continuation-failure tests
([sync failure](../tests/test_tool_effect_lifecycle_characterization.py#L855),
[async failure](../tests/test_tool_effect_lifecycle_characterization.py#L1154)).

At `E8`, current knowledge is known-completed for the controlled effect while the
Invocation remains active. At `E10`, that effect knowledge must survive the
continuation failure. At `E11`, policy and forensic reads must not infer that
abnormal enclosing termination erased or reversed the effect.

### `T-late-knowledge`: epistemic refinement after termination

```text
L1  Invocation begins
L2  effect attempt begins
L3  completion is currently unknown
L4  Invocation terminates with completion still unknown
L5  later evidence E arrives
L6  current completion knowledge becomes known-completed
```

Run 008 does not observe remote ambiguity. `L3` through `L6` are a conservative
workload derived from Run 009's effect-knowledge state space
([knowledge distinctions](./run-009-ars-execution-semantics-derivation.md#L513)).

At `L4`, the only sound current answer is that completion remains unknown. At
`L6`, the current answer is known-completed and cites E. Forensic reads must still
show that the runtime held unknown knowledge at `L3` and terminated under that
knowledge at `L4`. Termination therefore closes activity, not the ability to
record later epistemic facts.

## Representation constraint ledger

Each constraint traces to a semantic obligation, concrete workload, and read or
write pressure.

| ID | Representation constraint | Run 009 obligation | Workload and query pressure |
|---|---|---|---|
| `R-01` | Preserve historically meaningful claims rather than overwriting them with current values | Effect knowledge and durable coverage ([Run 009](./run-009-ars-execution-semantics-derivation.md#L332)) | `T-late-knowledge`; `Q-R04` |
| `R-02` | Derive one current interpretation through explicit refinement, supersession, contradiction, or invalidation rules | Current knowledge differs from historical claims ([Run 009](./run-009-ars-execution-semantics-derivation.md#L497)) | `L3` to `L6`; `Q-C04`, `Q-P03` |
| `R-03` | Permit facts to attach after subordinate or enclosing termination | Termination does not establish all later knowledge ([Run 009](./run-009-ars-execution-semantics-derivation.md#L332)) | `T-late-knowledge`; `W-08`, `W-11` |
| `R-04` | Preserve containment and demonstrated local order independently | Parent and child outcomes plus local order ([Run 009](./run-009-ars-execution-semantics-derivation.md#L458)) | All traces; `Q-R01`–`Q-R03` |
| `R-05` | Associate each manifestation, observation, effect, accounting item, and outcome with its producing operation | Independent fact domains ([Run 009](./run-009-ars-execution-semantics-derivation.md#L263)) | `T-stream-failure`, `T-effect-mixed`; `Q-R02` |
| `R-06` | Preserve subordinate and enclosing outcomes independently | Parent-only state is insufficient ([Run 009](./run-009-ars-execution-semantics-derivation.md#L194)) | `E10`–`E11`; `Q-P04`, `Q-R03` |
| `R-07` | Distinguish meaningful absence, unavailable evidence, recorded zero, unknown, and undecided | Accounting, effect knowledge, and acceptance are separate ([Run 009](./run-009-ars-execution-semantics-derivation.md#L263)) | Every trace prefix; `Q-C04`–`Q-C06` |
| `R-08` | Accommodate repeated manifestations without turning the latest manifestation into completion | Manifestation differs from completion ([Run 009](./run-009-ars-execution-semantics-derivation.md#L311)) | `S3`–`S5`; `Q-C03`, `Q-R01` |
| `R-09` | Make current coordination incrementally maintainable without making the current view authoritative | Current facts and forensic history serve different reads ([Run 009](./run-009-ars-execution-semantics-derivation.md#L263)) | Repeated `Q-C*` between writes; all traces |
| `R-10` | Reconstruct current views deterministically from authoritative durable information and report the covered prefix | Durable recording is independent ([Run 009](./run-009-ars-execution-semantics-derivation.md#L393)) | Every recovery prefix; `Q-R05`, `Q-R06` |
| `R-11` | Preserve uncertainty where external occurrence and local durability cannot be atomic | Effect truth, knowledge, and recording are distinct ([Run 009](./run-009-ars-execution-semantics-derivation.md#L497)) | Atomicity windows below; `Q-R05`, `Q-R07` |
| `R-12` | Preserve acceptance and its basis separately from realization and enclosing outcome | Completion does not establish acceptance ([Run 009](./run-009-ars-execution-semantics-derivation.md#L408)) | `O5`–`O7`; `Q-C05`, `Q-P06` |
| `R-13` | Support serialization and evolution without changing the meaning of already recorded claims | Historical claims remain evidence about what was known | All traces and forensic reads |

`R-13` is a **representation constraint** at the family level: a family that
cannot preserve the meaning of old claims across representation evolution is not
recoverable. Concrete version tags, migrations, codecs, and compatibility rules
remain unresolved.

Future concurrency is an evaluation pressure, not a derived concurrency model.
Candidates should not require one scalar mutable status whose update would
silently discard an independent fact, but this run selects no locking, merge, or
distributed-ordering semantics.

## Candidate representation families

### A. One authoritative mutable Invocation aggregate

One serialized aggregate is the authoritative current state. Its values and
collections are updated in place. There is no separately authoritative history of
execution and knowledge facts.

This definition concerns logical authority, not whether the aggregate is stored
as one row, document, or heap object.

### B. Authoritative nested mutable operation tree

The Invocation owns mutable subordinate operation nodes arranged primarily by
containment. Observations, manifestations, effects, accounting, and outcomes live
on or below those nodes. The tree is authoritative; no independent fact history
exists.

### C. Authoritative flat append-only execution facts

Historical facts are authoritative and retain local order and association. There
is no maintained current-state projection. Current questions are answered by
folding or searching authoritative facts when asked.

### D. Authoritative append-oriented facts plus derived current-state views

Historically meaningful execution and knowledge facts are authoritative. Current
views are derived and rebuildable from a known covered fact prefix. New evidence
can append refinements, contradictions, or invalidations; derivation rules select
the current interpretation without deleting the historical claim.

The derived view may eventually be ephemeral, incrementally maintained, or
durably materialized. That is an unresolved choice within the family. If durable,
it is still disposable and non-authoritative.

### E. Authoritative normalized mutable records

Current Invocation, subordinate operation, effect, accounting, and acceptance
values are stored separately with explicit relationships. Those mutable current
records are authoritative. Historical rows, if present only for diagnostics, do
not determine current truth.

## Candidate replay matrix

Verdicts mean:

- **Native:** the family satisfies the workload through its defining authority
  model.
- **Bounded augmentation:** the family needs support that does not change its
  authority model.
- **Becomes D:** satisfying the workload requires authoritative append-oriented
  facts plus a derived current interpretation.
- **Deficient:** the family loses or invents required meaning under its stated
  definition.
- **Insufficient evidence:** the distinction depends on measurements or semantics
  this run does not have.

| Candidate | `T-ordinary` | `T-stream-failure` | `T-effect-mixed` | `T-late-knowledge` | Prefix recovery |
|---|---|---|---|---|---|
| A: mutable aggregate | Native for latest ordinary state | Must retain manifestation history inside the aggregate or lose A/B at failure | Current fields can show mixed outcome, but overwrites obscure how knowledge evolved | Updating unknown to completed erases the historically relevant unknown claim unless history is made authoritative | Snapshot answers latest values but cannot explain superseded knowledge without authoritative history |
| B: mutable tree | Native containment | Can attach manifestations to the stream node; repeated history and order must be added | Native containment of differing child outcomes; cross-child local order needs augmentation | Mutating a terminated effect node erases prior knowledge unless node-level fact history becomes authoritative | Tree snapshot recovers hierarchy but not necessarily epistemic chronology |
| C: append-only facts | Native and lossless | Native: manifestations and failure coexist | Native: operation facts preserve mixed outcomes and order | Native: later evidence appends after termination | Deterministic fold over each durable prefix; current reads require repeated fold/search without a maintained view |
| D: facts plus derived views | Native | Native history plus direct current stream view | Native history plus independent current child/parent views | Native refinement history plus current known-completed view | Authoritative prefix replays; derived view can be rebuilt or checked against its covered prefix |
| E: normalized mutable records | Native for latest ordinary state | Append-like manifestation rows are natural, but current outcome overwrites remain separate | Relations express mixed children; mutable effect state loses prior epistemic claims | Updating the effect row from unknown to completed erases when and why unknown held unless authoritative knowledge facts are added | Recovers latest normalized values; forensic epistemic reconstruction is deficient without authoritative history |

### Prefix falsification

At `S4`, candidates must report two manifestations and an active stream. At `S5`,
they must retain both manifestations and report stream failure. A single mutable
`content` plus `failed` value cannot answer how output manifested. A and B can
retain the manifestations only by maintaining history inside their authoritative
aggregate or tree.

At `E10`, candidates must report a completed controlled effect, failed
continuation, selection accounting, and still-active enclosing attempt. At `E11`,
only the enclosing activity changes. Any representation that derives child effect
state from parent failure is falsified by the Run 008 counterexample
([evidence](../tests/test_tool_effect_lifecycle_characterization.py#L855)).

At `L4`, candidates must answer completion unknown. At `L6`, they must answer
known-completed with evidence E while retaining that unknown was the recorded
knowledge at termination. A, B, and E can do that only by adding authoritative
knowledge-history facts; under the family identity rule, that augmentation moves
their epistemic authority model toward D.

## Read-workload comparison

| Candidate | Current coordination | Policy reads | Recovery / forensic reads | Concrete disadvantage |
|---|---|---|---|---|
| A | Direct latest-value access | Direct if every independent dimension is retained | Weak for superseded claims and causal explanation | Faithful history turns the aggregate into an embedded fact collection; repeated writes may replace the entire serialization depending on storage |
| B | Direct traversal for known nodes | Direct within a node; cross-operation queries need indexes/order support | Good hierarchy, weak cross-cutting chronology and epistemic history | Tree containment is not the demonstrated local order; additional order and history structures are necessary |
| C | Correct but requires fold/search over the authoritative prefix when no view is maintained | Correct from facts but repeats derivation at decision points | Native chronological reconstruction | Current coordination work grows with retained facts; adding an incremental current interpretation is D |
| D | Direct through a derived view whose covered prefix is known | Current knowledge plus supporting facts are both available | Native facts and rebuildable views | Derivation logic, view invalidation, and fact evolution add complexity; a persisted view can lag |
| E | Direct latest-value and indexed relational reads | Direct if current fields cover every policy input | Good relationship queries, weak historical knowledge without authoritative change facts | Adding authoritative evidence/change facts and deriving current values makes it D-like |

### Current-state cost without unsupported scale claims

Candidate C is semantically adequate for all four traces. Its deficiency is the
combined read/write workload: in the family as defined, every current coordination
or policy read must re-derive the relevant current interpretation from retained
facts. The number of manifestation and evidence facts is not source-bounded. An
incrementally maintained fold is a derived current-state view and therefore moves
the design to D, even if that view exists only in memory and is rebuilt at load.

No benchmark is needed to establish that structural difference. A benchmark is
still required to choose view persistence, indexing, partitioning, or storage.

## Candidate-by-candidate falsification

### Candidate A

Candidate A handles a small ordinary execution compactly and can make current
reads direct. It fails `R-01` and `R-02` if effect knowledge is overwritten from
unknown to completed. It fails `R-08` if repeated manifestation is reduced to one
latest content value. Adding authoritative arrays of historical claims and a
separate latest interpretation may still be stored in one document, but logically
creates authoritative facts plus a derived view: D.

**Verdict:** possible only by becoming D for the workloads that matter. The
physical convenience of one container does not rescue the original authority
model.

### Candidate B

Candidate B naturally models containment and independent child outcomes. It does
not natively model cross-child local order, and mutating terminated nodes with
late evidence erases epistemic history. Adding order facts, knowledge-refinement
facts, and current reductions again introduces D's authority model inside the
tree.

**Verdict:** possible only by becoming D. A tree may later be a derived view, but
Run 009 did not establish it as the authoritative representation.

### Candidate C

Candidate C preserves every representative trace and supports deterministic
prefix recovery. It cleanly records that a claim existed without declaring it
eternally current. It can answer all reads by folding facts.

Its concrete disadvantage is current coordination. `Q-C*` and `Q-P*` recur during
execution, while facts grow with manifestations, observations, evidence, and
operations. Maintaining the fold incrementally is the narrowest bounded
augmentation; by definition, that yields D.

**Verdict:** semantically adequate, operationally incomplete for the combined
current and forensic read workload. Bounded augmentation becomes D.

### Candidate D

Candidate D preserves the authoritative chronology needed by `Q-R*`, supports
late facts after termination, and maintains direct current answers for `Q-C*` and
`Q-P*`. Its view can say known-completed at `L6` while the facts still show unknown
at `L3` and the evidence transition at `L5`.

Its costs are real:

- derivation rules must define currentness rather than unioning assertions;
- a view must identify the authoritative prefix it covers;
- persisted views can lag and must be rebuildable;
- fact meaning must evolve compatibly;
- duplicate, contradictory, or invalidating evidence needs future semantics;
- retained fact volume and view maintenance require measurement.

Those are implementation and evolution costs, not violations of the four
workloads.

**Verdict:** native across all four traces and all three read classes. D survives
the falsification set.

### Candidate E

Candidate E makes current relationship queries straightforward and may use
transactions within one persistence engine. Its authoritative mutable values lose
the prior knowledge state in `T-late-knowledge` and cannot explain currentness in
`Q-R04` without an authoritative evidence/change history. Once current values are
derived from that history, the logical family is D regardless of table layout.

**Verdict:** possible only by becoming D for epistemic and forensic fidelity.

## Atomicity and durability workload

No candidate representation makes external observation or effect execution
atomic with local persistence. The family must preserve what the runtime knows
about these gaps rather than imply they cannot occur.

### Manifestation windows

| Order | Possible world / record divergence | Required representation behavior |
|---|---|---|
| Durable local claim first, external emission second | The record may claim an intended or attempted manifestation that the consumer never observed if emission fails | Do not label intent or attempt as externally manifested without evidence appropriate to the delivery mechanism |
| External emission first, durable local claim second | The consumer may observe output that a recovered runtime cannot enumerate after a crash | Recovery must not infer “nothing manifested” merely from local absence; coverage may be uncertain |

Run 007 directly establishes manifestation before durable conversational history,
though it does not exercise a process crash
([commit boundary](../tests/test_streaming_lifecycle_characterization.py#L252)).
Crash durability is a **derived workload**, not an inherited observation.

### Effect windows

```text
authority/policy decision recorded
    -> effect dispatch attempted
    -> effect may complete
    -> process fails before completion evidence is durable
```

After recovery, objective completion may differ from durable runtime knowledge.
The representation must permit `attempted, completion unknown` and later evidence
without rewriting the prior recovered state into a claim it never supported.
Run 008 supplies the completed-effect-plus-later-failure counterexample; remote
ambiguity remains conservative rather than observed
([Run 009 boundary](./run-009-ars-execution-semantics-derivation.md#L497)).

### Authoritative fact and derived-view window

```text
authoritative fact becomes durable
    -> derived view update fails or process stops
```

Candidate D tolerates this only if the view is non-authoritative, identifies the
fact prefix it covers, and can be rebuilt or advanced. Treating both facts and
view as independent authorities would create an unresolved split rather than a
current-state answer.

This does not select a transaction, write-ahead log, queue, or update protocol.

### Acceptance and enclosing-completion window

```text
realization result becomes durable
    -> acceptance remains undecided or not durable
    -> process stops
```

Recovery must not infer acceptance from realization completion. If acceptance is
durable but enclosing completion is not, the runtime must likewise retain those
facts independently. Whether either pair should be recorded atomically is
**unresolved** because the execution and persistence contract has not been chosen.

### Accounting window

Provider usage can be observed alongside a result and lost before local durable
recording. Conversely, a durable accounting observation does not prove later
history or acceptance completed. A viable family attaches accounting to its
producer and reports missing coverage rather than deriving enclosing state from
the aggregate
([Run 009 accounting invariant](./run-009-ars-execution-semantics-derivation.md#L746)).

### Atomicity questions exposed, not answered

The workload leaves open:

- which individual facts must be indivisible;
- whether any fact groups require one local atomic boundary;
- how delivery acknowledgement changes manifestation knowledge;
- how an effect mechanism supplies attempt and completion evidence;
- whether a derived view is ephemeral or durably materialized;
- how duplicate writes or repeated evidence are recognized;
- how retention, correction, and deletion interact with historical fidelity.

No prettier in-memory structure answers those questions or removes the external
failure windows.

## Retry-policy input boundary

Run 010 does not decide retry. It requires the representation family to supply,
without inference from one scalar disposition:

| Future policy input | Authoritative basis in the selected family |
|---|---|
| Failure location | Per-operation outcome facts and enclosing relationship |
| Effect-attempt knowledge | Attempt and operation-association facts |
| Current completion knowledge | Derived view over completion evidence and refinements |
| Supporting evidence | Authoritative historical evidence facts |
| Operation properties | Associated operation facts whose concrete form is unresolved |
| Durable-record coverage | Covered authoritative prefix and explicit uncertainty where known |

Whether those inputs make replay safe, idempotent, compensatable, or permissible
is outside this run
([Run 009 invariant](./run-009-ars-execution-semantics-derivation.md#L799)).

## Representation-family outcome

### Narrowest adequate family

Candidate D—authoritative append-oriented execution facts plus derived,
rebuildable current-state views—is the narrowest family that satisfies all of:

- the four trace workloads at every prefix;
- historical epistemic fidelity;
- one unambiguous current interpretation;
- facts arriving after termination;
- independent enclosing and subordinate outcomes;
- containment and demonstrated local order;
- repeated partial manifestations;
- policy reads with supporting evidence;
- forensic and recovery reconstruction;
- a non-authoritative current view that can tolerate lag.

Candidate C is the semantic core of D and remains a useful lower bound: facts
alone preserve meaning. The required current coordination workload earns the
derived view. A, B, and E become D logically when augmented enough to preserve
the same historical claims and derive their current interpretations.

This conclusion selects a logical representation family only. It does not select:

- one physical append log;
- event sourcing;
- a fact payload or schema;
- in-memory versus durable views;
- a relational, document, graph, or log database;
- indexing, transactions, partitions, or caches;
- an API or object model.

### Constraints on any future realization of D

Without prescribing a representation, the family verdict requires that any
future realization demonstrate:

1. authoritative historical facts retain the meaning they had when recorded;
2. later facts can refine or invalidate current interpretation without erasing
   that history;
3. current views are derived, non-authoritative, and tied to a known covered
   prefix;
4. views are rebuildable from authoritative durable information;
5. absence and uncertainty are not silently converted into negative facts;
6. containment, producer association, and local order survive serialization;
7. late knowledge can attach after operation and Invocation termination;
8. external manifestation/effect durability gaps remain representable as
   uncertainty;
9. acceptance and accounting remain independent from lifecycle disposition.

These are falsification criteria for a future concrete representation, not a
construction plan.

## Unresolved physical questions

The family comparison does not answer:

- manifestation and fact volume;
- read/write frequency or latency targets;
- how facts obtain stable identity and local order;
- whether facts are physically immutable;
- retention, compaction, deletion, and privacy requirements;
- contradiction and evidence-precedence semantics;
- concrete current-view derivation rules;
- view persistence, checkpoints, and rebuild costs;
- duplicate-write and idempotency behavior;
- transaction boundaries;
- concurrency, nesting, or distributed ordering;
- serialization and representation-version migration;
- effect evidence and reconciliation protocols;
- any retry, compensation, or replay algorithm;
- a storage engine, package layout, public API, or Python type;
- DSPy, txtai, or Textual integration.

Those questions determine a concrete substrate. They do not reopen the logical
family result unless evidence shows that D cannot satisfy one of the workloads.

## Synthesis and stop

Run 009 established that execution state is multidimensional. The workload in
this run adds a physical consequence: several facts accumulate over time, some
arrive after termination, and current interpretation changes without making the
runtime's earlier knowledge disappear from history.

```text
authoritative historical facts
        +
derived current interpretation
```

is therefore not an aesthetic event-model preference. It is the narrowest family
that simultaneously supports current coordination, policy evidence, recovery,
and forensic reconstruction across ordinary execution, streaming failure,
effectful mixed outcome, and late knowledge.

The result is a representation-family constraint, not an implementation design.
No concrete substrate is introduced here. This is the stopping point for Run 010.
