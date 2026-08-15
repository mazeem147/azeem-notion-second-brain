# 02 — Diary voice input

**What to build:** A microphone on each of the 5 diary interview answers so the user can speak instead of type. The user records an answer, it gets transcribed, translated to English, and lightly polished, and the result lands in the **editable** answer field — the user reads it, fixes anything wrong, and saves. Saving flows through the existing diary synthesis → SQLite → markdown → vector-index → connections path with no change. The verbatim transcript is preserved so nothing spoken is ever lost.

**Blocked by:** 01 — Dictation core.

**Status:** ready-for-agent

- [ ] A native `st.audio_input()` mic is available on each of the 5 diary answer fields (not on any non-text field).
- [ ] Recording an answer calls `dictate(mode="diary")` and writes `polished_text` into the editable answer field before the widget renders (dynamic key `answer_{step}`), so it appears in the text area on rerun.
- [ ] The user can edit the polished text and re-record before saving.
- [ ] A spinner/indicator shows while transcription + polish run; a transcription failure shows a clear error and the user can still type into the same field.
- [ ] On save, the existing synthesis/SQLite/markdown/embed/connections flow runs unchanged; a voice answer is indistinguishable from a typed one downstream.
- [ ] The per-answer `raw_transcript` is appended to the diary `.md` under a `## Raw voice transcript` section; it is NOT embedded into the vector index.
- [ ] No schema change to `diary_entries`.
- [ ] `OPENAI_API_KEY` present in `.env` is documented as the prerequisite for the mic to function (one-line user action).
