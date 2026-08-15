"""Executable tests for the isolated Run 011 fact/projection kernel."""

from dataclasses import FrozenInstanceError
import unittest

from experiments.invocation_fact_kernel import (
    EMPTY_FACTS,
    FactConstructionError,
    FactDecodeError,
    FactSequenceError,
    append_fact,
    decode_facts,
    encode_facts,
    make_fact,
    Projection,
    ProjectionIssue,
    project,
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
        fact(kind, len(facts) + 1, associations=associations, payload=payload),
    )


def ordinary_trace():
    facts = append_record(EMPTY_FACTS, "invocation_began")
    facts = append_record(facts, "operation_began", associations={"operation_id": "inference-1"}, payload={"operation_kind": "inference"})
    facts = append_record(facts, "observation_recorded", associations={"operation_id": "inference-1"}, payload={"observation_kind": "result", "value": "answer"})
    facts = append_record(facts, "accounting_observed", associations={"operation_id": "inference-1"}, payload={"metric": "input_tokens", "amount": 4})
    facts = append_record(facts, "operation_terminated", associations={"operation_id": "inference-1"}, payload={"outcome": "completed"})
    facts = append_record(facts, "acceptance_decided", payload={"decision": "accepted", "basis": "test requirement"})
    return append_record(facts, "invocation_terminated", payload={"outcome": "completed"})


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


class OrdinaryProjectionTests(unittest.TestCase):
    def test_every_ordinary_prefix_preserves_independent_state(self):
        facts = ordinary_trace()
        projections = tuple(project(facts[:size]) for size in range(len(facts) + 1))
        self.assertEqual(tuple(item.covered_prefix for item in projections), tuple(range(8)))
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


class EffectProjectionTests(unittest.TestCase):
    def test_every_effectful_prefix_preserves_independent_outcomes(self):
        facts = effect_mixed_trace()
        projections = tuple(project(facts[:size]) for size in range(len(facts) + 1))
        self.assertEqual(tuple(item.covered_prefix for item in projections), tuple(range(14)))
        completion_by_prefix = tuple(item.effects[0].completion_knowledge if item.effects else "absent" for item in projections)
        self.assertEqual(completion_by_prefix, ("absent", "absent", "absent", "absent", "absent", "absent", None, None, "unknown", "known_completed", "known_completed", "known_completed", "known_completed", "known_completed"))
        self.assertEqual(projections[5].accounting[0].amount, 3)
        self.assertEqual(projections[6].effects[0].authorization_knowledge, "observed_authorized")
        self.assertEqual(projections[6].effects[0].attempt_knowledge, "not_observed")
        self.assertEqual(projections[8].effects[0].attempt_knowledge, "observed_attempted")
        self.assertEqual(projections[8].effects[0].completion_knowledge, "unknown")
        self.assertEqual(projections[9].effects[0].completion_knowledge, "known_completed")
        effect_operation = next(operation for operation in projections[10].operations if operation.operation_id == "effect-op")
        continuation = next(operation for operation in projections[12].operations if operation.operation_id == "continuation")
        self.assertEqual(effect_operation.outcome, "completed")
        self.assertEqual(continuation.outcome, "failed")
        self.assertEqual(projections[12].effects[0].completion_knowledge, "known_completed")
        self.assertEqual(projections[13].invocation_outcome, "failed")
        self.assertEqual(projections[13].effects[0].completion_knowledge, "known_completed")
        self.assertTrue(all(not item.issues for item in projections))

    def test_late_fact_refines_knowledge_without_mutating_terminated_prefix(self):
        complete = late_knowledge_trace()
        projections = tuple(project(complete[:size]) for size in range(len(complete) + 1))
        self.assertEqual(tuple(item.effects[0].completion_knowledge if item.effects else "absent" for item in projections), ("absent", "absent", "absent", None, "unknown", "unknown", "unknown", "known_completed"))
        self.assertEqual(tuple(item.covered_prefix for item in projections), tuple(range(8)))
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


class FactConstructionTests(unittest.TestCase):
    def test_fact_is_frozen_and_canonical(self):
        recorded = fact("operation_began", 1, associations={"operation_id": "op-a"}, payload={"operation_kind": "inference"})
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
            fact("operation_began", 1, associations={"operation_id": "op-a", "extra": "x"}, payload={"operation_kind": "inference"})
        with self.assertRaises(FactConstructionError):
            fact("accounting_observed", 1, associations={"operation_id": "op-a"}, payload={"metric": "input_tokens", "amount": True})

    def test_missing_referent_is_not_a_construction_error(self):
        recorded = fact("effect_completion_evidence_observed", 1, associations={"effect_id": "missing-effect"}, payload={"conclusion": "completed", "evidence": "receipt"})
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
        facts_2 = append_record(facts_1, "operation_began", associations={"operation_id": "op-a"}, payload={"operation_kind": "inference"})
        self.assertEqual(facts_1, facts_2[:-1])
        self.assertEqual(len(facts_1), 1)
        self.assertEqual(facts_2[-1].local_position, 2)

    def test_append_rejects_noncontiguous_position_and_mixed_identity(self):
        facts = append_record(EMPTY_FACTS, "invocation_began")
        with self.assertRaises(FactSequenceError):
            append_fact(facts, fact("invocation_terminated", 3, payload={"outcome": "failed"}))
        with self.assertRaises(FactSequenceError):
            append_fact(facts, fact("invocation_terminated", 2, invocation_id="other-invocation", payload={"outcome": "failed"}))

    def test_read_rejects_manually_assembled_invalid_tuple(self):
        invalid = (fact("invocation_began", 1), fact("invocation_terminated", 3, payload={"outcome": "failed"}))
        with self.assertRaises(FactSequenceError):
            read_facts(invalid)


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

        surrogate_facts = append_fact(
            EMPTY_FACTS,
            fact("invocation_began", 1, invocation_id="\ud800"),
        )
        self.assertEqual(decode_facts(encode_facts(surrogate_facts)), surrogate_facts)

    def test_decode_rejects_invalid_representation(self):
        invalid_documents = (
            b"not json",
            b'{"version":2,"facts":[]}',
            b'{"version":1,"facts":{},"extra":true}',
            b'{"version":1,"facts":[{"kind":"unknown"}]}',
            b'{"version":1,"facts":[{"associations":null,"invocation_id":"inv-011",'
            b'"kind":"invocation_began","local_position":1,"payload":{}}]}',
            b'{"version":1,"facts":[{"associations":{},"invocation_id":"inv-011",'
            b'"kind":"invocation_began","local_position":1,"payload":null}]}',
        )

        for document in invalid_documents:
            with self.subTest(document=document):
                with self.assertRaises(FactDecodeError):
                    decode_facts(document)

        document = (
            b'{"version":1,"facts":[{"associations":{},'
            b'"invocation_id":"inv-011","kind":"invocation_began",'
            b'"local_position":' + b"9" * 5000 + b',"payload":{}}]}'
        )

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


if __name__ == "__main__":
    unittest.main()
