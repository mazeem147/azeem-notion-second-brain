"""
connections.py — finds related past notes and asks Claude why they connect.
Used by diary.py and media.py after saving a new entry.
"""

import os
import anthropic
from dotenv import load_dotenv

load_dotenv()

CLAUDE_MODEL = "claude-sonnet-4-6"
N_CONNECTIONS = 3


def find_connections(new_text: str, embed_model, collection, exclude_prefix: str = ""):
    """
    Query ChromaDB for the top N chunks related to new_text,
    excluding chunks whose ID starts with exclude_prefix (the just-saved entry).
    Returns a list of dicts: {text, title, created, source}.
    """
    embedding = embed_model.encode([new_text]).tolist()
    results = collection.query(
        query_embeddings=embedding,
        n_results=N_CONNECTIONS + 10,  # fetch extra to filter out self-matches
    )

    seen_sources = set()
    connections = []
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        # Deduplicate by filename so we don't show two chunks from the same page
        source_key = meta.get("filename", "")
        if source_key in seen_sources:
            continue
        if exclude_prefix and meta.get("filename", "").startswith(exclude_prefix.split("__")[0]):
            continue
        seen_sources.add(source_key)
        connections.append({
            "text": doc,
            "title": meta.get("title", "Untitled"),
            "created": meta.get("created", "")[:10],
            "source": meta.get("source", "notion"),
            "notion_url": meta.get("notion_url", ""),
        })
        if len(connections) >= N_CONNECTIONS:
            break

    return connections


def explain_connections(new_text: str, connections: list) -> list:
    """
    Ask Claude to write one sentence explaining why each connection relates
    to the new entry. Returns the same list with an 'explanation' key added.
    """
    if not connections:
        return connections

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    numbered = "\n\n".join(
        f"[{i+1}] From '{c['title']}' ({c['created']}):\n{c['text'][:400]}"
        for i, c in enumerate(connections)
    )

    prompt = (
        f"The user just wrote the following new entry:\n\n{new_text[:600]}\n\n"
        f"Here are {len(connections)} related notes from their past:\n\n{numbered}\n\n"
        f"For each past note, write exactly one short sentence (under 20 words) explaining "
        f"why it connects to the new entry. Reply as a numbered list matching the numbers above. "
        f"Be specific — name the actual idea or theme that links them."
    )

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()
    lines = [l.strip() for l in raw.splitlines() if l.strip()]

    # Extract explanation lines (lines starting with [1], [2], [3] or 1. 2. 3.)
    explanations = []
    for line in lines:
        for i in range(len(connections)):
            if line.startswith(f"[{i+1}]") or line.startswith(f"{i+1}."):
                explanations.append(line.split("]", 1)[-1].split(".", 1)[-1].strip())
                break

    # Fallback: just use lines in order if parsing fails
    if len(explanations) != len(connections):
        explanations = lines[:len(connections)]
        while len(explanations) < len(connections):
            explanations.append("")

    for c, exp in zip(connections, explanations):
        c["explanation"] = exp

    return connections
