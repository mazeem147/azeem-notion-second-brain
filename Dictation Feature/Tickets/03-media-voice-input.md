# 03 — Media voice input

**What to build:** A microphone on the media log's free-text fields — the **reaction** and the **enrich** follow-up answer — so the user can speak their reaction to a piece of content. Recorded speech is transcribed, translated to English, and polished at the medium level (restructured into clean prose), then lands in the **editable** field for review before saving. Saving flows through the existing media save path unchanged. The verbatim transcript is preserved.

**Blocked by:** 01 — Dictation core. (Independent of ticket 02 — different page, can run in parallel.)

**Status:** ready-for-agent

- [ ] A native `st.audio_input()` mic is available on the media reaction field and the enrich follow-up answer field.
- [ ] No mic on Title or URL.
- [ ] Recording calls `dictate(mode="media")` and writes `polished_text` into the editable field for review; the user can edit and re-record before saving.
- [ ] A spinner/indicator shows while transcription + polish run; a failure shows a clear error and the user can still type into the same field.
- [ ] On save, the existing media SQLite/markdown/embed flow runs unchanged; the polished reaction is stored and embedded exactly as a typed reaction would be.
- [ ] The `raw_transcript` is appended to the media `.md` under a `## Raw voice transcript` section; it is NOT embedded into the vector index.
- [ ] No schema change to `media_logs`.
- [ ] `OPENAI_API_KEY` present in `.env` is documented as the prerequisite for the mic to function.
