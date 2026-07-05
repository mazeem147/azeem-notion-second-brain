"""
app.py — navigation entry point. Run with:
    ./venv/bin/streamlit run app.py
"""

import streamlit as st
from ui import apply_styles, sidebar_brand

st.set_page_config(page_title="Second Brain", page_icon="🧠", layout="wide")
apply_styles()

pages = [
    st.Page("pages/chat.py",  title="Chat",      icon="💬", default=True),
    st.Page("pages/diary.py", title="Diary",     icon="📓"),
    st.Page("pages/media.py", title="Media Log", icon="🎧"),
    st.Page("pages/sync.py",  title="Sync",      icon="🔄"),
]

pg = st.navigation(pages, position="hidden")

# ── Global sidebar (renders on every page) ────────────────────────────────
with st.sidebar:
    sidebar_brand()
    st.markdown("---")

    for page in pages:
        is_active = pg.title == page.title
        if st.button(
            f"{page.icon}  {page.title}",
            key=f"nav_{page.title}",
            use_container_width=True,
            type="primary" if is_active else "secondary",
            disabled=is_active,
        ):
            st.switch_page(page)

    st.markdown("---")

pg.run()
