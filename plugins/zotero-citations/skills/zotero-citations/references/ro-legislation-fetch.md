# Fetching Romanian legislation text (source recipe)

Downloading the text of a Romanian statute is a solved lookup, not an exploration — but the
obvious portals fail in non-obvious ways. Try sources in this order; stop at the first that yields
extractable text. (Derived from a live run that burned ~30 min on trial-and-error across all four.)

| Source | URL shape | Verdict |
|---|---|---|
| **cdep.ro** (Chamber of Deputies legislative DB) | `http://www.cdep.ro/pls/legis/legis_pck.htp_act_text?idt=<ID>` | **BEST.** Returns the full act as plain HTML — convert to text/markdown with pandoc. Old acts included (e.g. Legea 57/1968). Needs the internal `idt` (see below). |
| **legislatie.just.ro** (official consolidated portal) | `https://legislatie.just.ro/Public/DetaliiDocument/<ID>` (or `DetaliiDocumentAfis`) | **Consolidated text, but hard to scrape.** The body is rendered client-side and the headers/article numbering do **not** extract cleanly from raw HTML (recurring caveat). Use only via a real browser (claude-in-chrome) or OCR the printed PDF; do not rely on `curl`. |
| **monitoruljuridic.ro** | — | **Paywall.** Skip. |
| **lege5.ro** | — | **Paywall / registration wall.** Skip. |

## Finding the cdep `idt`

The `idt` is cdep's internal act id, not the law number. Resolve it first:
- Search cdep's legislative DB (`http://www.cdep.ro/pls/legis/legis_pck.frame`) or a plain web
  search `site:cdep.ro <lege nr>/<an>`, then read the `idt=` off the result URL.
- Sanity-check you got the right act/version (republished vs. original) before ingesting — cdep
  carries multiple forms of the same law.

## Then ingest it

Convert and file in one step — no separate hand-rolled SQL:

```bash
# 1. fetch + convert to markdown/text (cdep HTML → readable)
curl -s -A "Mozilla/5.0" "http://www.cdep.ro/pls/legis/legis_pck.htp_act_text?idt=27845" \
  | pandoc -f html -t markdown -o "legislatie/Legea_57_1968.md"
# (or -t pdf via wkhtmltopdf/weasyprint if you want a stored PDF to attach)
```

Then create the `statute` item + attach the file, inside one `write_session` (see
`zotero-schema.md` → "Add a statute"). Set `shortTitle`, `nameOfAct`, `codeNumber` (`57/1968`),
`dateEnacted` (`YYYY-00-00 YYYY`), and `history` (Monitorul Oficial reference) so the
`build_legislation_list.py` house format renders correctly.

**Content stays the user's call** (the rulare/conținut split): if you can't confirm you fetched the
exact version cited, surface that — don't ingest a best-guess act.
