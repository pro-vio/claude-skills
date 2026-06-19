#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_manuscris.py — render a manuscript with LIVE citations from Zotero.

Pipeline:
  manuscript .md with [@citekey]
    -> pull CSL-JSON for ONLY the cited keys from Zotero
       (local web API, /items?format=csljson — id == the Better BibTeX citekey,
        also reads pinned "Citation Key:" / "Original Date:" from the Extra field)
    -> pandoc --citeproc --csl <style>
    -> HTML (or any pandoc output). The "References" list is generated automatically,
       so it contains exactly what is cited — never stale, never extra.

Source of truth = Zotero (must be OPEN; API on port 23119). NOT a hand-made bib file.
Update workflow: change something in Zotero -> re-run this script. That's it.

Why the bulk csljson endpoint (not Better BibTeX item.export / item.search):
  - item.export is all-or-nothing and serves a STALE cache after direct DB writes.
  - item.search is flaky on multi-word terms.
  The standard API reads the live DB and returns id == citekey, so a dict lookup resolves keys.

Usage:
  python build_manuscris.py <manuscript.md> [--csl <style>] [--out <file>]
                            [--user-id N] [--to <pandoc-format>]
  --csl     style name from ~/Zotero/styles (apa, ieee, ...) or a .csl path.
            Default = the chicago-author-date.csl bundled with this skill.
  --out     output path. Default = <md_dir>/<md_stem>.html
  --to      pandoc output format (html, docx, ...). Inferred from --out extension.
  --user-id Zotero library user id for the API URL. Default = env ZOTERO_USER_ID
            or auto-detect from zotero.sqlite (see zot.detect_user_id).
"""
import re, sys, os, json, subprocess, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import zot  # sibling helper

# Windows consoles default to cp1252; our status prints carry diacritics/emoji and would
# crash AFTER the output file is already written. Force UTF-8 stdout so runs don't appear to fail.
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

SKILL = os.path.dirname(HERE)
BUNDLED_CSL = os.path.join(SKILL, "references", "chicago-author-date.csl")
ZOTERO_STYLES = os.path.expanduser("~/Zotero/styles")

# pandoc citation keys: @key / [@key, loc] / [-@key] / [@k1; @k2]; keys may be unicode
CITE_RE = re.compile(r'(?<![\w@])-?@([^\s\]\[;,.]+)')

def parse_args(argv):
    a = {"md": None, "csl": None, "out": None, "user_id": None, "to": None}
    i = 0
    while i < len(argv):
        t = argv[i]
        if t == "--csl": a["csl"] = argv[i+1]; i += 2
        elif t == "--out": a["out"] = argv[i+1]; i += 2
        elif t == "--user-id": a["user_id"] = argv[i+1]; i += 2
        elif t == "--to": a["to"] = argv[i+1]; i += 2
        elif a["md"] is None: a["md"] = t; i += 1
        else: i += 1
    if not a["md"]:
        sys.exit("Utilizare: build_manuscris.py <manuscript.md> [--csl ..] [--out ..] [--user-id N]")
    return a

def resolve_csl(arg):
    if not arg: return BUNDLED_CSL
    if os.path.isfile(arg): return arg
    name = arg if arg.endswith(".csl") else arg + ".csl"
    for base in (ZOTERO_STYLES, os.path.join(SKILL, "references")):
        p = os.path.join(base, name)
        if os.path.isfile(p): return p
    sys.exit(f"CSL negăsit: {arg!r} (nici cale, nici în ~/Zotero/styles, nici bundled).")

def extract_keys(text):
    # ignore hand-made bibliography sections so we don't harvest junk keys
    body = text.split("\n# References")[0].split("\n# Legislation")[0]
    keys = []
    for m in CITE_RE.finditer(body):
        k = m.group(1).rstrip(".")
        if k and k not in keys: keys.append(k)
    return keys

def main():
    a = parse_args(sys.argv[1:])
    md = a["md"]
    md_dir = os.path.dirname(os.path.abspath(md))
    stem = os.path.splitext(os.path.basename(md))[0]
    out = a["out"] or os.path.join(md_dir, stem + ".html")
    to = a["to"] or os.path.splitext(out)[1].lstrip(".") or "html"
    csl = resolve_csl(a["csl"])
    refs = os.path.join(md_dir, f".{stem}.refs.json")

    uid = a["user_id"] or zot.detect_user_id()
    if not uid:
        sys.exit("user id Zotero nedetectat. Dă --user-id N sau setează ZOTERO_USER_ID.")
    api = f"http://127.0.0.1:23119/api/users/{uid}/items"

    text = open(md, encoding="utf-8").read()
    keys = extract_keys(text)
    print(f"[1] {len(keys)} chei citate în corp.")

    print("[2] trag CSL-JSON din Zotero (API standard, format=csljson)...")
    try:
        url = api + "?format=csljson&limit=2000&itemType=-attachment"
        allrefs = json.loads(urllib.request.urlopen(url, timeout=30).read().decode())
    except Exception as e:
        sys.exit(f"Nu pot citi din Zotero (deschis? port 23119?). Eroare: {e}")
    by = {r.get("id"): r for r in allrefs if r.get("id")}
    refs_used = [by[k] for k in keys if k in by]
    got = {r["id"] for r in refs_used}
    missing = [k for k in keys if k not in got]
    json.dump(refs_used, open(refs, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"    {len(got)}/{len(keys)} rezolvate.")
    if missing:
        print("    ⚠️  CHEI NEGĂSITE ÎN ZOTERO:")
        for k in missing: print(f"        @{k}")

    print(f"[3] pandoc --citeproc (stil: {os.path.basename(csl)}, -> {to}) ...")
    cmd = ["pandoc", md, "-o", out, "--standalone", "--citeproc",
           "--csl", csl, "--bibliography", refs,
           f"--resource-path={md_dir}{os.pathsep}{md_dir}/_media",
           "--metadata", "lang=en"]
    if to == "html": cmd += ["--embed-resources", "--mathjax"]
    env = dict(os.environ, PYTHONUTF8="1")
    r = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if r.returncode != 0:
        print("    pandoc STDERR:", r.stderr[:1000]); sys.exit(1)
    print(f"    OK -> {out}")
    print("\n✅ Toate citările rezolvate." if not missing else "\n⚠️  Render făcut, dar lipsesc citări (vezi mai sus).")

if __name__ == "__main__":
    main()
