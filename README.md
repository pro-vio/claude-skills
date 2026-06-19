# claude-skills

A Claude Code plugin marketplace. Add it once, then install the plugins you want.

## Install

```
/plugin marketplace add pro-vio/claude-skills
/plugin install zotero-citations@claude-skills
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

## Layout

```
.claude-plugin/marketplace.json     catalog (lists the plugins)
plugins/<name>/.claude-plugin/plugin.json
plugins/<name>/skills/<name>/SKILL.md + scripts/ + references/
```

More plugins (e.g. a Word track-changes `scriere` skill) may be added as separate entries.
