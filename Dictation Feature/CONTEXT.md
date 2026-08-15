# Notion Second Brain

A local, portable webapp that imports the user's Notion notes, embeds them for local search, and lets the user chat with their own notes and capture new ones (diary, media). This glossary fixes the language of the domain so code and conversation stay aligned.

## Entries

**Diary Entry**:
A dated personal journal record produced by answering the fixed 5-question interview. What gets stored and searched is the synthesized first-person entry, not the raw answers.
_Avoid_: Journal, log, note

**Media Log**:
A record of the user's reaction to a piece of consumed content (Article, Book, Podcast, Video), with a type, rating, and free-text reaction.
_Avoid_: Review, bookmark, note

**Synthesis**:
The condensed, LLM-written version of a Diary Entry — the 5 raw answers distilled into 3–5 first-person sentences. This is the text that is embedded and searched.
_Avoid_: Summary, digest

## Voice Capture

**Voice Capture**:
Speaking an answer instead of typing it. Applies only to free-text fields: the 5 Diary answers, the Media reaction, and the Media enrich answer. Never to Title or URL.
_Avoid_: Recording, dictation, audio note

**Raw Transcript**:
The verbatim English text Whisper returns from a single Voice Capture, before polishing. Preserved in the entry's markdown file for the record; never embedded or searched.
_Avoid_: Transcription, raw text, original

**Polished Text**:
The Raw Transcript after a light (diary) or medium (media) LLM cleanup. This is what lands in the editable field, what the user saves, and — via the normal save path — what gets embedded.
_Avoid_: Cleaned text, corrected text, final text

**Transcribe-and-Translate**:
The single Whisper `translations` call that turns mixed Urdu/English speech into English text. It is one step, not two — Whisper's translations endpoint always outputs English.
_Avoid_: Transcription (implies same-language), STT

**Polish**:
The separate LLM pass that turns a Raw Transcript into Polished Text. Light-touch for diary (keep the user's phrasing, remove filler, fix grammar); medium for media (restructure into clean prose). Never rewrites into the user's outward-facing newsletter voice.
_Avoid_: Rewrite, edit, clean
