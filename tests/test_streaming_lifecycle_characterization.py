import unittest
from unittest.mock import patch

import orjson

from simpleaichat.chatgpt import ChatGPTSession
from simpleaichat.models import ChatMessage


BASELINE_COMMIT = "683a7391c15e69aff5ee741e24617856c5dc24b2"


def content_line(content, prefix="data: "):
    return delta_line({"content": content}, prefix=prefix)


def delta_line(delta, prefix="data: "):
    payload = {"choices": [{"delta": delta}]}
    return prefix + orjson.dumps(payload).decode()


class StreamFailure(Exception):
    pass


class FakeSyncResponse:
    def __init__(self, lines, events=None):
        self.lines = lines
        self.events = events if events is not None else []
        self.entered = 0
        self.exits = []
        self.iter_lines_calls = 0
        self.raise_for_status_calls = 0
        self.json_calls = 0

    def __enter__(self):
        self.entered += 1
        self.events.append("response-enter")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.exits.append((exc_type, exc_value, traceback))
        self.events.append("response-exit")
        return False

    def iter_lines(self):
        self.iter_lines_calls += 1
        self.events.append("iter-lines")
        for line in self.lines:
            if isinstance(line, BaseException):
                raise line
            yield line

    def raise_for_status(self):
        self.raise_for_status_calls += 1

    def json(self):
        self.json_calls += 1
        return {"not": "used by streaming"}


class FakeSyncClient:
    def __init__(self, response, events=None):
        self.response = response
        self.events = events if events is not None else []
        self.calls = []

    def stream(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        self.events.append("client-stream")
        return self.response


class FakeAsyncResponse:
    def __init__(self, lines, events=None):
        self.lines = lines
        self.events = events if events is not None else []
        self.entered = 0
        self.exits = []
        self.aiter_lines_calls = 0
        self.raise_for_status_calls = 0
        self.json_calls = 0

    async def __aenter__(self):
        self.entered += 1
        self.events.append("response-enter")
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        self.exits.append((exc_type, exc_value, traceback))
        self.events.append("response-exit")
        return False

    async def aiter_lines(self):
        self.aiter_lines_calls += 1
        self.events.append("aiter-lines")
        for line in self.lines:
            if isinstance(line, BaseException):
                raise line
            yield line

    def raise_for_status(self):
        self.raise_for_status_calls += 1

    def json(self):
        self.json_calls += 1
        return {"not": "used by streaming"}


class FakeAsyncClient:
    def __init__(self, response, events=None):
        self.response = response
        self.events = events if events is not None else []
        self.calls = []

    def stream(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        self.events.append("client-stream")
        return self.response


def make_session():
    return ChatGPTSession(auth={"api_key": "test-key"}, model="test-model")


def prepared_values():
    return (
        {"X-Prepared": "header"},
        {"opaque": object()},
        ChatMessage(role="user", content="prepared user"),
    )


class SyncStreamingLifecycleTests(unittest.TestCase):
    def test_stream_is_lazy_then_dispatches_the_exact_prepared_objects(self):
        session = make_session()
        expected_url = str(session.api_url)
        headers, data, user_message = prepared_values()
        response = FakeSyncResponse([content_line("first")])
        client = FakeSyncClient(response)
        params = {"temperature": 0.25}
        input_schema = object()
        observed = {}

        def fake_prepare_request(
            current_session,
            prompt,
            system,
            received_params,
            stream,
            received_input_schema,
            output_schema=None,
        ):
            observed["call"] = (
                current_session,
                prompt,
                system,
                received_params,
                stream,
                received_input_schema,
                output_schema,
            )
            return headers, data, user_message

        with patch.object(
            ChatGPTSession, "prepare_request", new=fake_prepare_request
        ):
            generator = session.stream(
                "question",
                client=client,
                system="specimen system",
                save_messages=True,
                params=params,
                input_schema=input_schema,
            )

            self.assertNotIn("call", observed)
            self.assertEqual(client.calls, [])
            self.assertEqual(response.entered, 0)
            self.assertEqual(session.messages, [])

            self.assertEqual(
                next(generator), {"delta": "first", "response": "first"}
            )

            self.assertEqual(
                observed["call"],
                (
                    session,
                    "question",
                    "specimen system",
                    params,
                    True,
                    input_schema,
                    None,
                ),
            )
            self.assertEqual(len(client.calls), 1)
            method, url, kwargs = client.calls[0]
            self.assertEqual(method, "POST")
            self.assertEqual(url, expected_url)
            self.assertIs(kwargs["headers"], headers)
            self.assertIs(kwargs["json"], data)
            self.assertIsNone(kwargs["timeout"])
            self.assertEqual(session.messages, [])

            generator.close()

        self.assertEqual(response.raise_for_status_calls, 0)
        self.assertEqual(response.json_calls, 0)

    def test_stream_parsing_skips_done_without_terminating_and_accumulates_content(
        self,
    ):
        session = make_session()
        headers, data, user_message = prepared_values()
        response = FakeSyncResponse(
            [
                "",
                delta_line({"role": "assistant"}),
                delta_line({"function_call": {"arguments": "ignored"}}),
                content_line(""),
                content_line("A", prefix="xxxxxx"),
                "data: [DONE]",
                content_line("B"),
            ]
        )
        client = FakeSyncClient(response)

        with patch.object(
            ChatGPTSession,
            "prepare_request",
            return_value=(headers, data, user_message),
        ):
            yielded = list(session.stream("question", client=client))

        self.assertEqual(
            yielded,
            [
                {"delta": "A", "response": "A"},
                {"delta": "B", "response": "AB"},
            ],
        )
        self.assertEqual(
            [message.content for message in session.messages],
            ["prepared user", "AB"],
        )
        self.assertEqual(response.iter_lines_calls, 1)
        self.assertEqual(response.raise_for_status_calls, 0)
        self.assertEqual(response.json_calls, 0)

    def test_sync_commit_occurs_only_after_post_yield_exhaustion_and_returns_message(
        self,
    ):
        events = []
        session = make_session()
        headers, data, user_message = prepared_values()
        response = FakeSyncResponse([content_line("complete")], events)
        client = FakeSyncClient(response, events)
        original_add_messages = ChatGPTSession.add_messages

        def observed_add_messages(
            current_session, prepared_user, assistant_message, save_messages=None
        ):
            events.append("add-messages")
            return original_add_messages(
                current_session, prepared_user, assistant_message, save_messages
            )

        with patch.object(
            ChatGPTSession,
            "prepare_request",
            return_value=(headers, data, user_message),
        ), patch.object(
            ChatGPTSession, "add_messages", new=observed_add_messages
        ):
            generator = session.stream(
                "question", client=client, save_messages=True
            )

            self.assertEqual(
                next(generator), {"delta": "complete", "response": "complete"}
            )
            self.assertEqual(session.messages, [])
            self.assertEqual(response.exits, [])
            self.assertEqual(events, ["client-stream", "response-enter", "iter-lines"])

            with self.assertRaises(StopIteration) as stopped:
                next(generator)

        assistant_message = stopped.exception.value
        self.assertIsInstance(assistant_message, ChatMessage)
        self.assertIs(session.messages[0], user_message)
        self.assertIs(session.messages[1], assistant_message)
        self.assertEqual(assistant_message.role, "assistant")
        self.assertEqual(assistant_message.content, "complete")
        self.assertIsNone(assistant_message.name)
        self.assertIsNone(assistant_message.function_call)
        self.assertIsNone(assistant_message.finish_reason)
        self.assertIsNone(assistant_message.prompt_length)
        self.assertIsNone(assistant_message.completion_length)
        self.assertIsNone(assistant_message.total_length)
        self.assertIsNotNone(assistant_message.received_at)
        self.assertEqual(
            events,
            [
                "client-stream",
                "response-enter",
                "iter-lines",
                "response-exit",
                "add-messages",
            ],
        )
        self.assertEqual(session.total_prompt_length, 0)
        self.assertEqual(session.total_completion_length, 0)
        self.assertEqual(session.total_length, 0)

    def test_normal_exhaustion_stores_an_empty_assistant_when_no_content_is_yielded(
        self,
    ):
        session = make_session()
        headers, data, user_message = prepared_values()
        response = FakeSyncResponse(
            ["", delta_line({"role": "assistant"}), "data: [DONE]"]
        )

        with patch.object(
            ChatGPTSession,
            "prepare_request",
            return_value=(headers, data, user_message),
        ):
            yielded = list(
                session.stream(
                    "question", client=FakeSyncClient(response), save_messages=True
                )
            )

        self.assertEqual(yielded, [])
        self.assertIs(session.messages[0], user_message)
        self.assertEqual(session.messages[1].role, "assistant")
        self.assertEqual(session.messages[1].content, "")

    def test_normal_exhaustion_respects_explicit_save_messages_false(self):
        session = make_session()
        headers, data, user_message = prepared_values()
        response = FakeSyncResponse([content_line("complete")])

        with patch.object(
            ChatGPTSession,
            "prepare_request",
            return_value=(headers, data, user_message),
        ):
            yielded = list(
                session.stream(
                    "question", client=FakeSyncClient(response), save_messages=False
                )
            )

        self.assertEqual(yielded, [{"delta": "complete", "response": "complete"}])
        self.assertEqual(session.messages, [])

    def test_midstream_exception_preserves_partial_manifestation_but_does_not_commit(
        self,
    ):
        session = make_session()
        headers, data, user_message = prepared_values()
        failure = StreamFailure("stream interrupted")
        response = FakeSyncResponse([content_line("partial"), failure])

        with patch.object(
            ChatGPTSession,
            "prepare_request",
            return_value=(headers, data, user_message),
        ):
            generator = session.stream(
                "question", client=FakeSyncClient(response), save_messages=True
            )
            self.assertEqual(
                next(generator), {"delta": "partial", "response": "partial"}
            )
            self.assertEqual(session.messages, [])

            with self.assertRaises(StreamFailure) as raised:
                next(generator)

        self.assertIs(raised.exception, failure)
        self.assertEqual(session.messages, [])
        self.assertEqual(len(response.exits), 1)
        self.assertIs(response.exits[0][0], StreamFailure)
        self.assertIs(response.exits[0][1], failure)
        self.assertEqual(session.total_length, 0)

    def test_live_suspension_then_close_cleans_up_without_committing(self):
        session = make_session()
        headers, data, user_message = prepared_values()
        response = FakeSyncResponse([content_line("partial"), content_line("later")])

        with patch.object(
            ChatGPTSession,
            "prepare_request",
            return_value=(headers, data, user_message),
        ):
            generator = session.stream(
                "question", client=FakeSyncClient(response), save_messages=True
            )
            self.assertEqual(
                next(generator), {"delta": "partial", "response": "partial"}
            )

            self.assertEqual(session.messages, [])
            self.assertEqual(response.exits, [])

            generator.close()

        self.assertEqual(session.messages, [])
        self.assertEqual(len(response.exits), 1)
        self.assertIs(response.exits[0][0], GeneratorExit)
        self.assertIsInstance(response.exits[0][1], GeneratorExit)
        self.assertEqual(session.total_length, 0)

    def test_invalid_json_and_missing_provider_structure_propagate_without_commit(self):
        specimens = [
            ("data: not-json", orjson.JSONDecodeError),
            ("data: {}", KeyError),
        ]

        for line, expected_exception in specimens:
            with self.subTest(line=line):
                session = make_session()
                headers, data, user_message = prepared_values()
                response = FakeSyncResponse([line])

                with patch.object(
                    ChatGPTSession,
                    "prepare_request",
                    return_value=(headers, data, user_message),
                ):
                    generator = session.stream(
                        "question", client=FakeSyncClient(response), save_messages=True
                    )
                    with self.assertRaises(expected_exception):
                        next(generator)

                self.assertEqual(session.messages, [])
                self.assertEqual(len(response.exits), 1)


class AsyncStreamingLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_stream_async_is_lazy_then_dispatches_the_exact_prepared_objects(
        self,
    ):
        session = make_session()
        expected_url = str(session.api_url)
        headers, data, user_message = prepared_values()
        response = FakeAsyncResponse([content_line("first")])
        client = FakeAsyncClient(response)
        params = {"temperature": 0.25}
        input_schema = object()
        observed = {}

        def fake_prepare_request(
            current_session,
            prompt,
            system,
            received_params,
            stream,
            received_input_schema,
            output_schema=None,
        ):
            observed["call"] = (
                current_session,
                prompt,
                system,
                received_params,
                stream,
                received_input_schema,
                output_schema,
            )
            return headers, data, user_message

        with patch.object(
            ChatGPTSession, "prepare_request", new=fake_prepare_request
        ):
            generator = session.stream_async(
                "question",
                client=client,
                system="specimen system",
                save_messages=True,
                params=params,
                input_schema=input_schema,
            )

            self.assertNotIn("call", observed)
            self.assertEqual(client.calls, [])
            self.assertEqual(response.entered, 0)
            self.assertEqual(session.messages, [])

            self.assertEqual(
                await generator.__anext__(),
                {"delta": "first", "response": "first"},
            )

            self.assertEqual(
                observed["call"],
                (
                    session,
                    "question",
                    "specimen system",
                    params,
                    True,
                    input_schema,
                    None,
                ),
            )
            self.assertEqual(len(client.calls), 1)
            method, url, kwargs = client.calls[0]
            self.assertEqual(method, "POST")
            self.assertEqual(url, expected_url)
            self.assertIs(kwargs["headers"], headers)
            self.assertIs(kwargs["json"], data)
            self.assertIsNone(kwargs["timeout"])
            self.assertEqual(session.messages, [])

            await generator.aclose()

        self.assertEqual(response.raise_for_status_calls, 0)
        self.assertEqual(response.json_calls, 0)

    async def test_stream_async_parsing_matches_sync_including_content_after_done(self):
        session = make_session()
        headers, data, user_message = prepared_values()
        response = FakeAsyncResponse(
            [
                "",
                delta_line({"role": "assistant"}),
                delta_line({"function_call": {"arguments": "ignored"}}),
                content_line(""),
                content_line("A", prefix="xxxxxx"),
                "data: [DONE]",
                content_line("B"),
            ]
        )

        with patch.object(
            ChatGPTSession,
            "prepare_request",
            return_value=(headers, data, user_message),
        ):
            yielded = [
                item
                async for item in session.stream_async(
                    "question", client=FakeAsyncClient(response)
                )
            ]

        self.assertEqual(
            yielded,
            [
                {"delta": "A", "response": "A"},
                {"delta": "B", "response": "AB"},
            ],
        )
        self.assertEqual(
            [message.content for message in session.messages],
            ["prepared user", "AB"],
        )
        self.assertEqual(response.aiter_lines_calls, 1)
        self.assertEqual(response.raise_for_status_calls, 0)
        self.assertEqual(response.json_calls, 0)

    async def test_async_commit_requires_exhaustion_and_has_no_return_value(
        self,
    ):
        events = []
        session = make_session()
        headers, data, user_message = prepared_values()
        response = FakeAsyncResponse([content_line("complete")], events)
        client = FakeAsyncClient(response, events)
        original_add_messages = ChatGPTSession.add_messages

        def observed_add_messages(
            current_session, prepared_user, assistant_message, save_messages=None
        ):
            events.append("add-messages")
            return original_add_messages(
                current_session, prepared_user, assistant_message, save_messages
            )

        with patch.object(
            ChatGPTSession,
            "prepare_request",
            return_value=(headers, data, user_message),
        ), patch.object(
            ChatGPTSession, "add_messages", new=observed_add_messages
        ):
            generator = session.stream_async(
                "question", client=client, save_messages=True
            )

            self.assertEqual(
                await generator.__anext__(),
                {"delta": "complete", "response": "complete"},
            )
            self.assertEqual(session.messages, [])
            self.assertEqual(response.exits, [])
            self.assertEqual(events, ["client-stream", "response-enter", "aiter-lines"])

            with self.assertRaises(StopAsyncIteration) as stopped:
                await generator.__anext__()

        self.assertEqual(stopped.exception.args, ())
        self.assertIs(session.messages[0], user_message)
        assistant_message = session.messages[1]
        self.assertEqual(assistant_message.role, "assistant")
        self.assertEqual(assistant_message.content, "complete")
        self.assertIsNone(assistant_message.name)
        self.assertIsNone(assistant_message.function_call)
        self.assertIsNone(assistant_message.finish_reason)
        self.assertIsNone(assistant_message.prompt_length)
        self.assertIsNone(assistant_message.completion_length)
        self.assertIsNone(assistant_message.total_length)
        self.assertIsNotNone(assistant_message.received_at)
        self.assertEqual(
            events,
            [
                "client-stream",
                "response-enter",
                "aiter-lines",
                "response-exit",
                "add-messages",
            ],
        )
        self.assertEqual(session.total_prompt_length, 0)
        self.assertEqual(session.total_completion_length, 0)
        self.assertEqual(session.total_length, 0)

    async def test_async_normal_exhaustion_stores_empty_assistant_and_honors_save_false(
        self,
    ):
        specimens = ((True, ["prepared user", ""]), (False, []))
        for save_messages, expected_contents in specimens:
            with self.subTest(save_messages=save_messages):
                session = make_session()
                headers, data, user_message = prepared_values()
                response = FakeAsyncResponse(
                    ["", delta_line({"role": "assistant"}), "data: [DONE]"]
                )

                with patch.object(
                    ChatGPTSession,
                    "prepare_request",
                    return_value=(headers, data, user_message),
                ):
                    yielded = [
                        item
                        async for item in session.stream_async(
                            "question",
                            client=FakeAsyncClient(response),
                            save_messages=save_messages,
                        )
                    ]

                self.assertEqual(yielded, [])
                self.assertEqual(
                    [message.content for message in session.messages], expected_contents
                )

    async def test_async_midstream_exception_does_not_commit_partial_manifestation(
        self,
    ):
        session = make_session()
        headers, data, user_message = prepared_values()
        failure = StreamFailure("stream interrupted")
        response = FakeAsyncResponse([content_line("partial"), failure])

        with patch.object(
            ChatGPTSession,
            "prepare_request",
            return_value=(headers, data, user_message),
        ):
            generator = session.stream_async(
                "question", client=FakeAsyncClient(response), save_messages=True
            )
            self.assertEqual(
                await generator.__anext__(),
                {"delta": "partial", "response": "partial"},
            )
            self.assertEqual(session.messages, [])

            with self.assertRaises(StreamFailure) as raised:
                await generator.__anext__()

        self.assertIs(raised.exception, failure)
        self.assertEqual(session.messages, [])
        self.assertEqual(len(response.exits), 1)
        self.assertIs(response.exits[0][0], StreamFailure)
        self.assertIs(response.exits[0][1], failure)
        self.assertEqual(session.total_length, 0)

    async def test_async_live_suspension_then_aclose_cleans_up_without_committing(self):
        session = make_session()
        headers, data, user_message = prepared_values()
        response = FakeAsyncResponse(
            [content_line("partial"), content_line("later")]
        )

        with patch.object(
            ChatGPTSession,
            "prepare_request",
            return_value=(headers, data, user_message),
        ):
            generator = session.stream_async(
                "question", client=FakeAsyncClient(response), save_messages=True
            )
            self.assertEqual(
                await generator.__anext__(),
                {"delta": "partial", "response": "partial"},
            )

            self.assertEqual(session.messages, [])
            self.assertEqual(response.exits, [])

            await generator.aclose()

        self.assertEqual(session.messages, [])
        self.assertEqual(len(response.exits), 1)
        self.assertIs(response.exits[0][0], GeneratorExit)
        self.assertIsInstance(response.exits[0][1], GeneratorExit)
        self.assertEqual(session.total_length, 0)


if __name__ == "__main__":
    unittest.main()
