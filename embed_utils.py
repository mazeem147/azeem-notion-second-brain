"""
embed_utils.py — shared helpers for chunking and upserting a single document
into ChromaDB. Used by the diary and media log pages for immediate indexing.
"""

import os
import streamlit as st
import chromadb
from sentence_transformers import SentenceTransformer

CHROMA_DIR = os.path.join(os.path.dirname(__file__), "data", "chroma")
COLLECTION_NAME = "second_brain"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
CHUNK_SIZE_WORDS = 350
CHUNK_OVERLAP_WORDS = 50


@st.cache_resource
def load_embed_model():
    return SentenceTransformer(EMBEDDING_MODEL)


@st.cache_resource
def load_collection():
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    return client.get_or_create_collection(
        COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def chunk_text(text, chunk_size=CHUNK_SIZE_WORDS, overlap=CHUNK_OVERLAP_WORDS):
    words = text.split()
    if not words:
        return []
    chunks, start = [], 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start += chunk_size - overlap
    return chunks


def upsert_document(doc_id_prefix: str, text: str, metadata: dict):
    """Chunk text and upsert all chunks into ChromaDB."""
    model = load_embed_model()
    collection = load_collection()
    chunks = chunk_text(text)
    if not chunks:
        return
    embeddings = model.encode(chunks, show_progress_bar=False).tolist()
    ids = [f"{doc_id_prefix}__chunk{i}" for i in range(len(chunks))]
    metas = [{**metadata, "chunk_index": i} for i in range(len(chunks))]
    collection.upsert(ids=ids, embeddings=embeddings, documents=chunks, metadatas=metas)
