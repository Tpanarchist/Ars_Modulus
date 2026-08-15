import unittest
from unittest.mock import patch

from simpleaichat.chatgpt import ChatGPTSession, tool_prompt
from simpleaichat.models import ChatMessage
from simpleaichat.simpleaichat import AIChat, AsyncAIChat


BASELINE_COMMIT = "29d6cc960d9b3e681a3a4113e78566b10819a249"


class EffectFailure(Exception):
    pass


class ModelFailure(Exception):
    pass


def provider_response(
    content,
    prompt_tokens=1,
    completion_tokens=1,
    total_tokens=2,
    finish_reason="stop",
):
    return {
        "choices": [
            {
                "message": {"role": "assistant", "content": content},
                "finish_reason": finish_reason,
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        },
    }


class FakeDecodedResponse:
    def __init__(self, decoded):
        self.decoded = decoded
        self.json_calls = 0

    def json(self):
        self.json_calls += 1
        return self.decoded


class SequencedClient:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []
        self.responses = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        response = FakeDecodedResponse(outcome)
        self.responses.append(response)
        return response


class SequencedAsyncClient:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []
        self.responses = []

    async def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        response = FakeDecodedResponse(outcome)
        self.responses.append(response)
        return response


class RecordingSyncTool:
    def __init__(self, name, doc, result=None, failure=None, events=None):
        self.__name__ = name
        self.__doc__ = doc
        self.result = result
        self.failure = failure
        self.events = events
        self.calls = []

    def __call__(self, prompt):
        self.calls.append(prompt)
        if self.events is not None:
            self.events.append(("tool", self.__name__, prompt))
        if self.failure is not None:
            raise self.failure
        return self.result


class RecordingAsyncTool:
    def __init__(self, name, doc, result=None, failure=None, events=None):
        self.__name__ = name
        self.__doc__ = doc
        self.result = result
        self.failure = failure
        self.events = events
        self.calls = []

    async def __call__(self, prompt):
        self.calls.append(prompt)
        if self.events is not None:
            self.events.append(("tool", self.__name__, prompt))
        if self.failure is not None:
            raise self.failure
        return self.result


def make_session(**kwargs):
    return ChatGPTSession(
        auth={"api_key": "test-key"},
        model="test-model",
        **kwargs,
    )


def make_seeded_session():
    existing = ChatMessage(role="user", content="existing history")
    session = make_session(
        messages=[existing],
        total_prompt_length=10,
        total_completion_length=20,
        total_length=30,
    )
    return session, existing


def make_facade(facade_type, session, client):
    return facade_type.model_construct(
        client=client,
        default_session=session,
        sessions={session.id: session},
    )


class ToolFacadeContractTests(unittest.TestCase):
    def test_sync_facade_delegates_the_exact_tool_list_and_arguments(self):
        session = make_session()
        client = object()
        chat = make_facade(AIChat, session, client)
        tools = [
            RecordingSyncTool("first", "First tool.", result="first"),
            RecordingSyncTool("second", "Second tool.", result="second"),
        ]
        params = {"temperature": 0.25}
        sentinel = object()
        observed = {}

        def fake_gen_with_tools(
            current_session,
            prompt,
            received_tools,
            client,
            system=None,
            save_messages=None,
            params=None,
        ):
            observed["call"] = (
                current_session,
                prompt,
                received_tools,
                client,
                system,
                save_messages,
                params,
            )
            return sentinel

        with patch.object(
            ChatGPTSession, "gen_with_tools", new=fake_gen_with_tools
        ):
            result = chat(
                "question",
                tools=tools,
                system="custom system",
                save_messages=False,
                params=params,
            )

        self.assertIs(result, sentinel)
        self.assertEqual(observed["call"][0], session)
        self.assertEqual(observed["call"][1], "question")
        self.assertIs(observed["call"][2], tools)
        self.assertIs(observed["call"][3], client)
        self.assertEqual(observed["call"][4], "custom system")
        self.assertIs(observed["call"][5], False)
        self.assertIs(observed["call"][6], params)

    def test_sync_facade_guards_truthy_tool_workflows(self):
        session = make_session()
        chat = make_facade(AIChat, session, object())
        documented = RecordingSyncTool("tool", "A documented tool.")
        undocumented = RecordingSyncTool("tool", None)

        specimens = [
            (
                {"tools": [documented], "input_schema": object()},
                "When using tools, input/output schema are ignored",
            ),
            (
                {"tools": [documented], "output_schema": object()},
                "When using tools, input/output schema are ignored",
            ),
            (
                {"tools": [undocumented]},
                "does not have a docstring",
            ),
            (
                {
                    "tools": [
                        RecordingSyncTool(f"tool_{index}", "Documented.")
                        for index in range(10)
                    ]
                },
                "maximum of 9 tools",
            ),
        ]

        for kwargs, message in specimens:
            with self.subTest(message=message):
                with self.assertRaisesRegex(AssertionError, message):
                    chat("question", **kwargs)

    def test_empty_tool_list_uses_ordinary_generation(self):
        session = make_session()
        client = object()
        chat = make_facade(AIChat, session, client)
        sentinel = object()
        observed = {}

        def fake_gen(current_session, prompt, **kwargs):
            observed["call"] = (current_session, prompt, kwargs)
            return sentinel

        def forbidden_tool_workflow(*args, **kwargs):
            raise AssertionError("empty tools entered the tool workflow")

        with patch.object(ChatGPTSession, "gen", new=fake_gen), patch.object(
            ChatGPTSession,
            "gen_with_tools",
            new=forbidden_tool_workflow,
        ):
            result = chat("question", tools=[])

        self.assertIs(result, sentinel)
        self.assertIs(observed["call"][0], session)
        self.assertEqual(observed["call"][1], "question")
        self.assertIs(observed["call"][2]["client"], client)


class AsyncToolFacadeContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_async_facade_delegates_the_exact_tool_list_and_arguments(self):
        session = make_session()
        client = object()
        chat = make_facade(AsyncAIChat, session, client)
        tools = [RecordingAsyncTool("tool", "Async tool.", result="value")]
        params = {"temperature": 0.25}
        sentinel = object()
        observed = {}

        async def fake_gen_with_tools_async(
            current_session,
            prompt,
            received_tools,
            client,
            system=None,
            save_messages=None,
            params=None,
        ):
            observed["call"] = (
                current_session,
                prompt,
                received_tools,
                client,
                system,
                save_messages,
                params,
            )
            return sentinel

        with patch.object(
            ChatGPTSession,
            "gen_with_tools_async",
            new=fake_gen_with_tools_async,
        ):
            result = await chat(
                "question",
                tools=tools,
                system="custom system",
                save_messages=False,
                params=params,
            )

        self.assertIs(result, sentinel)
        self.assertIs(observed["call"][0], session)
        self.assertEqual(observed["call"][1], "question")
        self.assertIs(observed["call"][2], tools)
        self.assertIs(observed["call"][3], client)
        self.assertEqual(observed["call"][4], "custom system")
        self.assertIs(observed["call"][5], False)
        self.assertIs(observed["call"][6], params)

    async def test_async_facade_repeats_the_tool_guards(self):
        session = make_session()
        chat = make_facade(AsyncAIChat, session, object())
        documented = RecordingAsyncTool("tool", "A documented tool.")
        undocumented = RecordingAsyncTool("tool", None)

        specimens = [
            {"tools": [documented], "input_schema": object()},
            {"tools": [documented], "output_schema": object()},
            {"tools": [undocumented]},
            {
                "tools": [
                    RecordingAsyncTool(f"tool_{index}", "Documented.")
                    for index in range(10)
                ]
            },
        ]

        for kwargs in specimens:
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(AssertionError):
                    await chat("question", **kwargs)


class SyncToolOrchestrationContractTests(unittest.TestCase):
    def test_selection_prompt_projection_and_in_place_result_mutation(self):
        session = make_session()
        client = object()
        params = {"top_p": 0.5}
        result_mapping = {
            "context": {"fact": "model-visible"},
            "private": "not model-visible",
            "tool": "old tool",
            "response": "old response",
        }
        first = RecordingSyncTool("first_tool", "First documentation.")
        second = RecordingSyncTool(
            "second_tool",
            "Second documentation.",
            result=result_mapping,
        )
        tools = [first, second]
        model_outputs = ["2", "final answer"]
        calls = []

        def fake_gen(current_session, prompt, **kwargs):
            calls.append((current_session, prompt, kwargs))
            return model_outputs.pop(0)

        with patch.object(ChatGPTSession, "gen", new=fake_gen):
            result = session.gen_with_tools(
                "original prompt",
                tools,
                client=client,
                system="custom system",
                save_messages=True,
                params=params,
            )

        expected_tools = "1: First documentation.\n2: Second documentation."
        expected_selection_system = tool_prompt.format(tools=expected_tools)
        self.assertEqual(len(calls), 2)
        self.assertIs(calls[0][0], session)
        self.assertEqual(calls[0][1], "original prompt")
        self.assertIs(calls[0][2]["client"], client)
        self.assertEqual(calls[0][2]["system"], expected_selection_system)
        self.assertIs(calls[0][2]["save_messages"], False)
        self.assertEqual(
            calls[0][2]["params"],
            {
                "temperature": 0.0,
                "max_tokens": 1,
                "logit_bias": {"15": 100, "16": 100, "17": 100},
            },
        )

        expected_prompt = (
            "Context: {'fact': 'model-visible'}\n\nUser: original prompt"
        )
        expected_system = (
            "custom system\n\n"
            "You MUST use information from the context in your response."
        )
        self.assertEqual(calls[1][1], expected_prompt)
        self.assertNotIn("private", calls[1][1])
        self.assertNotIn("second_tool", calls[1][1])
        self.assertIs(calls[1][2]["client"], client)
        self.assertEqual(calls[1][2]["system"], expected_system)
        self.assertIs(calls[1][2]["save_messages"], False)
        self.assertIs(calls[1][2]["params"], params)

        self.assertEqual(first.calls, [])
        self.assertEqual(second.calls, ["original prompt"])
        self.assertIs(result, result_mapping)
        self.assertEqual(result_mapping["tool"], "second_tool")
        self.assertEqual(result_mapping["response"], "final answer")
        self.assertEqual(
            [(message.role, message.content) for message in session.messages],
            [("user", "original prompt"), ("assistant", "final answer")],
        )

    def test_string_result_is_wrapped_and_empty_system_uses_session_default(self):
        session = make_session()
        client = object()
        tool = RecordingSyncTool(
            "string_tool",
            "Return a string.",
            result="string context",
        )
        model_outputs = ["1", "answer"]
        calls = []

        def fake_gen(current_session, prompt, **kwargs):
            calls.append((prompt, kwargs))
            return model_outputs.pop(0)

        with patch.object(ChatGPTSession, "gen", new=fake_gen):
            result = session.gen_with_tools(
                "question",
                [tool],
                client=client,
                system="",
                save_messages=False,
            )

        self.assertEqual(
            calls[1][0],
            "Context: string context\n\nUser: question",
        )
        self.assertEqual(
            calls[1][1]["system"],
            session.system
            + "\n\nYou MUST use information from the context in your response.",
        )
        self.assertEqual(
            result,
            {
                "context": "string context",
                "tool": "string_tool",
                "response": "answer",
            },
        )
        self.assertEqual(session.messages, [])

    def test_int_conversion_and_python_negative_indexing_are_preserved(self):
        specimens = [
            (" 2\n", "second_tool"),
            ("-1", "second_tool"),
            ("-2", "first_tool"),
        ]

        for selection, expected_tool in specimens:
            with self.subTest(selection=selection):
                session = make_session()
                tools = [
                    RecordingSyncTool(
                        "first_tool", "First.", result="first context"
                    ),
                    RecordingSyncTool(
                        "second_tool", "Second.", result="second context"
                    ),
                    RecordingSyncTool(
                        "third_tool", "Third.", result="third context"
                    ),
                ]
                outputs = [selection, "answer"]

                def fake_gen(current_session, prompt, **kwargs):
                    return outputs.pop(0)

                with patch.object(ChatGPTSession, "gen", new=fake_gen):
                    result = session.gen_with_tools(
                        "question",
                        tools,
                        client=object(),
                        save_messages=False,
                    )

                self.assertEqual(result["tool"], expected_tool)
                called = [tool.__name__ for tool in tools if tool.calls]
                self.assertEqual(called, [expected_tool])

    def test_direct_session_call_bypasses_docstring_and_count_guards(self):
        session = make_session()
        tools = [
            RecordingSyncTool(f"tool_{index}", None, result="unused")
            for index in range(10)
        ]
        outputs = ["0", "ordinary answer"]
        calls = []

        def fake_gen(current_session, prompt, **kwargs):
            calls.append((prompt, kwargs))
            return outputs.pop(0)

        with patch.object(ChatGPTSession, "gen", new=fake_gen):
            result = session.gen_with_tools(
                "question",
                tools,
                client=object(),
                save_messages=False,
            )

        self.assertEqual(result, {"response": "ordinary answer", "tool": None})
        self.assertIn("1: None", calls[0][1]["system"])
        self.assertIn("10: None", calls[0][1]["system"])
        self.assertEqual(
            calls[0][1]["params"]["logit_bias"],
            {str(value): 100 for value in range(15, 26)},
        )
        self.assertTrue(all(tool.calls == [] for tool in tools))

    def test_zero_selection_uses_ordinary_generation_arguments(self):
        session = make_session()
        client = object()
        params = {"temperature": 0.9}
        tool = RecordingSyncTool("tool", "A tool.", result="unused")
        outputs = ["0", "ordinary answer"]
        calls = []

        def fake_gen(current_session, prompt, **kwargs):
            calls.append((prompt, kwargs))
            return outputs.pop(0)

        with patch.object(ChatGPTSession, "gen", new=fake_gen):
            result = session.gen_with_tools(
                "question",
                [tool],
                client=client,
                system="ordinary system",
                save_messages=True,
                params=params,
            )

        self.assertEqual(result, {"response": "ordinary answer", "tool": None})
        self.assertEqual(tool.calls, [])
        self.assertEqual(len(calls), 2)
        self.assertIs(calls[0][1]["save_messages"], False)
        self.assertEqual(calls[1][0], "question")
        self.assertIs(calls[1][1]["client"], client)
        self.assertEqual(calls[1][1]["system"], "ordinary system")
        self.assertIs(calls[1][1]["save_messages"], True)
        self.assertIs(calls[1][1]["params"], params)


class AsyncToolOrchestrationContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_async_projection_mutates_mapping_and_uses_internal_save_false(self):
        session = make_session()
        client = object()
        params = {"top_p": 0.5}
        result_mapping = {
            "context": "async context",
            "tool": "old tool",
            "response": "old response",
        }
        tool = RecordingAsyncTool(
            "async_tool",
            "Async documentation.",
            result=result_mapping,
        )
        outputs = ["1", "async answer"]
        calls = []

        async def fake_gen_async(current_session, prompt, **kwargs):
            calls.append((current_session, prompt, kwargs))
            return outputs.pop(0)

        with patch.object(
            ChatGPTSession, "gen_async", new=fake_gen_async
        ):
            result = await session.gen_with_tools_async(
                "question",
                [tool],
                client=client,
                system="",
                save_messages=True,
                params=params,
            )

        self.assertIs(result, result_mapping)
        self.assertEqual(tool.calls, ["question"])
        self.assertEqual(result_mapping["tool"], "async_tool")
        self.assertEqual(result_mapping["response"], "async answer")
        self.assertEqual(len(calls), 2)
        self.assertIs(calls[0][2]["save_messages"], False)
        self.assertIs(calls[1][2]["save_messages"], False)
        self.assertEqual(
            calls[1][1],
            "Context: async context\n\nUser: question",
        )
        self.assertEqual(
            calls[1][2]["system"],
            session.system
            + "\n\nYou MUST use information from the context in your response.",
        )
        self.assertIs(calls[1][2]["params"], params)

    async def test_async_selection_retains_python_negative_indexing(self):
        session = make_session()
        tools = [
            RecordingAsyncTool("first", "First.", result="first context"),
            RecordingAsyncTool("second", "Second.", result="second context"),
            RecordingAsyncTool("third", "Third.", result="third context"),
        ]
        outputs = ["-1", "answer"]

        async def fake_gen_async(current_session, prompt, **kwargs):
            return outputs.pop(0)

        with patch.object(
            ChatGPTSession, "gen_async", new=fake_gen_async
        ):
            result = await session.gen_with_tools_async(
                "question",
                tools,
                client=object(),
                save_messages=False,
            )

        self.assertEqual(result["tool"], "second")
        self.assertEqual(tools[0].calls, [])
        self.assertEqual(tools[1].calls, ["question"])
        self.assertEqual(tools[2].calls, [])

    async def test_direct_async_session_call_bypasses_facade_guards(self):
        session = make_session()
        tools = [
            RecordingAsyncTool(f"tool_{index}", None, result="unused")
            for index in range(10)
        ]
        outputs = ["0", "ordinary answer"]
        calls = []

        async def fake_gen_async(current_session, prompt, **kwargs):
            calls.append((prompt, kwargs))
            return outputs.pop(0)

        with patch.object(
            ChatGPTSession, "gen_async", new=fake_gen_async
        ):
            result = await session.gen_with_tools_async(
                "question",
                tools,
                client=object(),
                save_messages=False,
            )

        self.assertEqual(result, {"response": "ordinary answer", "tool": None})
        self.assertIn("1: None", calls[0][1]["system"])
        self.assertIn("10: None", calls[0][1]["system"])
        self.assertEqual(
            calls[0][1]["params"]["logit_bias"],
            {str(value): 100 for value in range(15, 26)},
        )
        self.assertTrue(all(tool.calls == [] for tool in tools))


class SyncToolEffectLifecycleTests(unittest.TestCase):
    def test_success_orders_accounting_effect_second_call_and_history_commit(self):
        session, existing = make_seeded_session()
        events = []
        result_mapping = {
            "context": "effect result",
            "private": "not model-visible",
            "tool": "old tool",
            "response": "old response",
        }

        def effect_tool(prompt):
            """Perform the specimen effect."""
            events.append(
                (
                    "tool",
                    prompt,
                    session.total_prompt_length,
                    session.total_completion_length,
                    session.total_length,
                    list(session.messages),
                )
            )
            return result_mapping

        client = SequencedClient(
            [
                provider_response("1", 1, 2, 3),
                provider_response("final answer", 4, 5, 9),
            ]
        )
        original_add_messages = ChatGPTSession.add_messages

        def observed_add_messages(
            current_session,
            user_message,
            assistant_message,
            save_messages=None,
        ):
            events.append(
                (
                    "add",
                    save_messages,
                    current_session.total_prompt_length,
                    current_session.total_completion_length,
                    current_session.total_length,
                    len(current_session.messages),
                    user_message.content,
                    assistant_message.content,
                )
            )
            return original_add_messages(
                current_session,
                user_message,
                assistant_message,
                save_messages,
            )

        with patch.object(
            ChatGPTSession, "add_messages", new=observed_add_messages
        ):
            result = session.gen_with_tools(
                "original question",
                [effect_tool],
                client=client,
                system="custom system",
                save_messages=True,
                params={"temperature": 0.2},
            )

        self.assertIs(result, result_mapping)
        self.assertEqual(
            events[0],
            ("add", False, 10, 20, 30, 1, "original question", "1"),
        )
        self.assertEqual(events[1][0:5], ("tool", "original question", 11, 22, 33))
        self.assertEqual(events[1][5], [existing])
        self.assertEqual(
            events[2],
            (
                "add",
                False,
                11,
                22,
                33,
                1,
                "Context: effect result\n\nUser: original question",
                "final answer",
            ),
        )
        self.assertEqual(
            events[3],
            (
                "add",
                True,
                15,
                27,
                42,
                1,
                "original question",
                "final answer",
            ),
        )

        self.assertEqual(
            (
                session.total_prompt_length,
                session.total_completion_length,
                session.total_length,
            ),
            (15, 27, 42),
        )
        self.assertIs(session.messages[0], existing)
        self.assertEqual(
            [(message.role, message.content) for message in session.messages[1:]],
            [
                ("user", "original question"),
                ("assistant", "final answer"),
            ],
        )
        final_message = session.messages[-1]
        self.assertIsNone(final_message.finish_reason)
        self.assertIsNone(final_message.prompt_length)
        self.assertIsNone(final_message.completion_length)
        self.assertIsNone(final_message.total_length)

        self.assertEqual(len(client.calls), 2)
        second_body = client.calls[1][1]["json"]
        self.assertEqual(
            second_body["messages"],
            [
                {
                    "role": "system",
                    "content": (
                        "custom system\n\n"
                        "You MUST use information from the context in your response."
                    ),
                },
                {"role": "user", "content": "existing history"},
                {
                    "role": "user",
                    "content": (
                        "Context: effect result\n\nUser: original question"
                    ),
                },
            ],
        )
        self.assertNotIn("private", second_body["messages"][-1]["content"])
        self.assertNotIn("effect_tool", second_body["messages"][-1]["content"])
        self.assertEqual(result_mapping["tool"], "effect_tool")
        self.assertEqual(result_mapping["response"], "final answer")

    def test_tool_exception_leaves_only_selection_accounting(self):
        session, existing = make_seeded_session()
        failure = EffectFailure("tool failed")
        tool = RecordingSyncTool(
            "failing_tool",
            "Fail after an effect attempt.",
            failure=failure,
        )
        client = SequencedClient([provider_response("1", 2, 3, 5)])

        with self.assertRaises(EffectFailure) as raised:
            session.gen_with_tools(
                "question",
                [tool],
                client=client,
                save_messages=True,
            )

        self.assertIs(raised.exception, failure)
        self.assertEqual(tool.calls, ["question"])
        self.assertEqual(session.messages, [existing])
        self.assertIs(session.messages[0], existing)
        self.assertEqual(
            (
                session.total_prompt_length,
                session.total_completion_length,
                session.total_length,
            ),
            (12, 23, 35),
        )
        self.assertEqual(len(client.calls), 1)

    def test_successful_effect_then_second_model_failure_has_no_history_record(self):
        session, existing = make_seeded_session()
        failure = ModelFailure("second dispatch failed")
        result_mapping = {
            "context": "effect completed",
            "tool": "old tool",
            "response": "old response",
        }
        tool = RecordingSyncTool(
            "effect_tool",
            "Perform an effect.",
            result=result_mapping,
        )
        client = SequencedClient(
            [provider_response("1", 2, 3, 5), failure]
        )

        with self.assertRaises(ModelFailure) as raised:
            session.gen_with_tools(
                "question",
                [tool],
                client=client,
                save_messages=True,
            )

        self.assertIs(raised.exception, failure)
        self.assertEqual(tool.calls, ["question"])
        self.assertEqual(result_mapping["tool"], "effect_tool")
        self.assertEqual(result_mapping["response"], "old response")
        self.assertEqual(session.messages, [existing])
        self.assertIs(session.messages[0], existing)
        self.assertEqual(
            (
                session.total_prompt_length,
                session.total_completion_length,
                session.total_length,
            ),
            (12, 23, 35),
        )
        self.assertEqual(len(client.calls), 2)

    def test_original_mapping_identity_survives_successful_in_place_mutation(self):
        session = make_session()
        original_mapping = {
            "context": "context value",
            "tool": "replace me",
            "response": "replace me too",
        }
        tool = RecordingSyncTool(
            "identity_tool",
            "Return the retained mapping.",
            result=original_mapping,
        )
        client = SequencedClient(
            [provider_response("1"), provider_response("answer")]
        )

        result = session.gen_with_tools(
            "question",
            [tool],
            client=client,
            save_messages=False,
        )

        self.assertIs(result, original_mapping)
        self.assertEqual(original_mapping["tool"], "identity_tool")
        self.assertEqual(original_mapping["response"], "answer")

    def test_missing_context_fails_after_effect_and_tool_key_mutation(self):
        session, existing = make_seeded_session()
        result_mapping = {"private": "effect result", "tool": "old tool"}
        tool = RecordingSyncTool(
            "missing_context_tool",
            "Return no context key.",
            result=result_mapping,
        )
        client = SequencedClient([provider_response("1", 2, 3, 5)])

        with self.assertRaises(KeyError) as raised:
            session.gen_with_tools(
                "question",
                [tool],
                client=client,
                save_messages=True,
            )

        self.assertEqual(raised.exception.args, ("context",))
        self.assertEqual(tool.calls, ["question"])
        self.assertEqual(result_mapping["tool"], "missing_context_tool")
        self.assertNotIn("response", result_mapping)
        self.assertEqual(session.messages, [existing])
        self.assertEqual(session.total_length, 35)
        self.assertEqual(len(client.calls), 1)

    def test_malformed_and_out_of_range_selections_account_then_fail(self):
        specimens = [
            ("not an integer", ValueError),
            ("2", IndexError),
            ("-1", IndexError),
        ]

        for selection, expected_exception in specimens:
            with self.subTest(selection=selection):
                session, existing = make_seeded_session()
                tool = RecordingSyncTool(
                    "tool", "Only available tool.", result="unused"
                )
                client = SequencedClient(
                    [provider_response(selection, 2, 3, 5)]
                )

                with self.assertRaises(expected_exception):
                    session.gen_with_tools(
                        "question",
                        [tool],
                        client=client,
                        save_messages=True,
                    )

                self.assertEqual(tool.calls, [])
                self.assertEqual(session.messages, [existing])
                self.assertEqual(
                    (
                        session.total_prompt_length,
                        session.total_completion_length,
                        session.total_length,
                    ),
                    (12, 23, 35),
                )
                self.assertEqual(len(client.calls), 1)

    def test_zero_branch_accounts_selection_then_stores_normal_message_metadata(self):
        session, existing = make_seeded_session()
        tool = RecordingSyncTool("unused_tool", "Unused.", result="unused")
        client = SequencedClient(
            [
                provider_response("0", 1, 2, 3),
                provider_response("ordinary answer", 4, 5, 9, "length"),
            ]
        )

        result = session.gen_with_tools(
            "question",
            [tool],
            client=client,
            system="ordinary system",
            save_messages=True,
            params={"temperature": 0.4},
        )

        self.assertEqual(result, {"response": "ordinary answer", "tool": None})
        self.assertEqual(tool.calls, [])
        self.assertIs(session.messages[0], existing)
        self.assertEqual(
            [(message.role, message.content) for message in session.messages[1:]],
            [("user", "question"), ("assistant", "ordinary answer")],
        )
        final_message = session.messages[-1]
        self.assertEqual(final_message.finish_reason, "length")
        self.assertEqual(final_message.prompt_length, 4)
        self.assertEqual(final_message.completion_length, 5)
        self.assertEqual(final_message.total_length, 9)
        self.assertEqual(
            (
                session.total_prompt_length,
                session.total_completion_length,
                session.total_length,
            ),
            (15, 27, 42),
        )
        self.assertEqual(len(client.calls), 2)
        second_body = client.calls[1][1]["json"]
        self.assertEqual(second_body["messages"][0]["content"], "ordinary system")
        self.assertEqual(second_body["messages"][-1]["content"], "question")

    def test_selected_success_with_save_false_has_effect_and_accounting_only(self):
        session, existing = make_seeded_session()
        tool = RecordingSyncTool(
            "effect_tool",
            "Perform an effect.",
            result="effect context",
        )
        client = SequencedClient(
            [
                provider_response("1", 1, 2, 3),
                provider_response("answer", 4, 5, 9),
            ]
        )

        result = session.gen_with_tools(
            "question",
            [tool],
            client=client,
            save_messages=False,
        )

        self.assertEqual(tool.calls, ["question"])
        self.assertEqual(result["response"], "answer")
        self.assertEqual(session.messages, [existing])
        self.assertIs(session.messages[0], existing)
        self.assertEqual(
            (
                session.total_prompt_length,
                session.total_completion_length,
                session.total_length,
            ),
            (15, 27, 42),
        )


class AsyncToolEffectLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_async_tool_is_awaited_after_selection_accounting(self):
        session, existing = make_seeded_session()
        observations = []
        result_mapping = {"context": "async effect"}

        async def async_tool(prompt):
            """Perform the asynchronous effect."""
            observations.append(
                (
                    prompt,
                    session.total_prompt_length,
                    session.total_completion_length,
                    session.total_length,
                    list(session.messages),
                )
            )
            return result_mapping

        client = SequencedAsyncClient(
            [
                provider_response("1", 1, 2, 3),
                provider_response("async answer", 4, 5, 9),
            ]
        )

        result = await session.gen_with_tools_async(
            "question",
            [async_tool],
            client=client,
            save_messages=True,
        )

        self.assertIs(result, result_mapping)
        self.assertEqual(observations[0][0:4], ("question", 11, 22, 33))
        self.assertEqual(observations[0][4], [existing])
        self.assertEqual(result_mapping["tool"], "async_tool")
        self.assertEqual(result_mapping["response"], "async answer")
        self.assertIs(session.messages[0], existing)
        self.assertEqual(
            [(message.role, message.content) for message in session.messages[1:]],
            [("user", "question"), ("assistant", "async answer")],
        )
        self.assertIsNone(session.messages[-1].finish_reason)
        self.assertEqual(
            (
                session.total_prompt_length,
                session.total_completion_length,
                session.total_length,
            ),
            (15, 27, 42),
        )

    async def test_sync_callable_effect_occurs_before_await_type_error(self):
        session, existing = make_seeded_session()
        effect_observations = []
        returned_mapping = {"context": "sync effect"}

        def synchronous_tool(prompt):
            """Execute synchronously inside async orchestration."""
            effect_observations.append(
                (
                    prompt,
                    session.total_prompt_length,
                    session.total_completion_length,
                    session.total_length,
                )
            )
            return returned_mapping

        client = SequencedAsyncClient(
            [provider_response("1", 2, 3, 5)]
        )

        with self.assertRaises(TypeError):
            await session.gen_with_tools_async(
                "question",
                [synchronous_tool],
                client=client,
                save_messages=True,
            )

        self.assertEqual(effect_observations, [("question", 12, 23, 35)])
        self.assertEqual(returned_mapping, {"context": "sync effect"})
        self.assertEqual(session.messages, [existing])
        self.assertIs(session.messages[0], existing)
        self.assertEqual(session.total_length, 35)
        self.assertEqual(len(client.calls), 1)

    async def test_async_effect_then_second_model_failure_has_no_history_record(self):
        session, existing = make_seeded_session()
        failure = ModelFailure("async second dispatch failed")
        result_mapping = {
            "context": "effect completed",
            "tool": "old tool",
            "response": "old response",
        }
        tool = RecordingAsyncTool(
            "async_effect_tool",
            "Perform an asynchronous effect.",
            result=result_mapping,
        )
        client = SequencedAsyncClient(
            [provider_response("1", 2, 3, 5), failure]
        )

        with self.assertRaises(ModelFailure) as raised:
            await session.gen_with_tools_async(
                "question",
                [tool],
                client=client,
                save_messages=True,
            )

        self.assertIs(raised.exception, failure)
        self.assertEqual(tool.calls, ["question"])
        self.assertEqual(result_mapping["tool"], "async_effect_tool")
        self.assertEqual(result_mapping["response"], "old response")
        self.assertEqual(session.messages, [existing])
        self.assertIs(session.messages[0], existing)
        self.assertEqual(session.total_length, 35)
        self.assertEqual(len(client.calls), 2)

    async def test_async_tool_exception_leaves_only_selection_accounting(self):
        session, existing = make_seeded_session()
        failure = EffectFailure("async tool failed")
        tool = RecordingAsyncTool(
            "failing_async_tool",
            "Fail asynchronously.",
            failure=failure,
        )
        client = SequencedAsyncClient(
            [provider_response("1", 2, 3, 5)]
        )

        with self.assertRaises(EffectFailure) as raised:
            await session.gen_with_tools_async(
                "question",
                [tool],
                client=client,
                save_messages=True,
            )

        self.assertIs(raised.exception, failure)
        self.assertEqual(tool.calls, ["question"])
        self.assertEqual(session.messages, [existing])
        self.assertEqual(session.total_length, 35)
        self.assertEqual(len(client.calls), 1)

    async def test_async_zero_branch_uses_normal_history_and_metadata(self):
        session, existing = make_seeded_session()
        tool = RecordingAsyncTool(
            "unused_tool",
            "Unused.",
            result="unused",
        )
        client = SequencedAsyncClient(
            [
                provider_response("0", 1, 2, 3),
                provider_response("ordinary answer", 4, 5, 9, "length"),
            ]
        )

        result = await session.gen_with_tools_async(
            "question",
            [tool],
            client=client,
            save_messages=True,
        )

        self.assertEqual(result, {"response": "ordinary answer", "tool": None})
        self.assertEqual(tool.calls, [])
        self.assertIs(session.messages[0], existing)
        self.assertEqual(session.messages[-1].content, "ordinary answer")
        self.assertEqual(session.messages[-1].finish_reason, "length")
        self.assertEqual(session.messages[-1].prompt_length, 4)
        self.assertEqual(session.messages[-1].completion_length, 5)
        self.assertEqual(session.messages[-1].total_length, 9)
        self.assertEqual(
            (
                session.total_prompt_length,
                session.total_completion_length,
                session.total_length,
            ),
            (15, 27, 42),
        )


if __name__ == "__main__":
    unittest.main()
