"""Run 003 tests for the history-selection and provider-lowering seams."""

import unittest
from unittest.mock import patch

import simpleaichat.models as models
from simpleaichat.models import ChatMessage, ChatSession


def messages_with_contents(*contents: str):
    return [ChatMessage(role="user", content=content) for content in contents]


class HistorySelectionSeamTests(unittest.TestCase):
    def selector(self):
        selector = getattr(models, "select_history", None)
        self.assertIsNotNone(selector, "select_history() has not been extracted")
        return selector

    def test_none_and_zero_return_the_original_history_list(self):
        history = messages_with_contents("first", "second", "third")

        for recent_messages in (None, 0):
            with self.subTest(recent_messages=recent_messages):
                selected = self.selector()(history, recent_messages)

                self.assertIs(selected, history)

    def test_positive_and_negative_limits_preserve_python_slicing(self):
        history = messages_with_contents("first", "second", "third", "fourth")
        cases = (
            (2, [history[2], history[3]]),
            (10, list(history)),
            (-1, [history[1], history[2], history[3]]),
            (-2, [history[2], history[3]]),
        )

        for recent_messages, expected in cases:
            with self.subTest(recent_messages=recent_messages):
                selected = self.selector()(history, recent_messages)

                self.assertEqual(selected, expected)
                self.assertTrue(
                    all(actual is wanted for actual, wanted in zip(selected, expected))
                )

    def test_selection_does_not_serialize_messages(self):
        history = messages_with_contents("first", "second", "third")

        with patch.object(
            ChatMessage,
            "model_dump",
            side_effect=AssertionError("history selection serialized a message"),
        ):
            selected = self.selector()(history, 2)

        self.assertIs(selected[0], history[1])
        self.assertIs(selected[1], history[2])


class ProviderLoweringSeamTests(unittest.TestCase):
    def lowerer(self):
        lowerer = getattr(models, "lower_messages", None)
        self.assertIsNotNone(lowerer, "lower_messages() has not been extracted")
        return lowerer

    def test_lowering_orders_explicit_inputs_and_filters_each_message(self):
        system = ChatMessage(role="system", content="instructions")
        history = [
            ChatMessage(role="user", content="earlier"),
            ChatMessage(
                role="assistant",
                content="answer",
                name="legacy-tool",
                function_call="legacy-call",
                finish_reason="stop",
                total_length=12,
            ),
        ]
        current = ChatMessage(
            role="function",
            content='{"value":7}',
            name="SchemaInput",
        )

        lowered = self.lowerer()(
            system,
            history,
            current,
            {"role", "content", "name"},
        )

        self.assertEqual(
            lowered,
            [
                {"role": "system", "content": "instructions"},
                {"role": "user", "content": "earlier"},
                {
                    "role": "assistant",
                    "content": "answer",
                    "name": "legacy-tool",
                },
                {
                    "role": "function",
                    "content": '{"value":7}',
                    "name": "SchemaInput",
                },
            ],
        )

    def test_empty_input_fields_preserve_one_mapping_per_explicit_message(self):
        system = ChatMessage(role="system", content="instructions")
        history = [ChatMessage(role="assistant", content="earlier")]
        current = ChatMessage(role="user", content="current")

        lowered = self.lowerer()(system, history, current, {})

        self.assertEqual(lowered, [{}, {}, {}])

    def test_lowering_does_not_mutate_explicit_inputs(self):
        system = ChatMessage(role="system", content="instructions")
        history = [ChatMessage(role="assistant", content="earlier")]
        current = ChatMessage(role="user", content="current")
        input_fields = {"role", "content"}
        original_messages = [
            system.model_dump(),
            history[0].model_dump(),
            current.model_dump(),
        ]
        original_input_fields = set(input_fields)

        self.lowerer()(system, history, current, input_fields)

        self.assertEqual(
            [
                system.model_dump(),
                history[0].model_dump(),
                current.model_dump(),
            ],
            original_messages,
        )
        self.assertEqual(input_fields, original_input_fields)


class CompatibilityWrapperTests(unittest.TestCase):
    def test_format_input_messages_passes_session_state_through_both_seams(self):
        session = ChatSession(
            auth={"api_key": "test-key"},
            api_url="https://example.test/v1/chat",
            model="specimen-model",
            system="specimen system",
            messages=messages_with_contents("first", "second"),
            input_fields={"role", "content"},
            recent_messages=1,
        )
        system = ChatMessage(role="system", content="instructions")
        current = ChatMessage(role="user", content="current")
        selected_history = [session.messages[1]]
        lowered_messages = [{"delegated": True}]
        observed = {}

        def fake_select_history(messages, recent_messages):
            observed["selection"] = (messages, recent_messages)
            return selected_history

        def fake_lower_messages(
            system_message,
            history,
            current_message,
            input_fields,
        ):
            observed["lowering"] = (
                system_message,
                history,
                current_message,
                input_fields,
            )
            return lowered_messages

        with patch.object(models, "select_history", new=fake_select_history), patch.object(
            models,
            "lower_messages",
            new=fake_lower_messages,
        ):
            result = session.format_input_messages(system, current)

        self.assertIs(result, lowered_messages)
        self.assertIs(observed["selection"][0], session.messages)
        self.assertEqual(observed["selection"][1], session.recent_messages)
        self.assertIs(observed["lowering"][0], system)
        self.assertIs(observed["lowering"][1], selected_history)
        self.assertIs(observed["lowering"][2], current)
        self.assertIs(observed["lowering"][3], session.input_fields)


if __name__ == "__main__":
    unittest.main()
