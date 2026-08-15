"""Run 011: isolated immutable fact and projection experiment."""

from dataclasses import dataclass
import json
from typing import Any, Callable, Dict, Mapping, Optional, Tuple, Union


FactScalar = Union[str, int]
FactItems = Tuple[Tuple[str, FactScalar], ...]


class FactConstructionError(ValueError):
    """A single fact representation is not structurally readable."""


class FactSequenceError(ValueError):
    """A fact tuple violates authoritative sequence structure."""


class FactDecodeError(ValueError):
    """Encoded bytes cannot produce a structurally readable sequence."""


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
        ("operation_id",), (), (("operation_kind", _one_of("inference", "stream", "effect")),)
    ),
    "observation_recorded": _KindSchema(
        ("operation_id",), (), (("observation_kind", _one_of("result", "error")), ("value", _is_string))
    ),
    "manifestation_recorded": _KindSchema(("producer_operation_id",), (), (("content", _is_string),)),
    "accounting_observed": _KindSchema(
        ("operation_id",), (), (("metric", _one_of("input_tokens", "output_tokens")), ("amount", _is_nonnegative_integer))
    ),
    "effect_authorized": _KindSchema(("effect_id",), (), (("basis", _is_string),)),
    "effect_attempted": _KindSchema(("effect_id",), ("operation_id",), ()),
    "effect_completion_evidence_observed": _KindSchema(
        ("effect_id",), (), (("conclusion", _one_of("completed", "not_completed")), ("evidence", _is_string))
    ),
    "operation_terminated": _KindSchema(("operation_id",), (), (("outcome", _one_of("completed", "failed")),)),
    "acceptance_decided": _KindSchema((), (), (("decision", _one_of("accepted", "rejected")), ("basis", _is_string))),
    "invocation_terminated": _KindSchema((), (), (("outcome", _one_of("completed", "failed")),)),
}


def _canonical_items(values: Optional[Mapping[str, FactScalar]], label: str) -> FactItems:
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
    return dict(items)


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
    if not isinstance(fact.local_position, int) or isinstance(fact.local_position, bool) or fact.local_position < 1:
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


def make_fact(*, kind: str, invocation_id: str, local_position: int, associations: Optional[Mapping[str, FactScalar]] = None, payload: Optional[Mapping[str, FactScalar]] = None) -> Fact:
    return Fact(kind=kind, invocation_id=invocation_id, local_position=local_position, associations=_canonical_items(associations, "associations"), payload=_canonical_items(payload, "payload"))


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
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _decode_document(data: bytes) -> Dict[str, Any]:
    if not isinstance(data, bytes):
        raise FactDecodeError("encoded facts must be bytes")
    try:
        document = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as error:
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
            if not isinstance(raw_fact["associations"], dict) or not isinstance(
                raw_fact["payload"], dict
            ):
                raise FactDecodeError("encoded fact mappings must be JSON objects")
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


def _values(facts: FactSequence, kind: str) -> Tuple[Fact, ...]:
    return tuple(item for item in facts if item.kind == kind)


def _association(fact: Fact, key: str) -> Optional[str]:
    value = dict(fact.associations).get(key)
    return value if isinstance(value, str) else None


def _payload(fact: Fact, key: str) -> FactScalar:
    return dict(fact.payload)[key]


def _issue_sort_key(issue: ProjectionIssue):
    first = issue.fact_positions[0] if issue.fact_positions else 0
    return (first, issue.code, issue.subject_id or "", issue.fact_positions)


def _conclusion(facts: Tuple[Fact, ...], payload_key: str, conflict_code: str, subject_id: Optional[str]):
    values = {_payload(item, payload_key) for item in facts}
    if not values:
        return None, ()
    if len(values) == 1:
        return next(iter(values)), ()
    positions = tuple(item.local_position for item in facts)
    return "conflicted", (ProjectionIssue(conflict_code, positions, subject_id),)


def project(facts: FactSequence) -> Projection:
    _validate_fact_sequence(facts)
    invocation_id = facts[0].invocation_id if facts else None
    issues = []
    began = _values(facts, "invocation_began")
    if facts and not began:
        issues.append(ProjectionIssue("missing_invocation_begin", (facts[0].local_position,), invocation_id))

    operation_begins = _values(facts, "operation_began")
    operation_ids = sorted({_association(item, "operation_id") for item in operation_begins})
    operation_ids_set = set(operation_ids)
    operations = []
    for operation_id in operation_ids:
        begins = tuple(item for item in operation_begins if _association(item, "operation_id") == operation_id)
        kind, kind_issues = _conclusion(begins, "operation_kind", "conflicting_operation_kind", operation_id)
        issues.extend(kind_issues)
        terminations = tuple(item for item in _values(facts, "operation_terminated") if _association(item, "operation_id") == operation_id)
        outcome, outcome_issues = _conclusion(terminations, "outcome", "conflicting_operation_outcome", operation_id)
        issues.extend(outcome_issues)
        operations.append(OperationView(operation_id, kind, "terminated" if terminations else "active", outcome))

    observations = []
    for item in _values(facts, "observation_recorded"):
        operation_id = _association(item, "operation_id")
        if operation_id not in operation_ids_set:
            issues.append(ProjectionIssue("unsupported_operation", (item.local_position,), operation_id))
        else:
            observations.append(ObservationView(item.local_position, operation_id, _payload(item, "observation_kind"), _payload(item, "value")))

    accounting = []
    for item in _values(facts, "accounting_observed"):
        operation_id = _association(item, "operation_id")
        if operation_id not in operation_ids_set:
            issues.append(ProjectionIssue("unsupported_operation", (item.local_position,), operation_id))
        else:
            accounting.append(AccountingView(item.local_position, operation_id, _payload(item, "metric"), _payload(item, "amount")))

    for item in _values(facts, "operation_terminated"):
        operation_id = _association(item, "operation_id")
        if operation_id not in operation_ids_set:
            issues.append(ProjectionIssue("unsupported_operation", (item.local_position,), operation_id))

    manifestations = []
    for item in _values(facts, "manifestation_recorded"):
        producer_operation_id = _association(item, "producer_operation_id")
        if producer_operation_id not in operation_ids_set:
            issues.append(
                ProjectionIssue(
                    "unsupported_producer_operation",
                    (item.local_position,),
                    producer_operation_id,
                )
            )
        else:
            manifestations.append(
                ManifestationView(
                    item.local_position,
                    producer_operation_id,
                    _payload(item, "content"),
                )
            )

    acceptance_value, acceptance_issues = _conclusion(_values(facts, "acceptance_decided"), "decision", "conflicting_acceptance", None)
    issues.extend(acceptance_issues)
    invocation_outcome, invocation_issues = _conclusion(_values(facts, "invocation_terminated"), "outcome", "conflicting_invocation_outcome", invocation_id)
    issues.extend(invocation_issues)
    lifecycle = "terminated" if began and _values(facts, "invocation_terminated") else ("active" if began else "absent")
    return Projection(
        covered_prefix=len(facts),
        invocation_id=invocation_id,
        invocation_lifecycle=lifecycle,
        invocation_outcome=invocation_outcome,
        operations=tuple(operations),
        observations=tuple(observations),
        manifestations=tuple(manifestations),
        accounting=tuple(accounting),
        effects=(),
        acceptance=acceptance_value or "undecided",
        issues=tuple(sorted(issues, key=_issue_sort_key)),
    )
