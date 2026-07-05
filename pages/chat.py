"""
pages/chat.py — Chat interface (loaded by app.py navigation).
"""

import os
import sys
import json
import uuid
import textwrap
from dotenv import load_dotenv

import streamlit as st
import chromadb
from openai import OpenAI
from sentence_transformers import SentenceTransformer

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)
from db import init_db, get_conn

load_dotenv()
init_db()

CHROMA_DIR = os.path.join(ROOT, "data", "chroma")
COLLECTION_NAME = "second_brain"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
MODELS = {
    "Claude Sonnet 4.6": "anthropic/claude-sonnet-4-6",
    "Llama 4 Maverick": "meta-llama/llama-4-maverick",
}
MAX_HISTORY_TURNS = 6

SYSTEM_PROMPT = textwrap.dedent("""\
    You are a thinking partner built from the user's own personal notes, diary entries,
    and reflections. Your job is to help them think harder using what they have already written.

    Rules:
    - Answer primarily from the retrieved notes shown below — not from general knowledge.
    - Quote or closely paraphrase the user's own words when relevant so they recognise the source.
    - If their past notes contradict each other, name the contradiction rather than smoothing it over.
    - If the notes don't contain enough to answer well, say so clearly and briefly.
    - Keep responses focused and direct — this person thinks in systems, not platitudes.
    - Do not pad answers with generic advice. Stay in the user's world.
""")

EXAMPLE_PROMPTS = [
    "What have I thought about career decisions?",
    "What patterns come up in my diary?",
    "What did I write about motivation or productivity?",
    "What's the most important decision I've wrestled with?",
]


# ---------------------------------------------------------------------------
# Cached resources
# ---------------------------------------------------------------------------

@st.cache_resource
def load_embedding_model():
    return SentenceTransformer(EMBEDDING_MODEL)


@st.cache_resource
def load_chroma_collection():
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    return client.get_collection(COLLECTION_NAME)


@st.cache_resource
def load_openrouter_client():
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        st.error("OPENROUTER_API_KEY not found in .env")
        st.stop()
    return OpenAI(api_key=api_key, base_url=OPENROUTER_BASE_URL)


# ---------------------------------------------------------------------------
# Session DB helpers
# ---------------------------------------------------------------------------

def db_create_session():
    sid = str(uuid.uuid4())
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO chat_sessions (id, title, messages) VALUES (?, ?, ?)",
            (sid, "New chat", "[]"),
        )
        conn.commit()
    return sid


def db_save_messages(session_id, messages):
    slim = [{"role": m["role"], "content": m["content"]} for m in messages]
    with get_conn() as conn:
        conn.execute(
            "UPDATE chat_sessions SET messages = ?, updated_at = datetime('now') WHERE id = ?",
            (json.dumps(slim), session_id),
        )
        conn.commit()


def db_update_title(session_id, title):
    with get_conn() as conn:
        conn.execute("UPDATE chat_sessions SET title = ? WHERE id = ?", (title, session_id))
        conn.commit()


def db_load_messages(session_id):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT messages FROM chat_sessions WHERE id = ?", (session_id,)
        ).fetchone()
    return json.loads(row["messages"]) if row else []


def db_list_sessions():
    with get_conn() as conn:
        return conn.execute(
            "SELECT id, title, updated_at FROM chat_sessions ORDER BY updated_at DESC LIMIT 50"
        ).fetchall()


def db_delete_session(session_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
        conn.commit()


# ---------------------------------------------------------------------------
# Retrieval helpers
# ---------------------------------------------------------------------------

def retrieve_chunks(query, model, collection, n):
    embedding = model.encode([query]).tolist()
    results = collection.query(query_embeddings=embedding, n_results=n)
    return [
        {"text": doc, "meta": meta}
        for doc, meta in zip(results["documents"][0], results["metadatas"][0])
    ]


def format_context(chunks):
    parts = []
    for i, c in enumerate(chunks, 1):
        meta = c["meta"]
        header = f"[{i}] {meta.get('title', 'Untitled')} — {meta.get('created', '')[:10]}"
        parts.append(f"{header}\n{c['text']}")
    return "\n\n---\n\n".join(parts)


def render_sources(chunks):
    with st.expander("Sources", expanded=False):
        for c in chunks:
            meta = c["meta"]
            label = f"{meta.get('title', 'Untitled')}  ·  {meta.get('created', '')[:10]}"
            url = meta.get("notion_url", "")
            st.markdown(f"[{label}]({url})" if url else label)


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_chunks" not in st.session_state:
    st.session_state.session_chunks = {}

# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------

embed_model = load_embedding_model()
collection = load_chroma_collection()
openrouter = load_openrouter_client()

# ---------------------------------------------------------------------------
# Sidebar — chat-specific (appended after app.py's global nav)
# ---------------------------------------------------------------------------

with st.sidebar:
    if st.button("+ New chat", use_container_width=True, type="primary"):
        st.session_state.current_session_id = None
        st.session_state.messages = []
        st.session_state.session_chunks = {}
        st.rerun()

    selected_model_name = st.radio(
        "Model",
        options=list(MODELS.keys()),
        index=0,
        horizontal=True,
    )
    selected_model_id = MODELS[selected_model_name]

    n_results = st.slider(
        "Chunks per query", min_value=3, max_value=15, value=5,
        help="More = richer context, higher cost",
    )
    st.caption(f"~${n_results * 0.0002:.3f} per query")

    st.markdown("---")
    st.markdown("**Chats**")

    sessions = db_list_sessions()
    if not sessions:
        st.caption("No chats yet.")

    for s in sessions:
        is_active = s["id"] == st.session_state.current_session_id
        col_btn, col_del = st.columns([5, 1])
        with col_btn:
            label = ("→ " if is_active else "") + s["title"]
            if st.button(label, key=f"sess_{s['id']}", use_container_width=True):
                if not is_active:
                    st.session_state.current_session_id = s["id"]
                    st.session_state.messages = db_load_messages(s["id"])
                    st.session_state.session_chunks = {}
                    st.rerun()
        with col_del:
            if st.button("✕", key=f"del_{s['id']}"):
                db_delete_session(s["id"])
                if is_active:
                    st.session_state.current_session_id = None
                    st.session_state.messages = []
                    st.session_state.session_chunks = {}
                st.rerun()

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.title("Chat")
st.caption("Answers grounded in your own notes and diary.")

# ---------------------------------------------------------------------------
# Empty state
# ---------------------------------------------------------------------------

if not st.session_state.messages:
    st.markdown("""
    <div style="margin:3.5rem auto 0;max-width:460px;text-align:center;">
      <div style="font-size:2rem;margin-bottom:0.85rem;">🧠</div>
      <p style="font-size:0.97rem;font-weight:500;color:#18171f;margin-bottom:0.35rem;">
        What's on your mind?
      </p>
      <p style="font-size:0.8rem;color:#8b8a9e;line-height:1.65;">
        Ask anything — answers are pulled from your Notion notes, diary entries, and media logs.
      </p>
    </div>
    <div style="margin:1.5rem auto 0;max-width:460px;display:flex;flex-direction:column;gap:0.4rem;">
    """, unsafe_allow_html=True)

    for ep in EXAMPLE_PROMPTS:
        st.markdown(f"""
        <div style="border:1px solid #e4e0f4;border-radius:8px;padding:0.5rem 0.9rem;
                    font-size:0.8rem;color:#4a4862;background:#fff;
                    font-family:'DM Sans',sans-serif;">{ep}</div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Conversation
# ---------------------------------------------------------------------------

for idx, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and idx in st.session_state.session_chunks:
            render_sources(st.session_state.session_chunks[idx])

# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------

if prompt := st.chat_input("Ask something from your past…"):

    if not st.session_state.current_session_id:
        sid = db_create_session()
        title = prompt[:60] + ("…" if len(prompt) > 60 else "")
        db_update_title(sid, title)
        st.session_state.current_session_id = sid

    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.spinner("Searching your notes…"):
        prior = next(
            (m["content"][:200] for m in reversed(st.session_state.messages) if m["role"] == "assistant"),
            None,
        )
        retrieval_query = f"{prior} {prompt}" if prior else prompt
        chunks = retrieve_chunks(retrieval_query, embed_model, collection, n_results)
        context = format_context(chunks)

    history = st.session_state.messages[-(MAX_HISTORY_TURNS + 1):-1]
    api_messages = [{"role": m["role"], "content": m["content"]} for m in history]
    api_messages.append({
        "role": "user",
        "content": f"<retrieved_notes>\n{context}\n</retrieved_notes>\n\nQuestion: {prompt}",
    })

    with st.chat_message("assistant"):
        placeholder = st.empty()
        answer = ""
        stream = openrouter.chat.completions.create(
            model=selected_model_id,
            max_tokens=4096,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + api_messages,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            answer += delta
            placeholder.markdown(answer + "▌")
        placeholder.markdown(answer)
        render_sources(chunks)

    assistant_idx = len(st.session_state.messages)
    st.session_state.messages.append({"role": "assistant", "content": answer})
    st.session_state.session_chunks[assistant_idx] = chunks
    db_save_messages(st.session_state.current_session_id, st.session_state.messages)
