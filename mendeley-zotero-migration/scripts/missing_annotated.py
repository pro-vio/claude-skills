# -*- coding: utf-8 -*-
"""'PDF missing + annotated' has two readings — check both:
  A. attachments in Zotero whose file is gone from disk, that carry annotations;
  B. PDFs annotated in Mendeley that never made it into Zotero at all."""
import sqlite3, sys, os, json
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\Viorel Proteasa\.claude\skills\zotero-citations\scripts")
import zot

DB = os.path.join(zot.ZDIR, "zotero.sqlite")
ZSTOR = os.path.join(zot.ZDIR, "storage")
c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True).cursor()

print("=" * 74)
print("A. IN ZOTERO: atasamente cu FISIERUL lipsa de pe disc, care au adnotari")
rows = c.execute("""SELECT ia.itemID, i.key, ia.path, ia.parentItemID FROM itemAttachments ia
                    JOIN items i ON i.itemID=ia.itemID WHERE ia.path LIKE 'storage:%'""").fetchall()
bad = 0
for aid, key, path, parent in rows:
    fp = os.path.join(ZSTOR, key, path[len("storage:"):])
    if os.path.exists(fp):
        continue
    n = c.execute("SELECT COUNT(*) FROM itemAnnotations WHERE parentItemID=?", (aid,)).fetchone()[0]
    if n:
        bad += 1
        print(f"  atasament {aid} (item {parent}): {n} adnotari — {path}")
print(f"  -> {bad} (toate fisierele sunt pe disc)" if bad == 0 else f"  -> {bad}")

print("\n" + "=" * 74)
print("B. DIN MENDELEY: PDF-uri adnotate care NU au ajuns in Zotero")
amap = json.load(open("extract/ann_by_filehash.json", encoding="utf-8"))
h2att = json.load(open("extract/zotero_sha1_to_attach.json", encoding="utf-8"))
remap = json.load(open("extract/hash_remap.json", encoding="utf-8"))
data = json.load(open("extract/mendeley_local.json", encoding="utf-8"))
docs = data["documents"]; files = data["files"]
h_info = {}
for did, fl in files.items():
    for f in fl:
        if f.get("filehash"):
            h_info[f["filehash"]] = (did, f.get("file_name"), f.get("size"))
absent = [h for h in amap if h not in h2att and h not in remap]
rows = []
for h in absent:
    did, fname, size = h_info.get(h, (None, None, None))
    d = docs.get(did) or {}
    au = d.get("authors") or []
    names = ", ".join((a.get("last_name") or "") for a in au[:2] if isinstance(a, dict)) or "-"
    mine = sum(1 for x in amap[h] if x["author"] is None)
    who = sorted({x["author"] for x in amap[h] if x["author"]})
    ident = d.get("identifiers") or {}
    rows.append((len(amap[h]), names, d.get("year"), d.get("title") or fname, mine, who,
                 ident.get("doi"), d.get("type"), round((size or 0) / 1e6, 1)))
rows.sort(key=lambda r: -r[0])
print(f"  {len(absent)} PDF-uri | {sum(r[0] for r in rows)} adnotari blocate\n")
for n, names, yr, t, mine, who, doi, ty, mb in rows:
    print(f"  {n:3} adnotari — {mine} ale tale" + (f", {', '.join(who)}" if who else ""))
    print(f"      {names} ({yr}) — {str(t)[:74]}")
    print(f"      tip={ty} | {mb} MB | DOI: {doi or '-'}")
    print()
