# PDF text cache (memoize extraction as a Zotero child note)

Re-extracting the same PDF's text on every read is wasted work — the source doesn't change
between reads. `scripts/pdf_text_cache.py` memoizes the extraction as a **child note on the
attachment itself**, keyed to `storageHash`, instead of a parallel cache file: it travels with
the library, needs no separate directory, and invalidates automatically when the PDF file
changes (a new `storageHash` no longer matches the one recorded in the note).

## The two-step pattern — check first, don't close Zotero on a hit

The actual efficiency win is **not just** "don't re-extract" — it's "don't force a close/reopen
cycle to find out whether you need to." `get_cached()` is read-only and works with Zotero left
open; only fall through to a closed `write_session` on an actual miss:

```python
import pdf_text_cache, zot

text = pdf_text_cache.get_cached(attachment_key)          # read-only — Zotero can stay open
if text is None:                                          # miss: NOW pay the close/reopen cost
    with zot.write_session(f"pdf-text-cache-{attachment_key}") as cur:
        text, _ = pdf_text_cache.ensure_cached(cur, attachment_key, pdf_path)
```

Calling `ensure_cached` inside a fresh `write_session` on every check (skipping the read-only
pre-check) still avoids re-extraction, but needlessly closes Zotero even on a cache hit — always
check `get_cached()` first, and only open the write cycle when it returns `None`.

## Linked attachments: `storageHash` is always NULL — hash the file yourself

Zotero attachments come in two kinds: an **imported stored copy** (file lives under
`storage/<key>/`, Zotero computes and tracks `storageHash`) and a **linked file** (attachment
`path` is an absolute path to a file Zotero doesn't own — e.g. a PDF still sitting in a thesis
student's own reference folder). Zotero never computes `storageHash` for the second kind — it's
always `NULL` in the DB, by design, not a data-quality gap to fix.

The first version of this cache didn't account for that: it wrote `f"storageHash: {current_hash}"`
straight from the DB value, and when that value was Python's `None`, the note ended up with the
literal text `storageHash: None`. On every later check, the *string* `"None"` parsed back out of
the note was compared against a freshly-queried *actual* `None` — and `"None" == None` is always
`False` in Python. The cache looked permanently stale for every linked attachment, no matter how
many times it was rewritten. This happened for real, silently, across a separate coordination
project's reference folder (13 linked PDFs) before it was caught.

The fix, in `_content_hash(stored_hash, pdf_path)`: use Zotero's `storageHash` when the attachment
has one; otherwise compute an MD5 of the file's own bytes as the fallback content key. This needs
`zot.attachment_path(key)` to resolve a linked attachment's absolute path (a stored-copy path is
already the DB value; a linked path needs no `storage/<key>/` join). `get_cached` and
`ensure_cached` both changed to route through `_content_hash` — never write the raw DB value
(which can be `None`) into a note directly.

If you're diagnosing "a command said the file wasn't cached" and the attachment in question has
no `storage/<key>/` copy — check `itemAttachments.storageHash IS NULL` first; that's the tell.

## Batching many items in one `write_session`: never open a second connection

A batch of `ensure_cached` calls **must** look up each item's existing cache note through the
**same cursor** the `write_session` gave you (`ensure_cached` does this internally, via
`_find_cache_note_cur(cur, ...)`) — never through a fresh `zot._ro()` connection while a write
transaction from an earlier item in the same loop is still open. A real run hit exactly this: 81
items in one `write_session`, every single one failed with `database is locked`, because the
first version of `ensure_cached` looked up existing notes via `_find_cache_note` →
`zot.find_child_notes` → a brand-new `_ro()` connection. That's harmless for a single
stand-alone call (no write has happened yet, so no lock exists) but breaks the moment a second
item's lookup runs while item one's `INSERT` is still uncommitted on the write connection.
**No data was lost** — the session's own `commit()` still "succeeded" as a no-op (nothing had
actually been written), which is how the failure was caught: the reported `pending sync` count
didn't match the number of items processed. One connection, for both reads and writes, for the
whole session — the `get_cached()` stand-alone path is unaffected since it never runs inside an
open write transaction.

## Pregătire în lot pentru verificarea unei teze (`prefetch_collection.py`)

When the next step is comparing a thesis's in-text citations against their actual sources (grading
workflow), the friction isn't re-extraction — it's the **permission prompt**, once per new source
file touched during that pass. `scripts/prefetch_collection.py <collection name>` resolves every
PDF attachment in a Zotero collection (the student's subcollection, e.g. `matyasi_desiree`) and
runs `ensure_cached` on all of them in **one** `write_session` — same batching rule as above, one
close/reopen for the whole collection, not one per source:

```
python prefetch_collection.py matyasi_desiree
```

Run this once before starting the source-verification pass; after it, `get_cached()` serves every
citation check read-only, Zotero can stay open, and no new file-read prompt appears no matter how
many sources the thesis cites. Pair it with adding the folder that actually holds the PDFs (a
student's own reference folder, for linked attachments) to `additionalDirectories` in
`~/.claude/settings.json` — the script removes the re-extraction cost, that settings entry removes
the per-file permission prompt; neither alone is enough.

**Real failure mode hit while building this, worth knowing if it recurs:** a full run failed
`database is locked` on *every* attachment even with the one-cursor rule above already correctly
in place. Root cause was environmental, not a code bug: `write_session.__enter__` checks once,
at the start, that Zotero is closed — it does not re-check during the loop. Zotero got relaunched
between that check and the loop's per-item queries (a manual reopen mid-run), and a second live
writer against the same file is exactly what produces this error. Fix was operational, not a code
change: close Zotero, run the script, and don't reopen it until the script has printed its final
manifest line. If this error reappears despite the single-cursor code being correct, check
`Get-Process zotero` and the DB's `-journal`/`-wal` files before re-reading the script — the
symptom is identical to the connection-reuse bug this file documents above, but the cause here is
a second *process*, not a second connection object in the same script.

## Scans: run the OCR-overlay ask-first flow before this, not instead of it

`extract_pdf_text` pulls whatever text layer the PDF already has — it does **not** OCR anything.
If the attachment is an unprocessed scan, extraction returns near-empty text and caching that is
pointless. Check `ocr_overlay.detect_scan()` first; if it's a scan, run the ask-first OCR-overlay
workflow (`references/ocr-overlay.md`) so the PDF has a real text layer, *then* use this cache on
top of it. The two features compose: overlay makes the scan text-bearing once; the cache makes
every subsequent read of *any* text-bearing PDF (scanned or born-digital) skip re-extraction.

## Cache note format and why it survives Zotero's own rewriting

The note is written as plain text (never HTML — see the zotero-schema.md "Child note" pattern):

```
[zotero-citations:pdf-text-cache]
storageHash: <the attachment's storageHash at extraction time>

--- page 1 ---
<page 1 text>

--- page 2 ---
<page 2 text>
...
```

At Zotero's next startup it wraps this in its own `<div class="zotero-note znv1">`, turning each
line into its own `<p>` (blank lines become `<p>&nbsp;</p>`) — and, separately, substitutes
`&nbsp;` for any run of 2+ consecutive spaces **within** a line, so the HTML doesn't visually
collapse them. `pdf_text_cache._dehtml` reverses both: strips the paragraph tags back to
newlines, unescapes HTML entities, then folds the resulting NBSP (U+00A0) back to a plain space —
without that last step a cached phrase containing a double space would stop substring-matching
the same phrase typed with regular spaces, silently degrading search/verification against the
cached text. `get_cached` and `_parse_cache_note` handle both the as-written (before Zotero's
next restart) and the Zotero-wrapped form transparently — callers never need to know which one
they're reading.

## Updating a stale cache

If a fresh cache note already exists (hash matches), `ensure_cached` reuses it untouched. If one
exists but is **stale** (hash mismatch — the PDF file changed, e.g. after an OCR overlay), it
**overwrites the existing note in place** (`zot.update_note`) rather than creating a second one —
there is never more than one cache note per attachment.

## Helpers used (in `scripts/zot.py`)

- `add_child_note(cur, parent_item_id, note_text)` — general-purpose, not cache-specific: create
  a plain-text child note under any item **or attachment** (Zotero's own PDF-reader sidebar uses
  the same attachment-as-parent mechanism for "add note from annotations").
- `find_child_notes(parent_item_id)` — read-only list of `(noteItemID, key, note_text)`.
- `update_note(cur, note_item_id, note_text)` — overwrite an existing note's content in place.
