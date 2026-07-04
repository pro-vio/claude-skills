# -*- coding: utf-8 -*-
"""
pdf_text_cache.py — memoize extracted PDF text as a Zotero child note, keyed to
the attachment's storageHash, so the same PDF is never re-extracted twice.

Why a Zotero note and not a local file: "Zotero is the only source of truth"
(SKILL.md principle A) — the cache then travels with the library and needs no
separate cache directory to keep in sync. Invalidation is automatic: if the
PDF file changes, storageHash changes, and the stored hash no longer matches.

CHECK FIRST, WITHOUT CLOSING ZOTERO — that's the actual efficiency win, not just
"don't re-extract": get_cached() is read-only and works with Zotero left open.
Only fall through to a closed write_session on an actual cache miss:

    text = get_cached(attachment_key)                    # Zotero can stay open
    if text is None:                                      # miss: NOW pay the close/reopen cost
        with zot.write_session(f"pdf-text-cache-{attachment_key}") as cur:
            text, _ = ensure_cached(cur, attachment_key, pdf_path)

Calling ensure_cached() inside a write_session on every check (skipping the
get_cached() pre-check) still avoids re-extraction, but needlessly closes
Zotero even on a hit — always check read-only first.

CLI (the `ensure` subcommand always opens a write_session, for convenience —
scripted callers should follow the two-step pattern above instead):
  python pdf_text_cache.py get <attachment_key>
  python pdf_text_cache.py ensure <attachment_key> <pdf_path>
"""
try: import sys; sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
import re, html
import fitz
import zot

MARKER = "[zotero-citations:pdf-text-cache]"


def _dehtml(text):
    """Undo Zotero's own wrapping of a plain-text note: each line becomes its
    own <p>...</p> (blank lines -> <p>&nbsp;</p>), and Zotero also substitutes
    &nbsp; for runs of 2+ consecutive spaces WITHIN a line so the HTML doesn't
    collapse them on display. Reverse both: </p> -> newline, strip remaining
    tags, unescape entities, then fold the resulting NBSP (U+00A0) back to a
    plain space — otherwise a cached phrase with a double space would no
    longer substring-match the same phrase typed with regular spaces."""
    text = re.sub(r"</p\s*>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text).replace("\xa0", " ")


def _parse_cache_note(note_text):
    """(stored_hash, extracted_text) from a cache note's body, or None if this
    note isn't one of ours. Handles both the as-written plain text (before
    Zotero's next restart) and the <div class="zotero-note znv1"> form Zotero
    wraps it in afterwards."""
    text = _dehtml(note_text) if "zotero-note" in note_text[:80] else note_text
    lines = text.strip("\n").splitlines()
    if not lines or MARKER not in lines[0]:
        return None
    if len(lines) < 2 or not lines[1].strip().startswith("storageHash:"):
        return None
    stored_hash = lines[1].split(":", 1)[1].strip()
    body_lines = lines[2:]
    while body_lines and not body_lines[0].strip():
        body_lines.pop(0)  # drop the blank/nbsp separator line, in either format
    return stored_hash, "\n".join(body_lines)


def _find_cache_note(attachment_item_id):
    """(note_item_id, stored_hash, text) for the existing cache note among an
    attachment's children, or None if there is none yet."""
    for note_id, key, note_text in zot.find_child_notes(attachment_item_id):
        parsed = _parse_cache_note(note_text)
        if parsed:
            return note_id, parsed[0], parsed[1]
    return None


def get_cached(attachment_key):
    """Extracted text if a fresh cache note exists (hash matches current
    storageHash), else None. Read-only — works whether Zotero is open or not."""
    row = zot._ro().execute("SELECT itemID, storageHash FROM items JOIN itemAttachments USING(itemID) "
                             "WHERE key=?", (attachment_key,)).fetchone()
    if not row:
        raise ValueError(f"no attachment with key {attachment_key!r}")
    item_id, current_hash = row
    found = _find_cache_note(item_id)
    if not found:
        return None
    _, stored_hash, text = found
    return text if stored_hash == current_hash else None


def extract_pdf_text(pdf_path):
    """Plain per-page text extraction, page-marked. Call ocr_overlay.detect_scan()
    first if the source might be an unprocessed scan — this function does not
    OCR anything; it only pulls whatever text layer the PDF already has."""
    doc = fitz.open(pdf_path)
    parts = []
    for i, page in enumerate(doc):
        parts.append(f"--- page {i + 1} ---\n{page.get_text().strip()}")
    doc.close()
    return "\n\n".join(parts)


def _find_cache_note_cur(cur, parent_item_id):
    """Same lookup as _find_cache_note, but over the CALLER's own cursor —
    not a fresh zot._ro() connection. Required inside ensure_cached: a second
    connection opened mid-write-transaction (e.g. on item 2+ of a batched
    write_session, once item 1's INSERT has opened a transaction on the main
    connection) hits 'database is locked' against SQLite's own writer lock.
    Confirmed: a batch of 81 ensure_cached calls in one write_session failed
    ALL 81 with this error before the fix — the write_session's own commit()
    still "succeeded" (as a no-op, nothing had actually been written), so no
    data was lost, but nothing was cached either. One connection per session
    for both reads and writes, always, is the only safe pattern here."""
    for note_id, note_text in cur.execute(
            "SELECT itemID, note FROM items JOIN itemNotes USING(itemID) WHERE parentItemID=?",
            (parent_item_id,)).fetchall():
        parsed = _parse_cache_note(note_text)
        if parsed:
            return note_id, parsed[0], parsed[1]
    return None


def ensure_cached(cur, attachment_key, pdf_path):
    """Inside a zot.write_session: return (text, was_cached). Extracts and
    writes the cache note only when there is no fresh cache already."""
    row = cur.execute("SELECT itemID, storageHash FROM items JOIN itemAttachments USING(itemID) "
                       "WHERE key=?", (attachment_key,)).fetchone()
    if not row:
        raise ValueError(f"no attachment with key {attachment_key!r}")
    item_id, current_hash = row
    found = _find_cache_note_cur(cur, item_id)
    if found and found[1] == current_hash:
        return found[2], True
    text = extract_pdf_text(pdf_path)
    note_body = f"{MARKER}\nstorageHash: {current_hash}\n\n{text}"
    if found:
        zot.update_note(cur, found[0], note_body)
    else:
        zot.add_child_note(cur, item_id, note_body)
    return text, False


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else None
    if cmd == "get":
        t = get_cached(sys.argv[2])
        print(t if t is not None else "(no fresh cache)")
    elif cmd == "ensure":
        with zot.write_session(f"pdf-text-cache-{sys.argv[2]}") as cur:
            text, was_cached = ensure_cached(cur, sys.argv[2], sys.argv[3])
        print(f"was_cached={was_cached}  chars={len(text)}")
    else:
        print(__doc__)
