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

**Add a statute** (itemTypeID 36): insert `items`, then `itemData` rows for
`nameOfAct`/`codeNumber`/`dateEnacted` (date format `YYYY-00-00 YYYY`), add to the collection via
`collectionItems`, then attach the PDF (copy file to `storage/<8charKey>/<file>`, linkMode 0,
storageHash = md5, storageModTime = mtime·1000).

**Native annotation** (color encodes author — convention: purple `#a28ae5` = "Claude", yellow = user):
compute the highlight rectangles read-only with PyMuPDF while Zotero is open (Zotero/PDF.js use
CropBox-relative, bottom-left origin: `H − y`), queue them, then flush all writes in one pass with
Zotero closed. Don't re-run a write that already succeeded — it duplicates annotations.

**Child note** (summaries etc.): insert `items` (itemTypeID 1) + `itemNotes(itemID, parentItemID, note)`.
**Write PLAIN TEXT** (blank-line paragraph breaks), NOT HTML: externally-written note HTML is
escaped/sanitized at the next startup (wrapped in `zotero-note znv1`, tags rendered as literal text).
Zotero converts the plain text to proper `<p>` paragraphs itself, stably.

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
