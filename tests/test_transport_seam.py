"""Run 005 tests for the explicit non-streaming transport boundary."""

import copy
import unittest
from unittest.mock import patch

import simpleaichat.chatgpt as chatgpt

from simpleaichat.chatgpt import ChatGPTSession
from simpleaichat.models import ChatMessage


class SpecimenUrl:
    def __init__(self, value):
        self.value = value
        self.string_calls = 0

    def __str__(self):
        self.string_calls += 1
        return self.value


class FakeResponse:
    def __init__(self, decoded):
        self.decoded = decoded
        self.json_calls = 0

    def json(self):
        self.json_calls += 1
        return self.decoded


class FakeClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.response


class FakeAsyncClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    async def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.response


class TransportFailure(Exception):
    pass


class FailingClient:
    def __init__(self, failure):
        self.failure = failure

    def post(self, url, **kwargs):
        raise self.failure


class FailingAsyncClient:
    def __init__(self, failure):
        self.failure = failure

    async def post(self, url, **kwargs):
        raise self.failure


def decoded_response():
    return {
        "choices": [
            {
                "message": {"role": "assistant", "content": "answer"},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 5,
            "completion_tokens": 7,
            "total_tokens": 12,
        },
    }


class SyncTransportSeamTests(unittest.TestCase):
    def sender(self):
        sender = getattr(chatgpt, "send_request", None)
        self.assertIsNotNone(sender, "send_request() has not been extracted")
        return sender

    def test_sync_transport_dispatches_decodes_and_returns_the_same_object(self):
        decoded = {"opaque": ["provider", "data"]}
        response = FakeResponse(decoded)
        client = FakeClient(response)
        api_url = SpecimenUrl("https://provider.test/v1/chat")
        headers = {"Authorization": "Bearer specimen"}
        data = {"messages": [{"role": "user", "content": "question"}]}
        original_inputs = copy.deepcopy({"headers": headers, "data": data})

        result = self.sender()(client, api_url, headers, data)

        self.assertEqual(
            client.calls,
            [
                (
                    "https://provider.test/v1/chat",
                    {"json": data, "headers": headers, "timeout": None},
                )
            ],
        )
        self.assertIs(client.calls[0][1]["json"], data)
        self.assertIs(client.calls[0][1]["headers"], headers)
        self.assertEqual(api_url.string_calls, 1)
        self.assertEqual(response.json_calls, 1)
        self.assertIs(result, decoded)
        self.assertEqual({"headers": headers, "data": data}, original_inputs)

    def test_sync_transport_propagates_the_original_exception(self):
        failure = TransportFailure("dispatch failed")

        with self.assertRaises(TransportFailure) as raised:
            self.sender()(FailingClient(failure), SpecimenUrl("unused"), {}, {})

        self.assertIs(raised.exception, failure)

    def test_gen_delegates_prepared_objects_then_interprets_and_mutates_state(self):
        session = ChatGPTSession(auth={"api_key": "test-key"}, model="model")
        expected_api_url = session.api_url
        prepared_headers = {"X-Specimen": "header"}
        prepared_data = {"opaque": object()}
        prepared_user_message = ChatMessage(role="user", content="prepared")
        decoded = decoded_response()
        direct_response = FakeResponse(decoded)
        client = FakeClient(direct_response)
        observed = {}

        def fake_prepare_request(
            current_session,
            prompt,
            system,
            params,
            stream,
            input_schema,
            output_schema,
        ):
            self.assertIs(current_session, session)
            return prepared_headers, prepared_data, prepared_user_message

        def fake_send_request(received_client, api_url, headers, data):
            observed["call"] = (received_client, api_url, headers, data)
            return decoded

        with patch.object(
            ChatGPTSession, "prepare_request", new=fake_prepare_request
        ), patch.object(chatgpt, "send_request", new=fake_send_request):
            result = session.gen("question", client=client, save_messages=True)

        self.assertIn("call", observed, "gen() bypassed send_request()")
        received_client, api_url, headers, data = observed["call"]
        self.assertIs(received_client, client)
        self.assertIs(api_url, expected_api_url)
        self.assertIs(headers, prepared_headers)
        self.assertIs(data, prepared_data)
        self.assertEqual(client.calls, [])
        self.assertEqual(direct_response.json_calls, 0)
        self.assertEqual(result, "answer")
        self.assertIs(session.messages[0], prepared_user_message)
        self.assertEqual(session.messages[1].role, "assistant")
        self.assertEqual(session.messages[1].content, "answer")
        self.assertEqual(session.total_prompt_length, 5)
        self.assertEqual(session.total_completion_length, 7)
        self.assertEqual(session.total_length, 12)


class AsyncTransportSeamTests(unittest.IsolatedAsyncioTestCase):
    def sender(self):
        sender = getattr(chatgpt, "send_request_async", None)
        self.assertIsNotNone(
            sender, "send_request_async() has not been extracted"
        )
        return sender

    async def test_async_transport_dispatches_decodes_and_returns_the_same_object(self):
        decoded = {"opaque": ["provider", "data"]}
        response = FakeResponse(decoded)
        client = FakeAsyncClient(response)
        api_url = SpecimenUrl("https://provider.test/v1/chat")
        headers = {"Authorization": "Bearer specimen"}
        data = {"messages": [{"role": "user", "content": "question"}]}
        original_inputs = copy.deepcopy({"headers": headers, "data": data})

        result = await self.sender()(client, api_url, headers, data)

        self.assertEqual(
            client.calls,
            [
                (
                    "https://provider.test/v1/chat",
                    {"json": data, "headers": headers, "timeout": None},
                )
            ],
        )
        self.assertIs(client.calls[0][1]["json"], data)
        self.assertIs(client.calls[0][1]["headers"], headers)
        self.assertEqual(api_url.string_calls, 1)
        self.assertEqual(response.json_calls, 1)
        self.assertIs(result, decoded)
        self.assertEqual({"headers": headers, "data": data}, original_inputs)

    async def test_async_transport_propagates_the_original_exception(self):
        failure = TransportFailure("dispatch failed")

        with self.assertRaises(TransportFailure) as raised:
            await self.sender()(
                FailingAsyncClient(failure), SpecimenUrl("unused"), {}, {}
            )

        self.assertIs(raised.exception, failure)

    async def test_gen_async_delegates_prepared_objects_then_interprets_and_mutates_state(
        self,
    ):
        session = ChatGPTSession(auth={"api_key": "test-key"}, model="model")
        expected_api_url = session.api_url
        prepared_headers = {"X-Specimen": "header"}
        prepared_data = {"opaque": object()}
        prepared_user_message = ChatMessage(role="user", content="prepared")
        decoded = decoded_response()
        direct_response = FakeResponse(decoded)
        client = FakeAsyncClient(direct_response)
        observed = {}

        def fake_prepare_request(
            current_session,
            prompt,
            system,
            params,
            stream,
            input_schema,
            output_schema,
        ):
            self.assertIs(current_session, session)
            return prepared_headers, prepared_data, prepared_user_message

        async def fake_send_request_async(received_client, api_url, headers, data):
            observed["call"] = (received_client, api_url, headers, data)
            return decoded

        with patch.object(
            ChatGPTSession, "prepare_request", new=fake_prepare_request
        ), patch.object(
            chatgpt, "send_request_async", new=fake_send_request_async
        ):
            result = await session.gen_async(
                "question", client=client, save_messages=True
            )

        self.assertIn("call", observed, "gen_async() bypassed send_request_async()")
        received_client, api_url, headers, data = observed["call"]
        self.assertIs(received_client, client)
        self.assertIs(api_url, expected_api_url)
        self.assertIs(headers, prepared_headers)
        self.assertIs(data, prepared_data)
        self.assertEqual(client.calls, [])
        self.assertEqual(direct_response.json_calls, 0)
        self.assertEqual(result, "answer")
        self.assertIs(session.messages[0], prepared_user_message)
        self.assertEqual(session.messages[1].role, "assistant")
        self.assertEqual(session.messages[1].content, "answer")
        self.assertEqual(session.total_prompt_length, 5)
        self.assertEqual(session.total_completion_length, 7)
        self.assertEqual(session.total_length, 12)


if __name__ == "__main__":
    unittest.main()
