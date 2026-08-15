# Minimal Invocation Fact Kernel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an isolated executable proof that immutable authoritative facts plus a pure, total, rebuildable projection preserve the four Run 010 workloads and degrade conservatively on readable defective histories.

**Architecture:** One experimental module owns a frozen discriminated `Fact`, strict construction/sequence/JSON boundaries, functional append/read operations, immutable projection values, and a two-pass projector. Facts are the only authority; views and issues are deterministic disposable derivations, and every structurally readable input satisfies `covered_prefix == len(facts)`.

**Tech Stack:** Python 3.13.15 standard library (`dataclasses`, `json`, `typing`, `unittest`); no new dependencies.

**Spec:** `docs/run-011-minimal-invocation-fact-kernel-design.md`

## Global Constraints

- Begin from HEAD `28cf161bb88b42fbe594682ca0e31a7f22f69dc7` plus Run 009 SHA-256 `7CA2888F2E2477C3A017A4F7F55A298B54AB1AD154CBA441EAD2D23B9A309C09`, Run 010 SHA-256 `D157CFB48EB70E005727A25728931051B481C273938667C3AA14D485F26BC844`, and Run 011 design SHA-256 `5DB19F9283092650D8C15F6833939B336C18DE40A4C0C9D620050AEFBFA49613`. If Runs 009–011 are committed before execution, replace this composite preflight with the resulting atomic commit.
- Do not modify `simpleaichat/`, existing tests, dependency files, scripts, or prior Run artifacts.
- Create only `experiments/__init__.py`, `experiments/invocation_fact_kernel.py`, and `tests/test_invocation_fact_kernel.py` during implementation.
- Use standard-library Python only. Do not import Pydantic, DSPy, txtai, Textual, an HTTP client, a database driver, or an event-sourcing framework.
- Facts are authoritative. `Projection`, all nested view values, and `ProjectionIssue` are immutable derived values and never become input facts.
- The only documented legal sequence construction paths are `EMPTY_FACTS` followed by validated `append_fact(...)`, or `decode_facts(...)`.
- `append_fact`, `read_facts`, `encode_facts`, and `project` must structurally revalidate the supplied tuple. A manually assembled tuple with mixed Invocation identities, noncontiguous positions, a non-`Fact` member, or an invalid `Fact` must fail at the representation boundary rather than enter semantic projection.
- Projection is total only for structurally readable `FactSequence` values. Semantic defects produce issues; invalid representation and projector bugs raise ordinary exceptions in their respective domains.
- For every structurally readable `F`, `project(F).covered_prefix == len(F)`, including `F == EMPTY_FACTS` and histories containing issues.
- Local position establishes record order only. It never implies causality, occurrence time, containment, producer identity, authorization, precedence, or supersession.
- Run every test offline. The final suite must be discovered before installing the non-loopback socket guard.
- Commit only the exact implementation/test files named by each task; do not accidentally stage the untracked Run artifacts or this plan.

---

## File Structure

| Path | Action | Responsibility |
|---|---|---|
| `experiments/__init__.py` | Create | Mark the namespace as explicitly experimental and non-production. |
| `experiments/invocation_fact_kernel.py` | Create | Fact representation, construction and sequence validation, append/read, canonical JSON encoding/decoding, immutable projection records, and pure projection. |
| `tests/test_invocation_fact_kernel.py` | Create | Construction-boundary tests, legal-path tests, four every-prefix replays, malformed-history matrix, projection laws, round-trip laws, and authority-isolation assertions. |

No production module imports `experiments`. Keep the experiment in one source file because its representations and fold rules change together and the approved design names one module. If this file becomes unwieldy during implementation, record that as Run 012 evidence; do not split the approved experiment opportunistically.

## Spec Coverage Map

| Approved design obligation | Implemented and proved by |
|---|---|
| Facts are authoritative; views and issues are disposable and never feed history | Tasks 1, 3, 5, and 6; final falsification audit in Task 7 |
| Only empty-plus-append and decode are legal sequence construction paths | Task 1 append/read boundary, Task 2 decoder, Task 6 authority-function rejection tests |
| Invalid representation fails before projection semantics | Tasks 1 and 2; invalid-manual-sequence tests in Task 6 |
| Semantic defects yield maximal view plus deterministic issues | Tasks 3–6, especially issue-localization and malformed-history tests |
| Projector defects remain ordinary exceptions | Task 6 instruction not to catch projector-body exceptions; Task 7 scope review |
| `covered_prefix == len(facts)` even when issues exist | Every-prefix tests in Tasks 3–6 and Task 7 falsification audit |
| Local position never implies causality, authority, or precedence | Later-producer test in Task 4, later-attempt and conflict tests in Tasks 5–6 |
| Strict immutable fact record with kind-specific payload validation | Task 1 |
| Deterministic encoding and strict decoding | Task 2 |
| Pure, deterministic, rebuildable projection | Tasks 3 and 6 |
| Ordinary completion replay at every prefix | Task 3 |
| Streaming manifestation followed by failure at every prefix | Task 4 |
| Completed effect followed by continuation failure at every prefix | Task 5 |
| Post-termination late completion knowledge at every prefix | Task 5 |
| Unknown is valid; unsupported and conflicted are distinct | Tasks 5 and 6 |
| Missing relationships never synthesize attempts, operations, producers, or Invocation state | Tasks 4 and 6 |
| All readable prefixes satisfy `project(F) == project(decode_facts(encode_facts(F)))` | Task 6 |
| Production isolation, offline execution, and frozen inherited behavior | Task 7 |

## Locked Experimental Interfaces

The implementation tasks use these names consistently:

```python
FactScalar = Union[str, int]
FactItems = Tuple[Tuple[str, FactScalar], ...]
FactSequence = Tuple["Fact", ...]

EMPTY_FACTS: FactSequence = ()

class FactConstructionError(ValueError):
    """A single fact representation is not structurally readable."""

class FactSequenceError(ValueError):
    """A fact tuple violates authoritative sequence structure."""

class FactDecodeError(ValueError):
    """Encoded bytes cannot produce a structurally readable sequence."""

@dataclass(frozen=True)
class Fact:
    kind: str
    invocation_id: str
    local_position: int
    associations: FactItems
    payload: FactItems
```

Function contracts:

```text
make_fact(*, kind: str, invocation_id: str, local_position: int,
          associations: Optional[Mapping[str, FactScalar]] = None,
          payload: Optional[Mapping[str, FactScalar]] = None) -> Fact
append_fact(facts: FactSequence, fact: Fact) -> FactSequence
read_facts(facts: FactSequence) -> FactSequence
encode_facts(facts: FactSequence) -> bytes
decode_facts(data: bytes) -> FactSequence
project(facts: FactSequence) -> Projection
```

`make_fact` is a fact-construction boundary, not a third sequence-construction path. A sequence becomes legal only through repeated validated append from `EMPTY_FACTS` or through `decode_facts`. Every authority-facing function revalidates sequence structure, so an arbitrary tuple cannot smuggle invalid positions or identities into projection.

The immutable projection records are:

```python
@dataclass(frozen=True)
class ProjectionIssue:
    code: str
    fact_positions: Tuple[int, ...]
    subject_id: Optional[str]

@dataclass(frozen=True)
class OperationView:
    operation_id: str
    operation_kind: str
    lifecycle: str
    outcome: Optional[str]

@dataclass(frozen=True)
class ObservationView:
    local_position: int
    operation_id: str
    observation_kind: str
    value: str

@dataclass(frozen=True)
class ManifestationView:
    local_position: int
    producer_operation_id: str
    content: str

@dataclass(frozen=True)
class AccountingView:
    local_position: int
    operation_id: str
    metric: str
    amount: int

@dataclass(frozen=True)
class EffectView:
    effect_id: str
    authorization_knowledge: str
    attempt_knowledge: str
    operation_id: Optional[str]
    completion_knowledge: Optional[str]
    evidence_positions: Tuple[int, ...]

@dataclass(frozen=True)
class Projection:
    covered_prefix: int
    invocation_id: Optional[str]
    invocation_lifecycle: str
    invocation_outcome: Optional[str]
    operations: Tuple[OperationView, ...]
    observations: Tuple[ObservationView, ...]
    manifestations: Tuple[ManifestationView, ...]
    accounting: Tuple[AccountingView, ...]
    effects: Tuple[EffectView, ...]
    acceptance: str
    issues: Tuple[ProjectionIssue, ...]
```

Locked current values:

- Invocation lifecycle: `absent`, `active`, `terminated`.
- Invocation/operation outcome: `None`, `completed`, `failed`, `conflicted`.
- Operation kind: `inference`, `stream`, `effect`, or `conflicted`.
- Acceptance: `undecided`, `accepted`, `rejected`, `conflicted`.
- Authorization knowledge: `not_observed`, `observed_authorized`.
- Attempt knowledge: `not_observed`, `observed_attempted`.
- Effect completion knowledge: `None` when no attempt is observed; otherwise `unknown`, `known_completed`, `known_not_completed`, or `conflicted`.

Locked issue codes:

```text
missing_invocation_begin
unsupported_operation
unsupported_producer_operation
unsupported_effect_attempt
conflicting_operation_kind
conflicting_operation_outcome
conflicting_invocation_outcome
conflicting_acceptance
conflicting_effect_operation
conflicting_effect_completion
```

Issues sort by `(first implicated position, code, subject_id or "", all positions)`. No free-form message participates in equality.

## Implementation Preflight

- [ ] **Step 1: Verify the composite baseline before touching experiment code**

Run:

```powershell
git rev-parse HEAD
Get-FileHash -Algorithm SHA256 -LiteralPath 'docs/run-009-ars-execution-semantics-derivation.md','docs/run-010-invocation-workload-and-representation-constraints.md','docs/run-011-minimal-invocation-fact-kernel-design.md'
git status --short
```

Expected before an atomic documentation commit:

```text
HEAD = 28cf161bb88b42fbe594682ca0e31a7f22f69dc7
Run 009 = 7CA2888F2E2477C3A017A4F7F55A298B54AB1AD154CBA441EAD2D23B9A309C09
Run 010 = D157CFB48EB70E005727A25728931051B481C273938667C3AA14D485F26BC844
Run 011 design = 5DB19F9283092650D8C15F6833939B336C18DE40A4C0C9D620050AEFBFA49613
Run 009, Run 010, Run 011, and this plan are the only untracked files
```

If documentation has been committed, record the new atomic HEAD in the execution notes and verify that production and tests still match it. If any unrelated tracked or untracked change appears, stop and preserve it rather than staging or overwriting it.

- [ ] **Step 2: Confirm the substrate interpreter**

Run:

```powershell
.\.venv\Scripts\python.exe --version
```

Expected: `Python 3.13.15`.

---

### Task 1: Immutable Fact Construction and Legal Sequence Paths

**Files:**
- Create: `experiments/__init__.py`
- Create: `experiments/invocation_fact_kernel.py`
- Create: `tests/test_invocation_fact_kernel.py`

**Interfaces:**
- Consumes: Only Python standard-library values.
- Produces: `Fact`, `FactSequence`, `EMPTY_FACTS`, `FactConstructionError`, `FactSequenceError`, `make_fact`, `append_fact`, and `read_facts` with the locked signatures above.

- [ ] **Step 1: Write failing construction and sequence tests**

Create `tests/test_invocation_fact_kernel.py` with this initial structure:

```python
"""Executable tests for the isolated Run 011 fact/projection kernel."""

from dataclasses import FrozenInstanceError
import unittest

from experiments.invocation_fact_kernel import (
    EMPTY_FACTS,
    FactConstructionError,
    FactSequenceError,
    append_fact,
    make_fact,
    read_facts,
)


INVOCATION_ID = "inv-011"


def fact(kind, position, *, associations=None, payload=None, invocation_id=INVOCATION_ID):
    return make_fact(
        kind=kind,
        invocation_id=invocation_id,
        local_position=position,
        associations=associations,
        payload=payload,
    )


def append_record(facts, kind, *, associations=None, payload=None):
    return append_fact(
        facts,
        fact(
            kind,
            len(facts) + 1,
            associations=associations,
            payload=payload,
        ),
    )


class FactConstructionTests(unittest.TestCase):
    def test_fact_is_frozen_and_canonical(self):
        recorded = fact(
            "operation_began",
            1,
            associations={"operation_id": "op-a"},
            payload={"operation_kind": "inference"},
        )

        self.assertEqual(recorded.associations, (("operation_id", "op-a"),))
        self.assertEqual(recorded.payload, (("operation_kind", "inference"),))
        with self.assertRaises(FrozenInstanceError):
            recorded.kind = "invocation_began"

    def test_kind_specific_shape_is_enforced_at_construction(self):
        with self.assertRaises(FactConstructionError):
            fact("unknown_kind", 1)
        with self.assertRaises(FactConstructionError):
            fact("operation_began", 1, associations={"operation_id": "op-a"})
        with self.assertRaises(FactConstructionError):
            fact(
                "operation_began",
                1,
                associations={"operation_id": "op-a", "extra": "x"},
                payload={"operation_kind": "inference"},
            )
        with self.assertRaises(FactConstructionError):
            fact(
                "accounting_observed",
                1,
                associations={"operation_id": "op-a"},
                payload={"metric": "input_tokens", "amount": True},
            )

    def test_missing_referent_is_not_a_construction_error(self):
        recorded = fact(
            "effect_completion_evidence_observed",
            1,
            associations={"effect_id": "missing-effect"},
            payload={"conclusion": "completed", "evidence": "receipt"},
        )

        self.assertEqual(recorded.local_position, 1)


class FactSequenceTests(unittest.TestCase):
    def test_empty_plus_append_is_a_legal_sequence_path(self):
        first = fact("invocation_began", 1)
        facts = append_fact(EMPTY_FACTS, first)

        self.assertEqual(facts, (first,))
        self.assertIs(read_facts(facts), facts)
        self.assertEqual(EMPTY_FACTS, ())

    def test_append_returns_new_sequence_and_preserves_exact_prefix(self):
        facts_1 = append_record(EMPTY_FACTS, "invocation_began")
        facts_2 = append_record(
            facts_1,
            "operation_began",
            associations={"operation_id": "op-a"},
            payload={"operation_kind": "inference"},
        )

        self.assertEqual(facts_1, facts_2[:-1])
        self.assertEqual(len(facts_1), 1)
        self.assertEqual(facts_2[-1].local_position, 2)

    def test_append_rejects_noncontiguous_position_and_mixed_identity(self):
        facts = append_record(EMPTY_FACTS, "invocation_began")

        with self.assertRaises(FactSequenceError):
            append_fact(facts, fact("invocation_terminated", 3, payload={"outcome": "failed"}))
        with self.assertRaises(FactSequenceError):
            append_fact(
                facts,
                fact(
                    "invocation_terminated",
                    2,
                    invocation_id="other-invocation",
                    payload={"outcome": "failed"},
                ),
            )

    def test_read_rejects_manually_assembled_invalid_tuple(self):
        invalid = (
            fact("invocation_began", 1),
            fact("invocation_terminated", 3, payload={"outcome": "failed"}),
        )

        with self.assertRaises(FactSequenceError):
            read_facts(invalid)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_invocation_fact_kernel.py" -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'experiments'`.

- [ ] **Step 3: Add the experimental marker and minimal representation implementation**

Create `experiments/__init__.py`:

```python
"""Non-production experiments for Ars Modulus architectural validation."""
```

Create `experiments/invocation_fact_kernel.py`. Use frozen dataclasses and this exact schema inventory:

```python
"""Run 011: isolated immutable fact and projection experiment."""

from dataclasses import dataclass
from typing import Callable, Dict, Mapping, Optional, Tuple, Union


FactScalar = Union[str, int]
FactItems = Tuple[Tuple[str, FactScalar], ...]


class FactConstructionError(ValueError):
    """A single fact representation is not structurally readable."""


class FactSequenceError(ValueError):
    """A fact tuple violates authoritative sequence structure."""


class FactDecodeError(ValueError):
    """Encoded bytes cannot produce a structurally readable sequence."""


def _is_string(value: FactScalar) -> bool:
    return isinstance(value, str)


def _is_nonnegative_integer(value: FactScalar) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _one_of(*allowed: str) -> Callable[[FactScalar], bool]:
    return lambda value: isinstance(value, str) and value in allowed


@dataclass(frozen=True)
class _KindSchema:
    required_associations: Tuple[str, ...]
    optional_associations: Tuple[str, ...]
    payload_rules: Tuple[Tuple[str, Callable[[FactScalar], bool]], ...]


_KIND_SCHEMAS = {
    "invocation_began": _KindSchema((), (), ()),
    "operation_began": _KindSchema(
        ("operation_id",),
        (),
        (("operation_kind", _one_of("inference", "stream", "effect")),),
    ),
    "observation_recorded": _KindSchema(
        ("operation_id",),
        (),
        (
            ("observation_kind", _one_of("result", "error")),
            ("value", _is_string),
        ),
    ),
    "manifestation_recorded": _KindSchema(
        ("producer_operation_id",), (), (("content", _is_string),)
    ),
    "accounting_observed": _KindSchema(
        ("operation_id",),
        (),
        (
            ("metric", _one_of("input_tokens", "output_tokens")),
            ("amount", _is_nonnegative_integer),
        ),
    ),
    "effect_authorized": _KindSchema(
        ("effect_id",), (), (("basis", _is_string),)
    ),
    "effect_attempted": _KindSchema(
        ("effect_id",), ("operation_id",), ()
    ),
    "effect_completion_evidence_observed": _KindSchema(
        ("effect_id",),
        (),
        (
            ("conclusion", _one_of("completed", "not_completed")),
            ("evidence", _is_string),
        ),
    ),
    "operation_terminated": _KindSchema(
        ("operation_id",), (), (("outcome", _one_of("completed", "failed")),)
    ),
    "acceptance_decided": _KindSchema(
        (),
        (),
        (
            ("decision", _one_of("accepted", "rejected")),
            ("basis", _is_string),
        ),
    ),
    "invocation_terminated": _KindSchema(
        (), (), (("outcome", _one_of("completed", "failed")),)
    ),
}
```

Complete the same module with these validation rules:

```python
def _canonical_items(
    values: Optional[Mapping[str, FactScalar]], label: str
) -> FactItems:
    if values is None:
        return ()
    if not isinstance(values, Mapping):
        raise FactConstructionError(f"{label} must be a mapping")
    if any(not isinstance(key, str) for key in values):
        raise FactConstructionError(f"{label} keys must be strings")
    return tuple(sorted(values.items()))


def _items_as_dict(items: FactItems, label: str) -> Dict[str, FactScalar]:
    if not isinstance(items, tuple):
        raise FactConstructionError(f"{label} must use immutable tuple storage")
    if any(not isinstance(item, tuple) or len(item) != 2 for item in items):
        raise FactConstructionError(f"{label} entries must be key/value tuples")
    keys = tuple(item[0] for item in items)
    if any(not isinstance(key, str) for key in keys):
        raise FactConstructionError(f"{label} keys must be strings")
    if keys != tuple(sorted(keys)):
        raise FactConstructionError(f"{label} entries must be canonical")
    if len(set(keys)) != len(keys):
        raise FactConstructionError(f"{label} keys must be unique")
    result = dict(items)
    return result


@dataclass(frozen=True)
class Fact:
    kind: str
    invocation_id: str
    local_position: int
    associations: FactItems
    payload: FactItems

    def __post_init__(self) -> None:
        _validate_fact(self)


FactSequence = Tuple[Fact, ...]
EMPTY_FACTS: FactSequence = ()


def _validate_fact(fact: Fact) -> None:
    if not isinstance(fact.kind, str) or fact.kind not in _KIND_SCHEMAS:
        raise FactConstructionError(f"unsupported fact kind: {fact.kind!r}")
    if not isinstance(fact.invocation_id, str) or not fact.invocation_id:
        raise FactConstructionError("invocation_id must be a nonempty string")
    if (
        not isinstance(fact.local_position, int)
        or isinstance(fact.local_position, bool)
        or fact.local_position < 1
    ):
        raise FactConstructionError("local_position must be a positive integer")

    associations = _items_as_dict(fact.associations, "associations")
    payload = _items_as_dict(fact.payload, "payload")
    schema = _KIND_SCHEMAS[fact.kind]
    required = set(schema.required_associations)
    allowed = required | set(schema.optional_associations)
    if not required.issubset(associations) or set(associations) - allowed:
        raise FactConstructionError(f"invalid associations for {fact.kind}")
    if any(not isinstance(value, str) or not value for value in associations.values()):
        raise FactConstructionError("association identifiers must be nonempty strings")

    rules = dict(schema.payload_rules)
    if set(payload) != set(rules):
        raise FactConstructionError(f"invalid payload keys for {fact.kind}")
    for key, validator in rules.items():
        if not validator(payload[key]):
            raise FactConstructionError(f"invalid payload value for {fact.kind}.{key}")


def make_fact(
    *,
    kind: str,
    invocation_id: str,
    local_position: int,
    associations: Optional[Mapping[str, FactScalar]] = None,
    payload: Optional[Mapping[str, FactScalar]] = None,
) -> Fact:
    return Fact(
        kind=kind,
        invocation_id=invocation_id,
        local_position=local_position,
        associations=_canonical_items(associations, "associations"),
        payload=_canonical_items(payload, "payload"),
    )


def _validate_fact_sequence(facts: FactSequence) -> None:
    if not isinstance(facts, tuple):
        raise FactSequenceError("fact sequence must be an immutable tuple")
    invocation_id = None
    for expected_position, fact in enumerate(facts, start=1):
        if not isinstance(fact, Fact):
            raise FactSequenceError("fact sequence contains a non-Fact value")
        try:
            _validate_fact(fact)
        except FactConstructionError as error:
            raise FactSequenceError(str(error)) from error
        if fact.local_position != expected_position:
            raise FactSequenceError("fact positions must be contiguous from one")
        if invocation_id is None:
            invocation_id = fact.invocation_id
        elif fact.invocation_id != invocation_id:
            raise FactSequenceError("one sequence must contain one invocation_id")


def append_fact(facts: FactSequence, fact: Fact) -> FactSequence:
    _validate_fact_sequence(facts)
    if not isinstance(fact, Fact):
        raise FactSequenceError("append requires a structurally valid Fact")
    if fact.local_position != len(facts) + 1:
        raise FactSequenceError("appended fact must have the next local position")
    if facts and fact.invocation_id != facts[0].invocation_id:
        raise FactSequenceError("appended fact must retain invocation_id")
    result = facts + (fact,)
    _validate_fact_sequence(result)
    return result


def read_facts(facts: FactSequence) -> FactSequence:
    _validate_fact_sequence(facts)
    return facts
```

Do not add projection or serialization yet.

- [ ] **Step 4: Run the focused tests to verify they pass**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_invocation_fact_kernel.py" -v
```

Expected: 7 tests pass.

- [ ] **Step 5: Commit the representation boundary**

Run:

```powershell
git add experiments/__init__.py experiments/invocation_fact_kernel.py tests/test_invocation_fact_kernel.py
git commit -m "experiment: add immutable invocation facts"
```

Verify `git status --short` still lists only the uncommitted documentation artifacts, if they were not committed before execution.

---

### Task 2: Deterministic Encoding and Strict Decoding

**Files:**
- Modify: `experiments/invocation_fact_kernel.py`
- Modify: `tests/test_invocation_fact_kernel.py`

**Interfaces:**
- Consumes: `Fact`, `FactSequence`, `make_fact`, and `_validate_fact_sequence` from Task 1.
- Produces: `encode_facts(facts: FactSequence) -> bytes` and `decode_facts(data: bytes) -> FactSequence`.

- [ ] **Step 1: Add failing encoding/decoding tests**

Add `FactDecodeError`, `decode_facts`, and `encode_facts` to the test imports. Append this class:

```python
class FactEncodingTests(unittest.TestCase):
    def test_encoding_is_deterministic_and_round_trips_equal_facts(self):
        facts = append_record(EMPTY_FACTS, "invocation_began")

        encoded_1 = encode_facts(facts)
        encoded_2 = encode_facts(facts)

        self.assertIsInstance(encoded_1, bytes)
        self.assertEqual(encoded_1, encoded_2)
        self.assertEqual(decode_facts(encoded_1), facts)
        self.assertEqual(
            encoded_1,
            b'{"facts":[{"associations":{},"invocation_id":"inv-011",'
            b'"kind":"invocation_began","local_position":1,"payload":{}}],'
            b'"version":1}',
        )

    def test_decode_rejects_invalid_representation(self):
        invalid_documents = (
            b"not json",
            b'{"version":2,"facts":[]}',
            b'{"version":1,"facts":{},"extra":true}',
            b'{"version":1,"facts":[{"kind":"unknown"}]}',
        )

        for document in invalid_documents:
            with self.subTest(document=document):
                with self.assertRaises(FactDecodeError):
                    decode_facts(document)

    def test_decode_rejects_noncontiguous_and_mixed_sequences(self):
        noncontiguous = (
            b'{"facts":['
            b'{"associations":{},"invocation_id":"inv-011",'
            b'"kind":"invocation_began","local_position":1,"payload":{}},'
            b'{"associations":{},"invocation_id":"inv-011",'
            b'"kind":"invocation_terminated","local_position":3,'
            b'"payload":{"outcome":"failed"}}],"version":1}'
        )
        mixed = noncontiguous.replace(
            b'"invocation_id":"inv-011","kind":"invocation_terminated",'
            b'"local_position":3',
            b'"invocation_id":"other","kind":"invocation_terminated",'
            b'"local_position":2',
        )

        for document in (noncontiguous, mixed):
            with self.subTest(document=document):
                with self.assertRaises(FactDecodeError):
                    decode_facts(document)

    def test_semantic_missing_reference_decodes_successfully(self):
        facts = append_record(
            EMPTY_FACTS,
            "effect_completion_evidence_observed",
            associations={"effect_id": "missing-effect"},
            payload={"conclusion": "completed", "evidence": "receipt"},
        )

        self.assertEqual(decode_facts(encode_facts(facts)), facts)
```

- [ ] **Step 2: Run the focused suite and verify the new tests fail**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_invocation_fact_kernel.py" -v
```

Expected: import failure for `encode_facts` or `decode_facts`.

- [ ] **Step 3: Implement canonical encoding and strict decoding**

Add `import json` and `Any` to the module imports, then add:

```python
_ENCODING_VERSION = 1
_FACT_DOCUMENT_KEYS = {
    "kind",
    "invocation_id",
    "local_position",
    "associations",
    "payload",
}


def encode_facts(facts: FactSequence) -> bytes:
    _validate_fact_sequence(facts)
    document = {
        "version": _ENCODING_VERSION,
        "facts": [
            {
                "kind": fact.kind,
                "invocation_id": fact.invocation_id,
                "local_position": fact.local_position,
                "associations": dict(fact.associations),
                "payload": dict(fact.payload),
            }
            for fact in facts
        ],
    }
    return json.dumps(
        document,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _decode_document(data: bytes) -> Dict[str, Any]:
    if not isinstance(data, bytes):
        raise FactDecodeError("encoded facts must be bytes")
    try:
        document = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise FactDecodeError("encoded facts are not valid UTF-8 JSON") from error
    if not isinstance(document, dict) or set(document) != {"version", "facts"}:
        raise FactDecodeError("encoded envelope must contain version and facts")
    if (
        not isinstance(document["version"], int)
        or isinstance(document["version"], bool)
        or document["version"] != _ENCODING_VERSION
    ):
        raise FactDecodeError("unsupported encoded fact version")
    if not isinstance(document["facts"], list):
        raise FactDecodeError("encoded facts must be a list")
    return document


def decode_facts(data: bytes) -> FactSequence:
    document = _decode_document(data)
    decoded = EMPTY_FACTS
    try:
        for raw_fact in document["facts"]:
            if not isinstance(raw_fact, dict) or set(raw_fact) != _FACT_DOCUMENT_KEYS:
                raise FactDecodeError("encoded fact has invalid fields")
            recorded = make_fact(
                kind=raw_fact["kind"],
                invocation_id=raw_fact["invocation_id"],
                local_position=raw_fact["local_position"],
                associations=raw_fact["associations"],
                payload=raw_fact["payload"],
            )
            decoded = append_fact(decoded, recorded)
    except (FactConstructionError, FactSequenceError, TypeError) as error:
        raise FactDecodeError(str(error)) from error
    return decoded
```

Keep semantic referent checks out of the decoder.

- [ ] **Step 4: Run the focused suite to verify it passes**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_invocation_fact_kernel.py" -v
```

Expected: 11 tests pass.

- [ ] **Step 5: Commit the encoding boundary**

Run:

```powershell
git add experiments/invocation_fact_kernel.py tests/test_invocation_fact_kernel.py
git commit -m "experiment: add deterministic fact encoding"
```

---

### Task 3: Immutable Projection Values and Ordinary Prefix Replay

**Files:**
- Modify: `experiments/invocation_fact_kernel.py`
- Modify: `tests/test_invocation_fact_kernel.py`

**Interfaces:**
- Consumes: structurally validated `FactSequence` values from Tasks 1–2.
- Produces: all locked immutable view records and `project(facts: FactSequence) -> Projection` for Invocation lifecycle, operations, observations, accounting, and acceptance.

- [ ] **Step 1: Add the ordinary trace helper and failing every-prefix test**

Extend imports with `Projection`, `ProjectionIssue`, and `project`. Add:

```python
def ordinary_trace():
    facts = append_record(EMPTY_FACTS, "invocation_began")
    facts = append_record(
        facts,
        "operation_began",
        associations={"operation_id": "inference-1"},
        payload={"operation_kind": "inference"},
    )
    facts = append_record(
        facts,
        "observation_recorded",
        associations={"operation_id": "inference-1"},
        payload={"observation_kind": "result", "value": "answer"},
    )
    facts = append_record(
        facts,
        "accounting_observed",
        associations={"operation_id": "inference-1"},
        payload={"metric": "input_tokens", "amount": 4},
    )
    facts = append_record(
        facts,
        "operation_terminated",
        associations={"operation_id": "inference-1"},
        payload={"outcome": "completed"},
    )
    facts = append_record(
        facts,
        "acceptance_decided",
        payload={"decision": "accepted", "basis": "test requirement"},
    )
    return append_record(
        facts,
        "invocation_terminated",
        payload={"outcome": "completed"},
    )


class OrdinaryProjectionTests(unittest.TestCase):
    def test_every_ordinary_prefix_preserves_independent_state(self):
        facts = ordinary_trace()
        projections = tuple(project(facts[:size]) for size in range(len(facts) + 1))

        self.assertEqual(
            tuple(item.covered_prefix for item in projections), tuple(range(8))
        )
        self.assertEqual(projections[0].invocation_lifecycle, "absent")
        self.assertEqual(projections[1].invocation_lifecycle, "active")
        self.assertEqual(projections[2].operations[0].lifecycle, "active")
        self.assertEqual(projections[3].observations[0].value, "answer")
        self.assertEqual(projections[3].operations[0].lifecycle, "active")
        self.assertEqual(projections[4].accounting[0].amount, 4)
        self.assertEqual(projections[4].invocation_lifecycle, "active")
        self.assertEqual(projections[5].operations[0].outcome, "completed")
        self.assertEqual(projections[5].acceptance, "undecided")
        self.assertEqual(projections[6].acceptance, "accepted")
        self.assertEqual(projections[6].invocation_lifecycle, "active")
        self.assertEqual(projections[7].invocation_lifecycle, "terminated")
        self.assertEqual(projections[7].invocation_outcome, "completed")
        self.assertTrue(all(not item.issues for item in projections))

    def test_projection_is_frozen_and_deterministic(self):
        facts = ordinary_trace()
        first = project(facts)
        second = project(facts)

        self.assertEqual(first, second)
        with self.assertRaises(FrozenInstanceError):
            first.covered_prefix = 0
```

- [ ] **Step 2: Run the focused suite and verify it fails**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_invocation_fact_kernel.py" -v
```

Expected: import failure for `Projection` or `project`.

- [ ] **Step 3: Add immutable output records and the base two-pass projector**

Add the locked view dataclasses exactly as declared under **Locked Experimental Interfaces**. Implement these helpers:

```python
def _values(facts: FactSequence, kind: str) -> Tuple[Fact, ...]:
    return tuple(fact for fact in facts if fact.kind == kind)


def _association(fact: Fact, key: str) -> Optional[str]:
    value = dict(fact.associations).get(key)
    return value if isinstance(value, str) else None


def _payload(fact: Fact, key: str) -> FactScalar:
    return dict(fact.payload)[key]


def _issue_sort_key(issue: ProjectionIssue):
    first = issue.fact_positions[0] if issue.fact_positions else 0
    return (first, issue.code, issue.subject_id or "", issue.fact_positions)


def _conclusion(
    facts: Tuple[Fact, ...],
    payload_key: str,
    conflict_code: str,
    subject_id: Optional[str],
):
    values = {_payload(fact, payload_key) for fact in facts}
    if not values:
        return None, ()
    if len(values) == 1:
        return next(iter(values)), ()
    positions = tuple(fact.local_position for fact in facts)
    return "conflicted", (
        ProjectionIssue(conflict_code, positions, subject_id),
    )
```

Implement `project` as a pure function. For this task its two passes must:

1. call `_validate_fact_sequence(facts)` before semantic work;
2. inventory `invocation_began` and every `operation_began` across the complete supplied prefix;
3. derive one operation per explicit `operation_id`, sorting by identity;
4. diagnose conflicting kinds and outcomes without using record order;
5. include observations and accounting only when their explicit operation exists;
6. diagnose missing operation references using the implicated fact's position;
7. derive acceptance and Invocation outcome with `_conclusion`;
8. set Invocation lifecycle to `absent`, `active`, or `terminated` without deriving it from child state; and
9. return empty `manifestations` and `effects` until their tasks are implemented.

Use `missing_invocation_begin` only for a nonempty sequence containing no
`invocation_began`; the empty sequence has no issue. That issue uses the first
readable position and the sequence's `invocation_id` as its subject. Use
`unsupported_operation` for observation, accounting, or termination facts whose
operation is absent. Sort issues with `_issue_sort_key` before constructing the
immutable tuple.

The return statement must set `covered_prefix=len(facts)` unconditionally after
structural validation.

- [ ] **Step 4: Run the focused suite and verify all tests pass**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_invocation_fact_kernel.py" -v
```

Expected: 13 tests pass.

- [ ] **Step 5: Commit the ordinary projection slice**

Run:

```powershell
git add experiments/invocation_fact_kernel.py tests/test_invocation_fact_kernel.py
git commit -m "experiment: project ordinary invocation facts"
```

---

### Task 4: Streaming Manifestations and Localized Relationship Issues

**Files:**
- Modify: `experiments/invocation_fact_kernel.py`
- Modify: `tests/test_invocation_fact_kernel.py`

**Interfaces:**
- Consumes: `project`, `OperationView`, `ProjectionIssue`, and the trace helpers already in the test module.
- Produces: ordered `ManifestationView` values, `unsupported_producer_operation` issues, and later-referent resolution without temporal inference.

- [ ] **Step 1: Add the streaming trace and malformed-producer tests**

Append:

```python
def streaming_trace():
    facts = append_record(EMPTY_FACTS, "invocation_began")
    facts = append_record(
        facts,
        "operation_began",
        associations={"operation_id": "stream-1"},
        payload={"operation_kind": "stream"},
    )
    facts = append_record(
        facts,
        "manifestation_recorded",
        associations={"producer_operation_id": "stream-1"},
        payload={"content": "foo"},
    )
    facts = append_record(
        facts,
        "manifestation_recorded",
        associations={"producer_operation_id": "stream-1"},
        payload={"content": "bar"},
    )
    facts = append_record(
        facts,
        "operation_terminated",
        associations={"operation_id": "stream-1"},
        payload={"outcome": "failed"},
    )
    return append_record(
        facts, "invocation_terminated", payload={"outcome": "failed"}
    )


class StreamingProjectionTests(unittest.TestCase):
    def test_every_streaming_prefix_preserves_manifestation_before_failure(self):
        facts = streaming_trace()
        projections = tuple(project(facts[:size]) for size in range(len(facts) + 1))

        self.assertEqual(
            tuple(item.covered_prefix for item in projections), tuple(range(7))
        )
        self.assertEqual(tuple(item.content for item in projections[3].manifestations), ("foo",))
        self.assertEqual(tuple(item.content for item in projections[4].manifestations), ("foo", "bar"))
        self.assertEqual(projections[4].operations[0].lifecycle, "active")
        self.assertEqual(projections[5].operations[0].outcome, "failed")
        self.assertEqual(tuple(item.content for item in projections[5].manifestations), ("foo", "bar"))
        self.assertEqual(projections[5].invocation_lifecycle, "active")
        self.assertEqual(projections[6].invocation_outcome, "failed")
        self.assertTrue(all(not item.issues for item in projections))

    def test_missing_producer_is_localized_and_later_facts_still_project(self):
        facts = append_record(EMPTY_FACTS, "invocation_began")
        facts = append_record(
            facts,
            "manifestation_recorded",
            associations={"producer_operation_id": "missing"},
            payload={"content": "orphan"},
        )
        facts = append_record(
            facts,
            "operation_began",
            associations={"operation_id": "valid"},
            payload={"operation_kind": "stream"},
        )
        facts = append_record(
            facts,
            "manifestation_recorded",
            associations={"producer_operation_id": "valid"},
            payload={"content": "supported"},
        )
        facts = append_record(
            facts,
            "operation_terminated",
            associations={"operation_id": "valid"},
            payload={"outcome": "failed"},
        )

        result = project(facts)

        self.assertEqual(result.covered_prefix, 5)
        self.assertEqual(tuple(item.content for item in result.manifestations), ("supported",))
        self.assertEqual(result.operations[0].outcome, "failed")
        self.assertEqual(
            result.issues,
            (ProjectionIssue("unsupported_producer_operation", (2,), "missing"),),
        )

    def test_later_operation_can_resolve_reference_without_implied_causality(self):
        prefix = append_record(EMPTY_FACTS, "invocation_began")
        prefix = append_record(
            prefix,
            "manifestation_recorded",
            associations={"producer_operation_id": "late-producer"},
            payload={"content": "observed"},
        )
        before = project(prefix)
        complete = append_record(
            prefix,
            "operation_began",
            associations={"operation_id": "late-producer"},
            payload={"operation_kind": "stream"},
        )
        after = project(complete)

        self.assertEqual(before.issues[0].code, "unsupported_producer_operation")
        self.assertEqual(before.manifestations, ())
        self.assertEqual(tuple(item.content for item in after.manifestations), ("observed",))
        self.assertEqual(after.issues, ())
        self.assertEqual(after.manifestations[0].local_position, 2)
```

- [ ] **Step 2: Run the focused suite and verify the streaming tests fail**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_invocation_fact_kernel.py" -v
```

Expected: failures showing empty manifestations and absent producer issues.

- [ ] **Step 3: Extend the second pass with manifestation resolution**

After inventorying all operations, process every `manifestation_recorded` in
`local_position` order. For a known producer, construct `ManifestationView` from
the fact position, explicit producer, and content. For an absent producer, add:

```python
ProjectionIssue(
    code="unsupported_producer_operation",
    fact_positions=(fact.local_position,),
    subject_id=producer_operation_id,
)
```

Do not create a placeholder operation or inferred manifestation placement. Because
the operation inventory covers the whole supplied prefix, a later
`operation_began` can resolve an earlier reference on rebuild. Preserve the
manifestation's own local position; add no derived causal or occurrence-time
field.

- [ ] **Step 4: Run the focused suite and verify all tests pass**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_invocation_fact_kernel.py" -v
```

Expected: 16 tests pass.

- [ ] **Step 5: Commit manifestation projection**

Run:

```powershell
git add experiments/invocation_fact_kernel.py tests/test_invocation_fact_kernel.py
git commit -m "experiment: project streaming manifestations"
```

---

### Task 5: Effect Knowledge, Mixed Failure, and Late Refinement

**Files:**
- Modify: `experiments/invocation_fact_kernel.py`
- Modify: `tests/test_invocation_fact_kernel.py`

**Interfaces:**
- Consumes: validated explicit `effect_id` and optional `operation_id` associations.
- Produces: deterministic `EffectView` values, conservative completion knowledge, mixed-outcome replay, late-knowledge replay, and effect issue codes.

- [ ] **Step 1: Add effectful mixed and late-knowledge trace builders**

Append these builders:

```python
def effect_mixed_trace():
    records = (
        ("invocation_began", None, None),
        ("operation_began", {"operation_id": "selection"}, {"operation_kind": "inference"}),
        ("observation_recorded", {"operation_id": "selection"}, {"observation_kind": "result", "value": "1"}),
        ("accounting_observed", {"operation_id": "selection"}, {"metric": "input_tokens", "amount": 3}),
        ("operation_terminated", {"operation_id": "selection"}, {"outcome": "completed"}),
        ("effect_authorized", {"effect_id": "effect-x"}, {"basis": "test authority"}),
        ("operation_began", {"operation_id": "effect-op"}, {"operation_kind": "effect"}),
        ("effect_attempted", {"effect_id": "effect-x", "operation_id": "effect-op"}, None),
        ("effect_completion_evidence_observed", {"effect_id": "effect-x"}, {"conclusion": "completed", "evidence": "receipt-x"}),
        ("operation_terminated", {"operation_id": "effect-op"}, {"outcome": "completed"}),
        ("operation_began", {"operation_id": "continuation"}, {"operation_kind": "inference"}),
        ("operation_terminated", {"operation_id": "continuation"}, {"outcome": "failed"}),
        ("invocation_terminated", None, {"outcome": "failed"}),
    )
    facts = EMPTY_FACTS
    for kind, associations, payload in records:
        facts = append_record(facts, kind, associations=associations, payload=payload)
    return facts


def late_knowledge_trace():
    records = (
        ("invocation_began", None, None),
        ("operation_began", {"operation_id": "effect-op"}, {"operation_kind": "effect"}),
        ("effect_authorized", {"effect_id": "effect-x"}, {"basis": "test authority"}),
        ("effect_attempted", {"effect_id": "effect-x", "operation_id": "effect-op"}, None),
        ("operation_terminated", {"operation_id": "effect-op"}, {"outcome": "failed"}),
        ("invocation_terminated", None, {"outcome": "failed"}),
        ("effect_completion_evidence_observed", {"effect_id": "effect-x"}, {"conclusion": "completed", "evidence": "late receipt"}),
    )
    facts = EMPTY_FACTS
    for kind, associations, payload in records:
        facts = append_record(facts, kind, associations=associations, payload=payload)
    return facts
```

- [ ] **Step 2: Add failing lifecycle assertions**

Append:

```python
class EffectProjectionTests(unittest.TestCase):
    def test_every_effectful_prefix_preserves_independent_outcomes(self):
        facts = effect_mixed_trace()
        projections = tuple(project(facts[:size]) for size in range(len(facts) + 1))

        self.assertEqual(
            tuple(item.covered_prefix for item in projections), tuple(range(14))
        )
        completion_by_prefix = tuple(
            item.effects[0].completion_knowledge if item.effects else "absent"
            for item in projections
        )
        self.assertEqual(
            completion_by_prefix,
            (
                "absent",
                "absent",
                "absent",
                "absent",
                "absent",
                "absent",
                None,
                None,
                "unknown",
                "known_completed",
                "known_completed",
                "known_completed",
                "known_completed",
                "known_completed",
            ),
        )
        self.assertEqual(projections[5].accounting[0].amount, 3)
        self.assertEqual(projections[6].effects[0].authorization_knowledge, "observed_authorized")
        self.assertEqual(projections[6].effects[0].attempt_knowledge, "not_observed")
        self.assertEqual(projections[8].effects[0].attempt_knowledge, "observed_attempted")
        self.assertEqual(projections[8].effects[0].completion_knowledge, "unknown")
        self.assertEqual(projections[9].effects[0].completion_knowledge, "known_completed")
        effect_operation = next(
            operation
            for operation in projections[10].operations
            if operation.operation_id == "effect-op"
        )
        continuation = next(
            operation
            for operation in projections[12].operations
            if operation.operation_id == "continuation"
        )
        self.assertEqual(effect_operation.outcome, "completed")
        self.assertEqual(continuation.outcome, "failed")
        self.assertEqual(projections[12].effects[0].completion_knowledge, "known_completed")
        self.assertEqual(projections[13].invocation_outcome, "failed")
        self.assertEqual(projections[13].effects[0].completion_knowledge, "known_completed")
        self.assertTrue(all(not item.issues for item in projections))

    def test_late_fact_refines_knowledge_without_mutating_terminated_prefix(self):
        complete = late_knowledge_trace()
        projections = tuple(
            project(complete[:size]) for size in range(len(complete) + 1)
        )
        self.assertEqual(
            tuple(
                item.effects[0].completion_knowledge if item.effects else "absent"
                for item in projections
            ),
            (
                "absent",
                "absent",
                "absent",
                None,
                "unknown",
                "unknown",
                "unknown",
                "known_completed",
            ),
        )
        self.assertEqual(
            tuple(item.covered_prefix for item in projections), tuple(range(8))
        )
        self.assertTrue(all(not item.issues for item in projections))
        facts_1 = complete[:-1]
        projection_1 = project(facts_1)
        facts_1_snapshot = tuple(facts_1)
        projection_1_snapshot = projection_1

        facts_2 = append_fact(facts_1, complete[-1])
        projection_2 = project(facts_2)

        self.assertEqual(projection_1.effects[0].completion_knowledge, "unknown")
        self.assertEqual(projection_1.invocation_outcome, "failed")
        self.assertEqual(projection_2.effects[0].completion_knowledge, "known_completed")
        self.assertEqual(projection_2.invocation_outcome, "failed")
        self.assertEqual(facts_1, facts_1_snapshot)
        self.assertEqual(projection_1, projection_1_snapshot)
        self.assertEqual(facts_2[:-1], facts_1)
```

- [ ] **Step 3: Run the focused suite and verify effect tests fail**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_invocation_fact_kernel.py" -v
```

Expected: failures showing empty effect projections.

- [ ] **Step 4: Implement two-pass effect projection**

Inventory authorization, attempts, and completion evidence by explicit
`effect_id` across the complete prefix. An effect summary exists when an
authorization or attempt exists. Evidence alone never creates one.

For each effect identity in sorted order:

1. authorization knowledge is `observed_authorized` when any authorization fact
   exists, otherwise `not_observed`;
2. attempt knowledge is `observed_attempted` when any attempt exists, otherwise
   `not_observed`;
3. optional attempt `operation_id` values resolve only against inventoried
   operations; missing operations add `unsupported_operation`;
4. multiple distinct supported attempt operation identities produce
   `operation_id=None` plus `conflicting_effect_operation` naming all attempt
   positions;
5. no attempt yields `completion_knowledge=None` even if evidence exists;
6. an attempt with no evidence yields `unknown` and no issue;
7. only `completed` evidence yields `known_completed`;
8. only `not_completed` evidence yields `known_not_completed`; and
9. both conclusions yield `conflicted` plus
   `conflicting_effect_completion` naming all evidence positions.

For evidence whose `effect_id` has no attempt, add one deterministic
`unsupported_effect_attempt` issue per effect identity, containing every such
evidence position. Do not synthesize an attempt or completion state.

Set `EffectView.evidence_positions` to all supported evidence positions in local
record order. Authorization absence is not a structural issue.

- [ ] **Step 5: Run the focused suite and verify all tests pass**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_invocation_fact_kernel.py" -v
```

Expected: 18 tests pass.

- [ ] **Step 6: Commit effect and late-knowledge projection**

Run:

```powershell
git add experiments/invocation_fact_kernel.py tests/test_invocation_fact_kernel.py
git commit -m "experiment: project effect knowledge and late evidence"
```

---

### Task 6: Malformed Histories, Conflict Semantics, and Projection Laws

**Files:**
- Modify: `experiments/invocation_fact_kernel.py`
- Modify: `tests/test_invocation_fact_kernel.py`

**Interfaces:**
- Consumes: complete fact/encoding/projector API from Tasks 1–5.
- Produces: the full malformed-history matrix, every-prefix round-trip corpus, and executable authority-isolation laws.

- [ ] **Step 1: Add failing malformed-history tests**

Append:

```python
class MalformedHistoryTests(unittest.TestCase):
    def test_evidence_without_attempt_reports_issue_and_synthesizes_no_effect(self):
        facts = append_record(EMPTY_FACTS, "invocation_began")
        facts = append_record(
            facts,
            "effect_completion_evidence_observed",
            associations={"effect_id": "missing-effect"},
            payload={"conclusion": "completed", "evidence": "orphan receipt"},
        )

        result = project(facts)

        self.assertEqual(result.covered_prefix, 2)
        self.assertEqual(result.effects, ())
        self.assertEqual(
            result.issues,
            (ProjectionIssue("unsupported_effect_attempt", (2,), "missing-effect"),),
        )

    def test_unknown_is_valid_and_not_an_issue(self):
        facts = append_record(EMPTY_FACTS, "invocation_began")
        facts = append_record(
            facts,
            "effect_attempted",
            associations={"effect_id": "effect-x"},
        )

        result = project(facts)

        self.assertEqual(result.effects[0].completion_knowledge, "unknown")
        self.assertEqual(result.issues, ())

    def test_conflicting_completion_evidence_is_not_last_write_wins(self):
        facts = append_record(EMPTY_FACTS, "invocation_began")
        facts = append_record(
            facts, "effect_attempted", associations={"effect_id": "effect-x"}
        )
        facts = append_record(
            facts,
            "effect_completion_evidence_observed",
            associations={"effect_id": "effect-x"},
            payload={"conclusion": "completed", "evidence": "receipt-a"},
        )
        facts = append_record(
            facts,
            "effect_completion_evidence_observed",
            associations={"effect_id": "effect-x"},
            payload={"conclusion": "not_completed", "evidence": "receipt-b"},
        )

        result = project(facts)

        self.assertEqual(result.effects[0].completion_knowledge, "conflicted")
        self.assertEqual(
            result.issues,
            (ProjectionIssue("conflicting_effect_completion", (3, 4), "effect-x"),),
        )

    def test_later_attempt_resolves_reference_without_order_precedence(self):
        prefix = append_record(EMPTY_FACTS, "invocation_began")
        prefix = append_record(
            prefix,
            "effect_completion_evidence_observed",
            associations={"effect_id": "effect-x"},
            payload={"conclusion": "completed", "evidence": "receipt"},
        )
        before = project(prefix)
        complete = append_record(
            prefix, "effect_attempted", associations={"effect_id": "effect-x"}
        )
        after = project(complete)

        self.assertEqual(before.effects, ())
        self.assertEqual(before.issues[0].code, "unsupported_effect_attempt")
        self.assertEqual(after.effects[0].completion_knowledge, "known_completed")
        self.assertEqual(after.effects[0].evidence_positions, (2,))
        self.assertEqual(after.issues, ())

    def test_semantic_issue_never_reduces_coverage_or_erases_later_valid_state(self):
        facts = append_record(EMPTY_FACTS, "invocation_began")
        facts = append_record(
            facts,
            "effect_completion_evidence_observed",
            associations={"effect_id": "missing-effect"},
            payload={"conclusion": "completed", "evidence": "receipt"},
        )
        facts = append_record(
            facts,
            "operation_began",
            associations={"operation_id": "operation-a"},
            payload={"operation_kind": "stream"},
        )
        facts = append_record(
            facts,
            "manifestation_recorded",
            associations={"producer_operation_id": "operation-a"},
            payload={"content": "foo"},
        )
        facts = append_record(
            facts,
            "operation_terminated",
            associations={"operation_id": "operation-a"},
            payload={"outcome": "failed"},
        )

        result = project(facts)

        self.assertEqual(result.covered_prefix, 5)
        self.assertEqual(result.operations[0].outcome, "failed")
        self.assertEqual(result.manifestations[0].content, "foo")
        self.assertEqual(result.issues[0].code, "unsupported_effect_attempt")

    def test_nonempty_history_without_invocation_begin_is_diagnosed_not_repaired(self):
        facts = append_record(
            EMPTY_FACTS,
            "operation_began",
            associations={"operation_id": "operation-a"},
            payload={"operation_kind": "inference"},
        )

        result = project(facts)

        self.assertEqual(result.covered_prefix, 1)
        self.assertEqual(result.invocation_lifecycle, "absent")
        self.assertEqual(result.operations[0].operation_id, "operation-a")
        self.assertEqual(
            result.issues,
            (ProjectionIssue("missing_invocation_begin", (1,), INVOCATION_ID),),
        )

    def test_missing_operation_relationships_are_localized(self):
        records = (
            (
                "observation_recorded",
                {"operation_id": "missing-observation-op"},
                {"observation_kind": "result", "value": "orphan"},
            ),
            (
                "accounting_observed",
                {"operation_id": "missing-accounting-op"},
                {"metric": "input_tokens", "amount": 1},
            ),
            (
                "operation_terminated",
                {"operation_id": "missing-termination-op"},
                {"outcome": "failed"},
            ),
        )

        for kind, associations, payload in records:
            with self.subTest(kind=kind):
                facts = append_record(EMPTY_FACTS, "invocation_began")
                facts = append_record(
                    facts, kind, associations=associations, payload=payload
                )
                result = project(facts)
                self.assertEqual(result.covered_prefix, 2)
                self.assertEqual(result.operations, ())
                self.assertEqual(result.observations, ())
                self.assertEqual(result.accounting, ())
                self.assertEqual(result.issues[0].code, "unsupported_operation")
                self.assertEqual(result.issues[0].fact_positions, (2,))

    def test_authority_functions_reject_invalid_manual_sequence_before_semantics(self):
        noncontiguous = (
            fact("invocation_began", 1),
            fact("invocation_terminated", 3, payload={"outcome": "failed"}),
        )
        mixed = (
            fact("invocation_began", 1),
            fact(
                "invocation_terminated",
                2,
                invocation_id="other",
                payload={"outcome": "failed"},
            ),
        )

        for invalid in (noncontiguous, mixed):
            for consumer in (read_facts, encode_facts, project):
                with self.subTest(invalid=invalid, consumer=consumer.__name__):
                    with self.assertRaises(FactSequenceError):
                        consumer(invalid)
```

- [ ] **Step 2: Add conflict tests for the remaining scalar current views**

Append one table-driven test that builds readable facts for each conflict:

```python
    def test_other_incompatible_conclusions_project_as_conflicted(self):
        cases = (
            (
                (
                    ("operation_began", {"operation_id": "op"}, {"operation_kind": "inference"}),
                    ("operation_began", {"operation_id": "op"}, {"operation_kind": "stream"}),
                ),
                "conflicting_operation_kind",
                lambda result: result.operations[0].operation_kind,
                "conflicted",
            ),
            (
                (
                    ("operation_began", {"operation_id": "op"}, {"operation_kind": "inference"}),
                    ("operation_terminated", {"operation_id": "op"}, {"outcome": "completed"}),
                    ("operation_terminated", {"operation_id": "op"}, {"outcome": "failed"}),
                ),
                "conflicting_operation_outcome",
                lambda result: result.operations[0].outcome,
                "conflicted",
            ),
            (
                (
                    ("invocation_terminated", None, {"outcome": "completed"}),
                    ("invocation_terminated", None, {"outcome": "failed"}),
                ),
                "conflicting_invocation_outcome",
                lambda result: result.invocation_outcome,
                "conflicted",
            ),
            (
                (
                    ("acceptance_decided", None, {"decision": "accepted", "basis": "a"}),
                    ("acceptance_decided", None, {"decision": "rejected", "basis": "b"}),
                ),
                "conflicting_acceptance",
                lambda result: result.acceptance,
                "conflicted",
            ),
            (
                (
                    ("operation_began", {"operation_id": "effect-a"}, {"operation_kind": "effect"}),
                    ("operation_began", {"operation_id": "effect-b"}, {"operation_kind": "effect"}),
                    ("effect_attempted", {"effect_id": "effect-x", "operation_id": "effect-a"}, None),
                    ("effect_attempted", {"effect_id": "effect-x", "operation_id": "effect-b"}, None),
                ),
                "conflicting_effect_operation",
                lambda result: result.effects[0].operation_id,
                None,
            ),
        )

        for records, issue_code, current_value, expected_value in cases:
            with self.subTest(issue_code=issue_code):
                facts = append_record(EMPTY_FACTS, "invocation_began")
                for kind, associations, payload in records:
                    facts = append_record(
                        facts, kind, associations=associations, payload=payload
                    )
                result = project(facts)
                self.assertEqual(current_value(result), expected_value)
                self.assertIn(issue_code, tuple(issue.code for issue in result.issues))
```

- [ ] **Step 3: Run the focused suite and verify any missing issue behavior fails**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_invocation_fact_kernel.py" -v
```

Expected before the final conflict/localization implementation: at least one new malformed or conflict assertion fails. If all pass because prior tasks already implemented the exact behavior, record that evidence and proceed without adding redundant code.

- [ ] **Step 4: Complete issue localization and conflict handling**

Ensure `project` implements all locked issue codes and these exact rules:

- each unsupported relationship names only the positions and subject involved;
- valid unrelated observations, manifestations, accounting, operations, and
  lifecycle facts remain in the view;
- evidence without an attempt creates no `EffectView` unless authorization or an
  attempt independently establishes that effect; even then completion remains
  `None` until an attempt exists;
- duplicate identical conclusions do not conflict;
- incompatible operation kind, operation outcome, Invocation outcome,
  acceptance, effect operation, and completion conclusions produce `conflicted`;
- issue sorting uses the locked deterministic tuple; and
- the return path always uses `covered_prefix=len(facts)`.

Do not catch exceptions around the projector body. Only semantic conditions
explicitly recognized by these rules become `ProjectionIssue`; programming
errors propagate.

- [ ] **Step 5: Add the full projection-law corpus**

Append:

```python
class ProjectionLawTests(unittest.TestCase):
    def test_every_trace_prefix_is_pure_deterministic_and_round_trip_rebuildable(self):
        readable_defect = append_record(EMPTY_FACTS, "invocation_began")
        readable_defect = append_record(
            readable_defect,
            "effect_completion_evidence_observed",
            associations={"effect_id": "missing-effect"},
            payload={"conclusion": "completed", "evidence": "orphan receipt"},
        )
        readable_defect = append_record(
            readable_defect,
            "operation_began",
            associations={"operation_id": "valid-operation"},
            payload={"operation_kind": "inference"},
        )
        traces = (
            ordinary_trace(),
            streaming_trace(),
            effect_mixed_trace(),
            late_knowledge_trace(),
            readable_defect,
        )

        for trace_index, facts in enumerate(traces):
            for size in range(len(facts) + 1):
                with self.subTest(trace=trace_index, size=size):
                    prefix = facts[:size]
                    snapshot = tuple(prefix)
                    first = project(prefix)
                    second = project(prefix)
                    rebuilt = project(decode_facts(encode_facts(prefix)))

                    self.assertEqual(first.covered_prefix, size)
                    self.assertEqual(first, second)
                    self.assertEqual(first, rebuilt)
                    self.assertEqual(prefix, snapshot)

    def test_projection_and_issues_are_disposable_and_never_feed_history(self):
        facts = late_knowledge_trace()
        before = read_facts(facts)
        projection_1 = project(facts)
        del projection_1
        projection_2 = project(facts)

        self.assertIs(read_facts(facts), before)
        self.assertEqual(projection_2, project(facts))
        self.assertEqual(read_facts(facts), facts)
```

- [ ] **Step 6: Run the focused suite and verify it passes**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_invocation_fact_kernel.py" -v
```

Expected: 29 tests pass with zero failures or errors.

- [ ] **Step 7: Commit the complete experimental laws**

Run:

```powershell
git add experiments/invocation_fact_kernel.py tests/test_invocation_fact_kernel.py
git commit -m "experiment: enforce conservative fact projection laws"
```

---

### Task 7: Full Offline Regression and Scope Audit

**Files:**
- Verify only: `experiments/__init__.py`
- Verify only: `experiments/invocation_fact_kernel.py`
- Verify only: `tests/test_invocation_fact_kernel.py`
- Verify unchanged: `simpleaichat/`, existing tests, prior Run artifacts

**Interfaces:**
- Consumes: completed Run 011 experiment and all inherited tests.
- Produces: fresh evidence that the experiment passes offline and remains isolated.

- [ ] **Step 1: Run the complete test suite with non-loopback networking blocked**

Run from PowerShell:

```powershell
@'
import ipaddress
import socket
import sys
import unittest

suite = unittest.defaultTestLoader.discover('tests')

_real_socket = socket.socket
_real_create_connection = socket.create_connection
_real_getaddrinfo = socket.getaddrinfo


def _allow_host(host):
    if host in {'localhost', 'localhost.localdomain'}:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _check_address(address):
    if isinstance(address, tuple) and address:
        host = address[0]
        if isinstance(host, bytes):
            host = host.decode('ascii')
        if _allow_host(host):
            return
    raise AssertionError(f'network access blocked by offline test guard: {address!r}')


class OfflineSocket(_real_socket):
    def connect(self, address):
        _check_address(address)
        return super().connect(address)

    def connect_ex(self, address):
        _check_address(address)
        return super().connect_ex(address)


def offline_create_connection(address, *args, **kwargs):
    _check_address(address)
    return _real_create_connection(address, *args, **kwargs)


def offline_getaddrinfo(host, *args, **kwargs):
    if isinstance(host, bytes):
        host = host.decode('ascii')
    if not _allow_host(host):
        raise AssertionError(f'network access blocked by offline test guard: {host!r}')
    return _real_getaddrinfo(host, *args, **kwargs)


socket.socket = OfflineSocket
socket.create_connection = offline_create_connection
socket.getaddrinfo = offline_getaddrinfo

result = unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(0 if result.wasSuccessful() else 1)
'@ | .\.venv\Scripts\python.exe -
```

Expected: all 102 tests pass (73 inherited plus 29 Run 011); zero network-guard assertions occur.

- [ ] **Step 2: Verify production isolation and exact changed-file scope**

Run:

```powershell
git status --short
git diff --name-only 28cf161bb88b42fbe594682ca0e31a7f22f69dc7 HEAD -- simpleaichat tests experiments
rg -n "simpleaichat|dspy|txtai|textual|sqlite|httpx" experiments tests/test_invocation_fact_kernel.py
```

Expected implementation scope:

```text
experiments/__init__.py
experiments/invocation_fact_kernel.py
tests/test_invocation_fact_kernel.py
```

The `rg` command may find the word `simpleaichat` only in a negative isolation
assertion if one is added; it must find no imports of prohibited packages.

- [ ] **Step 3: Recheck frozen documentation and inherited test hashes**

Run:

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath `
  'docs/run-009-ars-execution-semantics-derivation.md',`
  'docs/run-010-invocation-workload-and-representation-constraints.md',`
  'docs/run-011-minimal-invocation-fact-kernel-design.md',`
  'tests/test_message_seams.py',`
  'tests/test_models_characterization.py',`
  'tests/test_provider_lowering_characterization.py',`
  'tests/test_request_assembly_seam.py',`
  'tests/test_streaming_lifecycle_characterization.py',`
  'tests/test_tool_effect_lifecycle_characterization.py',`
  'tests/test_transport_seam.py'
```

Expected Run artifact hashes are the composite values in **Global Constraints**.
Expected inherited test hashes are:

```text
test_message_seams.py                          7BBF9F24E3EB6277EAED88C4EB0FEE0D5ACCDC080EBB3A116CD64E6CABB8D6A1
test_models_characterization.py                605CF0EA043B9944D2284346457D4AC46D5BECF9C206CC5F97E7CFBD4623046C
test_provider_lowering_characterization.py     37F5D5AF36321A430EF5283F16021A4F08ED5B62089630434A6D96F2F17B7B62
test_request_assembly_seam.py                   B44F4D841825B13E23A276A1F663B5AED67A8008A590459BF97EEEE60DE64AD7
test_streaming_lifecycle_characterization.py   519DCE501607BB686FA49D7D5275B94AD8634A2D7E0F4F4EC34F3701B26CA922
test_tool_effect_lifecycle_characterization.py 0AE4AD1E46618C019B7655F56F53DA4C1C4DDF73A2D47D9311D262F0B368C5ED
test_transport_seam.py                         2CBC1C0B0155E2196D667492B1BD668844C1056CD664274E96D314984C4E508C
```

- [ ] **Step 4: Audit the Run 011 falsification conditions explicitly**

Record a pass/fail result for every item:

```text
[ ] Facts unchanged by project
[ ] Old facts unchanged by append
[ ] Old projection unchanged after append
[ ] Projection independent of previous view
[ ] Encode/decode projection equivalence
[ ] Every prefix, including zero, projects
[ ] Issues never reduce covered_prefix
[ ] Unknown is valid and issue-free
[ ] Unsupported references synthesize nothing
[ ] Contradictions never use append order as precedence
[ ] Later referents add no causal or temporal meaning
[ ] Late knowledge refines completion after termination
[ ] Parent and subordinate outcomes remain independent
[ ] No prohibited dependency or production import exists
```

Any failure stops Run 011. Fix the mechanism or report that Candidate D was not
faithfully realized; do not weaken the assertion or alter the approved design.

- [ ] **Step 5: Commit only if the final audit required a corrective implementation change**

If no corrective change was needed, do not create an empty commit. If a correction
was needed and all verification is fresh:

```powershell
git add experiments/invocation_fact_kernel.py tests/test_invocation_fact_kernel.py
git commit -m "test: complete invocation kernel verification"
```

## Run 011 Completion Boundary

Stop after the offline test and scope evidence is recorded. Do not begin Run 012,
promote experimental names, move code into a production package, add durable
storage, or connect a provider/model runtime.

The completed experiment must establish only:

```text
readable authoritative facts
        |
        v
pure total conservative projection
        |
        +--> maximal supported current view
        +--> deterministic issues
        `--> covered_prefix == len(facts)
```

That is the entire Run 011 implementation target.
