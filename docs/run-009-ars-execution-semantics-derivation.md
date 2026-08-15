# Run 009: Ars execution semantics derivation

## Purpose and stopping rule

Runs 001 through 008 established what the inherited runtime does, where its
ordinary model-call boundaries lie, what DSPy 3.3.0 already owns, and how
streaming and callable workflows behave when work becomes externally observable
or effectful. This run asks a different question:

> What facts must an Ars runtime be capable of representing without discarding
> distinctions demonstrated by those executions?

The derivation rule is:

```text
observed execution
    |
    v
invalidated simplification
    |
    v
independent fact Ars must preserve
    |
    v
representation deliberately undecided
```

This document derives semantic obligations. It is not an architecture decision
record and does not choose classes, enums, protocols, schemas, event formats,
storage layouts, package boundaries, or integration APIs. It does not authorize
an implementation or migration.

The stopping point is:

```text
observations
    |
    v
countermodels falsified
    |
    v
independent facts derived
    |
    v
invariants established
    |
    v
candidate vocabulary evaluated
    |
    v
STOP
```

## Evidence baseline and claim discipline

### Exact Run 008 baseline

Run 008 was initially verified as one uncommitted artifact over Run 007. Before
Run 009 began, that composite state was committed without changing the artifact.
The atomic Run 009 baseline is therefore:

```text
HEAD
28cf161bb88b42fbe594682ca0e31a7f22f69dc7

Run 008 artifact
tests/test_tool_effect_lifecycle_characterization.py

Run 008 artifact SHA-256
0AE4AD1E46618C019B7655F56F53DA4C1C4DDF73A2D47D9311D262F0B368C5ED
```

The test artifacts frozen at the start of this run are:

| Artifact | SHA-256 |
|---|---|
| `tests/test_message_seams.py` | `7BBF9F24E3EB6277EAED88C4EB0FEE0D5ACCDC080EBB3A116CD64E6CABB8D6A1` |
| `tests/test_models_characterization.py` | `605CF0EA043B9944D2284346457D4AC46D5BECF9C206CC5F97E7CFBD4623046C` |
| `tests/test_provider_lowering_characterization.py` | `37F5D5AF36321A430EF5283F16021A4F08ED5B62089630434A6D96F2F17B7B62` |
| `tests/test_request_assembly_seam.py` | `B44F4D841825B13E23A276A1F663B5AED67A8008A590459BF97EEEE60DE64AD7` |
| `tests/test_streaming_lifecycle_characterization.py` | `519DCE501607BB686FA49D7D5275B94AD8634A2D7E0F4F4EC34F3701B26CA922` |
| `tests/test_tool_effect_lifecycle_characterization.py` | `0AE4AD1E46618C019B7655F56F53DA4C1C4DDF73A2D47D9311D262F0B368C5ED` |
| `tests/test_transport_seam.py` | `2CBC1C0B0155E2196D667492B1BD668844C1056CD664274E96D314984C4E508C` |

All other pre-existing files are frozen by their tracked contents at that HEAD.

### Claim labels

The document uses four labels strictly:

- **Observed** means the inherited source or a deterministic characterization
  test directly demonstrates the fact.
- **Derived requirement** means the runtime must retain the fact to avoid losing
  information exposed by observations. It does not select a representation.
- **Design invariant** means the requirement also follows from an already stated
  Ars principle. It is normative for Ars, not a description of inherited
  enforcement.
- **Unresolved** means the question is relevant but the current evidence does not
  establish an answer.

An absence in the inherited implementation is not automatically evidence for a
negative value. In particular, the inherited runtime does not represent
acceptance or authorization. The corresponding cells in this document therefore
say **not represented**, not `false`.

### Evidence scope

The SimpleAIChat evidence is local source and the frozen characterization suite.
The DSPy evidence is exclusively the version-pinned Run 006 comparison. Run 009
does not update or extend DSPy research. Run 006 itself distinguishes DSPy's
current/default, compatibility, experimental, and planned behavior
([maturity labels](./run-006-dspy-responsibility-comparison.md#L61)).

## Counterexample execution matrix

The table describes inherited executions. “Durable history” means the session's
stored conversational history, not every form of durable state. Accounting is
shown separately precisely because the inherited runtime can retain usage while
omitting the operations that caused it.

| Observed execution | Enclosing disposition | Manifested output | Subordinate operations | Callable effect | Accounting | Durable history | Acceptance / authorization |
|---|---|---|---|---|---|---|---|
| Ordinary non-streaming success | Normal completion | One final return | One inference completes | None | Provider usage added | User and assistant stored when enabled | Not represented |
| Stream suspended after its last content yield | Still active and suspended | Consumer has the accumulated output | Streaming inference has not reached iterator exhaustion | None | Not recorded by this path | Unchanged | Not represented |
| Stream raises after yielding content | Abnormal termination | Partial output was already observed | Streaming inference fails during iteration | None | Not recorded by this path | Unchanged | Not represented |
| Stream is explicitly closed after yielding content | Consumer termination | Partial output was already observed | Generator receives termination and response context exits | None | Not recorded by this path | Unchanged | Not represented |
| Selected-callable workflow succeeds | Normal completion | One final return after the second inference | Selection inference, callable, and continuation inference complete | Controlled callable completes | Both inference usages added | Only original user and final assistant are stored | Not represented |
| Callable raises | Abnormal termination | No final workflow result | Selection completes; callable raises; continuation is absent | Attempt observed; general external completion cannot be inferred from the raise | Selection usage added | Unchanged | Not represented |
| Callable completes; continuation inference fails | Abnormal termination | Callable result exists locally; no final workflow result | Selection and callable complete; continuation fails | Controlled effect is known completed | Selection usage only | Unchanged | Not represented |
| Synchronous callable used by async orchestration | Abnormal termination at `await` | Callable result exists locally; no final workflow result | Selection completes; callable body returns; awaiting its non-awaitable result fails | Controlled effect is known completed | Selection usage added | Unchanged | Not represented |
| Selection output is `0` | Normal completion | One final ordinary result | Selection and ordinary inference complete; no callable operation | Not attempted | Both inference usages added | Ordinary `gen`/`gen_async` messages and metadata are stored | Not represented |

Ordinary generation constructs and may store its assistant message, then updates
session totals from provider usage
([sync implementation](../simpleaichat/chatgpt.py#L95),
[delegation/state test](../tests/test_transport_seam.py#L130)). Streaming instead
constructs and stores its final assistant message only after the response iterator
and context manager finish
([sync implementation](../simpleaichat/chatgpt.py#L135),
[post-yield commit test](../tests/test_streaming_lifecycle_characterization.py#L252)).

The streaming tests separately demonstrate partial manifestation followed by an
exception, suspension, explicit close, and async close without history mutation
([sync failure](../tests/test_streaming_lifecycle_characterization.py#L362),
[sync suspension/close](../tests/test_streaming_lifecycle_characterization.py#L393),
[async failure](../tests/test_streaming_lifecycle_characterization.py#L668),
[async suspension/close](../tests/test_streaming_lifecycle_characterization.py#L700)).

The selected-callable success test records the actual sequence as first internal
message handling, first accounting, callable execution, second internal message
handling, second accounting, then final history storage
([ordered lifecycle](../tests/test_tool_effect_lifecycle_characterization.py#L672)).
The failure tests retain pre-existing history while proving that the callable ran
before the second dispatch failed
([sync continuation failure](../tests/test_tool_effect_lifecycle_characterization.py#L855),
[async continuation failure](../tests/test_tool_effect_lifecycle_characterization.py#L1154)).
The async-specific test proves that an ordinary callable runs synchronously and
returns before `await` rejects the non-awaitable value
([sync callable in async orchestration](../tests/test_tool_effect_lifecycle_characterization.py#L1118)).
The `0` branch has different storage semantics because its second call is ordinary
generation rather than the manually recorded selected-callable path
([sync zero branch](../tests/test_tool_effect_lifecycle_characterization.py#L986),
[async zero branch](../tests/test_tool_effect_lifecycle_characterization.py#L1214)).

## Countermodels falsified by the observations

### One scalar disposition

**Observed.** The following two enclosing executions both terminate abnormally:

```text
stream yields partial content
    -> stream fails
    -> no durable assistant message

callable completes an effect
    -> continuation inference fails
    -> no durable workflow messages
```

The first has manifested output but no callable effect. The second has a completed
controlled effect and selection accounting but no final manifested response. The
tests distinguish those facts despite the same coarse enclosing disposition
([stream failure](../tests/test_streaming_lifecycle_characterization.py#L362),
[effect then inference failure](../tests/test_tool_effect_lifecycle_characterization.py#L855)).

**Invalidated simplification.** A value such as `FAILED` cannot preserve what
manifested, which subordinate operation failed, whether an effect occurred, what
usage was measured, or what entered history.

**Derived requirement.** Enclosing disposition must remain only one fact among
independently representable execution facts.

### Parent-only state

**Observed.** A selected-callable workflow can contain a completed selection
inference, a completed callable effect, and a failed continuation inference while
the enclosing workflow terminates with failure
([sync evidence](../tests/test_tool_effect_lifecycle_characterization.py#L855),
[async evidence](../tests/test_tool_effect_lifecycle_characterization.py#L1154)).

**Invalidated simplification.** The enclosing result cannot substitute for the
outcomes of its subordinate operations. Copying `failed` from the parent to every
child would falsely erase completed work; copying `completed` from a child to the
parent would falsely report the workflow as complete.

**Derived requirement.** The runtime must preserve the relationship between an
enclosing execution attempt and subordinate operations while allowing their
outcomes to differ.

### History as execution truth

**Observed.** Streaming can manifest output without adding history. Internal tool
selection and continuation calls can add accounting without storing their
messages. A callable can complete before a failure leaves history unchanged
([stream failure](../tests/test_streaming_lifecycle_characterization.py#L362),
[selected success ordering](../tests/test_tool_effect_lifecycle_characterization.py#L672),
[async await failure](../tests/test_tool_effect_lifecycle_characterization.py#L1118)).

**Invalidated simplifications.** “History contains a result” does not enumerate
everything that executed. “History lacks a result” does not establish that no
output manifested, no accounting changed, or no effect occurred.

**Derived requirement.** Durable conversational history is one projection of an
execution, not the execution's complete semantic record.

### Accounting as execution truth

**Observed.** Session totals can include two unsaved internal model calls while
history contains only the original/final pair. They can also include only the
selection inference after a callable completed and the continuation failed
([successful ordering](../tests/test_tool_effect_lifecycle_characterization.py#L672),
[continuation failure](../tests/test_tool_effect_lifecycle_characterization.py#L855)).
Streaming can manifest and complete without updating these totals at all
([stream completion metadata](../tests/test_streaming_lifecycle_characterization.py#L252)).

**Invalidated simplifications.** Increased usage does not establish enclosing
completion or history completeness. Zero recorded usage does not establish that
no learned computation ran or no output manifested.

**Derived requirement.** Resource observations need operation association and an
explicitly representable absence or incompleteness; aggregate totals cannot stand
in for an execution trace.

### Successful production as acceptance

**Observed.** The inherited runtime returns successfully parsed provider content
or schema arguments but has no separate acceptance decision. Run 006 finds that
DSPy can enforce declared output presence and type/domain parsing while not
establishing semantic correctness, requirement satisfaction, authority, or
failure policy
([structured-output distinction](./run-006-dspy-responsibility-comparison.md#L372),
[information-loss ledger](./run-006-dspy-responsibility-comparison.md#L421)).

**Invalidated simplification.** A completed or typed realization cannot by itself
state that Ars accepted the result for a particular intended use.

**Design invariant.** Acceptance must remain a distinct post-realization fact,
consistent with the existing separation of type, guarantee, evidence,
requirement, and policy
([project principle](../README.md#L69)).

## Independently required fact domains

The following headings name fact domains, not proposed types or storage objects.
No one-to-one code mapping follows from this list.

### 1. Enclosing execution lifecycle

**Observed.** Generator construction, iteration start, manifestation, response
completion, final message construction, history mutation, and exhaustion are
separate moments. A generator can remain live and suspended after its last
content yield
([sync lifecycle](../tests/test_streaming_lifecycle_characterization.py#L252),
[async lifecycle](../tests/test_streaming_lifecycle_characterization.py#L571)).

**Derived requirement.** At the enclosing-attempt scope, Ars must be able to
retain at least:

- whether the attempt began;
- whether it remains active or has terminated;
- whether it reached its operation-defined normal completion boundary;
- how termination occurred when it did not;
- the distinction between a completed result and later acceptance.

These are facts to preserve, not a state-machine enum. The evidence does not
establish all legal combinations or transition rules.

### 2. Subordinate operations

**Observed.** The tool path performs a selection inference, callable invocation,
and possible continuation inference in a fixed sequential order
([sync source](../simpleaichat/chatgpt.py#L176),
[async source](../simpleaichat/chatgpt.py#L325)). Their outcomes and accounting
can diverge within one enclosing attempt
([ordered lifecycle](../tests/test_tool_effect_lifecycle_characterization.py#L672)).

**Derived requirement.** Ars must retain enough relationship information to
answer:

- which enclosing attempt an operation belongs to;
- what kind of operation ran;
- which operation preceded or caused the next observed operation;
- what outcome and observations belong to that operation;
- whether the enclosing attempt and operation outcomes differ.

A hierarchy alone would lose execution order. A flat ordered list alone could
lose containment and causality. The evidence requires preserving both
relationships; it does not choose a tree, trace, graph, or event model.

### 3. Manifestations

**Observed.** Each stream yield exposes `{delta, response}` to the consumer before
the generator's post-loop finalization and history mutation
([yield shape and accumulation](../tests/test_streaming_lifecycle_characterization.py#L212),
[commit boundary](../tests/test_streaming_lifecycle_characterization.py#L252)).
Early close or failure does not retract what the consumer already received
([failure](../tests/test_streaming_lifecycle_characterization.py#L362),
[close](../tests/test_streaming_lifecycle_characterization.py#L393)).

**Derived requirement.** Ars must be able to retain, when relevant:

- what output became externally observable;
- when it became observable relative to operation completion;
- which subordinate operation produced it;
- whether it was partial, cumulative, or final-looking;
- whether it later entered durable execution history.

Manifestation records exposure. It does not assert normal completion,
acceptance, correctness, or durability.

### 4. Effect attempt, completion, and knowledge

**Observed.** A controlled callable effect can complete before the continuation
inference fails, leaving no workflow history. In async orchestration, a
synchronous callable can complete its body before `await` raises
([sync continuation failure](../tests/test_tool_effect_lifecycle_characterization.py#L855),
[async await failure](../tests/test_tool_effect_lifecycle_characterization.py#L1118)).
Selection `0` proves a path in which no callable is attempted
([zero branch](../tests/test_tool_effect_lifecycle_characterization.py#L986)).

**Derived requirement.** Ars must keep separate:

- whether an effect was authorized;
- whether an attempt occurred;
- whether the effect objectively completed;
- what the runtime knows about completion;
- what evidence supports that knowledge;
- what result or error was observed;
- whether that knowledge entered a durable execution record.

The controlled tests allow the test harness to know that their local effect
marker was written. They do not prove that a general callable return establishes
completion of every external action the callable may have initiated.

### 5. Realization observations

**Observed.** The ordinary path returns decoded provider data unchanged across
the transport seam before downstream interpretation
([sync transport](../tests/test_transport_seam.py#L95),
[async transport](../tests/test_transport_seam.py#L187)). Run 006 identifies DSPy
predictions, typed response data, provider metadata, and errors as realization
observations rather than Ars semantic state
([response interpretation](./run-006-dspy-responsibility-comparison.md#L355),
[surviving boundary](./run-006-dspy-responsibility-comparison.md#L551)).

**Derived requirement.** Values, typed parses, provider metadata, streamed
output, and failures must be attributable to the realization operation that
produced them. Their existence must not silently imply acceptance, guarantee
satisfaction, authority, or effect completion.

### 6. Accounting observations

**Observed.** `gen()` and `gen_async()` update cumulative usage independently of
message storage, including internal calls made with `save_messages=False`
([field ownership evidence](./run-002-model-ownership-excavation.md#L129),
[selected workflow ordering](../tests/test_tool_effect_lifecycle_characterization.py#L672)).
Streaming omits both session and per-message token accounting
([stream metadata test](../tests/test_streaming_lifecycle_characterization.py#L252)).

**Derived requirement.** Ars must be able to associate available resource
observations with the operation that produced them and distinguish:

- a recorded zero;
- an unavailable measurement;
- an operation for which no accounting record was produced;
- aggregate accounting whose contributing operations are not in conversational
  history.

Accounting is itself recorded information. It is not evidence that the broader
execution record is complete.

### 7. Durable recording and coverage

**Observed.** The inherited `messages` list records selected user/assistant pairs,
not all inference inputs, partial manifestations, callable identities, callable
results, or failures. The selected-callable success path manually stores only the
original prompt and final response
([source](../simpleaichat/chatgpt.py#L237),
[test](../tests/test_tool_effect_lifecycle_characterization.py#L672)).

**Derived requirement.** Ars must distinguish the existence of execution facts
from their durable recording and retain enough coverage information to avoid
treating a partial projection as a complete history. “Recorded” must always be
understood relative to what was recorded and where; conversational history,
resource accounting, and a future execution record are not interchangeable.

### 8. Acceptance

**Observed.** Acceptance is not represented by the inherited runtime. Successful
response decoding, Pydantic parsing, or DSPy adapter parsing therefore cannot be
read as an inherited acceptance decision. Run 006 explicitly separates
successful typed shape enforcement from semantic correctness and application
requirements
([structured output](./run-006-dspy-responsibility-comparison.md#L372),
[synthesis](./run-006-dspy-responsibility-comparison.md#L623)).

**Design invariant.** Ars must be able to express whether an observation was
accepted for its intended use and what evidence, requirement, guarantee, or
policy supported that decision. Completion and acceptance may correlate in a
simple path, but one cannot substitute for the other.

### 9. Authority and policy

**Observed.** The inherited path converts model text with `int()`, indexes the
caller-supplied callable list, and invokes the selected callable with the original
prompt. Direct session methods also bypass the public facade's docstring and count
guards
([sync source](../simpleaichat/chatgpt.py#L192),
[selection fossils](../tests/test_tool_effect_lifecycle_characterization.py#L458),
[guard bypass](../tests/test_tool_effect_lifecycle_characterization.py#L496)).
This describes the inherited mechanism; it does not demonstrate authorization.

**Design invariant.** Model-produced data may propose or select an operation, but
cannot manufacture permission to execute it. This follows from the established
principle that model context does not create authority
([principle](../README.md#L59)) and Run 006's finding that DSPy argument parsing is
not authorization
([authority ledger](./run-006-dspy-responsibility-comparison.md#L432)).

Ars must be capable of preserving distinct facts for proposal interpretation,
authority or capability resolution, policy evaluation, and the resulting effect
attempt. No mechanism for those facts is selected here.

### 10. Retry eligibility

**Observed.** Failure can follow a known-completed controlled effect. The
inherited workflow exposes no retry policy and records no durable workflow fact
that would make automatic replay safe
([sync evidence](../tests/test_tool_effect_lifecycle_characterization.py#L855),
[async evidence](../tests/test_tool_effect_lifecycle_characterization.py#L1154)).

**Design invariant.** Enclosing failure alone cannot establish retry eligibility.
A future policy must be able to consider at least failure location, effect-attempt
knowledge, completion knowledge, and relevant operation properties. This does not
choose a retry algorithm, idempotency contract, or compensation mechanism.

## Relationship and ordering requirements

The observed selected-callable path establishes both containment and local order:

```text
enclosing execution attempt
    |
    +-- selection inference
    |
    +-- callable operation
    |
    `-- continuation inference

local causal order
selection inference -> callable operation -> continuation inference
```

**Observed.** The ordered lifecycle test inspects cumulative accounting at the
callable boundary and again before final history storage, proving that these are
not merely an unordered set of operations
([ordered evidence](../tests/test_tool_effect_lifecycle_characterization.py#L672)).

**Derived requirement.** The runtime must preserve enough identity and
relationship information to attach manifestations, effect knowledge, accounting,
errors, and durable records to their producing operation and enclosing attempt.
It must also preserve the demonstrated before/after relationships.

**Unresolved.** The evidence is sequential. It does not establish:

- a global total order;
- ordering across concurrent attempts;
- a causal directed acyclic graph;
- distributed clock semantics;
- parent/child rules for arbitrary nesting;
- event replay or event-sourcing requirements.

Those questions cannot be answered by turning the sequential diagram directly
into a data structure.

## Effect epistemics

The effect problem contains three propositions that must not collapse:

```text
the effect occurred

the runtime knows the effect occurred

the runtime durably recorded that knowledge
```

The first is about the world. The second is epistemic: it is a runtime claim
supported by evidence. The third is about retention. An external observer or test
harness may know more than the inherited session records.

### Minimum knowledge distinctions

| Knowledge distinction | Status in current evidence | Meaning |
|---|---|---|
| Not attempted | **Observed** | Selection `0` and selection conversion/index failures do not invoke a callable ([zero branch](../tests/test_tool_effect_lifecycle_characterization.py#L986), [invalid selection](../tests/test_tool_effect_lifecycle_characterization.py#L949)). |
| Attempted, known completed | **Observed for controlled local effects** | The test effect marker is written before continuation or await failure ([continuation failure](../tests/test_tool_effect_lifecycle_characterization.py#L855), [await failure](../tests/test_tool_effect_lifecycle_characterization.py#L1118)). |
| Attempted, known not completed | **Derived requirement** | Some mechanisms may supply evidence that an attempted effect did not cross their completion boundary. No general inherited callable test establishes this state. |
| Attempted, completion unknown | **Derived requirement** | A safe runtime must not convert missing completion evidence into either completion or non-completion. Remote ambiguity is not an observed SimpleAIChat behavior in these runs. |

The state space is intentionally phrased as runtime knowledge rather than an
omniscient effect truth. Evidence quality and the mechanism that can justify a
knowledge claim remain unresolved.

### Retry consequence

The semantic ordering must be:

```text
failure observed
    |
    v
effect-attempt and completion knowledge inspected
    |
    v
policy determines whether retry is eligible
```

It cannot safely be reduced to:

```text
failure observed -> retry automatically
```

This is a design invariant derived from the completed-effect-plus-failure
counterexample. It is not a claim that the inherited implementation already has
effect-aware retry behavior.

## Proposal, visibility, authority, and effect execution

The inherited callable mechanism is:

```text
model text
    |
    v
int conversion
    |
    v
Python list indexing
    |
    v
callable execution
```

The tests preserve whitespace acceptance, Python negative indexing, and direct
session bypass of facade checks
([selection contract](../tests/test_tool_effect_lifecycle_characterization.py#L458),
[sync bypass](../tests/test_tool_effect_lifecycle_characterization.py#L496),
[async bypass](../tests/test_tool_effect_lifecycle_characterization.py#L638)).
Those are observations to replace later, not authority semantics to inherit.

The Ars semantic boundary must instead distinguish:

```text
learned operation proposal
    |
    v
proposal interpretation
    |
    v
runtime authority or capability resolution
    |
    v
policy evaluation
    |
    v
effect attempt
    |
    v
effect observation and completion knowledge
```

This is a **design invariant**, not a chosen implementation pipeline. In
particular:

- visibility permits data to influence a learned computation;
- parsing may establish a structural interpretation of generated data;
- availability means a runtime knows an operation exists;
- selection identifies a proposed operation;
- authorization permits an operation under runtime authority;
- execution attempts the operation.

None of the first four propositions entails authorization. Tool output becoming
model-visible in a continuation also does not grant that output runtime privilege.
Run 006 reaches the same boundary for ordinary model calls: visibility filtering
belongs before learned realization, while authority meaning is neither preserved
nor enforced by prompt or metadata carriage
([visibility ledger](./run-006-dspy-responsibility-comparison.md#L433),
[dependency boundary](./run-006-dspy-responsibility-comparison.md#L551)).

## DSPy inside the larger execution semantics

Run 006's narrowest defensible boundary remains the evidence basis:

```text
Ars-owned semantic state and policy
    |
    v
deliberate model-visible projection
    |
    v
DSPy learned realization
    |
    v
prediction, provider observations, or error
    |
    v
Ars-owned acceptance, guarantee evaluation, and policy
```

Run 006 supports that split for the ordinary non-streaming model-call stack and
keeps DSPy's typed request, response, message, and metadata carriers out of the
Ars domain model
([dependency boundary](./run-006-dspy-responsibility-comparison.md#L551),
[synthesis](./run-006-dspy-responsibility-comparison.md#L623)). It also states that
the streaming and authority-bearing tool paths were evidence gaps
([unresolved gaps](./run-006-dspy-responsibility-comparison.md#L599)). Runs 007 and
008 establish the Ars semantic obligations at those boundaries; they do not prove
which DSPy APIs implement them.

For an effectful continuation, the required semantic placement is:

```text
Ars deliberate projection
    |
    v
learned realization
    |
    v
operation proposal
    |
    v
Ars authority and policy gate
    |
    v
effect attempt and observation
    |
    v
Ars deliberate continuation projection
    |
    v
learned continuation
    |
    v
Ars acceptance and policy
```

Authority-bearing effects therefore cannot become invisible internal details of
the learned-realization mechanism. DSPy may eventually participate in describing,
parsing, or formatting a proposal, but successful parsing cannot grant authority.

**Unresolved.** This document does not establish DSPy streaming support, tool
callbacks, program composition, or an interception API. It selects no adapter,
hook, or tool mechanism.

## Ten execution invariants

### 1. Observable output does not establish completion

- **Label:** Derived requirement, directly supported by observation.
- **Evidence:** A consumer can receive the last content yield while the generator
  remains suspended before context exit, final message construction, and history
  mutation
  ([sync](../tests/test_streaming_lifecycle_characterization.py#L252),
  [async](../tests/test_streaming_lifecycle_characterization.py#L571)).
- **Invalidated conflation:** `output observed == execution completed`.
- **Fact retained:** Manifestation and completion must be independently knowable.
- **Scope:** The tests establish sequential generator behavior, not every future
  output-delivery protocol.

### 2. Completion does not establish acceptance

- **Label:** Design invariant.
- **Evidence:** The inherited runtime has no separate acceptance decision, while
  Run 006 shows that successfully typed output can still lack semantic correctness
  or requirement satisfaction
  ([structured output](./run-006-dspy-responsibility-comparison.md#L372),
  [project distinctions](../README.md#L69)).
- **Invalidated conflation:** `realization completed == result accepted for use`.
- **Fact retained:** Ars acceptance and its supporting requirement, evidence,
  guarantee, and policy must be separately expressible.
- **Scope:** No acceptance mechanism or policy language is chosen.

### 3. Typed parsing does not establish semantic correctness

- **Label:** Design invariant backed by pinned DSPy evidence.
- **Evidence:** DSPy enforces declared field presence and type/domain parsing on a
  successful adapter result but does not prove the value is semantically correct
  or satisfies an application requirement
  ([structured-output analysis](./run-006-dspy-responsibility-comparison.md#L372),
  [information-loss ledger](./run-006-dspy-responsibility-comparison.md#L421)).
- **Invalidated conflation:** `value has declared type == value is correct`.
- **Fact retained:** Structural validity and semantic evaluation remain distinct.
- **Scope:** Typed parsing is still a useful enforcement mechanism for the shape it
  actually checks.

### 4. Failure does not establish absence of effects

- **Label:** Derived requirement, directly supported by observation.
- **Evidence:** A controlled callable writes its effect marker before the
  continuation dispatch fails; a synchronous callable does likewise before async
  `await` raises
  ([continuation failure](../tests/test_tool_effect_lifecycle_characterization.py#L855),
  [await failure](../tests/test_tool_effect_lifecycle_characterization.py#L1118)).
- **Invalidated conflation:** `enclosing failure == nothing effectful happened`.
- **Fact retained:** Effect attempt and completion knowledge survive enclosing
  failure.
- **Scope:** General external completion still depends on evidence supplied by the
  effect mechanism.

### 5. Effect completion does not establish enclosing completion

- **Label:** Derived requirement, directly supported by observation.
- **Evidence:** Both sync and async workflows contain a completed controlled effect
  followed by a failed continuation and unchanged history
  ([sync](../tests/test_tool_effect_lifecycle_characterization.py#L855),
  [async](../tests/test_tool_effect_lifecycle_characterization.py#L1154)).
- **Invalidated conflation:** `subordinate effect completed == enclosing attempt
  completed`.
- **Fact retained:** Subordinate and enclosing outcomes remain independently
  representable.
- **Scope:** Completion criteria for future operation kinds remain unresolved.

### 6. Accounting records do not establish execution-record completeness

- **Label:** Derived requirement, directly supported by observation.
- **Evidence:** Internal inference usage is accumulated while the corresponding
  prompts and responses are omitted from final history; streaming can manifest
  without accounting
  ([tool ordering](../tests/test_tool_effect_lifecycle_characterization.py#L672),
  [stream metadata](../tests/test_streaming_lifecycle_characterization.py#L252)).
- **Invalidated conflation:** `usage present == workflow fully recorded` and `usage
  absent == no learned work occurred`.
- **Fact retained:** Accounting association, availability, and execution-record
  coverage remain distinct.
- **Scope:** No accounting ledger or cost model is selected.

### 7. Model output does not grant runtime authority

- **Label:** Design invariant, motivated by an inherited counterexample.
- **Evidence:** The inherited path uses parsed model output immediately to select
  and execute a Python callable
  ([source](../simpleaichat/chatgpt.py#L192),
  [selection characterization](../tests/test_tool_effect_lifecycle_characterization.py#L458)).
  The project already states that model context does not create authority
  ([principle](../README.md#L59)).
- **Invalidated conflation:** `model selected operation == runtime authorized
  operation`.
- **Fact retained:** Proposal, authority resolution, policy decision, and effect
  attempt are separate.
- **Scope:** The authority or capability representation is unresolved.

### 8. Context visibility does not grant runtime authority

- **Label:** Design invariant.
- **Evidence:** Run 006 finds that DSPy can render selected context while neither
  preserving nor enforcing application authority meaning
  ([authority and visibility](./run-006-dspy-responsibility-comparison.md#L432)).
  The project principle explicitly separates provenance from privilege
  ([principle](../README.md#L59)).
- **Invalidated conflation:** `data visible to model == data grants permission`.
- **Fact retained:** Visibility policy and runtime authority remain separate even
  when their data travels through the same learned realization.
- **Scope:** No visibility lattice or taint mechanism is chosen.

### 9. Enclosing disposition cannot substitute for subordinate outcomes

- **Label:** Derived requirement, directly supported by observation.
- **Evidence:** Selection inference and callable completion coexist with
  continuation failure in one enclosing attempt
  ([sync](../tests/test_tool_effect_lifecycle_characterization.py#L855),
  [async](../tests/test_tool_effect_lifecycle_characterization.py#L1154)).
- **Invalidated conflation:** `parent disposition == every child disposition`.
- **Fact retained:** Containment, order, and per-operation outcome must survive.
- **Scope:** Arbitrary nesting and concurrent child operations remain unresolved.

### 10. Retry policy depends on effect knowledge, not failure alone

- **Label:** Design invariant derived from observed failure after effect
  completion.
- **Evidence:** The continuation-failure tests leave a completed controlled effect
  outside durable session history
  ([sync](../tests/test_tool_effect_lifecycle_characterization.py#L855),
  [async](../tests/test_tool_effect_lifecycle_characterization.py#L1154)).
- **Invalidated conflation:** `failed == safe to repeat`.
- **Fact retained:** Retry eligibility must be able to consult effect-attempt and
  completion knowledge plus policy-relevant operation properties.
- **Scope:** No retry, idempotency, deduplication, or compensation behavior has
  been characterized or selected.

## Candidate vocabulary evaluation

No candidate term was used to derive the fact domains above. The terms are tested
only now against the responsibilities already established.

### Evaluation criteria

A term earns or approaches a stable meaning only if it:

1. names an independently required semantic responsibility;
2. survives ordinary, streaming, and effectful execution;
3. remains independent of provider and DSPy implementation machinery;
4. does not conflate declaration, attempt, realization, enforcement, and result;
5. implies mechanical enforcement only when a mechanism can actually enforce it.

The verdicts mean:

- **Earned:** the semantic referent is required by the evidence across the
  examined lifecycles; representation remains undecided.
- **Provisional:** the referent is justified, but important scope or lifecycle
  evidence is missing.
- **Deferred:** the evidence does not yet justify assigning the proposed permanent
  meaning.
- **Rejected:** the proposed meaning conflicts with derived distinctions.

### Verdicts

| Candidate | Proposed semantic referent | Evidence test | Verdict |
|---|---|---|---|
| **Invocation** | One concrete attempted execution of a declared computation, encompassing its subordinate operations, manifestations, realization observations, effect knowledge, accounting observations, durable-record coverage, and enclosing outcome | Every counterexample requires a common enclosing attempt whose facts cannot collapse into one status. The referent survives ordinary calls, streams, callable success, and mixed failure. It is not a provider request or DSPy request object. | **Earned** |
| **Spell** | A reusable source-level declaration of learned computation whose concrete attempts and realizations may vary independently | The derivation requires distinguishing an attempted execution from whatever was declared, but Runs 001–008 characterize calls and sessions rather than declaration identity, versioning, composition, or reuse. | **Provisional** |
| **Sigil** | A prepared realization of a learned computation, potentially involving a configured DSPy program plus evidence about that realization | Run 006 earns a semantic/realization boundary but no integrated prepared-realization identity, lifecycle, or evidence attachment has been observed. Freezing the term now would risk naming imagined implementation structure. | **Deferred** |
| **Ward** | A mechanically enforced restriction on an execution attempt or effect | The project requires hard constraints to come from mechanisms rather than promises ([mechanism principle](../README.md#L83)), and the authority derivation requires an enforceable gate. No concrete enforcement scope, composition rule, or evidence protocol is yet established. The word cannot mean a prompt instruction or unevaluated policy statement. | **Provisional** |

`Invocation` therefore earns a semantic meaning, not a Python class design. `Spell`
and `Ward` identify viable responsibilities but remain provisional. `Sigil` remains
deferred until prepared realization identity is supported by actual integration
evidence. No candidate is grandfathered in by earlier aesthetic preference.

## Unresolved questions

The derivation intentionally leaves these questions open:

- concrete representations for lifecycle and outcome facts;
- event, trace, graph, or state-transition schemas;
- persistence boundaries and execution-record retention;
- cancellation semantics beyond the inherited generator observations;
- concurrent, nested, and distributed ordering;
- mechanisms and evidence quality for effect-completion knowledge;
- authority or capability representation and delegation;
- acceptance, requirement, guarantee, and policy interfaces;
- retry algorithms, idempotency, deduplication, and compensation;
- concrete DSPy streaming, tool, callback, or adapter integration;
- context-source and knowledge semantics for txtai;
- runtime event consumption and presentation in Textual;
- package layout, public APIs, migration order, and replacement types;
- source syntax or concrete magical-language vocabulary beyond the verdicts above.

None of those open questions weakens the derived distinctions. They prevent this
semantic document from silently becoming an implementation proposal.

## Synthesis and stop

The evidence falsifies any execution model in which one scalar disposition,
parent-only state, conversational history, or aggregate accounting stands for the
whole execution. Ars must preserve independently knowable facts about enclosing
lifecycle, subordinate operations, manifestations, effect attempts and completion
knowledge, realization observations, accounting, durable-record coverage,
acceptance, authority, and retry eligibility.

The central empirical result is:

```text
manifestation != completion
effect completion != enclosing completion
accounting != execution-record completeness
durable history != everything that happened
failure != absence of effects
```

The central design result is:

```text
model-visible proposal
    !=
runtime authority

typed realization
    !=
semantic acceptance
```

These statements identify what Ars must mean without prescribing how that meaning
is represented or executed. This is the stopping point for Run 009.
