"""A scripted fake of the Anthropic client, so the agent loop is tested offline."""

from types import SimpleNamespace as NS

import pytest


def text(t):
    return NS(type="text", text=t)


def tool(name, inp, id_="tu_1"):
    return NS(type="tool_use", name=name, input=inp, id=id_)


def response(content, stop="tool_use"):
    return NS(content=content, stop_reason=stop,
              usage=NS(input_tokens=1000, output_tokens=200,
                       cache_read_input_tokens=0, cache_creation_input_tokens=0))


class FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.beta = NS(messages=NS(create=self._create))

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        return self.responses.pop(0)


@pytest.fixture
def fake():
    return FakeClient
