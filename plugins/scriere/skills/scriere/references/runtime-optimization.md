# Runtime optimization: frictionless docx reading & validation

Goal, same as `zotero-citations`: **one permission accept at setup, zero prompts afterward** for
everything that is *running software* — unpacking, reading comment ranges, validating with
pandoc. Every *content* decision still belongs to a human, but for `scriere` that decision is
already externalized to the author's own accept/reject in Word — nothing Claude does here needs
a separate content gate beyond that.

## The rulare / conținut split for scriere

| Layer | Examples | Who decides |
|---|---|---|
| **Rulare** (running) | `Docx.unpack` (Python zipfile), reading a comment's range text, `pandoc` validation, `repack` to a **new** path | Claude, autonomously, after a one-time allowlist accept |
| **Conținut** (content) | which edits to propose as tracked changes, wording of a fix, whether something is in scope | Claude proposes; the actual content decision is the author's own accept/reject **inside Word** — that's the whole point of the tracked-changes round-trip (SKILL.md principle A/B) |

Because the human's accept/reject already gates content, the only things worth a permission
prompt on Claude's side are actions that are hard to reverse *before* the file ever reaches Word —
overwriting the original path, or deleting anything. Everything else is pure read/validate work.

## One-time allowlist (user-level `~/.claude/settings.json`)

```json
"permissions": {
  "allow": [
    "Bash(python *)",
    "Bash(pandoc *)",
    "Bash(pip install lxml)"
  ]
}
```

These three are already in place machine-wide (confirmed in `~/.claude/settings.json`), shared
with `zotero-citations` — this table exists so a fresh machine or project can reproduce the same
frictionless loop without re-discovering it, not because anything new needs adding here.

## Canonical command shapes (keep to these, or the prefix rules won't match)

| Action | Command |
|---|---|
| Unpack | `Docx.unpack("Manuscript.docx", "_work", date="...")` — Python `zipfile`, **never** shell `unzip` (leaves a stale `document.xml` on paths with `§`/diacritics — a silent, costly trap; see SKILL.md §"Unpack reliably") |
| Validate | `python scripts/validate_docx.py Manuscript_track.docx --grep "..."` — runs pandoc three ways (plain / `--track-changes=accept` / `--track-changes=reject`) |
| Repack | `d.repack("Manuscript_track.docx")` — always a **new** filename, never overwrite the original in place (Windows also locks working dirs, so a fresh path is required anyway) |

## Deliberately NOT batched — still prompts

- Repacking **over** the original file path (accidental-overwrite risk; the workflow already
  writes to a new path by convention, so this shouldn't come up in normal use)
- Deleting anything (`_work` directories, backups, the original .docx)
- `git commit` / `git push` of the manuscript or its edits

## Accept monitor — shared with zotero-citations, not a separate setup

The permission-prompt monitor (`~/.claude/skills/zotero-citations/scripts/log_perm.py`, hooked on
`PermissionRequest`/`PermissionDenied`) logs every prompt machine-wide regardless of which skill
triggered it — there is nothing scriere-specific to wire up. The cluster-and-propose ritual is
documented once, in `zotero-citations` `references/runtime-optimization.md` §"Accept monitor",
and applies here unchanged.
