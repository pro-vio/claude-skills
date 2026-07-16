# claude-skills

A Claude Code plugin marketplace. Add it once, then install the plugins you want.

## Install

```
/plugin marketplace add pro-vio/claude-skills
/plugin install zotero-citations@claude-skills
/plugin install scriere@claude-skills
/reload-plugins
```

You get updates when this repo is updated (auto at startup if enabled, or
`/plugin marketplace update claude-skills`).

## Plugins

### zotero-citations
Keep a manuscript's citations live and never stale, with **Zotero as the single source of
truth**:
- in-text author–date citations + an auto-generated **References** list via
  `pandoc --citeproc` with any swappable CSL style;
- a separate, chronological **Legislation & case law** list in a custom house format CSL
  cannot express;
- fixes for Zotero items that render wrong (ALL-CAPS titles, swapped place/publisher,
  reprint dates, ugly citekeys) via direct DB edits.

Requires Zotero running (local API), Better BibTeX, and pandoc on PATH. See the plugin's
`SKILL.md` for the full workflow.

### scriere
Edit a Word (`.docx`) manuscript as **tracked changes** (author "Claude") via a reliable lxml
round-trip — the author opens the file in Word and accepts/rejects each suggestion instead of
receiving a silent rewrite:
- tracked insert/delete/replace, heading promotion, footnotes;
- threaded replies to existing reviewer comments;
- a voice-preserving proofreading ("Grammarly") pass that fixes only clear errors;
- mandatory pandoc validation (accept / reject / plain) before handing the file back.

Requires pandoc on PATH and `lxml`. Pairs with **zotero-citations** for the bibliography. See
the plugin's `SKILL.md` for the full workflow.

## One-time permission gate

Both plugins bundle a `SessionStart` hook that, the **first time** you open a project, asks
once whether that project holds **sensitive data** and explains the consequence:
- **not sensitive** → frictionless `allow` rules are written to that project's
  `.claude/settings.local.json` so the skills' commands (python / pandoc / local Zotero API)
  run without per-command prompts;
- **sensitive** → permissions stay at default, so every command still prompts and you keep
  control.

The decision is recorded in `.claude/.perm-decision`, so you are asked **once per project** and
never again. Nothing broad is granted globally.

## Layout

```
.claude-plugin/marketplace.json     catalog (lists the plugins)
plugins/<name>/.claude-plugin/plugin.json
plugins/<name>/skills/<name>/SKILL.md + scripts/ + references/
plugins/<name>/hooks/hooks.json     the one-time permission gate
plugins/<name>/scripts/perm_gate.sh
```
