"""Shared fixtures for the dictation test suite.

Both network boundaries are mocked here — the OpenAI Whisper client and the
OpenRouter polish request — so the suite runs with no real API calls and no keys.
"""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

# Make the project root importable so ``import dictation`` works from tests/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture(autouse=True)
def _dummy_keys(monkeypatch):
    """Provide dummy keys so no real credentials are needed to run the suite.

    The network boundaries are mocked, so these values are never used to
    authenticate anything — they just stand in for a configured environment.
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")


class FakeTranslations:
    """Stand-in for ``client.audio.translations``.

    Records the arguments of the single ``create`` call and returns a canned
    transcript, or raises to simulate a Whisper failure.
    """

    def __init__(self, text="", error=None):
        self._text = text
        self._error = error
        self.calls = []

    def create(self, model, file):
        # ``file`` is a BytesIO with a .name — read it so we exercise the buffer.
        self.calls.append({"model": model, "file_name": getattr(file, "name", None)})
        if self._error is not None:
            raise self._error
        return SimpleNamespace(text=self._text)


class FakeOpenAI:
    """Stand-in for ``openai.OpenAI``. Captures the api_key and exposes audio."""

    last_instance = None

    def __init__(self, translations):
        self._translations = translations

    def __call__(self, api_key=None):
        self.api_key = api_key
        self.audio = SimpleNamespace(translations=self._translations)
        FakeOpenAI.last_instance = self
        return self


class FakeResponse:
    """Minimal stand-in for an httpx.Response from OpenRouter."""

    def __init__(self, content="", status_error=None):
        self._content = content
        self._status_error = status_error

    def raise_for_status(self):
        if self._status_error is not None:
            raise self._status_error

    def json(self):
        return {"choices": [{"message": {"content": self._content}}]}


class FakePost:
    """Stand-in for ``httpx.post``. Records each request and returns/raises."""

    def __init__(self, content="", status_error=None, raise_exc=None):
        self._content = content
        self._status_error = status_error
        self._raise_exc = raise_exc
        self.calls = []

    def __call__(self, url, headers=None, json=None, timeout=None):
        self.calls.append({"url": url, "headers": headers, "json": json})
        if self._raise_exc is not None:
            raise self._raise_exc
        return FakeResponse(self._content, status_error=self._status_error)

    @property
    def system_prompt(self):
        """The system message content of the most recent polish request."""
        messages = self.calls[-1]["json"]["messages"]
        return next(m["content"] for m in messages if m["role"] == "system")

    @property
    def user_content(self):
        """The user message content of the most recent polish request."""
        messages = self.calls[-1]["json"]["messages"]
        return next(m["content"] for m in messages if m["role"] == "user")


@pytest.fixture
def wire(monkeypatch):
    """Wire both boundaries with fakes.

    Returns a callable ``wire(transcript=..., whisper_error=..., polished=...,
    polish_status_error=..., polish_raise=...)`` that installs the fakes and
    returns ``(fake_openai, fake_post)`` for assertions.
    """
    import dictation

    def _install(
        transcript="raw whisper text",
        whisper_error=None,
        polished="polished text",
        polish_status_error=None,
        polish_raise=None,
    ):
        translations = FakeTranslations(text=transcript, error=whisper_error)
        fake_openai = FakeOpenAI(translations)
        fake_post = FakePost(
            content=polished,
            status_error=polish_status_error,
            raise_exc=polish_raise,
        )
        monkeypatch.setattr(dictation, "OpenAI", fake_openai)
        monkeypatch.setattr(dictation.httpx, "post", fake_post)
        return fake_openai, fake_post

    return _install
