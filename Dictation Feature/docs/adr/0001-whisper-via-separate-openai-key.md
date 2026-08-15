# Voice input uses OpenAI Whisper directly, via its own API key

Voice capture (transcribe + translate to English in one call) uses OpenAI's Whisper `audio.translations` endpoint via the `openai` SDK, authenticated with a dedicated `OPENAI_API_KEY`. The polish step reuses the existing `OPENROUTER_API_KEY` (Claude Haiku 4.5).

We already route all our Claude traffic through OpenRouter, so the obvious instinct is to route audio there too and keep a single provider. We can't: OpenRouter does not proxy Whisper audio transcription. The alternatives were a local model (`faster-whisper` — no per-call cost and no new key, but heavier install, slower on CPU, and no proven code) or the hosted Whisper API. We chose the hosted API because the exact pipeline already runs in the user's "Writing Workflow" project and handles mixed Urdu/English well, so reuse beats rebuild.

Consequence: the project now depends on two inference providers and two keys. `OPENAI_API_KEY` must be added to `.env` (it currently has `NOTION_TOKEN`, `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY`), and audio egress goes to OpenAI even though everything else deliberately stays local or on OpenRouter.
