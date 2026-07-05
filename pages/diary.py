"""
pages/diary.py — Daily Diary mode.
"""

import os
import sys
import datetime

import anthropic
import streamlit as st

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)
from db import init_db, get_conn
from embed_utils import upsert_document, load_embed_model, load_collection
from connections import find_connections, explain_connections
from ui import question_card, connection_card

RAW_DIARY_DIR = os.path.join(ROOT, "data", "raw", "diary")

QUESTIONS = [
    "What happened today?",
    "What are you grateful for?",
    "What's on your mind — worries, open loops, anything unsettled?",
    "What decision or challenge are you wrestling with?",
    "What's one thing to remember or act on tomorrow?",
]


def synthesize_entry(questions, answers):
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    qa_text = "\n\n".join(f"Q: {q}\nA: {a}" for q, a in zip(questions, answers))
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        messages=[{"role": "user", "content": (
            f"Here is a diary Q&A session from today:\n\n{qa_text}\n\n"
            "Write a concise first-person diary entry (3-5 sentences) that captures the "
            "essence of this person's day in their own voice. Be specific and direct. "
            "No preamble, no sign-off — just the entry."
        )}],
    )
    return response.content[0].text.strip()


init_db()
os.makedirs(RAW_DIARY_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

if "diary_step" not in st.session_state:
    st.session_state.diary_step = 0
if "diary_answers" not in st.session_state:
    st.session_state.diary_answers = []
if "diary_saved" not in st.session_state:
    st.session_state.diary_saved = False
if "diary_connections" not in st.session_state:
    st.session_state.diary_connections = []
if "diary_full_content" not in st.session_state:
    st.session_state.diary_full_content = ""

today = datetime.date.today().isoformat()

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("**Past entries**")
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT date, content FROM diary_entries ORDER BY date DESC LIMIT 12"
        ).fetchall()
    if rows:
        for row in rows:
            with st.expander(row["date"]):
                st.markdown(row["content"])
    else:
        st.caption("No entries yet.")

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.title("Daily Diary")
st.caption(today)
st.markdown("---")

# ---------------------------------------------------------------------------
# Already written today
# ---------------------------------------------------------------------------

with get_conn() as conn:
    existing = conn.execute(
        "SELECT id FROM diary_entries WHERE date = ?", (today,)
    ).fetchone()

if existing and not st.session_state.diary_saved:
    st.markdown("""
    <div style="
      background:#f0edff;border:1px solid #e0daf8;border-radius:9px;
      padding:1.1rem 1.4rem;margin-bottom:1rem;
    ">
      <p style="margin:0;font-size:0.9rem;color:#3c3a52;font-family:'DM Sans',sans-serif;">
        ✓ You've already written today's entry.
      </p>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Write another entry anyway"):
        st.session_state.diary_step = 0
        st.session_state.diary_answers = []
        st.session_state.diary_saved = False
        st.rerun()
    st.stop()

# ---------------------------------------------------------------------------
# Question flow
# ---------------------------------------------------------------------------

step = st.session_state.diary_step
total = len(QUESTIONS)

if not st.session_state.diary_saved and step < total:
    # Progress dots
    dots = "".join(
        '<span style="display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:5px;'
        + (f'background:#6e56cf;">' if i <= step else f'background:#dbd8ec;">') + "</span>"
        for i in range(total)
    )
    st.markdown(
        f'<div style="margin-bottom:0.25rem;">{dots}</div>'
        f'<span style="font-size:0.73rem;color:#8b8a9e;font-family:\'DM Mono\',monospace;">'
        f'{step + 1} of {total}</span>',
        unsafe_allow_html=True,
    )

    question_card(QUESTIONS[step])

    answer = st.text_area(
        "Your answer",
        key=f"answer_{step}",
        height=130,
        placeholder="Write freely — this is just for you.",
        label_visibility="collapsed",
    )

    col1, col2 = st.columns([1, 6])
    with col1:
        if st.button("Next →", type="primary", disabled=not answer.strip()):
            st.session_state.diary_answers.append(answer.strip())
            st.session_state.diary_step += 1
            st.rerun()

# ---------------------------------------------------------------------------
# Review & save
# ---------------------------------------------------------------------------

elif not st.session_state.diary_saved and step == total:
    st.markdown("""
    <p style="font-size:0.82rem;color:#8b8a9e;margin-bottom:1.25rem;font-family:'DM Sans',sans-serif;">
      Review your entry — then save.
    </p>
    """, unsafe_allow_html=True)

    full_content = ""
    for i, (q, a) in enumerate(zip(QUESTIONS, st.session_state.diary_answers), 1):
        st.markdown(f"""
        <div style="margin-bottom:1.1rem;">
          <p style="font-size:0.75rem;font-weight:600;color:#8b8a9e;text-transform:uppercase;
                    letter-spacing:0.07em;margin-bottom:0.3rem;font-family:'DM Sans',sans-serif;">
            {q}
          </p>
          <p style="font-size:0.9rem;color:#18171f;line-height:1.6;margin:0;
                    font-family:'DM Sans',sans-serif;">
            {a}
          </p>
        </div>
        """, unsafe_allow_html=True)
        full_content += f"### {q}\n{a}\n\n"

    st.markdown("---")
    col1, col2 = st.columns([2, 3])
    with col1:
        if st.button("Save entry", type="primary"):
            with st.spinner("Synthesising entry…"):
                synthesis = synthesize_entry(QUESTIONS, st.session_state.diary_answers)

            with get_conn() as conn:
                conn.execute(
                    "INSERT INTO diary_entries (date, content) VALUES (?, ?)",
                    (today, synthesis),
                )
                conn.commit()

            filename = f"diary-{today}.md"
            filepath = os.path.join(RAW_DIARY_DIR, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(
                    f"---\ntitle: Diary {today}\ncreated: {today}\nsource: diary\n---\n\n"
                    f"{synthesis}\n\n---\n\n{full_content}"
                )

            upsert_document(
                doc_id_prefix=f"diary-{today}",
                text=synthesis,
                metadata={
                    "title": f"Diary {today}",
                    "notion_url": "",
                    "created": today,
                    "page_id": "",
                    "filename": filename,
                    "source": "diary",
                    "source_type": "diary",
                },
            )

            with st.spinner("Finding related notes…"):
                raw = find_connections(
                    synthesis, load_embed_model(), load_collection(),
                    exclude_prefix=f"diary-{today}",
                )
                conns = explain_connections(synthesis, raw)
                st.session_state.diary_connections = conns

            st.session_state.diary_full_content = synthesis
            st.session_state.diary_saved = True
            st.rerun()

    with col2:
        if st.button("↩ Start over"):
            st.session_state.diary_step = 0
            st.session_state.diary_answers = []
            st.rerun()

# ---------------------------------------------------------------------------
# Saved state
# ---------------------------------------------------------------------------

elif st.session_state.diary_saved:
    st.markdown("""
    <div style="
      background:#f0edff;border:1px solid #e0daf8;border-radius:9px;
      padding:1rem 1.4rem;margin-bottom:1.5rem;
    ">
      <p style="margin:0;font-size:0.88rem;color:#3c3a52;font-family:'DM Sans',sans-serif;">
        ✓ Saved and indexed — searchable in Chat.
      </p>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.diary_connections:
        st.markdown("""
        <p style="font-size:0.8rem;font-weight:600;color:#8b8a9e;text-transform:uppercase;
                  letter-spacing:0.08em;margin-bottom:0.75rem;font-family:'DM Sans',sans-serif;">
          Related from your past
        </p>
        """, unsafe_allow_html=True)
        for c in st.session_state.diary_connections:
            connection_card(
                title=c["title"],
                date=c["created"],
                explanation=c.get("explanation", ""),
                text=c["text"],
                url=c.get("notion_url", ""),
            )

    st.markdown("---")
    if st.button("Done"):
        st.session_state.diary_step = 0
        st.session_state.diary_answers = []
        st.session_state.diary_saved = False
        st.session_state.diary_connections = []
        st.session_state.diary_full_content = ""
        st.rerun()
