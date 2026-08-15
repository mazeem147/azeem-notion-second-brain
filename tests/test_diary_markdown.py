"""Tests for build_raw_transcript_section() — the diary markdown Raw Transcript append.

This is the one non-UI helper the dictation feature adds to the diary flow, so it
gets a direct test. It is pure (no Streamlit, no DB, no network), so nothing is
mocked. The Streamlit widget wiring, session_state injection, and reruns are — per
the spec's Testing Decisions — deliberately not unit-tested; the dictate() seam is
the test boundary and is covered in test_dictation.py.
"""

from diary_markdown import RAW_TRANSCRIPT_HEADING, build_raw_transcript_section

QUESTIONS = [
    "What happened today?",
    "What are you grateful for?",
    "What's on your mind?",
    "What are you wrestling with?",
    "One thing for tomorrow?",
]


def _blanks():
    return ["", "", "", "", ""]


# ── Nothing spoken → nothing appended ─────────────────────────────────────────

def test_no_voice_answers_returns_empty_string():
    # A fully-typed entry must produce byte-for-byte the same markdown as before.
    assert build_raw_transcript_section(QUESTIONS, _blanks()) == ""


def test_whitespace_only_transcripts_count_as_typed():
    transcripts = ["   ", "\n", "\t ", "", "  \n  "]
    assert build_raw_transcript_section(QUESTIONS, transcripts) == ""


def test_none_transcripts_are_skipped():
    assert build_raw_transcript_section(QUESTIONS, [None, None, None, None, None]) == ""


# ── Spoken answers are recorded under the heading ─────────────────────────────

def test_single_spoken_answer_has_heading_and_its_question():
    transcripts = _blanks()
    transcripts[0] = "today I shipped the diary voice feature"
    section = build_raw_transcript_section(QUESTIONS, transcripts)

    assert RAW_TRANSCRIPT_HEADING in section
    assert "### What happened today?" in section
    assert "today I shipped the diary voice feature" in section
    # Opens with a rule so it is visually separated from the answers above it.
    assert section.startswith("---")


def test_only_spoken_answers_appear_not_typed_ones():
    transcripts = _blanks()
    transcripts[0] = "spoken answer one"
    transcripts[2] = "spoken answer three"
    section = build_raw_transcript_section(QUESTIONS, transcripts)

    assert "spoken answer one" in section
    assert "spoken answer three" in section
    # The typed questions must not get a heading in the raw section.
    assert "### What are you grateful for?" not in section
    assert "### One thing for tomorrow?" not in section
    # Exactly the two spoken questions are recorded.
    assert section.count("### ") == 2


def test_transcript_is_recorded_verbatim():
    # "verbatim Whisper output" — surrounding whitespace and all, as the record
    # must match exactly what was said.
    transcripts = _blanks()
    transcripts[1] = "  edges preserved  "
    section = build_raw_transcript_section(QUESTIONS, transcripts)
    assert "  edges preserved  " in section


def test_each_spoken_transcript_pairs_with_its_own_question():
    transcripts = _blanks()
    transcripts[3] = "wrestling-answer"
    section = build_raw_transcript_section(QUESTIONS, transcripts)
    # The transcript follows its matching question heading, not a different one.
    heading_then_text = "### What are you wrestling with?\nwrestling-answer"
    assert heading_then_text in section
