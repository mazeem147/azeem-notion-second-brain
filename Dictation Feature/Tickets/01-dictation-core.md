# 01 — Dictation core (`dictate()` seam + tests)

**What to build:** A single module that turns a spoken, mixed Urdu/English recording into clean English text ready to drop into an entry field. It exposes one function — `dictate(audio_bytes, mode) -> { raw_transcript, polished_text }` — that transcribes-and-translates the audio to English in one Whisper call, then polishes the result with an LLM. `mode` is `"diary"` (light-touch: remove filler, fix grammar, keep the user's phrasing) or `"media"` (medium: restructure into clean prose). Neither mode rewrites into the user's newsletter voice, and the polish returns clean text with no `[word?]` markers. This is the one test seam for the whole feature; the Diary and Media pages (tickets 02, 03) call it.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] `dictate(audio_bytes, mode)` returns both `raw_transcript` (verbatim Whisper output) and `polished_text`.
- [ ] Transcription uses OpenAI Whisper `audio.translations.create(model="whisper-1", ...)` — one call does transcribe + translate to English (per ADR 0001).
- [ ] Polish uses `anthropic/claude-haiku-4-5` via OpenRouter, reusing `OPENROUTER_API_KEY`.
- [ ] `mode="diary"` uses the light prompt; `mode="media"` uses the medium prompt.
- [ ] First test suite in the project; both network boundaries (Whisper client, OpenRouter call) are mocked — no real API calls, no keys needed to run tests.
- [ ] Test: `raw_transcript` is the exact Whisper output, unaffected by polishing.
- [ ] Test: `mode` routes to the correct polish path (diary vs media).
- [ ] Test: a Whisper failure surfaces a clear error and does NOT call polish.
- [ ] Test: a polish failure still preserves the raw transcript so spoken words aren't lost.
- [ ] No `[word?]` uncertainty markers in the returned polished text.
