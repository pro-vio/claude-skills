#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_legislation_list.py — generate a chronological "Legislation and case law" list.

Companion to build_manuscris.py. A CSL style covers the ACADEMIC apparatus only; statutes,
secondary legislation and case law follow a custom house format (see SKILL.md §G), so they
get their own list, separate from the academic "References".

Pipeline:
  Zotero collection (statutes/cases) via the local web API (format=json)
    -> FILTER to what is actually CITED in the manuscript body
    -> FORMAT (house style):
         laws:   {shortTitle}. {nameOfAct}, {history}.        (history = official gazette ref)
         HCL/secondary (nameOfAct starts "Hotărârea Consiliului Local"):  {nameOfAct}.
         cases:  {nameOfAct}[, {history}].
    -> SORT chronologically, DETERMINISTICALLY
       (year -> fine date from gazette / decision date -> type -> issuer -> act number)
    -> REPLACE the "# Legislation and case law" section in the manuscript.

Filtering rule: an item counts as cited if its codeNumber (e.g. "227/2015") appears in the
body, OR (for laws) its short title appears. Short titles whose base repeats across the
collection (e.g. two "Fiscal Code"s) require the year-qualified form so they stay distinct.

Usage:
  python build_legislation_list.py --manuscript <md> --collection <ZOTERO_COLLECTION_KEY>
        [--user-id N] [--source zotero|local --local-json <file>] [--write] [--header "..."]
  (default = DRY-RUN: prints the proposed section. --write replaces it, with a .bak backup.)
"""
import re, sys, os, json, shutil, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import zot

# Force UTF-8 stdout: Windows cp1252 consoles crash on diacritics/emoji in status prints
# (after the work is done), making a successful run look failed.
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

DEF_HEADER = "# Legislation and case law"
NOTE = ("*Statutes, case law, and international instruments, in chronological order. "
        "In-text references use the short title.*")
RO_MONTHS = {"ianuarie":1,"februarie":2,"martie":3,"aprilie":4,"mai":5,"iunie":6,
             "iulie":7,"august":8,"septembrie":9,"octombrie":10,"noiembrie":11,"decembrie":12}

def parse_args(argv):
    a = {"md": None, "coll": None, "uid": None, "source": "zotero",
         "local": None, "write": False, "header": DEF_HEADER}
    i = 0
    while i < len(argv):
        t = argv[i]
        if t == "--manuscript": a["md"] = argv[i+1]; i += 2
        elif t == "--collection": a["coll"] = argv[i+1]; i += 2
        elif t == "--user-id": a["uid"] = argv[i+1]; i += 2
        elif t == "--source": a["source"] = argv[i+1]; i += 2
        elif t == "--local-json": a["local"] = argv[i+1]; i += 2
        elif t == "--header": a["header"] = argv[i+1]; i += 2
        elif t == "--write": a["write"] = True; i += 1
        else: i += 1
    if not a["md"]: sys.exit("Lipsește --manuscript <md>.")
    if a["source"] == "zotero" and not a["coll"]: sys.exit("Lipsește --collection <KEY> (sursa zotero).")
    if a["source"] == "local" and not a["local"]: sys.exit("Lipsește --local-json <file> (sursa local).")
    return a

def _din(s):
    if not s: return None
    m = re.search(r'din\s+(\d{1,2})\s+([a-zăâîșț]+)\s+(\d{4})', s, re.I)
    return (RO_MONTHS.get(m.group(2).lower(), 13), int(m.group(1))) if m else None

def fine_date(it):
    # cases sort by decision date (in nameOfAct); laws by gazette publication date.
    if it["type"] == "case": return _din(it["nameOfAct"]) or _din(it["mo"]) or (13, 32)
    return _din(it["mo"]) or _din(it["nameOfAct"]) or (13, 32)

def _norm(d):
    code = d.get("codeNumber") or d.get("code") or d.get("id") or ""
    name = d.get("nameOfAct") or d.get("title") or ""
    if re.match(r'\s*Hotărârea Consiliului Local', name): typ = "hcl"
    elif re.match(r'\s*(Curtea|Tribunalul|Înalta Curte|Judecătoria)', name): typ = "case"
    else: typ = "law"
    de = d.get("dateEnacted") or str(d.get("year") or "")
    ym = re.search(r'(\d{4})', de)
    return {"type": typ, "shortTitle": d.get("shortTitle",""), "nameOfAct": name,
            "mo": d.get("history") or d.get("mo"), "year": int(ym.group(1)) if ym else None,
            "code": code}

def load_zotero(uid, coll):
    url = f"http://127.0.0.1:23119/api/users/{uid}/collections/{coll}/items?format=json&limit=500"
    raw = json.loads(urllib.request.urlopen(url, timeout=30).read().decode())
    out = []
    for it in raw:
        d = it.get("data", it)
        if d.get("itemType") == "attachment": continue
        out.append(_norm(d))
    return out

def load_local(path):
    j = json.load(open(path, encoding="utf-8"))
    out = []
    if isinstance(j, dict):
        for grp in ("laws", "hcl", "cases"):
            for d in j.get(grp, []): out.append(_norm(d))
    else:
        for d in j: out.append(_norm(d))
    return out

def base_short(s): return re.sub(r'\s*\(\d{4}\)\s*$', '', s).strip()

def cited_filter(items, body):
    bases = {}
    for it in items:
        if it["type"] == "law":
            bases[base_short(it["shortTitle"])] = bases.get(base_short(it["shortTitle"]), 0) + 1
    kept, dropped = [], []
    for it in items:
        tokens = []
        if it["type"] == "law" and it["shortTitle"]:
            b = base_short(it["shortTitle"])
            tokens.append(it["shortTitle"] if bases.get(b, 0) > 1 else b)
        if it["code"]: tokens.append(it["code"])
        (kept if any(t and t in body for t in tokens) else dropped).append(it)
    return kept, dropped

def fmt(it):
    st, name, mo = it["shortTitle"], it["nameOfAct"].strip(), it["mo"]
    if it["type"] == "law": return f"{st}. {name}, {mo}." if mo else f"{st}. {name}."
    if it["type"] == "hcl": return name.rstrip(".") + "."
    return f"{name.rstrip('.')}, {mo}." if mo else name.rstrip(".") + "."

def sort_key(it):
    grp = {"law": 0, "case": 1, "hcl": 2}.get(it["type"], 3)
    name = it["nameOfAct"]
    issuer = 0 if "Oradea" in name else (1 if "Timișoara" in name else 0)
    m = re.match(r'(\d+)', it["code"] or "")
    return (it["year"] or 9999, *fine_date(it), grp, issuer, int(m.group(1)) if m else 0)

def main():
    a = parse_args(sys.argv[1:])
    if a["source"] == "zotero":
        uid = a["uid"] or zot.detect_user_id()
        if not uid: sys.exit("user id nedetectat. Dă --user-id N sau setează ZOTERO_USER_ID.")
        items = load_zotero(uid, a["coll"])
    else:
        items = load_local(a["local"])
    text = open(a["md"], encoding="utf-8").read()
    body = text.split("\n" + a["header"])[0]
    kept, dropped = cited_filter(items, body)
    entries = sorted(kept, key=sort_key)
    section = "\n".join([a["header"], "", NOTE, ""] + [l for it in entries for l in (fmt(it), "")]).rstrip() + "\n"

    print(f"[sursă: {a['source']}] {len(items)} itemi | citați: {len(kept)} | scoși (necitați): {len(dropped)}")
    for it in dropped: print(f"   - scos: {it['shortTitle'] or it['nameOfAct'][:50]} [{it['code']}]")
    print("\n" + "="*70 + "\n" + section + "="*70)

    if not a["write"]:
        print("(dry-run: nimic scris. Adaugă --write ca să înlocuiești în manuscris.)"); return
    if a["header"] not in text: sys.exit(f"ABORT: '{a['header']}' negăsit în {a['md']}")
    bak = a["md"] + ".pre_leglist.bak"; shutil.copy2(a["md"], bak)
    before = text.split("\n" + a["header"])[0].rstrip("\n")
    open(a["md"], "w", encoding="utf-8").write(before + "\n\n\n" + section)
    print(f"✅ scris. backup -> {bak}")

if __name__ == "__main__":
    main()
