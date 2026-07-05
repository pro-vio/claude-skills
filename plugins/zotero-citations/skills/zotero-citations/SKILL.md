---
name: zotero-citations
description: >-
  Manage a manuscript's references with Zotero as the single source of truth: render LIVE
  in-text citations + an auto References list via pandoc + citeproc (any CSL style), and
  generate a custom chronological "Legislation and case law" list that CSL can't express.
  Use whenever someone does citation/bibliography work on a paper, article, or manuscript
  backed by Zotero — e.g. "rebuild the bibliography",
  "references went stale after accepting track changes", "regenerate citations", "switch the
  style to APA", "cite this from my Zotero library", "add a legislation/case-law list", or
  editing `[@citekey]` markers, CSL-JSON/.bib, or a Works-Cited section from a reference
  manager. Also fixes Zotero items that render wrong (ALL-CAPS titles, swapped place/publisher,
  ugly citekeys, reprint dates, annotations) via direct DB edits, since the live API is
  read-only. Reach for it even when "Zotero" isn't named but the user is wrangling
  reference-managed citations. Not for Zotero app setup or PDF organising.
---

# Zotero citations

Keep a manuscript's citations **live and never stale** by treating **Zotero as the single source
of truth** and regenerating from it, instead of hand-maintaining citation text or a parallel .bib.

Two products, two pipelines:
1. **Academic apparatus** — in-text author–date citations + the auto-generated "References" list,
   via `pandoc --citeproc` with a swappable CSL style. → `scripts/build_manuscris.py`
2. **Legislation & case law** — a separate, chronological list of statutes / secondary legislation
   / court decisions, in a custom house format a CSL style cannot express. → `scripts/build_legislation_list.py`

The golden rule everything follows: **the manuscript holds `[@citekey]` markers, not frozen
citation text.** You change something in Zotero, you re-run a script. That's the whole workflow.

## Prerequisites

- **Zotero running** (local API on port 23119) for reading. `HTTP 000` = it's closed.
- **Better BibTeX** installed (gives each item a stable citekey). After editing items directly in
  the DB, trigger a BBT scan / "regenerate citekeys" so the API reflects pins in the Extra field.
- **pandoc** on PATH (with built-in citeproc).
- **Zotero library user id** for the API URL. The scripts auto-detect it (`zot.detect_user_id`)
  or take `--user-id N` / the `ZOTERO_USER_ID` env var. To find it manually: it's the number in
  your Zotero sync URL, or run `python scripts/zot.py userid`.

Set `ZOTERO_DIR` if the Zotero data dir isn't `~/Zotero`.

## Workflow 1 — render live citations

The manuscript uses pandoc citation syntax in the body:
`[@key]` parenthetical · `[-@key]` narrative (author already named in prose) · `[@key, 45–48]` locator.

```
python scripts/build_manuscris.py <manuscript.md> [--csl <style>] [--out <file.html|.docx>]
python scripts/build_manuscris.py <manuscript.md> --check   # fast: resolve keys only, no render
```

What it does: extract the cited keys → pull CSL-JSON for **only those keys** from Zotero (the
standard `?format=csljson` endpoint, where `id` == the citekey) → `pandoc --citeproc`. The
"References" list is produced automatically, so it contains **exactly what is cited** — nothing
stale, nothing extra. The output format follows the `--out` extension (`.html`, `.docx`, …).

- **`--check` = the fast edit-loop path.** Extracts keys, hits Zotero, prints which resolve and which
  are missing, then exits — **no pandoc render, no file written** (exit 0 = all resolve, 1 = some
  missing). Use it after adding/fixing a key to confirm it resolves; only do a full render once it's
  green. Skips the ~1–2 s pandoc+CSL pass that dominates a "did my key land?" check.

- **Swappable style:** `--csl apa` (or `ieee`, `american-sociological-association`, … from
  `~/Zotero/styles`, or a `.csl` path). Default = the bundled `references/chicago-author-date.csl`.
  Changing the style reflows both the in-text form and the list.
- **Verify by rendering**, then scan for leftover raw `[@` keys after any bulk citation edit.
- If a key is unresolved, the script lists it — add/fix it in Zotero and re-run (the marker and
  its place in the text stay; only the resolution updates).

## Workflow 2 — legislation & case law list

A CSL style handles the academic side only. Statutes and case law follow a custom format, so they
live in their own list, separate from "References".

Keep these items in a dedicated Zotero collection (e.g. `legislation`), as `statute` items with:
`shortTitle` (the English/working short title, e.g. "Fiscal Code (2015)"), `nameOfAct` (full
official title in the original language), `history` (the official gazette reference, e.g. Monitorul
Oficial nr. …), `dateEnacted`, `codeNumber` (e.g. "227/2015"), `extra` (locator/notes).

To **add** a statute (download its text, create the item, attach the PDF, file it into the
collection) do it as one batched write — `zot.write_session` + `zot.add_item`/`attach_pdf` (see
`references/zotero-schema.md`), and fetch the text via `references/ro-legislation-fetch.md`
(cdep.ro is the source that actually scrapes). Resolve the collection id **before** closing Zotero
and keep everything in a single close/reopen cycle.

```
python scripts/build_legislation_list.py --manuscript <md> --collection <COLLECTION_KEY> \
       [--source zotero|local --local-json <file>] [--write]
```

What it does: read the collection → **filter to what is actually cited in the body** → format →
sort chronologically and deterministically → (with `--write`) replace the
`# Legislation and case law` section (backup `.pre_leglist.bak`). Default is a dry-run preview.

- **Filter = real citation, not mention.** An item counts if its `codeNumber` appears in the body,
  or (for laws) its short title does. A purely narrative mention (no citation) is correctly excluded.
- **House format** (see §G): laws `{shortTitle}. {nameOfAct}, {history}.` · secondary legislation
  (HCL) `{nameOfAct}.` · cases `{nameOfAct}[, {history}].`
- **Deterministic order:** year → fine date (gazette publication; for cases, the decision date in
  `nameOfAct`) → type → issuer → act number. Same input ⇒ same output, regardless of API order.
- `--source local` reads a JSON mirror with the same logic — use it to preview offline (Zotero
  closed) and to **check parity** against the live `zotero` source before writing.

## Optional: OCR overlay for scanned PDFs

Some attachments are image-only scans (no extractable text) — every read either extracts
nothing or costs vision tokens. Burning a permanent, invisible OCR text layer fixes this once,
but it touches the actual library file, so **always ask first — never trigger it silently**.

When about to read a Zotero PDF and it turns out to be a scan (`ocr_overlay.detect_scan`),
stop and present the tradeoff: a rough time estimate for a one-time OCR overlay
(`ocr_overlay.estimate` — local compute, no API cost) vs. the rough token cost of reading it
via vision *this time, and every time after*, since the file stays unchanged if declined. Only
run `overlay_pdf` on explicit agreement. Full ask-first script, verification steps, and the
file-replace + DB-update recipe: `references/ocr-overlay.md`.

## Optional: PDF text-extraction cache

Re-extracting the same PDF's text on every read wastes work — memoize it as a child note on
the attachment, keyed to `storageHash`, so a second read of the same file reuses it instead of
re-extracting. `pdf_text_cache.get_cached(key)` is read-only (Zotero can stay open); only fall
through to a closed `write_session` + `pdf_text_cache.ensure_cached(...)` on an actual cache
miss — checking first, without closing Zotero, is the real efficiency win, not just skipping
re-extraction. Composes with the OCR overlay above: if `ocr_overlay.detect_scan()` says the PDF
is an unprocessed scan, run that ask-first flow first so there's a real text layer to cache.
Full recipe, note format, and the NBSP-fold gotcha: `references/pdf-text-cache.md`. About to
check many sources at once (e.g. verifying a thesis's citations against its sources)? Prefetch
the whole collection in one batch instead of hitting the cache one file at a time — see
"Pregătire în lot" in the same reference and `scripts/prefetch_collection.py`.

## Working principles (why this setup)

These are the lessons that make the pipeline robust. Follow them; they prevent the classic failures.

**A. One source of truth.** Zotero only. No hand-made `biblioteca.json` / `refs.json` in parallel —
parallel copies diverge and go stale. Do **not** work from a flattened manuscript: running
`pandoc --track-changes=accept` freezes `[@key]` into plain "(Author Year)" text and severs the
link to Zotero. Keep the master with `[@key]` markers.

**B. Resolve keys via the bulk csljson API**, where `id` == the citekey (reads native citekey +
pinned `Citation Key:` / `Original Date:` from Extra). Do **not** use Better BibTeX `item.export`
(all-or-nothing, serves a stale cache after direct DB writes) or `item.search` (flaky on multi-word
terms).

**C. Pipeline = extract keys → bulk csljson → pandoc --citeproc --csl.** The References list is
generated, never authored. Verify by rendering and scan for residue after bulk conversions.

**D. Style is a swappable parameter** (`--csl`). CSL covers the academic apparatus only — the
legislation list is custom (Workflow 2), not CSL.

**E. Zotero data hygiene.** Reprints (CMOS): put `Original Date: <year>` in Extra → renders
`Author (orig) year`. Ugly auto keys: pin `Citation Key: <key>` in Extra. Foreign-language titles
get Title-Cased by CSL unless you set `language: ro` (etc.). ALL-CAPS in the source passes through —
fix it at the item. Verify the resolved item (author + year + title); watch for duplicate/junk items.

**F. Writing to Zotero.** New items → `/connector/saveItems` live (Zotero open; lands in the
selected collection — verify). Editing/moving/deleting existing items, or annotations → write
`zotero.sqlite` directly with **Zotero closed + backup** (API is read-only for these). Batch **all**
DB writes for a task into **one** close/reopen cycle — resolve collection ids (`zot.find_collection`)
while Zotero is still open, then a single `zot.write_session` — because each cycle costs ~2–4 min.
See `references/zotero-schema.md` for tables, fieldIDs, and the `scripts/zot.py` helpers, and
`references/runtime-optimization.md` for the batching rule.

**G. Citing legislation (house style, consistent with CMOS shortened citations).** CMOS doesn't
prescribe a format for non-US legislation and usually puts laws in notes, not the reference list;
a separate "Legislation and case law" list is a deliberate house choice (standard socio-legal
practice). In-text = the **short title** (derived from the official title), treated as a shortened
note, not author–date. Carry the **year** at first mention, and at **every** mention for laws with
multiple versions in the text (e.g. two Fiscal Codes 2015/2003) so the short form stays
identifiable. The list is separate, chronological, and filtered to what's actually cited.

## Bundled resources

- `scripts/build_manuscris.py` — Workflow 1 (live academic citations).
- `scripts/build_legislation_list.py` — Workflow 2 (legislation/case-law list).
- `scripts/zot.py` — Zotero helper: read offline, detect user id, find items/PDFs; low-level
  direct-write helpers (`open_rw`, `get_value`, `set_field`, `touch`, `field_id`); and the batched
  write cycle (`write_session`, `add_item`, `attach_pdf`, `add_to_collection`, `find_collection`) —
  one close/reopen for a whole task's inserts + attachments.
- `references/chicago-author-date.csl` — default style.
- `references/zotero-schema.md` — DB schema, fieldIDs, write/annotation patterns, and the
  `write_session` ingest recipe. **Read this before any direct database edit.**
- `references/ro-legislation-fetch.md` — where to actually download Romanian statute text
  (cdep.ro works; just.ro doesn't scrape; monitoruljuridic/lege5 are paywalled).
- `scripts/ocr_overlay.py` — scan detection (`detect_scan`), time/token tradeoff estimate
  (`estimate`), and the invisible-text-layer overlay (`overlay_pdf`) for scanned PDFs.
- `references/ocr-overlay.md` — the ask-first protocol for OCR overlay: when to offer it, what
  to ask, verification (0-pixel-diff check), and the file-replace + DB-update recipe.
- `scripts/pdf_text_cache.py` — memoize PDF text extraction as a child note keyed to
  `storageHash` (`get_cached`, `ensure_cached`, `extract_pdf_text`); `zot.add_child_note` /
  `find_child_notes` / `update_note` are the general-purpose note helpers it's built on.
- `references/pdf-text-cache.md` — the check-first-without-closing-Zotero usage pattern, note
  format, and why the NBSP fold-back matters for keeping cached text greppable.
- `scripts/prefetch_collection.py` — batch-populate the PDF text cache for every attachment in a
  named collection, in one `write_session` (e.g. before verifying a thesis's citations against
  its sources — zero new permission prompts afterward, however many sources are cited). See
  "Pregătire în lot" in `references/pdf-text-cache.md`.
- `references/runtime-optimization.md` — frictionless process control (one-time permission
  allowlist, canonical start/stop/ping command shapes, DB-write protocol, acceptance test,
  portability checklist). Follow its canonical command shapes so the prefix-matched allow rules
  keep working.
- `scripts/log_perm.py` — permission-prompt monitor (hook target). At the end of each iteration,
  review `~/.claude/perm-requests.jsonl` and propose one allowlist fix per prompt cluster — the
  ritual is specified in `references/runtime-optimization.md` §"Accept monitor".
