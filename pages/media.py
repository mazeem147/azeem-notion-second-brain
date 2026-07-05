"""
pages/media.py — Media Log with Claude take enrichment.
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
from ui import connection_card

RAW_MEDIA_DIR = os.path.join(ROOT, "data", "raw", "media")

MEDIA_TYPES = ["Article", "Book", "Podcast", "Video"]
TYPE_ICONS = {"Article": "📰", "Book": "📚", "Podcast": "🎙", "Video": "📺"}
STAR_LABELS = {1: "★☆☆☆☆", 2: "★★☆☆☆", 3: "★★★☆☆", 4: "★★★★☆", 5: "★★★★★"}

init_db()
os.makedirs(RAW_MEDIA_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def generate_follow_up(title, media_type, reaction):
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=120,
        messages=[{"role": "user", "content": (
            f"The user just logged a {media_type}: \"{title}\"\n"
            f"Their initial reaction: {reaction}\n\n"
            "Ask ONE short follow-up question to deepen their reflection. "
            "Pick the most interesting angle: a concrete behaviour change, "
            "a surprising idea, a connection to prior knowledge, or a point of disagreement. "
            "Return only the question, no preamble."
        )}],
    )
    return response.content[0].text.strip()


def save_entry(title, url, media_type, rating, final_text):
    now = datetime.datetime.now()
    date_str = now.date().isoformat()
    slug = (title or "untitled").lower().replace(" ", "-")[:40]
    filename = f"media-{date_str}-{slug}.md"

    with get_conn() as conn:
        conn.execute(
            "INSERT INTO media_logs (url, title, media_type, rating, reaction) VALUES (?, ?, ?, ?, ?)",
            (url.strip() or None, title.strip() or None, media_type, rating, final_text.strip()),
        )
        conn.commit()

    md_content = (
        f"---\ntitle: {title}\nmedia_type: {media_type}\nrating: {rating}\n"
        f"url: {url}\ncreated: {date_str}\nsource: media\n---\n\n{final_text.strip()}\n"
    )
    with open(os.path.join(RAW_MEDIA_DIR, filename), "w", encoding="utf-8") as f:
        f.write(md_content)

    embed_text = (
        f"Title: {title}\nType: {media_type}\nRating: {rating}/5\nURL: {url}\n\n"
        f"{final_text.strip()}"
    )
    upsert_document(
        doc_id_prefix=f"media-{date_str}-{slug}",
        text=embed_text,
        metadata={
            "title": title or "Untitled",
            "notion_url": url or "",
            "created": date_str,
            "page_id": "",
            "filename": filename,
            "source": "media",
            "source_type": "media",
            "media_type": media_type,
            "rating": str(rating),
        },
    )

    with st.spinner("Finding related notes…"):
        raw = find_connections(
            embed_text, load_embed_model(), load_collection(),
            exclude_prefix=f"media-{date_str}-{slug}",
        )
        conns = explain_connections(embed_text, raw)

    return conns, title, media_type, rating


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

_defaults = {
    "ml_step": "form",
    "ml_data": {},
    "ml_question": "",
    "ml_connections": [],
    "ml_saved_title": "",
    "ml_saved_type": "",
    "ml_saved_rating": 3,
}
for _k, _v in _defaults.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("**Recent logs**")
    type_filter = st.selectbox("Type", ["All"] + MEDIA_TYPES, label_visibility="collapsed")
    st.markdown("---")

    with get_conn() as conn:
        if type_filter == "All":
            rows = conn.execute(
                "SELECT title, media_type, rating, reaction, created_at FROM media_logs "
                "ORDER BY created_at DESC LIMIT 20"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT title, media_type, rating, reaction, created_at FROM media_logs "
                "WHERE media_type = ? ORDER BY created_at DESC LIMIT 20",
                (type_filter,),
            ).fetchall()

    if rows:
        for row in rows:
            stars = STAR_LABELS.get(row["rating"], "")
            icon = TYPE_ICONS.get(row["media_type"], "")
            label = f"{icon} {row['title'] or 'Untitled'}"
            with st.expander(label):
                st.markdown(f"""
                <span style="font-size:0.72rem;color:#5e5d7a;font-family:'DM Mono',monospace;">
                  {stars} · {row['created_at'][:10]}
                </span>
                """, unsafe_allow_html=True)
                st.markdown(row["reaction"])
    else:
        st.caption("No entries yet.")


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.title("Media Log")
st.caption("Log a book, article, podcast, or video.")
st.markdown("---")


# ---------------------------------------------------------------------------
# Step: form
# ---------------------------------------------------------------------------

if st.session_state.ml_step == "form":
    with st.form("media_form"):
        title = st.text_input("Title", placeholder="The Mom Test, Lex Fridman #400…")
        url = st.text_input("URL", placeholder="https://… (optional)")
        media_type = st.radio("Type", MEDIA_TYPES, horizontal=True)
        rating = st.select_slider(
            "Rating",
            options=[1, 2, 3, 4, 5],
            value=3,
            format_func=lambda x: STAR_LABELS[x],
        )
        reaction = st.text_area(
            "Your reaction",
            height=160,
            placeholder="What did you take away? What surprised you? What do you disagree with?",
        )
        submitted = st.form_submit_button("Log it")

    if submitted:
        if not reaction.strip():
            st.warning("Write at least a brief reaction before saving.")
        else:
            st.session_state.ml_data = {
                "title": title, "url": url, "media_type": media_type,
                "rating": rating, "reaction": reaction,
            }
            with st.spinner("One follow-up question…"):
                question = generate_follow_up(title, media_type, reaction)
            st.session_state.ml_question = question
            st.session_state.ml_step = "enrich"
            st.rerun()


# ---------------------------------------------------------------------------
# Step: enrich
# ---------------------------------------------------------------------------

elif st.session_state.ml_step == "enrich":
    d = st.session_state.ml_data

    st.markdown(f"""
    <div style="
      background:#fff;border:1px solid #e4e0f4;border-left:3px solid #6e56cf;
      border-radius:9px;padding:1.1rem 1.4rem;margin:0 0 1.25rem;
      box-shadow:0 1px 4px rgba(0,0,0,0.04);
    ">
      <p style="margin:0;font-size:0.97rem;font-weight:500;color:#18171f;line-height:1.55;
                font-family:'DM Sans',system-ui,sans-serif;">
        {st.session_state.ml_question}
      </p>
    </div>
    """, unsafe_allow_html=True)

    answer = st.text_area(
        "Your answer",
        height=120,
        placeholder="Optional — skip to save as-is.",
        label_visibility="collapsed",
    )

    col1, col2 = st.columns([2, 3])
    with col1:
        if st.button("Add to entry", type="primary"):
            final_text = (
                d["reaction"].strip() + "\n\n"
                + st.session_state.ml_question + "\n"
                + answer.strip()
            ) if answer.strip() else d["reaction"].strip()
            conns, sv_title, sv_type, sv_rating = save_entry(
                d["title"], d["url"], d["media_type"], d["rating"], final_text
            )
            st.session_state.ml_connections = conns
            st.session_state.ml_saved_title = sv_title
            st.session_state.ml_saved_type = sv_type
            st.session_state.ml_saved_rating = sv_rating
            st.session_state.ml_step = "done"
            st.rerun()
    with col2:
        if st.button("Skip enrichment"):
            conns, sv_title, sv_type, sv_rating = save_entry(
                d["title"], d["url"], d["media_type"], d["rating"], d["reaction"]
            )
            st.session_state.ml_connections = conns
            st.session_state.ml_saved_title = sv_title
            st.session_state.ml_saved_type = sv_type
            st.session_state.ml_saved_rating = sv_rating
            st.session_state.ml_step = "done"
            st.rerun()


# ---------------------------------------------------------------------------
# Step: done
# ---------------------------------------------------------------------------

elif st.session_state.ml_step == "done":
    icon = TYPE_ICONS.get(st.session_state.ml_saved_type, "")
    stars = STAR_LABELS.get(st.session_state.ml_saved_rating, "")
    title_display = st.session_state.ml_saved_title or "Entry"

    st.markdown(f"""
    <div style="
      background:#f0edff;border:1px solid #e0daf8;border-radius:9px;
      padding:1rem 1.4rem;margin-bottom:1.5rem;
    ">
      <p style="margin:0;font-size:0.88rem;color:#3c3a52;font-family:'DM Sans',sans-serif;">
        ✓ Saved — {icon} <strong>{title_display}</strong> · {stars}
      </p>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.ml_connections:
        st.markdown("""
        <p style="font-size:0.8rem;font-weight:600;color:#8b8a9e;text-transform:uppercase;
                  letter-spacing:0.08em;margin:0 0 0.75rem;font-family:'DM Sans',sans-serif;">
          Related from your past
        </p>
        """, unsafe_allow_html=True)
        for c in st.session_state.ml_connections:
            connection_card(
                title=c["title"],
                date=c["created"],
                explanation=c.get("explanation", ""),
                text=c["text"],
                url=c.get("notion_url", ""),
            )

    st.markdown("---")
    if st.button("Log another", type="primary"):
        for _k, _v in _defaults.items():
            st.session_state[_k] = _v
        st.rerun()
