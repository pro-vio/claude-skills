# Zotero internals — reading & writing zotero.sqlite

Read this when you need to **edit existing items**, **write annotations**, or **add statutes**
directly in the database. For just rendering citations you don't need any of this — the API is enough.

## Access model (why direct sqlite)

- **Read, live (Zotero running):** the local web API on `http://127.0.0.1:23119`.
  - `GET /api/users/<uid>/items?format=csljson` → `id` == the Better BibTeX citekey. Use for citations.
  - `GET /api/users/<uid>/collections/<key>/items?format=json` → raw fields (nameOfAct, history, …).
  - `HTTP 000` from port 23119 = Zotero is **closed**.
- **Create new items, live:** `POST /connector/saveItems` (Zotero open, returns HTTP 201).
  Lands in the **currently selected collection** — verify the selection or move afterwards.
- **Edit / move / delete existing items, or write annotations:** the API is READ-ONLY for this
  (`POST` → "Endpoint does not support method"). Do it by writing `zotero.sqlite` **directly**,
  with **Zotero CLOSED** and a **backup first**. `zot.open_rw()` refuses if Zotero is running.

Local-only library (no sync) ⇒ direct writes are safe. Always bump `items.version` and set
`synced=0` (helper `zot.touch`) so a later sync reconciles cleanly.

## Backup discipline (non-negotiable)

Before any DB write: `cp ~/Zotero/zotero.sqlite ~/Zotero/zotero.sqlite.pre-<task>.bak`.
The scripts that write also do this, but make your own checkpoint for ad-hoc edits.

## Tables you touch

- `items(itemID, itemTypeID, key, version, synced, dateModified, clientDateModified, libraryID)`
- `itemData(itemID, fieldID, valueID)` — one row per field on an item.
- `itemDataValues(valueID, value)` — **value is UNIQUE**. Reuse via `get_value` (insert if absent).
  Never UPDATE a shared value row; point the item's `itemData.valueID` at a new/existing value.
- `itemCreators` / `creators(firstName,lastName)` / `creatorTypes`.
- `collections(collectionID, key)` / `collectionItems(collectionID, itemID, orderIndex)`.
- `itemAttachments(itemID, parentItemID, linkMode, contentType, path, storageHash, storageModTime)`.
- `itemAnnotations(itemID, parentItemID, type, authorName, text, comment, color, pageLabel, sortIndex, position, isExternal)`.
- `deletedItems(itemID, dateDeleted)` — inserting here = move to **trash** (reversible, preferred over hard delete).

## Trashed items still appear in every table — filter them out explicitly

A trashed item is **not** removed from `items`/`itemAttachments`/`itemData` — it stays exactly as
it was, plus a row in `deletedItems`. Any read query meant to reflect "active library content"
(finding a PDF to open, listing an item's attachments, checking for duplicates) must exclude it,
or a trashed scan/duplicate silently reappears as if it were live. Trashing is also **per-item,
independently** — a parent can be active while one of its attachments is trashed (e.g. a scan
superseded by a text-native duplicate with highlights, the parent record kept). Always check the
specific row you're reading, not just its parent.

```sql
-- append to any items/itemAttachments query that means "currently in the library"
AND itemID NOT IN (SELECT itemID FROM deletedItems)
```

`zot.py` exposes this as `zot.NOT_TRASHED` (an f-string-able clause) and `zot.find()` already
applies it to both the item and its attachment lookup.

## itemTypeID (common)

`1` = note · `3` = attachment · `36` = statute. Use `SELECT itemTypeID FROM itemTypes WHERE typeName=?`
if unsure — IDs are stable per install but confirm rather than assume.

## fieldID — resolve, don't hardcode

IDs are stable within an install but **look them up** (`zot.field_id(cur,'name')`). Observed on one
install (illustrative, verify): `title 1`, `shortTitle 14`, `language 15`, `extra 19`, `publisher 25`,
`place 26`, `history 39`, `publicationTitle 41`, `originalPublisher 49`, `originalPlace 50`,
`nameOfAct 116`, `codeNumber 117`, `dateEnacted 119`.

## Patterns

**Edit a field** (e.g. fix ALL-CAPS title, swap place/publisher, set language):
```python
con = zot.open_rw(); cur = con.cursor()
zot.set_field(cur, item_id, zot.field_id(cur,'title'), "Proper Title Case")
zot.touch(cur, item_id); con.commit(); con.close()
```

**CMOS reprints & ugly keys via the Extra field** (read by the csljson API after a BBT scan):
- `Original Date: 1965` → renders `Olson (1965) 2003` (original in `[ ]` in-text, `( )` in list).
- `Citation Key: ShortPin` → pins an otherwise-ugly auto key (long institutional author).
Set these on the item's `extra` field; no native originalDate/citationKey field needed.

**RO/foreign titles get Title-Cased by CSL** when `language` is missing → set `language: ro`
so citeproc leaves the title as written. ALL-CAPS in the source passes through → fix at the item.

**Add a statute / any new item — use the batched helpers, don't hand-roll SQL.** `zot.py` ships
`write_session` + `add_item`/`attach_pdf`/`add_to_collection`/`find_collection`, which do the whole
protocol (wait-until-quiescent → backup → write → verify-on-disk) and all the create SQL. Resolve
collection ids with `find_collection` **while Zotero is still open**, then one closed cycle:

```python
import zot
key, cid = zot.find_collection("2026_teze")          # read-only — do this BEFORE closing Zotero
with zot.write_session("roman-ana") as cur:           # close Zotero first; this waits + backs up
    sid = zot.add_item(cur, "statute",
        {"shortTitle": "Legea 57/1968", "nameOfAct": "Lege nr. 57/1968 …",
         "codeNumber": "57/1968", "dateEnacted": "1968-00-00 1968",   # date format YYYY-00-00 YYYY
         "history": "Buletinul Oficial nr. …"}, collection_id=cid)
    zot.attach_pdf(cur, sid, "legislatie/Legea_57_1968.pdf")          # stored copy + md5 hash
    zot.add_item(cur, "webpage", {"title": "Servicii", "url": "…", "language": "ro"},
        creators=[("author", "LOGS Grup de Inițiative Sociale")], collection_id=cid)  # literal author
```

`add_item` fields = `{fieldName: value}`; creators are `("author", "Whole Institution")` (literal,
fieldMode 1) or `("author", last, first)` (personal). Under the hood it still does what the manual
recipe did — insert `items`, `itemData` rows, `collectionItems`, and for PDFs copy to
`storage/<8charKey>/<file>` with linkMode 0, storageHash = md5, storageModTime = mtime·1000 — but as
one tested call. **For pure *creation* with Zotero left OPEN, `POST /connector/saveItems` (HTTP 201)
needs no close at all** — reach for `write_session` when the same batch also edits or attaches.

**Native annotation** (color encodes author — convention: purple `#a28ae5` = "Claude", yellow = user):
compute the highlight rectangles read-only with PyMuPDF while Zotero is open (Zotero/PDF.js use
CropBox-relative, bottom-left origin: `H − y`), queue them, then flush all writes in one pass with
Zotero closed. Don't re-run a write that already succeeded — it duplicates annotations.

**Child note** (summaries, caches): `zot.add_child_note(cur, parent_item_id, note_text)` —
works for both a top-level item and an **attachment** as parent (Zotero's PDF-reader sidebar
uses attachment-as-parent for "add note from annotations"). `zot.find_child_notes(parent_item_id)`
reads them back (read-only); `zot.update_note(cur, note_item_id, note_text)` overwrites one in
place. **Write PLAIN TEXT** (blank-line paragraph breaks), NOT HTML: externally-written note HTML
is escaped/sanitized at the next startup (wrapped in `zotero-note znv1`, tags rendered as literal
text). Zotero converts the plain text to proper `<p>` paragraphs itself, stably — but also
substitutes `&nbsp;` for runs of 2+ consecutive spaces within a line, so anything read back that
needs to stay substring-searchable (e.g. a text cache) must fold NBSP back to a plain space; see
`references/pdf-text-cache.md` for the worked example (`pdf_text_cache.py` memoizes PDF text
extraction this way).

## Gotchas

- **Shutdown race:** after a graceful kill, a residual Zotero process may flush AFTER your write
  and silently discard it. Wait until all `zotero.exe` processes AND `zotero.sqlite-journal`/`-wal`
  are gone, write, then **verify on disk** before restarting Zotero.
- The **local API omits annotations** from `/items/<attKey>/children` — a zero result does not mean
  the highlights failed; check `itemAnnotations` in the DB or the Zotero reader.
- A junk-looking attachment titled like a date (`1969-01-01…`) is usually the item's **PDF**
  (`itemAttachments.parentItemID` points to the real item) — NOT a duplicate to delete. Check first.
- Duplicate/junk bib items do happen (mangled titles, wrong years) — verify the resolved item
  (author + year + title) before citing or editing; fuzzy lookups can hit the wrong one.
- `place`/`publisher` are easy to enter swapped → check rendered output, not just the field.
- **Trashed items don't disappear from the tables** — an `INSERT OR IGNORE` into `deletedItems`
  can silently no-op if the item was already trashed (PK conflict on `itemID`), which is itself
  a useful tell that it was trashed earlier than you thought. See "Trashed items still appear in
  every table" above — apply `zot.NOT_TRASHED` to any read query over item/attachment tables.
