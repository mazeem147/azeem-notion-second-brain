"""
ui.py — shared styles injected into every page.
Call apply_styles() at the top of each Streamlit page.
"""

import streamlit as st

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;1,9..40,400&family=DM+Mono:wght@400&display=swap');

/* ── Global ─────────────────────────────────────────── */
html, body, [class*="css"] {
    font-family: 'DM Sans', system-ui, -apple-system, sans-serif !important;
}

/* Remove Streamlit chrome */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
[data-testid="stDeployButton"] { display: none !important; }
header { background: transparent !important; box-shadow: none !important; }

/* ── Sidebar ─────────────────────────────────────────── */
section[data-testid="stSidebar"],
section[data-testid="stSidebar"] > div,
section[data-testid="stSidebar"] > div > div {
    background: #12111c !important;
}

section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] li,
section[data-testid="stSidebar"] .stMarkdown {
    color: #b5b4ca !important;
    font-size: 0.83rem;
}

section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
    color: #e6e5f5 !important;
}

section[data-testid="stSidebar"] strong {
    color: #7a7997 !important;
    font-size: 0.67rem !important;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    font-weight: 600 !important;
}

section[data-testid="stSidebar"] hr {
    border-color: #252336 !important;
    margin: 0.6rem 0 !important;
}

section[data-testid="stSidebar"] .stCaption,
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {
    color: #5e5d7a !important;
    font-size: 0.73rem !important;
}

/* Sidebar slider label */
section[data-testid="stSidebar"] [data-testid="stSlider"] label p {
    color: #b5b4ca !important;
    font-size: 0.8rem !important;
}
section[data-testid="stSidebar"] [data-testid="stSlider"] [data-testid="stTickBarMin"],
section[data-testid="stSidebar"] [data-testid="stSlider"] [data-testid="stTickBarMax"] {
    color: #5e5d7a !important;
}

/* Sidebar buttons — session list */
section[data-testid="stSidebar"] .stButton button {
    background: transparent !important;
    border: 1px solid #252336 !important;
    color: #b5b4ca !important;
    border-radius: 7px !important;
    font-size: 0.8rem !important;
    font-family: 'DM Sans', sans-serif !important;
    padding: 0.45rem 0.7rem !important;
    text-align: left !important;
    transition: background 0.12s, border-color 0.12s !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
}
section[data-testid="stSidebar"] .stButton button:hover {
    background: #1c1a2e !important;
    border-color: #3c3958 !important;
    color: #e6e5f5 !important;
}

/* Primary / active nav button */
section[data-testid="stSidebar"] .stButton button[kind="primary"] {
    background: #6e56cf !important;
    border-color: #6e56cf !important;
    color: #fff !important;
    font-weight: 500 !important;
    letter-spacing: 0.01em !important;
    font-size: 0.85rem !important;
}
section[data-testid="stSidebar"] .stButton button[kind="primary"]:hover {
    background: #5d47be !important;
    border-color: #5d47be !important;
}
/* Keep primary style even when disabled (active nav item) */
section[data-testid="stSidebar"] .stButton button[kind="primary"]:disabled,
section[data-testid="stSidebar"] .stButton button[kind="primary"][disabled] {
    background: #6e56cf !important;
    border-color: #6e56cf !important;
    color: #fff !important;
    opacity: 0.9 !important;
    cursor: default !important;
}

/* ── Main content ────────────────────────────────────── */
.main .block-container {
    max-width: 760px !important;
    padding-top: 2rem !important;
    padding-bottom: 5rem !important;
}

/* Headings */
h1 {
    font-size: 1.3rem !important;
    font-weight: 600 !important;
    color: #18171f !important;
    letter-spacing: -0.02em !important;
    margin-bottom: 0.1rem !important;
    text-wrap: balance;
}
h2 {
    font-size: 1rem !important;
    font-weight: 600 !important;
    color: #18171f !important;
    letter-spacing: -0.01em !important;
}
h3 {
    font-size: 0.88rem !important;
    font-weight: 500 !important;
    color: #3c3a52 !important;
}

[data-testid="stCaptionContainer"] p {
    color: #8b8a9e !important;
    font-size: 0.78rem !important;
}

/* ── Text cutoff fix ─────────────────────────────────── */
/* Prevent chat text from being cut off when sidebar is wide */
[data-testid="stChatMessage"] {
    min-width: 0 !important;
    overflow: visible !important;
}
[data-testid="stChatMessageContent"] {
    min-width: 0 !important;
    overflow-wrap: anywhere !important;
    word-break: break-word !important;
    flex: 1 !important;
}
[data-testid="stMarkdownContainer"] {
    min-width: 0 !important;
    overflow-wrap: anywhere !important;
    word-break: break-word !important;
}
.stMarkdown {
    min-width: 0 !important;
}

/* ── Chat messages ───────────────────────────────────── */
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
    background: #f0edff;
    border: 1px solid #e0daf8;
    border-radius: 12px;
    padding: 0.9rem 1.1rem !important;
    margin-bottom: 0.65rem;
}

[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
    background: #ffffff;
    border: 1px solid #ebebf2;
    border-radius: 12px;
    padding: 0.9rem 1.1rem !important;
    margin-bottom: 0.65rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}

/* ── Chat input ──────────────────────────────────────── */
[data-testid="stChatInput"] {
    border: 1.5px solid #dbd8ec !important;
    border-radius: 12px !important;
    background: #fff !important;
    transition: border-color 0.15s, box-shadow 0.15s !important;
}
[data-testid="stChatInput"]:focus-within {
    border-color: #6e56cf !important;
    box-shadow: 0 0 0 3px rgba(110,86,207,0.1) !important;
}

/* ── Text inputs ─────────────────────────────────────── */
.stTextInput input,
.stTextArea textarea {
    border-radius: 8px !important;
    border: 1.5px solid #dbd8ec !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.88rem !important;
    background: #fff !important;
    transition: border-color 0.15s, box-shadow 0.15s !important;
}
.stTextInput input:focus,
.stTextArea textarea:focus {
    border-color: #6e56cf !important;
    box-shadow: 0 0 0 3px rgba(110,86,207,0.1) !important;
}

.stTextInput label p,
.stTextArea label p,
.stSelectbox label p,
[data-testid="stSelectSlider"] label p,
[data-testid="stSlider"] label p {
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    color: #3c3a52 !important;
    margin-bottom: 0.25rem !important;
}

/* ── Buttons (main area) ─────────────────────────────── */
.main .stButton button {
    border-radius: 7px !important;
    font-weight: 500 !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.85rem !important;
    transition: all 0.12s !important;
}
.main .stButton button[kind="primary"] {
    background: #6e56cf !important;
    border-color: #6e56cf !important;
    color: #fff !important;
}
.main .stButton button[kind="primary"]:hover {
    background: #5d47be !important;
}

/* Form submit */
.stFormSubmitButton button {
    background: #6e56cf !important;
    border-color: #6e56cf !important;
    color: #fff !important;
    border-radius: 7px !important;
    font-weight: 500 !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.88rem !important;
    padding: 0.5rem 1.25rem !important;
}
.stFormSubmitButton button:hover {
    background: #5d47be !important;
    border-color: #5d47be !important;
}

/* ── Expanders ───────────────────────────────────────── */
[data-testid="stExpander"] {
    border: 1px solid #ebebf2 !important;
    border-radius: 9px !important;
    background: #fefefe !important;
    overflow: hidden !important;
}
[data-testid="stExpander"] summary {
    font-weight: 500;
    font-size: 0.85rem;
}
[data-testid="stExpander"] summary p {
    font-size: 0.85rem !important;
}

/* ── Alerts / banners ────────────────────────────────── */
[data-testid="stAlert"] {
    border-radius: 9px !important;
    font-size: 0.85rem !important;
}
[data-testid="stAlert"] p {
    font-size: 0.85rem !important;
}

/* ── Form card ───────────────────────────────────────── */
[data-testid="stForm"] {
    border: 1px solid #e8e6f4 !important;
    border-radius: 12px !important;
    padding: 1.5rem 1.5rem 1.25rem !important;
    background: #ffffff !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04) !important;
}

/* ── Progress bar ────────────────────────────────────── */
[data-testid="stProgress"] > div > div > div {
    background: #6e56cf !important;
}

/* ── Selectbox ───────────────────────────────────────── */
[data-testid="stSelectbox"] > div > div {
    border-radius: 8px !important;
    border-color: #dbd8ec !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.88rem !important;
}

/* ── Divider ─────────────────────────────────────────── */
hr {
    border-color: #ebe9f4 !important;
    margin: 1.25rem 0 !important;
}

/* ── Spinner ─────────────────────────────────────────── */
.stSpinner > div {
    border-top-color: #6e56cf !important;
}

/* Radio pills (for type selector) */
[data-testid="stRadio"] > div {
    flex-direction: row !important;
    gap: 0.4rem !important;
    flex-wrap: wrap;
}
[data-testid="stRadio"] label {
    border: 1px solid #dbd8ec !important;
    border-radius: 20px !important;
    padding: 0.25rem 0.85rem !important;
    font-size: 0.82rem !important;
    cursor: pointer;
    transition: all 0.12s !important;
    background: #fff;
    color: #3c3a52 !important;
}
[data-testid="stRadio"] label:has(input:checked) {
    background: #6e56cf !important;
    border-color: #6e56cf !important;
    color: #fff !important;
}
[data-testid="stRadio"] label:hover:not(:has(input:checked)) {
    border-color: #6e56cf !important;
    color: #6e56cf !important;
}
[data-testid="stRadio"] input { display: none !important; }
[data-testid="stRadio"] > label > div {
    display: none !important;
}
</style>
"""


def apply_styles():
    st.markdown(_CSS, unsafe_allow_html=True)


def sidebar_brand():
    """Render the branded sidebar header."""
    st.markdown("""
    <div style="display:flex;align-items:center;gap:0.55rem;padding:0.25rem 0 1.1rem;">
      <span style="font-size:1.15rem;line-height:1;">🧠</span>
      <span style="font-size:0.95rem;font-weight:600;color:#e6e5f5;letter-spacing:-0.01em;font-family:'DM Sans',sans-serif;">
        Second Brain
      </span>
    </div>
    """, unsafe_allow_html=True)


def question_card(text: str):
    """Render a styled question card for the diary flow."""
    st.markdown(f"""
    <div style="
      background:#fff;
      border:1px solid #e4e0f4;
      border-left:3px solid #6e56cf;
      border-radius:9px;
      padding:1.1rem 1.4rem;
      margin:1rem 0 1.25rem;
      box-shadow:0 1px 4px rgba(0,0,0,0.04);
    ">
      <p style="margin:0;font-size:0.97rem;font-weight:500;color:#18171f;line-height:1.55;
                font-family:'DM Sans',system-ui,sans-serif;">
        {text}
      </p>
    </div>
    """, unsafe_allow_html=True)


def connection_card(title: str, date: str, explanation: str, text: str, url: str = ""):
    """Render a styled connection card."""
    link = f'<a href="{url}" target="_blank" style="font-size:0.75rem;color:#6e56cf;text-decoration:none;">Open in Notion →</a>' if url else ""
    st.markdown(f"""
    <div style="
      background:#fff;
      border:1px solid #ebebf2;
      border-radius:9px;
      padding:1rem 1.2rem;
      margin-bottom:0.65rem;
      box-shadow:0 1px 3px rgba(0,0,0,0.04);
    ">
      <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:0.35rem;">
        <span style="font-size:0.85rem;font-weight:600;color:#18171f;font-family:'DM Sans',sans-serif;">{title}</span>
        <span style="font-size:0.72rem;color:#8b8a9e;font-family:'DM Mono',monospace;">{date}</span>
      </div>
      <p style="font-size:0.8rem;color:#6e56cf;margin:0 0 0.5rem;font-style:italic;font-family:'DM Sans',sans-serif;">{explanation}</p>
      <p style="font-size:0.82rem;color:#4a4862;margin:0 0 0.4rem;line-height:1.5;font-family:'DM Sans',sans-serif;">{text[:280]}{"…" if len(text)>280 else ""}</p>
      {link}
    </div>
    """, unsafe_allow_html=True)
