"""Run 004 tests for explicit provider request-body assembly."""

import copy
import unittest
from unittest.mock import patch

import simpleaichat.chatgpt as chatgpt
from pydantic import BaseModel

from simpleaichat.chatgpt import ChatGPTSession
from simpleaichat.models import ChatMessage


class SchemaInput(BaseModel):
    """A seam schema input."""

    value: int


class SchemaOutput(BaseModel):
    """A seam schema output."""

    result: str


class RequestAssemblySeamTests(unittest.TestCase):
    def assembler(self):
        assembler = getattr(chatgpt, "assemble_request", None)
        self.assertIsNotNone(assembler, "assemble_request() has not been extracted")
        return assembler

    def test_explicit_inputs_build_the_provider_request_body(self):
        messages = [{"role": "user", "content": "question"}]
        params = {"temperature": 0.2, "top_p": 0.9}

        request = self.assembler()(
            model="specimen-model",
            messages=messages,
            stream=False,
            params=params,
        )

        self.assertEqual(
            request,
            {
                "model": "specimen-model",
                "messages": [{"role": "user", "content": "question"}],
                "stream": False,
                "temperature": 0.2,
                "top_p": 0.9,
            },
        )

    def test_params_retain_authority_over_structural_request_fields(self):
        original_messages = [{"role": "user", "content": "question"}]
        overriding_messages = [{"role": "assistant", "content": "replacement"}]
        params = {
            "model": "overridden-model",
            "messages": overriding_messages,
            "stream": "overridden-stream",
            "temperature": 0.2,
        }

        request = self.assembler()(
            model="specimen-model",
            messages=original_messages,
            stream=False,
            params=params,
        )

        self.assertEqual(
            request,
            {
                "model": "overridden-model",
                "messages": [
                    {"role": "assistant", "content": "replacement"}
                ],
                "stream": "overridden-stream",
                "temperature": 0.2,
            },
        )
        self.assertIs(request["messages"], overriding_messages)

    def test_schema_metadata_overwrites_colliding_params(self):
        messages = [{"role": "user", "content": "question"}]
        functions = [{"name": "SchemaOutput", "parameters": {"type": "object"}}]
        function_call = {"name": "SchemaOutput"}
        params = {
            "functions": [{"name": "CallerFunction"}],
            "function_call": {"name": "CallerFunction"},
        }

        request = self.assembler()(
            model="specimen-model",
            messages=messages,
            stream=False,
            params=params,
            functions=functions,
            function_call=function_call,
        )

        self.assertEqual(request["functions"], functions)
        self.assertEqual(request["function_call"], function_call)
        self.assertIs(request["functions"], functions)
        self.assertIs(request["function_call"], function_call)

    def test_absent_schema_metadata_retains_arbitrary_param_keys(self):
        caller_functions = [{"name": "CallerFunction"}]
        caller_function_call = {"name": "CallerFunction"}
        params = {
            "functions": caller_functions,
            "function_call": caller_function_call,
        }

        request = self.assembler()(
            model="specimen-model",
            messages=[],
            stream=False,
            params=params,
        )

        self.assertIs(request["functions"], caller_functions)
        self.assertIs(request["function_call"], caller_function_call)

    def test_assembly_returns_a_fresh_mapping_without_mutating_inputs(self):
        messages = [{"role": "user", "content": "question"}]
        params = {"temperature": 0.2}
        functions = [{"name": "SchemaOutput", "parameters": {"type": "object"}}]
        function_call = {"name": "SchemaOutput"}
        original_inputs = copy.deepcopy(
            {
                "messages": messages,
                "params": params,
                "functions": functions,
                "function_call": function_call,
            }
        )

        request = self.assembler()(
            model="specimen-model",
            messages=messages,
            stream=True,
            params=params,
            functions=functions,
            function_call=function_call,
        )

        self.assertIsNot(request, params)
        self.assertEqual(
            {
                "messages": messages,
                "params": params,
                "functions": functions,
                "function_call": function_call,
            },
            original_inputs,
        )


class PrepareRequestCompatibilityTests(unittest.TestCase):
    def test_prepare_request_passes_final_body_inputs_through_assembly_seam(self):
        session = ChatGPTSession(
            auth={"api_key": "test-key"},
            model="specimen-model",
            params={"temperature": 0.2},
            recent_messages=1,
            messages=[
                ChatMessage(role="user", content="discarded"),
                ChatMessage(role="assistant", content="retained"),
            ],
        )
        prompt = SchemaInput(value=7)
        assembled_body = {"delegated": True}
        observed = {}

        def fake_assemble_request(
            model,
            messages,
            stream,
            params,
            functions=None,
            function_call=None,
        ):
            observed.update(
                {
                    "model": model,
                    "messages": messages,
                    "stream": stream,
                    "params": params,
                    "functions": functions,
                    "function_call": function_call,
                }
            )
            return assembled_body

        with patch.object(chatgpt, "assemble_request", new=fake_assemble_request):
            _headers, request, current = session.prepare_request(
                prompt,
                system="override system",
                params={},
                stream=True,
                input_schema=SchemaInput,
                output_schema=SchemaOutput,
            )

        self.assertIs(request, assembled_body)
        self.assertEqual(observed["model"], "specimen-model")
        self.assertEqual(
            observed["messages"],
            [
                {"role": "system", "content": "override system"},
                {"role": "assistant", "content": "retained"},
                {
                    "role": "function",
                    "content": '{"value":7}',
                    "name": "SchemaInput",
                },
            ],
        )
        self.assertIs(observed["stream"], True)
        self.assertIs(observed["params"], session.params)
        self.assertEqual(
            observed["functions"],
            [
                {
                    "name": "SchemaInput",
                    "description": "A seam schema input.",
                    "parameters": {
                        "description": "A seam schema input.",
                        "properties": {"value": {"type": "integer"}},
                        "required": ["value"],
                        "type": "object",
                    },
                },
                {
                    "name": "SchemaOutput",
                    "description": "A seam schema output.",
                    "parameters": {
                        "description": "A seam schema output.",
                        "properties": {"result": {"type": "string"}},
                        "required": ["result"],
                        "type": "object",
                    },
                },
            ],
        )
        self.assertEqual(observed["function_call"], {"name": "SchemaOutput"})
        self.assertEqual(current.role, "function")
        self.assertEqual(current.content, '{"value":7}')
        self.assertEqual(current.name, "SchemaInput")


if __name__ == "__main__":
    unittest.main()
