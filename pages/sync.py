"""
pages/sync.py — Sync controls: pull new pages from Notion, rebuild the search index.
"""

import os
import sys

import streamlit as st

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from indexer import run_index
from notion_import import run_sync

st.title("Sync")
st.caption("Keep your Second Brain up to date.")
st.markdown("---")

# ── Notion ────────────────────────────────────────────────────────────────

st.subheader("Notion")
st.caption("Pull new pages from your workspace. Already-imported pages are skipped.")

if st.button("Sync Notion", type="primary"):
    try:
        with st.spinner("Pulling pages from Notion…"):
            written, skipped, failed = run_sync()
        if failed:
            st.warning(f"{written} new pages · {skipped} already up to date · {failed} failed.")
        else:
            st.success(f"{written} new pages added · {skipped} already up to date.")
        if written > 0:
            st.info("Run **Rebuild index** below to make new pages searchable.", icon="ℹ️")
    except Exception as e:
        st.error(f"Sync failed: {e}")

st.markdown("---")

# ── Re-index ──────────────────────────────────────────────────────────────

st.subheader("Re-index")
st.caption("Rebuild the full search index from all notes in data/raw/.")
st.info(
    "Run this after syncing Notion. Rebuilds the entire index — takes 1–2 minutes on first run.",
    icon="ℹ️",
)

if st.button("Rebuild index"):
    with st.spinner("Indexing all notes — this takes a minute…"):
        total_chunks, files_indexed, files_skipped = run_index()
    st.success(
        f"{total_chunks} chunks indexed across {files_indexed} files "
        f"({files_skipped} skipped as too short)."
    )
