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
        fact(kind, len(facts) + 1, associations=associations, payload=payload),
    )


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


if __name__ == "__main__":
    unittest.main()
