"""Tests for the dictate() seam.

These assert the external behaviour a caller observes — given audio and a mode,
what comes back and which boundaries were hit — not prompt strings, HTTP shapes,
or Streamlit internals. Both network boundaries are mocked via the ``wire``
fixture in conftest.py; no real API calls, no keys.
"""

import pytest

import dictation


# ── The returned shape ────────────────────────────────────────────────────────

def test_returns_raw_and_polished(wire):
    wire(transcript="hello world", polished="Hello, world.")
    result = dictation.dictate(b"audio", mode="diary")
    assert set(result) == {"raw_transcript", "polished_text"}
    assert result["raw_transcript"] == "hello world"
    assert result["polished_text"] == "Hello, world."


def test_polished_text_is_what_caller_receives(wire):
    # Story 8 — the Polished Text is what lands in the editable field.
    wire(transcript="rough take", polished="A clean, readable version.")
    result = dictation.dictate(b"audio", mode="media")
    assert result["polished_text"] == "A clean, readable version."


# ── Raw transcript is preserved untouched (Story 12) ──────────────────────────

def test_raw_transcript_is_the_exact_whisper_output(wire):
    wire(transcript="the exact words I spoke", polished="something entirely different")
    result = dictation.dictate(b"audio", mode="diary")
    # Polishing must never alter the Raw Transcript.
    assert result["raw_transcript"] == "the exact words I spoke"
    assert result["raw_transcript"] != result["polished_text"]


def test_raw_transcript_is_verbatim_including_surrounding_whitespace(wire):
    # "verbatim Whisper output" / "exact Whisper output" — no trimming.
    wire(transcript="  spoken with edges  \n", polished="clean")
    result = dictation.dictate(b"audio", mode="diary")
    assert result["raw_transcript"] == "  spoken with edges  \n"


# ── Transcribe-and-Translate uses the right Whisper endpoint ──────────────────

def test_uses_whisper_translations_endpoint(wire):
    fake_openai, _ = wire(transcript="x")
    dictation.dictate(b"audio", mode="diary")
    # Exactly one translations call (transcribe + translate in one), on whisper-1.
    # The ticket names this endpoint + model as an acceptance criterion; we assert
    # only that contract, not the incidental buffer shape.
    calls = fake_openai._translations.calls
    assert len(calls) == 1
    assert calls[0]["model"] == "whisper-1"


# ── mode routes to the correct polish path (Stories 5, 6) ─────────────────────

def test_diary_mode_selects_the_diary_prompt(wire):
    _, fake_post = wire()
    dictation.dictate(b"audio", mode="diary")
    assert fake_post.system_prompt == dictation._POLISH_PROMPTS["diary"]


def test_media_mode_selects_the_media_prompt(wire):
    _, fake_post = wire()
    dictation.dictate(b"audio", mode="media")
    assert fake_post.system_prompt == dictation._POLISH_PROMPTS["media"]


def test_diary_and_media_take_distinct_polish_paths(wire):
    _, diary_post = wire()
    dictation.dictate(b"audio", mode="diary")
    diary_prompt = diary_post.system_prompt

    _, media_post = wire()
    dictation.dictate(b"audio", mode="media")
    media_prompt = media_post.system_prompt

    assert diary_prompt != media_prompt


def test_polish_receives_the_raw_transcript_as_input(wire):
    _, fake_post = wire(transcript="mixed urdu english, translated")
    dictation.dictate(b"audio", mode="diary")
    assert fake_post.user_content == "mixed urdu english, translated"


def test_invalid_mode_raises_before_any_network_call(wire):
    fake_openai, fake_post = wire()
    with pytest.raises(ValueError):
        dictation.dictate(b"audio", mode="newsletter")
    assert fake_openai._translations.calls == []
    assert fake_post.calls == []


# ── A Whisper failure short-circuits before Polish (Story 16) ─────────────────

def test_whisper_failure_raises_clear_error_and_skips_polish(wire):
    _, fake_post = wire(whisper_error=RuntimeError("whisper 500"))
    with pytest.raises(dictation.TranscriptionError):
        dictation.dictate(b"audio", mode="diary")
    # Polish must never be reached when transcription fails.
    assert fake_post.calls == []


def test_transcription_error_message_is_clear(wire):
    wire(whisper_error=RuntimeError("connection reset"))
    with pytest.raises(dictation.TranscriptionError) as exc:
        dictation.dictate(b"audio", mode="diary")
    assert "transcription failed" in str(exc.value).lower()


def test_missing_openai_key_is_a_config_error_not_a_transcription_failure(wire, monkeypatch):
    # A missing key is a misconfiguration, not a Whisper failure — it must not be
    # dressed up as a TranscriptionError (which would blame the audio/the call).
    wire()
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(KeyError):
        dictation.dictate(b"audio", mode="diary")


# ── A Polish failure preserves the raw transcript (Stories 12, 17) ────────────

def test_polish_exception_falls_back_to_raw_transcript(wire):
    wire(transcript="my spoken words", polish_raise=RuntimeError("polish down"))
    result = dictation.dictate(b"audio", mode="diary")
    # Words are never lost: polished_text falls back to the raw transcript.
    assert result["raw_transcript"] == "my spoken words"
    assert result["polished_text"] == "my spoken words"


def test_polish_http_error_falls_back_to_raw_transcript(wire):
    wire(
        transcript="my spoken words",
        polish_status_error=RuntimeError("502 Bad Gateway"),
    )
    result = dictation.dictate(b"audio", mode="media")
    assert result["polished_text"] == "my spoken words"


# ── No [word?] uncertainty markers in the returned polished text ──────────────

def test_returned_polished_text_has_no_uncertainty_markers(wire):
    # Contract: whatever polish returns, the caller never sees [word?] markers.
    wire(
        transcript="raw",
        polished="I went to the [bazaar?] and bought [mangoes?].",
    )
    result = dictation.dictate(b"audio", mode="diary")
    assert "?]" not in result["polished_text"]
    assert "[" not in result["polished_text"]
    # Best-guess words are kept, just unwrapped.
    assert result["polished_text"] == "I went to the bazaar and bought mangoes."
