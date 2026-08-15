# Spec: Voice Dictation for Diary and Media Entries

**Status:** ready-for-agent
**Area:** Notion Second Brain — `pages/diary.py`, `pages/media.py`, new `dictation.py`

## Problem Statement

Capturing a Diary Entry or Media Log by typing is slow and gets in the way of thinking, especially for reflective, end-of-day writing. The user thinks out loud in a mix of Urdu and English, and typing that out — then correcting it into readable English — is enough friction that entries don't get written at all (0 diary and 0 media entries saved to date). The user wants to just talk.

## Solution

Add a mic button to every free-text field in the Diary and Media flows. The user speaks in mixed Urdu/English; the app transcribes and translates the speech to English in one step, lightly polishes it, and drops the result into the **editable** field so the user can read and fix it before saving. The verbatim transcript is preserved in the entry's markdown record so nothing spoken is ever lost. The pipeline reuses the same third-party transcription service (OpenAI Whisper) already proven in the user's Writing Workflow project.

## User Stories

1. As a diary writer, I want to answer each of the 5 interview questions by speaking, so that I can reflect without the friction of typing.
2. As a bilingual speaker, I want to talk in a natural mix of Urdu and English, so that I don't have to consciously translate in my head while thinking.
3. As a bilingual speaker, I want my speech returned as English text, so that my Second Brain stays in one searchable language.
4. As a diary writer, I want the transcription and translation to happen in a single step, so that there's no visible two-stage delay or double round-trip.
5. As a diary writer, I want my spoken answer lightly cleaned up (filler removed, grammar fixed) while keeping my own phrasing and rhythm, so that the entry still reads as me and not as a generic rewrite.
6. As a media logger, I want my spoken reaction restructured into clean prose, so that a rougher out-loud reaction reads well when I revisit it.
7. As a media logger, I want the mic on the reaction field and the enrich follow-up field, so that I can respond to the LLM's follow-up question by voice too.
8. As any user, I want the polished text to land in an editable field, so that I can correct transcription mistakes before saving.
9. As any user, I want to re-record if a take goes badly, so that a bad transcription isn't trapped in the entry.
10. As a diary writer, I want the mic available on all 5 answers independently, so that I can mix voice and typing per question as I like.
11. As any user, I do NOT want a mic on the Title or URL fields, so that short structured fields stay fast to type and a URL is never dictated.
12. As a user reviewing an old entry, I want the verbatim transcript preserved alongside the polished version, so that I can always recover exactly what I said.
13. As a user searching my Second Brain, I want only the polished text embedded and searchable, so that search results aren't polluted by duplicate raw-and-polished copies of the same thought.
14. As a diary writer, I want the raw transcript stored per-answer in the entry's markdown file, so that each spoken answer is recoverable in context.
15. As a user, I want a clear indication while transcription and polishing are running, so that I know the app is working and not frozen.
16. As a user, I want a clear error if transcription fails, so that I can retry rather than lose my thought silently.
17. As a user, I want dictation to fall back gracefully so that if voice fails I can still just type into the same field.
18. As the project owner, I want the mic to use Streamlit's native recorder, so that the feature doesn't add a third-party UI dependency.
19. As the project owner, I want the transcription service to be the same one used in Writing Workflow, so that I maintain one proven voice pipeline across projects.
20. As a diary writer, I want my saved entry synthesis to continue working unchanged, so that voice input feeds the existing save/embed/connections flow rather than replacing it.
21. As a user, I want my polished spoken answer to flow into the same SQLite + markdown + vector-index save path as a typed answer, so that voice and typed entries are indistinguishable downstream.
22. As the project owner, I do NOT want a diary answer polished into my outward-facing newsletter voice, so that private reflection stays private in tone.

## Implementation Decisions

- **New module `dictation.py`** exposing a single entry function, the sole test seam:
  - `dictate(audio_bytes, mode) -> { raw_transcript, polished_text }` where `mode` is `"diary"` or `"media"`.
  - Internally: (1) a Whisper `audio.translations.create(model="whisper-1", file=...)` call that transcribes-and-translates mixed Urdu/English to English in one call; (2) a polish call to Claude Haiku 4.5 via OpenRouter. `mode` selects the polish prompt.
- **Transcribe-and-Translate is one step.** Whisper's `translations` endpoint always outputs English; there is no separate translation LLM call. (See CONTEXT.md and ADR 0001.)
- **Polish prompts differ by mode.** Diary: light-touch — remove filler, fix grammar, preserve the user's phrasing and rhythm. Media: medium — restructure into clean prose. Neither rewrites into the user's newsletter voice. The polish returns clean text with **no `[word?]` uncertainty markers** (unlike Writing Workflow's file-upload flow); the editable field is the correction mechanism.
- **Polish model/provider:** `anthropic/claude-haiku-4-5` via OpenRouter, reusing the existing `OPENROUTER_API_KEY`. Chosen over the direct Anthropic SDK client already used for diary synthesis because polish is a light task and this matches the Writing Workflow pipeline.
- **Transcription provider:** OpenAI Whisper via the `openai` SDK (already in `requirements.txt`), authenticated with a new `OPENAI_API_KEY` in `.env`. OpenRouter cannot proxy Whisper audio, hence a second provider and key. (See ADR 0001.)
- **Mic capture:** Streamlit 1.50 native `st.audio_input()`. No new UI dependency; Writing Workflow's `audio-recorder-streamlit` widget is deliberately not reused — only the Whisper+polish logic is.
- **Fields that get a mic:** the 5 Diary answers, the Media reaction, the Media enrich answer. Not Title, not URL.
- **Injection into fields:** `polished_text` is written into the target field's `session_state` key before the widget renders (diary uses the dynamic key `f"answer_{step}"`), so it appears in the editable text area on rerun. The user edits and saves as normal.
- **Save path unchanged.** Voice produces the same field text a typed answer would; the existing diary synthesis, SQLite insert, markdown write, vector upsert, and connections flow are untouched. Media likewise.
- **Raw Transcript storage:** appended to the entry's existing markdown file as a `## Raw voice transcript` section (per-answer for diary). **No schema migration** — `diary_entries` and `media_logs` tables are unchanged. The raw transcript is **not** embedded into the vector index.
- **No CONTEXT.md term conflicts.** New terms (Voice Capture, Raw Transcript, Polished Text, Transcribe-and-Translate, Polish) are defined in `Dictation Feature/CONTEXT.md`.

## Testing Decisions

- **A good test here asserts external behavior of the `dictate()` seam, not implementation.** It does not assert prompt strings verbatim, HTTP shapes, or Streamlit internals. It asserts what a caller observes: given audio and a mode, what comes back and which boundaries were hit.
- **Single module under test: `dictation.py`, via `dictate()`.** The two network boundaries (Whisper client, OpenRouter call) are mocked/stubbed; no real API calls in tests.
- **Cases to cover:**
  - Raw transcript is returned untouched — the exact Whisper output is preserved in `raw_transcript` regardless of polishing (Story 12).
  - `mode="diary"` routes to the light polish path; `mode="media"` routes to the medium polish path (Stories 5, 6). Assert via the distinct behavior/prompt selection, not the prompt text.
  - A Whisper failure surfaces as a clear error and short-circuits — polish is **not** called (Story 16).
  - A polish failure still preserves the raw transcript so the user's words aren't lost (Story 12, 17).
  - `polished_text` is what the caller receives for the field (Story 8).
- **Prior art:** none — the project currently has no test suite. This seam establishes the first tests. Keep them dependency-light (mock the `openai` client and the OpenRouter `httpx`/request boundary) so they run without network or keys.
- **Not tested:** Streamlit widget wiring, session_state injection, reruns, and the existing save/synthesis/embed path (already shipped, unchanged by this feature).

## Out of Scope

- **One-shot "brain dump" capture** that records a single monologue and splits it across the 5 diary fields. Deferred to a possible v2; v1 is strictly per-field.
- **`[word?]` uncertainty markers and a corrections UI** (as in Writing Workflow's file-upload flow). The editable field covers correction.
- **Keeping the original Urdu/mixed-language transcript.** Whisper's translations endpoint outputs English only; the non-English original is not retained.
- **Embedding or searching the raw transcript.** Only polished text is embedded.
- **Schema changes** to `diary_entries` / `media_logs`. Raw transcript lives in markdown only.
- **Mic on Title / URL fields.**
- **Reusing Writing Workflow's `audio-recorder-streamlit` widget.** Native capture only.
- **Rewriting entries into the user's newsletter/writing voice.**

## Further Notes

- **Dependency on `OPENAI_API_KEY`:** the feature does nothing until this key is added to `Notion Second Brain (Code)/.env`. The user has it in the Writing Workflow project. Whisper is the only consumer of it.
- **Reference implementation** for the pipeline lives at `Azeem's Writing Workflow/Code/` — `components/voice_input.py` (capture + Whisper call) and `pages/transcribe.py` (`_clean_transcript` polish call). Reuse the logic, not the mic widget.
- **Design docs** for this feature: `Dictation Feature/CONTEXT.md` (glossary) and `Dictation Feature/docs/adr/0001-whisper-via-separate-openai-key.md` (why two providers).
- **Cost/latency:** a full diary entry is up to 5 Whisper calls + 5 Haiku polish calls; both are cheap and fast. No batching needed for v1.
