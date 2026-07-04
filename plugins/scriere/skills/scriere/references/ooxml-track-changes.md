# OOXML track-changes — schema, patterns, gotchas

Reference for `scripts/docx_track.py`. Read this before extending the helper or hand-editing
`word/document.xml`. A `.docx` is a ZIP of XML parts; everything below lives under `word/`.

## Namespaces

| Prefix | URI | Used for |
|---|---|---|
| `w`   | `…/wordprocessingml/2006/main` | runs, text, ins/del, comments, footnotes |
| `w14` | `…/word/2010/wordml` | `paraId`, `textId` on comment paragraphs |
| `w15` | `…/word/2012/wordml` | `commentEx` (threading), `person` (people.xml) |
| `w16` | `…/word/2016/wordml/cid` | `commentId` (commentsIds.xml) |
| xml   | `…/XML/1998/namespace` | `xml:space="preserve"` on whitespace-edge text |

## The text model

A paragraph `w:p` contains runs `w:r`; each run holds `w:t` (visible text). Word splits text
into runs **arbitrarily** (a formatting boundary, a spell-check marker, nothing) — so a phrase
you see as continuous may be spread across several `w:r`. This is the single biggest source of
"MISS": the helper matches a substring **inside one direct run**. If a needle misses though the
text is clearly there, it is split across runs — shorten the needle to a fragment that fits one
run, or anchor differently.

`xml:space="preserve"` must be set on any `w:t`/`w:delText` whose text starts or ends with a
space, or Word collapses it. The helper does this automatically.

Apostrophes/quotes in real manuscripts are typically **typographic** (`’ „ "`), not ASCII
(`' "`). Copy the exact character from the source when building a needle.

## Tracked changes

| Change | Element | Notes |
|---|---|---|
| insertion | `w:ins`(id, author, date) → `w:r/w:t` | the inserted run lives *inside* `w:ins` |
| deletion | `w:del`(id, author, date) → `w:r/w:delText` | `delText`, not `t` |
| paragraph-format change | `w:pPrChange`(id, author, date) → inner `w:pPr` | the inner `w:pPr` records the OLD properties; the live `w:pPr` holds the new ones |

A **tracked replace** = `w:del`(old) immediately followed by `w:ins`(new) in place of the
original run, with any unaffected prefix/suffix re-emitted as plain runs. `id` must be unique
across the document; the helper uses one running counter for ins/del/pPrChange/comment ids.

**Editing text the user already inserted** (their own `w:ins`): you cannot nest `w:ins`. Two
cases — append *after* their insertion → drop a sibling `w:ins` right after their `w:ins`
(`insert_after_ins`); fix a typo *inside* their insertion → edit the `w:t` in place
(`fix_in_ins`), since it is already attributed to them.

## New anchored comments (`add_comment`)

A brand-new top-level comment, anchored at **paragraph level**: `commentRangeStart` right after
`w:pPr`, `commentRangeEnd` + a `CommentReference` run appended at the paragraph's end. The
comment visually covers the whole paragraph — right for reviewer notes, and it avoids run
surgery entirely.

- The paragraph is found by substring match on its concatenated `w:t` text (same
  quote/space/dash normalization as `replace`). TOC paragraphs (`pStyle` starting with `TOC`)
  are skipped when a non-TOC match exists; `occurrence="last"` picks the last match — needed
  when the anchor is a heading whose text also appears in the table of contents.
- If the document has no comments yet, `_ensure_comment_parts` creates `word/comments.xml` and
  `word/commentsExtended.xml` **plus** their `[Content_Types].xml` overrides and
  `document.xml.rels` relationships. `people.xml`/`commentsIds.xml` are optional — Word opens
  fine without them (Google Docs exports ship without them too).
- The new `w:id` is bumped above any existing comment id; the `commentEx` entry has no
  `paraIdParent` (top-level) and `done="0"`.

**Google Docs exports** bury most body paragraphs inside `w:sdt`/`w:sdtContent` wrappers
(`goog_rdk_*` tags). `_paras()` therefore iterates `body.iter(w:p)` — all descendants — not just
direct children; this also brings table-cell paragraphs into scope for all matchers.

## Threaded comment replies

A reply is a normal comment that is *linked* to its parent. Parts involved:

- `comments.xml` — `w:comment`(id, author, date, initials) → `w:p`(w14:paraId, w14:textId) with
  `pStyle=CommentText`; first run carries `rStyle=CommentReference` + `w:annotationRef`, second
  run the reply text.
- `commentsExtended.xml` — `w15:commentEx`(w15:paraId = the reply's paraId,
  **w15:paraIdParent = the parent comment's paraId**, w15:done="0"). This `paraIdParent` link is
  what makes Word render it as a threaded reply rather than a separate comment.
- `commentsIds.xml` — `w16:commentId`(w16:paraId, w16:durableId).
- `people.xml` — register the author once as `w15:person`(w15:author) with a `presenceInfo`.
- `document.xml` (body) — reuse the parent's span: add `commentRangeStart`/`commentRangeEnd`
  with the new id around the same range, and a `w:r` with `rStyle=CommentReference` +
  `w:commentReference`(id) right after the parent's reference run.

`paraId`/`durableId` are 8-hex-digit ids; they only need to be unique and stable within the doc.

## Footnotes

- `footnotes.xml` — new `w:footnote`(id) → `w:p`(`pStyle=FootnoteText`) whose first run has
  `rStyle=FootnoteReference` + `w:footnoteRef`, then a run with the note text. New id = max
  existing numeric id + 1 (ids 0 and -1 are reserved separators).
- `document.xml` (body) — a `w:r` with `rStyle=FootnoteReference` + `w:footnoteReference`(id),
  wrapped in `w:ins` so the footnote marker itself is a tracked insertion.

## Packing

- **Unzip** with Python `zipfile.extractall`, never the shell `unzip` — on paths with `§` or
  diacritics `unzip` can partially fail and leave a STALE `document.xml`, so you end up editing
  the wrong tree. (`docx_track.Docx.unpack` does this correctly.)
- **Rezip** by writing every file from the unpacked dir back into a new ZIP with forward-slash
  archive names. Working dirs can lock on Windows ("Device busy") — repack to a fresh path.

## Validation (always)

After any edit run `validate_docx.py`: `pandoc f.docx -t plain` (opens), `--track-changes=accept`
(your edits show), `--track-changes=reject` (original returns). The redlining/XSD validators in
`_docxtools/office/validate.py` (project-local, if present) compare against the ORIGINAL docx and
confirm "accept all" is clean — use them for a stronger guarantee on heavily-edited files.
