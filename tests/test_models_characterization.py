"""Run 001 characterizations for the inherited message and session models."""

import datetime
import unittest
from uuid import UUID

from simpleaichat.models import ChatMessage, ChatSession


FIXED_TIME = datetime.datetime(2024, 1, 2, 3, 4, 5, tzinfo=datetime.timezone.utc)


def make_session(**overrides) -> ChatSession:
    values = {
        "auth": {"api_key": "test-key"},
        "api_url": "https://example.test/v1/chat",
        "model": "specimen-model",
        "system": "specimen system",
    }
    values.update(overrides)
    return ChatSession(**values)


class ChatMessageCharacterizationTests(unittest.TestCase):
    def test_defaults_leave_optional_provider_and_runtime_fields_unset(self):
        before = datetime.datetime.now(datetime.timezone.utc)
        message = ChatMessage(role="user", content="hello")
        after = datetime.datetime.now(datetime.timezone.utc)

        self.assertEqual(message.role, "user")
        self.assertEqual(message.content, "hello")
        self.assertIsNone(message.name)
        self.assertIsNone(message.function_call)
        self.assertIsNone(message.finish_reason)
        self.assertIsNone(message.prompt_length)
        self.assertIsNone(message.completion_length)
        self.assertIsNone(message.total_length)
        self.assertEqual(message.received_at.tzinfo, datetime.timezone.utc)
        self.assertLessEqual(before, message.received_at)
        self.assertLessEqual(message.received_at, after)

    def test_model_dump_keeps_provider_data_runtime_metadata_and_accounting_together(self):
        message = ChatMessage(
            role="assistant",
            content="answer",
            name="legacy-tool",
            function_call="legacy-call",
            received_at=FIXED_TIME,
            finish_reason="stop",
            prompt_length=11,
            completion_length=7,
            total_length=18,
        )

        self.assertEqual(
            message.model_dump(),
            {
                "role": "assistant",
                "content": "answer",
                "name": "legacy-tool",
                "function_call": "legacy-call",
                "received_at": FIXED_TIME,
                "finish_reason": "stop",
                "prompt_length": 11,
                "completion_length": 7,
                "total_length": 18,
            },
        )

    def test_exclude_none_serialization_retains_the_runtime_timestamp(self):
        message = ChatMessage(role="user", content="hello", received_at=FIXED_TIME)

        self.assertEqual(
            message.model_dump(exclude_none=True),
            {
                "role": "user",
                "content": "hello",
                "received_at": FIXED_TIME,
            },
        )


class ChatSessionCharacterizationTests(unittest.TestCase):
    def test_defaults_create_empty_history_and_zero_accounting(self):
        session = make_session()

        self.assertIsInstance(session.id, UUID)
        self.assertEqual(session.created_at.tzinfo, datetime.timezone.utc)
        self.assertEqual(session.params, {})
        self.assertEqual(session.messages, [])
        self.assertIsInstance(session.input_fields, dict)
        self.assertEqual(session.input_fields, {})
        self.assertIsNone(session.recent_messages)
        self.assertIs(session.save_messages, True)
        self.assertEqual(session.total_prompt_length, 0)
        self.assertEqual(session.total_completion_length, 0)
        self.assertEqual(session.total_length, 0)
        self.assertIsNone(session.title)

    def test_mutable_defaults_are_isolated_between_sessions(self):
        first = make_session()
        second = make_session()

        first.params["temperature"] = 0.2
        first.input_fields["role"] = True
        first.messages.append(ChatMessage(role="user", content="first"))

        self.assertNotEqual(first.id, second.id)
        self.assertEqual(second.params, {})
        self.assertEqual(second.input_fields, {})
        self.assertEqual(second.messages, [])

    def test_add_messages_uses_session_default_unless_a_boolean_override_is_given(self):
        cases = (
            (True, None, ["question", "answer"]),
            (False, None, []),
            (True, False, []),
            (False, True, ["question", "answer"]),
        )

        for session_default, call_override, expected_contents in cases:
            with self.subTest(
                session_default=session_default, call_override=call_override
            ):
                session = make_session(save_messages=session_default)
                user = ChatMessage(role="user", content="question")
                assistant = ChatMessage(role="assistant", content="answer")

                session.add_messages(user, assistant, call_override)

                self.assertEqual(
                    [message.content for message in session.messages],
                    expected_contents,
                )

    def test_recent_history_is_selected_before_provider_lowering(self):
        session = make_session(
            input_fields={"role", "content", "name"},
            recent_messages=2,
            messages=[
                ChatMessage(role="user", content="oldest", received_at=FIXED_TIME),
                ChatMessage(
                    role="assistant",
                    content="middle",
                    name="legacy-tool",
                    function_call="legacy-call",
                    received_at=FIXED_TIME,
                    finish_reason="stop",
                    total_length=12,
                ),
                ChatMessage(role="user", content="newest", received_at=FIXED_TIME),
            ],
        )
        system = ChatMessage(role="system", content="system", received_at=FIXED_TIME)
        current = ChatMessage(role="user", content="current", received_at=FIXED_TIME)

        lowered = session.format_input_messages(system, current)

        self.assertEqual(
            lowered,
            [
                {"role": "system", "content": "system"},
                {
                    "role": "assistant",
                    "content": "middle",
                    "name": "legacy-tool",
                },
                {"role": "user", "content": "newest"},
                {"role": "user", "content": "current"},
            ],
        )
        self.assertEqual(
            [message.content for message in session.messages],
            ["oldest", "middle", "newest"],
        )

    def test_none_and_zero_recent_messages_both_keep_all_history(self):
        for recent_messages in (None, 0):
            with self.subTest(recent_messages=recent_messages):
                session = make_session(
                    input_fields={"role", "content"},
                    recent_messages=recent_messages,
                    messages=[
                        ChatMessage(role="user", content="first"),
                        ChatMessage(role="assistant", content="second"),
                    ],
                )
                system = ChatMessage(role="system", content="system")
                current = ChatMessage(role="user", content="current")

                lowered = session.format_input_messages(system, current)

                self.assertEqual(
                    lowered,
                    [
                        {"role": "system", "content": "system"},
                        {"role": "user", "content": "first"},
                        {"role": "assistant", "content": "second"},
                        {"role": "user", "content": "current"},
                    ],
                )

    def test_empty_input_fields_lower_every_message_to_an_empty_mapping(self):
        session = make_session(messages=[ChatMessage(role="assistant", content="past")])
        system = ChatMessage(role="system", content="system")
        current = ChatMessage(role="user", content="current")

        self.assertEqual(
            session.format_input_messages(system, current),
            [{}, {}, {}],
        )


if __name__ == "__main__":
    unittest.main()
