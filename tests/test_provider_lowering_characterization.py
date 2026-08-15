"""Run 001 characterizations for the inherited OpenAI request lowering path."""

import datetime
import unittest

from pydantic import BaseModel

from simpleaichat.chatgpt import ChatGPTSession
from simpleaichat.models import ChatMessage


FIXED_TIME = datetime.datetime(2024, 1, 2, 3, 4, 5, tzinfo=datetime.timezone.utc)


class SchemaInput(BaseModel):
    """A characterized schema input."""

    value: int


class SchemaOutput(BaseModel):
    """A characterized schema output."""

    result: str


def make_session(**overrides) -> ChatGPTSession:
    values = {
        "auth": {"api_key": "test-key"},
        "model": "specimen-model",
    }
    values.update(overrides)
    return ChatGPTSession(**values)


class PrepareRequestCharacterizationTests(unittest.TestCase):
    def test_plain_input_builds_default_system_and_current_user_messages(self):
        session = make_session()

        _headers, request, current = session.prepare_request("current question")

        self.assertEqual(current.role, "user")
        self.assertEqual(current.content, "current question")
        self.assertEqual(
            request,
            {
                "model": "specimen-model",
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "current question"},
                ],
                "stream": False,
                "temperature": 0.7,
            },
        )
        self.assertEqual(session.messages, [])

    def test_provider_order_is_system_selected_history_then_current_input(self):
        session = make_session(
            recent_messages=1,
            messages=[
                ChatMessage(role="user", content="discarded", received_at=FIXED_TIME),
                ChatMessage(
                    role="assistant",
                    content="retained",
                    name="legacy-tool",
                    function_call="legacy-call",
                    received_at=FIXED_TIME,
                    finish_reason="stop",
                    prompt_length=5,
                    completion_length=7,
                    total_length=12,
                ),
            ],
        )

        _headers, request, _current = session.prepare_request(
            "current",
            system="override system",
            stream=True,
        )

        self.assertEqual(
            request["messages"],
            [
                {"role": "system", "content": "override system"},
                {
                    "role": "assistant",
                    "content": "retained",
                    "name": "legacy-tool",
                },
                {"role": "user", "content": "current"},
            ],
        )
        self.assertIs(request["stream"], True)
        self.assertEqual(
            [message.content for message in session.messages],
            ["discarded", "retained"],
        )

    def test_none_and_empty_params_use_session_defaults_while_nonempty_params_replace_them(self):
        session = make_session(params={"temperature": 0.2, "top_p": 0.9})

        for supplied in (None, {}):
            with self.subTest(supplied=supplied):
                _headers, request, _current = session.prepare_request(
                    "question", params=supplied
                )
                self.assertEqual(request["temperature"], 0.2)
                self.assertEqual(request["top_p"], 0.9)

        _headers, overridden, _current = session.prepare_request(
            "question", params={"max_tokens": 17}
        )
        self.assertEqual(overridden["max_tokens"], 17)
        self.assertNotIn("temperature", overridden)
        self.assertNotIn("top_p", overridden)

    def test_schema_input_and_output_lower_to_function_message_and_metadata(self):
        session = make_session()
        prompt = SchemaInput(value=7)

        _headers, request, current = session.prepare_request(
            prompt,
            input_schema=SchemaInput,
            output_schema=SchemaOutput,
        )

        self.assertEqual(current.role, "function")
        self.assertEqual(current.content, '{"value":7}')
        self.assertEqual(current.name, "SchemaInput")
        self.assertEqual(
            request["messages"],
            [
                {"role": "system", "content": "You are a helpful assistant."},
                {
                    "role": "function",
                    "content": '{"value":7}',
                    "name": "SchemaInput",
                },
            ],
        )
        self.assertEqual(
            request["functions"],
            [
                {
                    "name": "SchemaInput",
                    "description": "A characterized schema input.",
                    "parameters": {
                        "description": "A characterized schema input.",
                        "properties": {"value": {"type": "integer"}},
                        "required": ["value"],
                        "type": "object",
                    },
                },
                {
                    "name": "SchemaOutput",
                    "description": "A characterized schema output.",
                    "parameters": {
                        "description": "A characterized schema output.",
                        "properties": {"result": {"type": "string"}},
                        "required": ["result"],
                        "type": "object",
                    },
                },
            ],
        )
        self.assertEqual(request["function_call"], {"name": "SchemaOutput"})

    def test_output_function_metadata_remains_when_forced_selection_is_disabled(self):
        session = make_session()

        _headers, request, _current = session.prepare_request(
            "question",
            output_schema=SchemaOutput,
            is_function_calling_required=False,
        )

        self.assertNotIn("function_call", request)
        self.assertEqual(
            request["functions"],
            [
                {
                    "name": "SchemaOutput",
                    "description": "A characterized schema output.",
                    "parameters": {
                        "description": "A characterized schema output.",
                        "properties": {"result": {"type": "string"}},
                        "required": ["result"],
                        "type": "object",
                    },
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
