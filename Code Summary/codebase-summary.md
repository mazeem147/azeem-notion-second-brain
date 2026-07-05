# Notion Second Brain — Codebase Summary

A local Streamlit webapp that imports Notion notes, embeds them with a local model, and lets you chat with your own notes via Claude API (RAG). Portable — runs from a single folder.

**Run command:**
```bash
./venv/bin/streamlit run app.py
```

---

## Architecture

Two pipelines:

- **Write pipeline:** Notion API → `notion_import.py` → `data/raw/*.md` → `indexer.py` → ChromaDB. Diary and media entries skip `notion_import` and `indexer` — they upsert directly via `embed_utils.py` at save time.
- **Read pipeline:** User query → embed locally → ChromaDB → top-k chunks → Claude with context → streamed answer.

Two databases:
- **ChromaDB** (`data/chroma/`) — vector store for semantic search across all sources
- **SQLite** (`data/brain.db`) — structured storage for diary entries, media logs, chat sessions

---

## File Structure

```
Notion Second Brain (Code)/
├── app.py                   ← navigation entry point
├── indexer.py               ← CLI: rebuild full ChromaDB index from data/raw/
├── notion_import.py         ← CLI: pull pages from Notion API into data/raw/
├── db.py                    ← SQLite helpers (init + get_conn)
├── embed_utils.py           ← chunking + ChromaDB upsert (used by diary/media)
├── connections.py           ← find + explain related past notes via Claude
├── ui.py                    ← CSS injection + UI components
├── requirements.txt
├── .env                     ← ANTHROPIC_API_KEY, NOTION_TOKEN
├── .streamlit/
│   └── config.toml          ← theme (iris violet #6e56cf, DM Sans)
├── data/
│   ├── raw/                 ← markdown exports from Notion
│   │   ├── diary/           ← diary entries saved as .md
│   │   └── media/           ← media log entries saved as .md
│   ├── chroma/              ← ChromaDB vector store
│   └── brain.db             ← SQLite
├── pages/
│   ├── chat.py              ← Chat page (RAG + streaming + session history)
│   ├── diary.py             ← Daily Diary (interview → Claude synthesis → save)
│   ├── media.py             ← Media Log (form → Claude follow-up → save)
│   └── sync.py              ← Sync page (Notion pull + index rebuild)
└── Code Summary/
    └── codebase-summary.md  ← this file
```

---

## Key Technical Choices

| Concern | Choice | Detail |
|---|---|---|
| Embedding model | `all-MiniLM-L6-v2` | Local, ~90MB, 384-dim vectors, no API cost |
| Vector store | ChromaDB PersistentClient | `data/chroma/`, cosine similarity (`hnsw:space: cosine`) |
| LLM | `claude-sonnet-4-6` | OpenRouter API (OpenAI-compatible client), streaming via `chat.completions.create()` |
| Chunk size | 350 words, 50-word overlap | Balances coherence vs retrieval precision |
| Structured DB | SQLite | diary_entries, media_logs, chat_sessions |
| Session management | JSON in SQLite `chat_sessions` | Chat history persists across app restarts |
| Navigation | `st.navigation()` with `position="hidden"` | Custom sidebar buttons via `app.py` |

---

## Design System

- **Palette:** sidebar `#12111c` (ink), body `#faf9f7` (warm white), accent `#6e56cf` (iris violet)
- **Font:** DM Sans (body), DM Mono (timestamps/metadata)
- **CSS:** injected via `ui.py`'s `apply_styles()` — called once in `app.py`

---

## File-by-File Reference

### `app.py`
Navigation entry point. Defines 4 pages (Chat, Diary, Media Log, Sync), renders the global sidebar with nav buttons, calls `apply_styles()` and `sidebar_brand()` from `ui.py`.

### `db.py`
SQLite helpers. `init_db()` creates three tables if missing:
- `diary_entries(id, date, content, created_at)`
- `media_logs(id, url, title, media_type, rating, reaction, created_at)`
- `chat_sessions(id, title, messages JSON, created_at, updated_at)`

`get_conn()` returns a connection with `row_factory = sqlite3.Row`.

### `embed_utils.py`
Shared chunking + ChromaDB helpers. Used by diary and media pages for immediate indexing on save.
- `load_embed_model()` — `@st.cache_resource`, loads `all-MiniLM-L6-v2`
- `load_collection()` — `@st.cache_resource`, gets/creates ChromaDB collection with cosine metadata
- `chunk_text(text)` — splits into 350-word chunks with 50-word overlap
- `upsert_document(doc_id_prefix, text, metadata)` — chunks, embeds, upserts to ChromaDB

### `indexer.py`
CLI script to rebuild the full index from `data/raw/`. Deletes and recreates the ChromaDB collection on each run (clean slate). Also exposes `run_index(progress_fn)` called by the Sync page.

Key behaviour:
- Reads YAML frontmatter from each `.md` file for title, notion_url, created, page_id, source
- Sets `source`/`source_type` = `"notion"` (or whatever the frontmatter says) on every chunk
- Batch embeds in groups of 32 to manage memory
- Returns `(total_chunks, files_indexed, files_skipped)`

### `notion_import.py`
CLI script to pull Notion pages. Idempotent — skips files that already exist in `data/raw/`. Also exposes `run_sync(progress_fn)` called by the Sync page.

Key behaviour:
- Paginates `notion.search` to discover all pages shared with the integration
- Rate-limited: 0.35s sleep between API calls, retries on `rate_limited` errors
- Renders all block types to Markdown; child pages render as a link, not inlined
- `build_filename(title, page_id)` — slug + 8-char page ID hash for uniqueness
- Returns `(written, skipped, failed)`

### `connections.py`
Called after every diary/media save. Finds top-3 related past notes and asks Claude to explain the connection in one sentence.
- `find_connections(new_text, embed_model, collection, exclude_prefix)` — queries ChromaDB, deduplicates by source file, excludes the just-saved entry
- `explain_connections(new_text, connections)` — single Claude call, numbered list response parsed into per-connection `explanation` keys

### `ui.py`
All CSS injected as a single `<style>` block via `st.markdown`. Components:
- `apply_styles()` — call once per page to inject all CSS
- `sidebar_brand()` — renders the 🧠 Second Brain header
- `question_card(text)` — styled question display for diary flow
- `connection_card(title, date, explanation, text, url)` — styled related-note card

### `pages/chat.py`
RAG chat with session history.

Flow:
1. User types → retrieve top-N chunks from ChromaDB
2. Build `api_messages`: last 6 turns of history + current query with `<retrieved_notes>` block
3. Stream response via OpenRouter `openrouter.chat.completions.create(stream=True)`
4. Save messages + chunk metadata to `chat_sessions` in SQLite

Session management: create session on first message, title = first 60 chars of query. Sidebar lists sessions with delete button.

Key state: `current_session_id`, `messages`, `session_chunks` (maps message index → chunks for source display).

### `pages/diary.py`
5-question interview flow with Claude synthesis.

State machine via `diary_step` (0–5) and `diary_saved`:
1. **Steps 0–4:** show one question at a time with progress dots, collect answers into `diary_answers`
2. **Step 5 (review):** display all Q&A pairs, "Save entry" button
3. **On save:** call `synthesize_entry()` → Claude writes a 3-5 sentence first-person entry from the raw Q&A → save synthesis to SQLite + embed → raw Q&A preserved in the `.md` file → find connections → show saved state
4. **Saved state:** show synthesis confirmation + connection cards

`synthesize_entry(questions, answers)` — single Claude call (`max_tokens=400`), returns the synthesised entry text.

Sidebar shows last 12 diary entries from SQLite in expanders.

### `pages/media.py`
Media logging with Claude take enrichment.

State machine via `ml_step` ("form" → "enrich" → "done"):
1. **form:** title, URL, type radio, star rating, reaction textarea → submit
2. **enrich:** `generate_follow_up()` asks Claude for one follow-up question; user answers or skips
3. **done:** save to SQLite + embed + find connections; show success + connection cards; "Log another" resets state

`generate_follow_up(title, media_type, reaction)` — Claude picks the most interesting angle (behaviour change, surprising idea, disagreement, connection to prior knowledge).

`save_entry(title, url, media_type, rating, final_text)` — handles DB insert, `.md` file write, ChromaDB upsert, and connection finding. Returns `(connections, title, media_type, rating)`.

### `pages/sync.py`
Two-button sync UI:
- **Sync Notion** → calls `run_sync()` from `notion_import.py`; shows counts of new/skipped/failed pages; prompts to rebuild index if new pages were added
- **Rebuild index** → calls `run_index()` from `indexer.py`; shows chunk/file counts on completion

---

## Data Flow: What Gets Indexed Where

| Source | Indexed by | Chunk ID prefix | `source_type` |
|---|---|---|---|
| Notion pages | `indexer.py` (CLI / Sync page) | `{page_id}__chunkN` | `"notion"` |
| Diary entries | `pages/diary.py` at save time | `diary-{date}__chunkN` | `"diary"` |
| Media logs | `pages/media.py` at save time | `media-{date}-{slug}__chunkN` | `"media"` |

All three land in the same ChromaDB collection (`second_brain`) and are queried together.

---

## Cost Profile

All embedding and vector search runs locally (free). Claude API is called for:

| Action | Model | Approx tokens | Approx cost |
|---|---|---|---|
| Chat response | claude-sonnet-4-6 | ~2k in / ~500 out | ~$0.003–0.005 |
| Diary synthesis | claude-sonnet-4-6 | ~600 in / ~400 out | ~$0.001 |
| Media follow-up | claude-sonnet-4-6 | ~200 in / ~120 out | ~$0.0005 |
| Connections explanation | claude-sonnet-4-6 | ~800 in / ~300 out | ~$0.001 |

Daily diary + a few chats ≈ well under $0.10/day.

---

## Ideas for Future Sessions

- **Explore page** — visualise the connection graph between notes
- **Re-index button per source** — index only diary/media without rebuilding Notion chunks
- **Export chat** — download a session as markdown
- **Source badges in chat** — visually distinguish Notion vs diary vs media chunks in source list
- **Notion incremental sync** — detect changed pages via `last_edited_time` and re-export only those
- **Mobile layout** — currently `layout="wide"`, could add a narrow-column mode
