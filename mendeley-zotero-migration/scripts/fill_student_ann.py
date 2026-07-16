# -*- coding: utf-8 -*-
"""Add the Mendeley annotations that Zotero's importer did not bring — chiefly the
students' ones (536) — onto the SAME attachment that already holds the user's own,
so every annotation for a PDF sits together. Attribution goes in authorName.

Colour convention follows Zotero's importer: the literal Mendeley RGB (e.g. #faf4d1),
not the Zotero palette. Dedup by (type, pageIndex, rounded rect) against what's there.
Dry-run by default.
"""
import sqlite3, sys, os, json, re
from collections import defaultdict
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\Viorel Proteasa\.claude\skills\zotero-citations\scripts")
import zot, annconv, fitz

DB = os.path.join(zot.ZDIR, "zotero.sqlite")
ZSTOR = os.path.join(zot.ZDIR, "storage")
amap = json.load(open("extract/ann_by_filehash.json", encoding="utf-8"))
h2att = json.load(open("extract/zotero_sha1_to_attach.json", encoding="utf-8"))
# Mendeley's `filehash` is the CLOUD copy's sha1; for 36 files the local copy (and the
# one Zotero imported) hashes differently, so those annotations looked unplaceable.
# hash_remap maps the recorded filehash -> the sha1 the file actually has.
try:
    remap = json.load(open("extract/hash_remap.json", encoding="utf-8"))
except FileNotFoundError:
    remap = {}
for old, new in remap.items():
    if old not in h2att and new in h2att:
        h2att[old] = h2att[new]

def mendeley_hex(a):
    """Literal Mendeley colour -> hex, exactly like Zotero's importer does."""
    ss = (a.get("stylesheet") or {}).get("value") or ""
    m = re.search(r"rgb\((\d+),(\d+),(\d+)\)", ss)
    if m:
        return "#%02x%02x%02x" % tuple(int(g) for g in m.groups())
    return annconv.COLOR.get((a.get("_custom") or {}).get("color"), "#ffd400")

def sig(typ, pos_json):
    """Order-independent signature. Multi-line highlights carry one rect per line and
    Zotero's importer orders them differently than Mendeley's positions array, so
    keying on rects[0] gives false 'missing'. The bounding box over ALL rects is
    stable under reordering."""
    p = json.loads(pos_json) if isinstance(pos_json, str) else pos_json
    rs = p.get("rects") or [[0, 0, 0, 0]]
    x0 = min(r[0] for r in rs); y0 = min(r[1] for r in rs)
    x1 = max(r[2] for r in rs); y1 = max(r[3] for r in rs)
    return (typ, p.get("pageIndex"), len(rs), round(x0), round(y0), round(x1), round(y1))

con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
c = con.cursor()

plan = []      # (attachID, converted-dict, authorName)
skipped_dup = 0
no_pdf = 0
for h, lst in amap.items():
    atts = h2att.get(h)
    if not atts:
        continue
    # target = attachment already holding the most annotations (keeps them together)
    counts = {}
    for a in atts:
        counts[a] = c.execute("SELECT COUNT(*) FROM itemAnnotations WHERE parentItemID=?", (a,)).fetchone()[0]
    target = sorted(atts, key=lambda a: (-counts[a], a))[0]
    existing = set()
    for typ, pos in c.execute("SELECT type,position FROM itemAnnotations WHERE parentItemID=?", (target,)).fetchall():
        try:
            existing.add(sig(typ, pos))
        except Exception:
            pass
    row = c.execute("SELECT i.key, ia.path FROM itemAttachments ia JOIN items i ON i.itemID=ia.itemID WHERE ia.itemID=?", (target,)).fetchone()
    fp = os.path.join(ZSTOR, row[0], row[1][len("storage:"):])
    if not os.path.exists(fp):
        no_pdf += 1
        continue
    doc = fitz.open(fp)
    seen = set()
    for x in lst:
        r = annconv.convert(x["ann"], doc)
        if not r:
            continue
        s = sig(r["type"], r["position"])
        if s in existing or s in seen:
            skipped_dup += 1
            continue
        seen.add(s)
        r["color"] = mendeley_hex(x["ann"])
        plan.append((target, r, x["author"]))
    doc.close()
con.close()

byauthor = defaultdict(int)
for _, _, au in plan:
    byauthor[au or "(eu)"] += 1
print(f"PDF-uri fara fisier pe disc: {no_pdf}")
print(f"adnotari deja prezente (sarite): {skipped_dup}")
print(f"\nDE INSERAT: {len(plan)} adnotari pe {len(set(a for a,_,_ in plan))} atasamente")
for au, n in sorted(byauthor.items(), key=lambda kv: -kv[1]):
    print(f"  {n:4}  {au}")

if "--apply" not in sys.argv:
    print("\n[DRY RUN] --apply pentru a scrie.")
    sys.exit(0)

with zot.write_session("fill-student-annotations") as w:
    tid = zot.item_type_id(w, "annotation")
    for att, r, author in plan:
        iid = zot._next_id(w, "itemID", "items")
        t = zot.now()
        w.execute("INSERT INTO items (itemID,itemTypeID,dateAdded,dateModified,clientDateModified,libraryID,key,version,synced) "
                  "VALUES (?,?,?,?,?,?,?,0,0)", (iid, tid, t, t, t, zot.LIBRARY_ID, zot.newkey()))
        w.execute("INSERT INTO itemAnnotations (itemID,parentItemID,type,authorName,text,comment,color,pageLabel,sortIndex,position,isExternal) "
                  "VALUES (?,?,?,?,?,?,?,?,?,?,0)",
                  (iid, att, r["type"], author, r["text"], r["comment"], r["color"], r["pageLabel"], r["sortIndex"], r["position"]))
    print(f"Inserate {len(plan)} adnotari.")
