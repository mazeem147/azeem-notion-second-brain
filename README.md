# Azeem's Notion Second Brain

A local Streamlit RAG app that imports your Notion notes, embeds them locally, and lets you chat with your own knowledge base via Claude.

## Features

- **Chat** — ask questions across all your Notion notes using semantic search + Claude
- **Daily Diary** — 5-question interview flow with Claude synthesis; speak any answer with the mic (mixed Urdu/English transcribed and translated to English)
- **Media Log** — log books, podcasts, videos with AI follow-up questions; speak your reaction or the follow-up answer with the mic too
- **Sync** — pull new Notion pages and rebuild the vector index

## Stack

| Layer | Tool |
|---|---|
| Frontend | Streamlit |
| Embeddings | `all-MiniLM-L6-v2` (local, free) |
| Vector store | ChromaDB |
| LLM | Claude via OpenRouter |
| Structured DB | SQLite |

## Setup

1. Clone the repo
2. Create a virtual environment and install dependencies:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and fill in your keys:
   ```
   NOTION_TOKEN=...
   ANTHROPIC_API_KEY=...
   OPENROUTER_API_KEY=...
   OPENAI_API_KEY=...   # only needed for the diary/media voice mic (Whisper)
   ```
4. Import Notion pages and build the index:
   ```bash
   ./venv/bin/python notion_import.py
   ./venv/bin/python indexer.py
   ```
5. Run the app:
   ```bash
   ./venv/bin/streamlit run app.py
   ```
