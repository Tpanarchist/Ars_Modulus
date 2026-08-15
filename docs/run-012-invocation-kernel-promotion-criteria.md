# Run 012: Promotion Criteria for the Invocation Kernel

## Status and review boundary

This artifact is a promotion review, not a design or an implementation. It
changes nothing in `experiments/`, `simpleaichat/`, or `tests/`. It does not
merge the `run011-fact-kernel` branch, create a production package, or delete
the experiment.

Run 012 asks one evaluative question:

> Which parts of the Run 011 experiment have actually earned promotion into
> the Ars runtime, and which parts remain test scaffolding or provisional
> representation choices?

The review boundary is:

```text
Run 011 evidence (design + implementation + tests)
        |
        v
promotion review against three categories
        |
        v
categorized findings, per candidate
        |
        v
USER REVIEW
        |
        v
STOP
```

Every verdict below is tied to a specific test, code path, or an explicit
admission already present in the Run 011 design artifact. Where Run 011 did
not generate evidence for a claim, that is treated as absence of evidence, not
as tacit approval.

## Frozen evidence baseline

Run 011's design artifact is committed on `main`. Its implementation and
tests are **not** — they live only on branch `run011-fact-kernel`, currently
held in a separate worktree. Any promotion decision therefore has two
distinct evidence sources with two distinct commit identities:

```text
main HEAD
fdf8ef2cd928d15005a5a194dc2463300d4d749c

run011-fact-kernel tip
284257f7abcc34acc8702165ee7edbd55b98eac0

Run 011 design artifact (on main)
docs/run-011-minimal-invocation-fact-kernel-design.md
SHA-256  5DB19F9283092650D8C15F6833939B336C18DE40A4C0C9D620050AEFBFA49613

Run 011 implementation (on run011-fact-kernel only)
experiments/invocation_fact_kernel.py
SHA-256  C801E494A17839D35F0F18943CF92FE6D3C8E5CEF88D000BAEFA52D26F211555

Run 011 tests (on run011-fact-kernel only)
tests/test_invocation_fact_kernel.py
SHA-256  0DA03B3FDFEB5FE68244FF73489AF3892BC0C332D9DCE4A7EA4A6F9AA020F62D
```

This review re-ran the offline suite directly against the
`run011-fact-kernel` worktree rather than trusting the prior completion
commit's claim:

```text
$ python -m unittest discover -s tests -p "test_*.py"
Ran 102 tests in 0.747s
OK
```

`git diff --name-only 28cf161…HEAD -- simpleaichat tests experiments` against
that branch confirms the changed set is exactly
`experiments/__init__.py`, `experiments/invocation_fact_kernel.py`,
`tests/test_invocation_fact_kernel.py` — matching the isolation the Run 011
design required.

The evidence below cites code and test line numbers from that worktree
checkout. Because `run011-fact-kernel` is not merged, none of that evidence is
currently reachable from `main`. That is itself a fact this review surfaces,
not a promotion decision — see [Findings not about the ten candidates](#findings-not-about-the-ten-candidates).

## Method

Each candidate below is placed in exactly one category:

- **Promote** — a semantic rule or mechanic with direct, repeatable test
  evidence, general enough to bind production design, independent of any
  implementation convenience used only to make Run 011 runnable in an
  afternoon.
- **Keep experimental** — useful, evidence-touched, but either (a) Run 011
  explicitly declined to claim it as a production decision, (b) no comparative
  evidence exists against an alternative, or (c) its evidence base is
  partial and untested against the requirements it doesn't yet cover.
- **Reject/replace** — an implementation convenience that the experiment
  needed to exist at all, but that no test result depends on specifically,
  and that would mislead a reader into thinking it was load-bearing if it
  quietly became the production default.

A candidate can split: the *rule* a mechanism embodies may promote while its
*concrete encoding* stays experimental or gets rejected. That split is the
main output of this review — collapsing it back into one verdict per
candidate is the mistake Run 012 exists to prevent.

## Findings by candidate

### 1. Append-oriented authority model — **Promote**

Facts are the only authority; views and issues are computed and disposable;
`append_fact` returns a new tuple and never mutates the old one
(`experiments/invocation_fact_kernel.py:217-227`). This is the mechanism Run
010 selected as Candidate D and the one Run 011 was built expressly to
falsify. It carries the densest evidence in the experiment:
`test_append_returns_new_sequence_and_preserves_exact_prefix` (L352),
`test_late_fact_refines_knowledge_without_mutating_terminated_prefix` (L288),
`test_projection_and_issues_are_disposable_and_never_feed_history` (L902), and
the full Task 7 falsification checklist, all passing.

Promote the *relation*: facts are sole authority; views/issues cannot
re-enter as source facts; append never rewrites a prior fact or a prior
projection. Do **not** promote the *physical* mechanism — an in-memory
functional Python tuple — as the production append mechanism. Run 010
deliberately left physical append and durability mechanics unresolved
([physical questions](./run-010-invocation-workload-and-representation-constraints.md#L749)),
and Run 011 says so explicitly about its own choice
([functional append caveat](./run-011-minimal-invocation-fact-kernel-design.md#L361)).
That remains a separate, still-open design question.

### 2. Pure rebuildable projection — **Promote**

`project(facts)` takes no other input and holds no memoized state
(`experiments/invocation_fact_kernel.py:340`). `test_projection_is_frozen_and_deterministic`
(L141) and `test_every_trace_prefix_is_pure_deterministic_and_round_trip_rebuildable`
(L843) exercise purity and the stronger round-trip law
`project(F) == project(decode(encode(F)))` across all four workloads at every
prefix, plus the malformed-history matrix. This held with zero exceptions in
102/102.

Promote as a binding production invariant: current-state views must be pure
functions of an authoritative prefix, safely discardable, and reconstructable
without consulting any prior view. No caveat is needed — nothing about this
candidate was implementation-specific.

### 3. Issue derivation — **Split**

**Promote** the policy: issues are non-authoritative diagnoses, never
synthesized repairs, localized to the conclusions they actually affect, and
can disappear purely because a later append supplies a previously-missing
referent — never because of append-order precedence. Evidence:
`test_conflicting_completion_evidence_is_not_last_write_wins` (L485),
`test_semantic_issue_never_reduces_coverage_or_erases_later_valid_state` (L556),
`test_later_attempt_resolves_reference_without_order_precedence` (L533),
`test_missing_operation_relationships_are_localized` (L642). All nine rows of
the design's malformed-history matrix are backed by a passing test.

**Keep experimental** the specific issue taxonomy — the exact codes
(`unsupported_effect_attempt`, `conflicting_operation_kind`, and similar,
`experiments/invocation_fact_kernel.py:346-448`). These are downstream of the
experimental kind vocabulary (candidate 9) and have not been exercised
against the Run 009 domains Run 011 doesn't cover. A production issue
taxonomy is a co-design problem with whatever ontology Run 012-and-later
choose, not a standalone artifact to inherit as-is.

### 4. Covered-prefix semantics — **Promote, with its definition attached**

`covered_prefix=len(facts)` unconditionally
(`experiments/invocation_fact_kernel.py:459`), independent of whether issues
exist. Tested at every prefix 0..N for all four workloads, including the
empty-sequence case, and the corresponding falsification condition
("coverage is less than the supplied readable fact count") did not occur in
102/102.

Promote the field and, just as importantly, promote its stated meaning
alongside it: `covered_prefix` means "authoritative prefix consumed," not
"semantically valid through position N"
([non-meaning](./run-011-minimal-invocation-fact-kernel-design.md#L140)). A
field name surviving into production without that attached definition is
exactly how "coverage" quietly gets reread as "correctness" later. The
promotion should carry the sentence, not just the field.

### 5. Fact identity / association rules — **Split**

**Promote** the rule: one `invocation_id` structurally scopes one sequence
(`_validate_fact_sequence`, `experiments/invocation_fact_kernel.py:198-215`,
tested by `test_append_rejects_noncontiguous_position_and_mixed_identity` L359
and `test_decode_rejects_noncontiguous_and_mixed_sequences` L421); every
relationship is an explicit, kind-validated association, never inferred from
adjacency or order (`test_later_operation_can_resolve_reference_without_implied_causality`
L204, `test_later_attempt_resolves_reference_without_order_precedence` L533).
`local_position` carries order only — this is directly falsifiable and was
directly tested, not merely asserted in prose.

**Keep experimental** the identifier scheme itself. Run 011 uses bare
nonempty opaque strings and says so is deliberate and unresolved
([identifier scope](./run-011-minimal-invocation-fact-kernel-design.md#L307),
deferred again at
[unresolved questions](./run-011-minimal-invocation-fact-kernel-design.md#L811)).
Sufficiency for exercising the rule is not evidence that production
identifiers should stay bare strings rather than typed or namespaced values.

### 6. The single `Fact` record shape — **Split**

Run 011's own design artifact already declines to claim this one:
"[the record] is not evidence that the durable Ars substrate must use one
universal record or table"
([test-instrument caveat](./run-011-minimal-invocation-fact-kernel-design.md#L289)),
and lists "whether future facts use one record shape or a typed union" as an
explicit open question
([deferred](./run-011-minimal-invocation-fact-kernel-design.md#L809)). No
typed-union alternative was built, so there is no comparative evidence either
way — **keep experimental**.

What has earned promotion is narrower than the five fields themselves. It is
the set of representation *obligations* those fields happened to satisfy,
independent of how many fields, tables, or types eventually carry them
([field table](./run-011-minimal-invocation-fact-kernel-design.md#L292-L300)):

```text
a fact must communicate what was recorded

it must be attributable to an Invocation

demonstrated local order must be recoverable

semantic relationships must be explicit rather than
inferred from adjacency

the recorded content needed to interpret the fact
must be preserved
```

**Promote** those five obligations — they are what the schema validation,
the association-vs-payload split, and the non-meaning table actually
exercised. **Do not promote** `kind` / `invocation_id` / `local_position` /
`associations` / `payload` as the production field decomposition. A future
representation could satisfy the same obligations with five fields, six
tables, a tagged union, separate relation records, or a shape nobody has
tried yet. Run 011 supplies no evidence that its particular decomposition is
the one that should survive; it only supplies evidence that the obligations
are real and separable from each other.

### 7. JSON encoding — **Keep experimental**

Run 011 calls this "the test adapter" and is explicit that "no filesystem or
database persistence is part of Run 011"
([scope](./run-011-minimal-invocation-fact-kernel-design.md#L370),
[L405](./run-011-minimal-invocation-fact-kernel-design.md#L405)). It did its
one assigned job well — `test_encoding_is_deterministic_and_round_trips_equal_facts`
(L373) and `test_decode_rejects_invalid_representation` (L395) hold, and the
round-trip law is folded into every prefix-replay test. But no test touches
the actual concerns a production wire or durability format has to answer:
schema evolution, compactness, streaming decode, or interoperability.

Keep the encoding experimental. **Promote** the round-trip law itself
(`decode(encode(F)) == F` and `project(F) == project(decode(encode(F)))`) as
a verification discipline to demand of whatever format is eventually chosen
— not JSON as that format.

### 8. Tuple storage — **Reject/replace** (as an architectural commitment)

`FactItems = Tuple[Tuple[str, FactScalar], ...]` — associations and payload
are stored as sorted, unique, string-keyed tuples of pairs, enforced by
`_canonical_items` / `_items_as_dict`
(`experiments/invocation_fact_kernel.py:129-151`). Every test that touches
these fields does so through `dict(...)` or a single-key lookup
(`_association`, `_payload`,
`experiments/invocation_fact_kernel.py:316-322`) — meaning what's actually
under test is "immutable, canonical, validated key/value data," never
"specifically a sorted tuple-of-2-tuples." No falsification condition and no
test depends on the pair-tuple encoding by itself.

This exists so a `@dataclass(frozen=True)` field can be hashable using only
the standard library — a reasonable implementation shortcut for a
same-afternoon experiment, and nothing more. Rejecting it does not mean the
implementation must be torn out or that Run 012 owes it a successor; the
encoding can stay exactly as it is in `experiments/` indefinitely. The
verdict is narrower and only needs to say: its successful use supplies no
evidence that this encoding deserves production status. Carrying it forward
as if it had earned that status is precisely the "the experiment worked,
therefore every detail is architecture" mistake this run exists to catch.

### 9. The specific fact-kind vocabulary — **Keep experimental**

Run 011's design artifact already predicts this verdict: "[t]he names,
values, and schemas are experimental and may be rejected by Run 012 ...
[t]hey cover only the four Run 010 traces; they do not implement all ten Run
009 domains"
([self-limitation](./run-011-minimal-invocation-fact-kernel-design.md#L332)).
Checking that claim against the actual code confirms it precisely. Mapping
Run 011's eleven kinds against
[Run 009's ten independently required domains](./run-009-ars-execution-semantics-derivation.md#L263):

| Run 009 domain | Run 011 coverage |
|---|---|
| 1. Enclosing execution lifecycle | `invocation_began` / `invocation_terminated` |
| 2. Subordinate operations | `operation_began` / `operation_terminated` |
| 3. Manifestations | `manifestation_recorded` |
| 4. Effect attempt, completion, and knowledge | `effect_authorized` / `effect_attempted` / `effect_completion_evidence_observed` |
| 5. Realization observations | `observation_recorded` |
| 6. Accounting observations | `accounting_observed` |
| 7. Durable recording and coverage | Addressed structurally by `covered_prefix`, not by a fact kind |
| 8. Acceptance | `acceptance_decided` |
| 9. Authority and policy | **Partially exercised.** See below. |
| 10. Retry eligibility | **Not represented at all.** Explicitly out of scope ([L209](./run-011-minimal-invocation-fact-kernel-design.md#L209)). |

Domain 9 deserves more precision than "untouched." Run 011 has an explicit
`effect_authorized` fact carrying an authorization basis, and projection
deliberately keeps authorization, attempt, and completion knowledge as three
independent fields rather than collapsing them
(`EffectView.authorization_knowledge` / `.attempt_knowledge` /
`.completion_knowledge`, `experiments/invocation_fact_kernel.py:449-456`).
So Run 011 proves:

```text
authorization decision  !=  effect attempt
```

and that an authorization can be recorded independently of whether an
attempt ever follows it. That is real, evidence-backed progress on the
domain, not zero.

It does not prove anything about:

```text
authority source
capability resolution
delegation
policy evaluation
mechanical authorization enforcement
```

An unaccompanied attempt is neither blocked nor flagged — Run 011 calls that
"a future policy question, not a structural projection issue"
([L499](./run-011-minimal-invocation-fact-kernel-design.md#L499)). No
mechanism decides who may authorize, what an authorization actually
permits, or what happens when an attempt lacks one. The domain is exercised,
not implemented.

Seven of ten domains map cleanly to an implemented, tested kind. One
(durable recording and coverage) is addressed by a different mechanism
entirely. One (authority and policy) is partially exercised in the narrow
sense above. One (retry eligibility) has zero representation and zero
adversarial exposure. That is real, useful, partial coverage — not a reason
to promote the vocabulary as the production ontology, and not a reason to
distrust the seven domains it does cover either.

### 10. The two-pass projector — **Split, and the description overstates the implementation**

The design artifact frames this as literally two passes: "(1) inventory
readable identity-establishing facts ... (2) resolve explicit associations
..." ([L437-442](./run-011-minimal-invocation-fact-kernel-design.md#L437)).
The actual `project()` function
(`experiments/invocation_fact_kernel.py:340-470`) is one linear function that
performs this inventory-then-resolve pattern *separately per relationship
domain* — operation IDs are inventoried before observations/accounting/
terminations/manifestations are checked against them; authorized/attempted
effect IDs are inventoried before evidence is checked against attempts — via
repeated single-kind scans (`_values()`), not two passes over the whole
sequence. This is a real, useful gap between what the design artifact says
and what the code does; nothing was wrong, but the description should not be
taken as an accurate architecture spec.

**Promote** the concept: identity-establishing facts must be inventoried
before references to them are resolved, so a later fact in the same supplied
prefix can resolve an earlier open reference without implying anything about
occurrence order. This is directly evidenced —
`test_later_operation_can_resolve_reference_without_implied_causality` (L204)
and `test_later_attempt_resolves_reference_without_order_precedence` (L533)
both exist specifically to test it.

**Keep experimental / do not promote** "exactly two passes" as an
architectural requirement, and do not assume the current repeated-scan
structure is fine at production scale. Run 011 never tested performance or
complexity — every workload here has well under twenty facts. A projector
that rescans the full authoritative sequence once per fact kind is adequate
for an in-memory 20-fact experiment and says nothing about a production log.

## Summary

| Candidate | Verdict |
|---|---|
| Append-oriented authority model | Promote (relation); physical mechanism stays open |
| Pure rebuildable projection | Promote |
| Issue derivation | Promote (policy); taxonomy stays experimental |
| Covered-prefix semantics | Promote, with its non-meaning attached |
| Fact identity / association rules | Promote (rule); identifier scheme stays experimental |
| Single `Fact` record shape | Keep experimental; the 5 obligations promote, not the 5 fields |
| JSON encoding | Keep experimental; round-trip law promotes instead |
| Tuple storage | Reject/replace, as an architectural commitment only — no successor mandated |
| Fact-kind vocabulary | Keep experimental — 7 domains covered, 1 by another mechanism, 1 partially exercised (authority/policy), 1 untouched (retry) |
| Two-pass projector | Promote the concept; reject "two passes" and untested scaling |

## Findings not about the ten candidates

Two things surfaced during this review that aren't promotion verdicts but
matter to how the state of the project should be described going forward:

**The implementation is not on `main`.** `main` currently contains the Run
011 *design* artifact and the completion report, but the code and tests that
generated all the evidence above live only on the unmerged
`run011-fact-kernel` branch. "Run 011 is complete" is accurate for the
experiment; "Run 011 is on main" is not yet true. The outstanding merge
decision from the branch's completion commit — merge locally, push and open
a PR, or leave the branch as-is — is still unresolved and is a precondition
for any of the above promotions actually landing anywhere.

**Promotion is not integration, and integration remains a prerequisite.**
Every "Promote" verdict above promotes a *rule*, not a location. None of them
authorize moving code out of `experiments/`, creating a production package,
wiring the kernel into `simpleaichat`, or deleting the experiment. Run 011's
own implementation plan says as much for itself — "[d]o not begin Run 012,
promote experimental names, move code into a production package"
([completion boundary](./superpowers/plans/2026-08-15-minimal-invocation-fact-kernel.md#L1961)) —
and that boundary does not move just because this review exists. Concretely,
the dependency runs in one direction only:

```text
Run 011 experiment exists and passes
        |
        v
Run 012 determines what deserves promotion
        |
        v
USER REVIEW / STOP
        |
        v
merge/integration decision still required
(run011-fact-kernel -> main)
        |
        v
only then can promoted mechanics enter
production architecture
```

A promotion verdict answers "was this idea earned by evidence," not "is this
now in `main`." Running the review before the merge, rather than after, is
deliberate: it means approving Run 011's merge later does not itself imply
that every implementation choice inside it became Ars architecture. Where
the promoted rules get implemented, and under what package layout, is a
still-later design run.

## Questions this review surfaces for later runs

- A comparative experiment between one polymorphic `Fact` record and a typed
  union per kind — Run 011 built only the former, so no run has evidence for
  either over the other.
- Physical append and durability mechanics — still open since Run 010.
- An identifier scheme beyond opaque nonempty strings.
- The unbuilt half of authority and policy (domain 9): authority source,
  capability resolution, delegation, policy evaluation, and mechanical
  enforcement, beyond the authorization/attempt separation Run 011 already
  proved. Fact-kind (or equivalent) coverage for retry eligibility (domain
  10), plus domain 7 (durable recording) beyond what `covered_prefix`
  already gives structurally.
- A precedence rule for incompatible evidence, if one is ever wanted — Run
  011 deliberately introduced none.
- Projector complexity and scaling behavior against a fact sequence larger
  than the ~20-fact traces tested here.
- The still-unresolved branch disposition for `run011-fact-kernel` itself.

## Synthesis and stop

Run 011 proved the mechanism: append-oriented authority, pure conservative
projection, disposable localized issues, and exact prefix coverage all
survived 102/102 tests, including an independent re-run performed for this
review. That is real evidence, and it sorts the ten candidates into three
groups rather than a clean promote/reject split.

Two promote close to whole: pure rebuildable projection outright, and
covered-prefix semantics once its non-meaning travels with it. Five split
cleanly into a promoted rule and an unpromoted encoding: append-oriented
authority (logical relation vs. physical mechanism), issue derivation
(policy vs. taxonomy), fact identity (relationship rule vs. identifier
scheme), the `Fact` record (representation obligations vs. field
decomposition), and the two-pass projector (inventory-before-resolve vs.
"exactly two passes" and untested scaling). Three carry no promotable core
of their own: JSON contributes only the round-trip law as a discipline, not
itself as a format; tuple storage earned nothing beyond having been
convenient; and the fact-kind vocabulary remains explicitly partial, by its
own design artifact's admission, against the domains it was never asked to
cover — including authority/policy, where Run 011 earned one real,
narrow distinction (authorization recorded independently of attempt)
without coming anywhere near a working authority system.

None of that is a criticism of Run 011, which scoped itself honestly and
predicted several of these verdicts in its own text. It is the difference
this run exists to draw — including the harder cases, like authority/policy,
where "some evidence" and "the domain is solved" are not the same claim.

This is the design-review stopping point. Nothing here should be acted on —
merged, split into a package, or built on further — without user review.
