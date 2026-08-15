"""diary_markdown.py — pure helpers for assembling the Diary Entry markdown record.

Kept import-safe (no Streamlit, no DB, no network) so the markdown assembly can be
unit-tested directly. ``pages/diary.py`` imports ``build_raw_transcript_section()``
to append each spoken answer's Raw Transcript to the entry's ``.md`` file, under a
``## Raw voice transcript`` section, so nothing spoken is ever lost. The Raw
Transcript lives here only — it is never embedded into the vector index.
"""

RAW_TRANSCRIPT_HEADING = "## Raw voice transcript"


def build_raw_transcript_section(questions: list[str], raw_transcripts: list[str]) -> str:
    """Return the ``## Raw voice transcript`` markdown section for a Diary Entry.

    Each spoken answer's verbatim Raw Transcript is recorded per-question so a
    spoken answer is recoverable in context. Answers that were typed (no
    transcript, or a blank one) are skipped. When no answer was spoken this
    returns ``""`` — so a fully-typed entry's markdown is byte-for-byte what it
    would have been before this feature, keeping voice and typed entries
    indistinguishable on disk too.

    Args:
        questions: the diary questions, in order.
        raw_transcripts: the per-answer Raw Transcripts, positionally aligned with
            ``questions``. A blank/empty/``None`` entry marks a typed answer.

    Returns:
        A markdown string that opens with a ``---`` rule and the section heading,
        or ``""`` when there is nothing spoken to record.
    """
    spoken = [
        (question, transcript)
        for question, transcript in zip(questions, raw_transcripts)
        if transcript and transcript.strip()
    ]
    if not spoken:
        return ""

    lines = ["---", "", RAW_TRANSCRIPT_HEADING, ""]
    for question, transcript in spoken:
        lines.append(f"### {question}")
        lines.append(transcript)  # verbatim — the record must match what was said
        lines.append("")
    return "\n".join(lines)
