"""
notion_import.py — pulls every page accessible to the Notion integration
and writes each one as a Markdown file (with YAML frontmatter) into data/raw/.

Idempotent: already-exported pages are skipped. Safe to re-run to pick up
new pages without re-fetching existing ones.
"""

import os
import time
import re

import yaml
from dotenv import load_dotenv
from notion_client import Client
from notion_client.errors import APIResponseError
from slugify import slugify

load_dotenv()

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "data", "raw")

notion = Client(auth=NOTION_TOKEN)

# Notion asks integrations to stay under ~3 requests/second on average.
REQUEST_DELAY_SECONDS = 0.35


def call_with_retry(fn, **kwargs):
    """Call a notion-client method, retrying on rate limits with backoff."""
    while True:
        try:
            result = fn(**kwargs)
            time.sleep(REQUEST_DELAY_SECONDS)
            return result
        except APIResponseError as e:
            if e.code == "rate_limited":
                retry_after = float(e.response.headers.get("Retry-After", 1))
                print(f"  rate limited, waiting {retry_after}s...")
                time.sleep(retry_after)
                continue
            raise


# ---------------------------------------------------------------------------
# Discovery: find every page accessible to the integration
# ---------------------------------------------------------------------------

def discover_pages():
    """Return every page object (not database containers) shared with the integration."""
    pages = []
    cursor = None
    while True:
        response = call_with_retry(
            notion.search,
            filter={"property": "object", "value": "page"},
            start_cursor=cursor,
            page_size=100,
        )
        pages.extend(response["results"])
        if not response.get("has_more"):
            break
        cursor = response["next_cursor"]
    return pages


# ---------------------------------------------------------------------------
# Property extraction (for database rows, and page titles)
# ---------------------------------------------------------------------------

def rich_text_to_plain(rich_text_array):
    return "".join(rt["plain_text"] for rt in rich_text_array)


def get_page_title(page):
    for prop in page["properties"].values():
        if prop["type"] == "title":
            text = rich_text_to_plain(prop["title"])
            return text if text else "Untitled"
    return "Untitled"


def render_property_value(prop):
    ptype = prop["type"]
    value = prop.get(ptype)

    if value is None:
        return None
    if ptype in ("title", "rich_text"):
        return rich_text_to_plain(value) or None
    if ptype == "number":
        return value
    if ptype == "select":
        return value["name"]
    if ptype == "status":
        return value["name"]
    if ptype == "multi_select":
        return [item["name"] for item in value]
    if ptype == "date":
        if value["end"]:
            return f"{value['start']} to {value['end']}"
        return value["start"]
    if ptype == "checkbox":
        return value
    if ptype == "url":
        return value
    if ptype == "email":
        return value
    if ptype == "phone_number":
        return value
    if ptype == "people":
        return [person.get("name", person["id"]) for person in value]
    if ptype == "files":
        return [f["name"] for f in value]
    if ptype == "relation":
        return [rel["id"] for rel in value]
    if ptype in ("created_time", "last_edited_time"):
        return value
    if ptype in ("created_by", "last_edited_by"):
        return value.get("name", value.get("id"))
    if ptype == "formula":
        return render_property_value({"type": value["type"], value["type"]: value[value["type"]]})
    if ptype == "rollup":
        return None  # rollups vary too much in shape to render generically; skip
    return None


def extract_frontmatter_properties(page):
    """Pull all database-row properties (skipping the title, handled separately)."""
    extra = {}
    for name, prop in page["properties"].items():
        if prop["type"] == "title":
            continue
        rendered = render_property_value(prop)
        if rendered is not None:
            extra[name] = rendered
    return extra


# ---------------------------------------------------------------------------
# Block fetching and Markdown conversion
# ---------------------------------------------------------------------------

def fetch_block_children(block_id):
    blocks = []
    cursor = None
    while True:
        response = call_with_retry(
            notion.blocks.children.list,
            block_id=block_id,
            start_cursor=cursor,
            page_size=100,
        )
        blocks.extend(response["results"])
        if not response.get("has_more"):
            break
        cursor = response["next_cursor"]
    return blocks


ANNOTATION_MARKERS = [
    ("code", "`"),
    ("bold", "**"),
    ("italic", "_"),
    ("strikethrough", "~~"),
]


def rich_text_to_markdown(rich_text_array):
    parts = []
    for rt in rich_text_array:
        text = rt["plain_text"]
        annotations = rt["annotations"]
        for key, marker in ANNOTATION_MARKERS:
            if annotations.get(key):
                text = f"{marker}{text}{marker}"
        link = rt.get("href")
        if link:
            text = f"[{text}]({link})"
        parts.append(text)
    return "".join(parts)


# Block types that are references to another page, which gets (or will get)
# its own file — render as a link instead of inlining/recursing.
REFERENCE_BLOCK_TYPES = {"child_page", "child_database", "link_to_page"}


def render_blocks(blocks, indent=0):
    lines = []
    pad = "  " * indent
    for block in blocks:
        btype = block["type"]
        data = block.get(btype, {})

        if btype in REFERENCE_BLOCK_TYPES:
            title = data.get("title") or "linked page"
            lines.append(f"{pad}- 🔗 {title} (see its own note)")
            continue

        if btype == "paragraph":
            text = rich_text_to_markdown(data["rich_text"])
            lines.append(f"{pad}{text}" if text else "")
        elif btype == "heading_1":
            lines.append(f"{pad}# {rich_text_to_markdown(data['rich_text'])}")
        elif btype == "heading_2":
            lines.append(f"{pad}## {rich_text_to_markdown(data['rich_text'])}")
        elif btype == "heading_3":
            lines.append(f"{pad}### {rich_text_to_markdown(data['rich_text'])}")
        elif btype == "bulleted_list_item":
            lines.append(f"{pad}- {rich_text_to_markdown(data['rich_text'])}")
        elif btype == "numbered_list_item":
            lines.append(f"{pad}1. {rich_text_to_markdown(data['rich_text'])}")
        elif btype == "to_do":
            box = "x" if data["checked"] else " "
            lines.append(f"{pad}- [{box}] {rich_text_to_markdown(data['rich_text'])}")
        elif btype == "toggle":
            lines.append(f"{pad}- **{rich_text_to_markdown(data['rich_text'])}**")
        elif btype == "quote":
            lines.append(f"{pad}> {rich_text_to_markdown(data['rich_text'])}")
        elif btype == "callout":
            emoji = data.get("icon", {}).get("emoji", "💡")
            lines.append(f"{pad}> {emoji} {rich_text_to_markdown(data['rich_text'])}")
        elif btype == "code":
            language = data.get("language", "")
            code_text = rich_text_to_plain(data["rich_text"])
            lines.append(f"{pad}```{language}\n{code_text}\n{pad}```")
        elif btype == "divider":
            lines.append(f"{pad}---")
        elif btype == "bookmark":
            lines.append(f"{pad}[{data.get('url')}]({data.get('url')})")
        elif btype == "image":
            url = data.get("file", data.get("external", {})).get("url", "")
            caption = rich_text_to_plain(data.get("caption", []))
            lines.append(f"{pad}![{caption}]({url})")
        elif btype == "table":
            pass  # table_row children below render the actual rows
        elif btype == "table_row":
            cells = [rich_text_to_markdown(cell) for cell in data["cells"]]
            lines.append(f"{pad}| " + " | ".join(cells) + " |")
        elif btype in ("column_list", "column", "synced_block"):
            pass  # layout-only containers; their children render normally below
        else:
            lines.append(f"{pad}[unsupported block: {btype}]")

        if block.get("has_children") and btype not in REFERENCE_BLOCK_TYPES:
            children = fetch_block_children(block["id"])
            child_indent = indent if btype in ("column_list", "column", "synced_block", "table") else indent + 1
            lines.append(render_blocks(children, indent=child_indent))

    return "\n".join(line for line in lines if line is not None)


# ---------------------------------------------------------------------------
# File writing
# ---------------------------------------------------------------------------

def build_filename(title, page_id):
    short_id = page_id.replace("-", "")[:8]
    slug = slugify(title)[:60] or "untitled"
    return f"{slug}-{short_id}.md"


def export_page(page):
    page_id = page["id"]
    title = get_page_title(page)

    frontmatter = {
        "title": title,
        "notion_url": page["url"],
        "last_edited_time": page["last_edited_time"],
        "page_id": page_id,
    }
    frontmatter.update(extract_frontmatter_properties(page))

    blocks = fetch_block_children(page_id)
    body = render_blocks(blocks)

    content = "---\n" + yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=True) + "---\n\n" + body + "\n"

    filename = build_filename(title, page_id)
    filepath = os.path.join(OUTPUT_DIR, filename)

    if os.path.exists(filepath):
        return filename, "skipped"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    return filename, "written"


def run_sync(progress_fn=print):
    """
    Pull new pages from Notion into data/raw/. Already-exported pages are skipped.
    Returns (pages_written, pages_skipped, pages_failed).
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    progress_fn("Discovering pages shared with the integration...")
    pages = discover_pages()
    progress_fn(f"Found {len(pages)} pages.")

    written = skipped = failed = 0
    for i, page in enumerate(pages, start=1):
        title = get_page_title(page)
        try:
            filename, status = export_page(page)
            if status == "skipped":
                skipped += 1
            else:
                written += 1
                progress_fn(f"[{i}/{len(pages)}] wrote {filename}")
        except Exception as e:
            failed += 1
            progress_fn(f"[{i}/{len(pages)}] FAILED on '{title}': {e}")

    return written, skipped, failed


def main():
    written, skipped, failed = run_sync(progress_fn=print)
    print(f"\nDone. {written} new pages written, {skipped} skipped, {failed} failed.")
    print(f"Pages are in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
