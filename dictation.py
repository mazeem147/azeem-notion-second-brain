"""dictation.py — the Voice Capture pipeline for Diary and Media entries.

Exposes a single entry point, the sole test seam for the feature:

    dictate(audio_bytes, mode) -> {"raw_transcript": str, "polished_text": str}

It turns a spoken, mixed Urdu/English recording into clean English text ready to
drop into an entry field, in two internal steps:

1. Transcribe-and-Translate — one OpenAI Whisper ``audio.translations`` call that
   transcribes AND translates the speech to English (Whisper's translations
   endpoint always outputs English). Uses ``OPENAI_API_KEY``. See ADR 0001.
2. Polish — one Claude Haiku 4.5 call via OpenRouter that cleans the Raw
   Transcript into Polished Text. ``mode`` selects the prompt: ``"diary"`` is
   light-touch (keep the speaker's phrasing, remove filler, fix grammar);
   ``"media"`` is medium (restructure a rough reaction into clean prose).

Neither mode rewrites into the user's outward-facing newsletter voice, and the
returned Polished Text carries no ``[word?]`` uncertainty markers — the editable
field is the correction mechanism.

Design contract that the tests pin down:
- ``raw_transcript`` is the verbatim Whisper output, never altered by polishing.
- A Whisper failure surfaces as a clear error and short-circuits — Polish is not
  called, so a transcription problem is never silently masked.
- A Polish failure still returns the Raw Transcript as the Polished Text, so the
  user's spoken words are never lost.
"""

import io
import os
import re

import httpx
from openai import OpenAI

# ── Polish configuration ──────────────────────────────────────────────────────

_POLISH_MODEL = "anthropic/claude-haiku-4-5"
_OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Diary: light-touch. Keep the speaker's own phrasing and rhythm — this is a
# private reflection, not outward-facing writing.
_DIARY_POLISH_PROMPT = (
    "You are lightly cleaning up a spoken diary answer that has already been "
    "translated into English. Remove filler words, false starts, and verbal tics; "
    "fix grammar and punctuation. Keep the speaker's own phrasing, word choices, and "
    "rhythm — do NOT restructure, summarise, or rewrite it into a more polished, "
    "literary, or outward-facing voice. It must still read as the speaker's own "
    "private reflection. Do not add commentary, headings, or uncertainty markers. "
    "Return only the cleaned answer text."
)

# Media: medium. A rough, out-loud reaction becomes clean, readable prose.
_MEDIA_POLISH_PROMPT = (
    "You are cleaning up a spoken reaction to a piece of media that has already been "
    "translated into English. Restructure the rough, out-loud reaction into clear, "
    "readable prose: fix grammar and punctuation, remove filler and repetition, and "
    "organise the thoughts into coherent sentences. Stay faithful to what the speaker "
    "meant — do NOT invent opinions or rewrite it into a formal or newsletter voice. "
    "Do not add commentary, headings, or uncertainty markers. "
    "Return only the cleaned reaction text."
)

_POLISH_PROMPTS = {
    "diary": _DIARY_POLISH_PROMPT,
    "media": _MEDIA_POLISH_PROMPT,
}

# Matches Writing Workflow's [word?] uncertainty markers. This pipeline never
# emits them, but we strip any that slip through so the editable field stays clean.
_UNCERTAIN_RE = re.compile(r"\[([^\[\]]+?)\?\]")


class TranscriptionError(RuntimeError):
    """Raised when Transcribe-and-Translate fails, so the caller can prompt a retry.

    Surfacing this short-circuits the pipeline before Polish is ever called.
    """


def dictate(audio_bytes: bytes, mode: str) -> dict:
    """Turn a Voice Capture into ``{raw_transcript, polished_text}``.

    Args:
        audio_bytes: Raw audio bytes from ``st.audio_input()``.
        mode: ``"diary"`` (light polish) or ``"media"`` (medium polish).

    Returns:
        ``{"raw_transcript": <verbatim Whisper output>,
           "polished_text": <cleaned text for the editable field>}``.

    Raises:
        ValueError: if ``mode`` is not ``"diary"`` or ``"media"``.
        TranscriptionError: if Whisper fails. Polish is not called in this case.
    """
    if mode not in _POLISH_PROMPTS:
        raise ValueError(
            "mode must be 'diary' or 'media', got " + repr(mode)
        )

    # Step 1 — Transcribe-and-Translate. A failure here raises and short-circuits;
    # Polish is never reached, so a transcription problem is surfaced, not masked.
    raw_transcript = _transcribe_and_translate(audio_bytes)

    # Step 2 — Polish. Intentionally broad: any polish failure (network, HTTP,
    # a missing OPENROUTER_API_KEY, a malformed response) falls back to the Raw
    # Transcript. Losing a diary/media entry the user just spoke is the worst
    # outcome here, so an unpolished-but-preserved answer always beats an error.
    try:
        polished_text = _polish(raw_transcript, mode)
    except Exception:
        polished_text = raw_transcript

    return {"raw_transcript": raw_transcript, "polished_text": polished_text}


def _transcribe_and_translate(audio_bytes: bytes) -> str:
    """One Whisper ``translations`` call: mixed Urdu/English speech -> English text.

    Returns the Raw Transcript verbatim — Whisper's exact output, unstripped, so
    the record preserved in markdown is truly what was said.
    """
    try:
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        buf = io.BytesIO(audio_bytes)
        buf.name = "recording.wav"
        result = client.audio.translations.create(model="whisper-1", file=buf)
        return result.text
    except Exception as e:
        raise TranscriptionError("Voice transcription failed: " + str(e)) from e


def _polish(raw_transcript: str, mode: str) -> str:
    """Clean the Raw Transcript into Polished Text via Claude Haiku 4.5 on OpenRouter."""
    key = os.environ["OPENROUTER_API_KEY"]
    resp = httpx.post(
        _OPENROUTER_URL,
        headers={
            "Authorization": "Bearer " + key,
            "Content-Type": "application/json",
        },
        json={
            "model": _POLISH_MODEL,
            "messages": [
                {"role": "system", "content": _POLISH_PROMPTS[mode]},
                {"role": "user", "content": raw_transcript},
            ],
        },
        timeout=60,
    )
    resp.raise_for_status()
    text = resp.json()["choices"][0]["message"]["content"].strip()
    return _strip_uncertainty_markers(text)


def _strip_uncertainty_markers(text: str) -> str:
    """Turn any stray ``[word?]`` marker into its best-guess word."""
    return _UNCERTAIN_RE.sub(lambda m: m.group(1), text)
