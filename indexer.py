"""
indexer.py — reads every .md file from data/raw/, chunks the content,
embeds with a local sentence-transformers model, and stores vectors
in ChromaDB at data/chroma/.

Run after notion_import.py:
    ./venv/bin/python indexer.py

Or trigger from the Sync page in the app.
Each run rebuilds the collection from scratch for a clean slate.
"""

import os
import math

import yaml
import chromadb
from sentence_transformers import SentenceTransformer

RAW_DIR = os.path.join(os.path.dirname(__file__), "data", "raw")
CHROMA_DIR = os.path.join(os.path.dirname(__file__), "data", "chroma")
COLLECTION_NAME = "second_brain"

EMBEDDING_MODEL = "all-MiniLM-L6-v2"
CHUNK_SIZE_WORDS = 350
CHUNK_OVERLAP_WORDS = 50
MIN_WORDS_TO_INDEX = 20
BATCH_SIZE = 32


def parse_frontmatter(text):
    """Return (metadata_dict, body_text) from a file with YAML frontmatter."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    yaml_block = text[3:end].strip()
    body = text[end + 4:].lstrip("\n")
    try:
        meta = yaml.safe_load(yaml_block) or {}
    except yaml.YAMLError:
        meta = {}
    return meta, body


def chunk_text(text, chunk_size=CHUNK_SIZE_WORDS, overlap=CHUNK_OVERLAP_WORDS):
    """Split text into overlapping word-count chunks."""
    words = text.split()
    if not words:
        return []
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start += chunk_size - overlap
    return chunks


def run_index(progress_fn=print):
    """
    Rebuild the full index from data/raw/.
    Deletes and recreates the ChromaDB collection for a clean slate.
    Returns (total_chunks, files_indexed, files_skipped).
    """
    os.makedirs(CHROMA_DIR, exist_ok=True)

    progress_fn(f"Loading embedding model '{EMBEDDING_MODEL}'...")
    model = SentenceTransformer(EMBEDDING_MODEL)

    client = chromadb.PersistentClient(path=CHROMA_DIR)
    if COLLECTION_NAME in [c.name for c in client.list_collections()]:
        client.delete_collection(COLLECTION_NAME)
    collection = client.create_collection(
        COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    md_files = sorted(f for f in os.listdir(RAW_DIR) if f.endswith(".md"))
    progress_fn(f"Found {len(md_files)} files in {RAW_DIR}")

    all_texts, all_ids, all_metas = [], [], []
    skipped = 0

    for filename in md_files:
        filepath = os.path.join(RAW_DIR, filename)
        with open(filepath, encoding="utf-8") as f:
            raw = f.read()

        meta, body = parse_frontmatter(raw)
        words = body.split()

        if len(words) < MIN_WORDS_TO_INDEX:
            skipped += 1
            continue

        chunks = chunk_text(body)
        title = str(meta.get("title", filename))
        notion_url = str(meta.get("notion_url", ""))
        created = str(meta.get("Created", meta.get("last_edited_time", "")))
        page_id = str(meta.get("page_id", ""))
        source = str(meta.get("source", "notion"))

        for i, chunk in enumerate(chunks):
            chunk_id = f"{page_id}__chunk{i}" if page_id else f"{filename}__chunk{i}"
            all_texts.append(chunk)
            all_ids.append(chunk_id)
            all_metas.append({
                "title": title,
                "notion_url": notion_url,
                "created": created,
                "page_id": page_id,
                "filename": filename,
                "chunk_index": i,
                "source": source,
                "source_type": source,
            })

    total_chunks = len(all_texts)
    files_indexed = len(md_files) - skipped
    progress_fn(
        f"Chunked into {total_chunks} chunks across {files_indexed} files "
        f"({skipped} skipped as too short)."
    )
    progress_fn("Embedding and storing (runs entirely locally)...")

    num_batches = math.ceil(total_chunks / BATCH_SIZE) if total_chunks else 0
    for batch_num in range(num_batches):
        start = batch_num * BATCH_SIZE
        end = min(start + BATCH_SIZE, total_chunks)

        embeddings = model.encode(all_texts[start:end], show_progress_bar=False).tolist()
        collection.add(
            ids=all_ids[start:end],
            embeddings=embeddings,
            documents=all_texts[start:end],
            metadatas=all_metas[start:end],
        )
        progress_fn(f"  batch {batch_num + 1}/{num_batches} — chunks {start + 1}–{end}")

    progress_fn(f"Done. {total_chunks} chunks indexed into {CHROMA_DIR}")
    return total_chunks, files_indexed, skipped


def main():
    run_index(progress_fn=print)


if __name__ == "__main__":
    main()
