# -*- coding: utf-8 -*-
"""Hash every PDF now in Zotero, match against the Mendeley annotation map (by SHA1),
and report what is placeable / missing / needs author attribution."""
import sqlite3, sys, json, os, hashlib
from collections import defaultdict
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\Viorel Proteasa\.claude\skills\zotero-citations\scripts")
import zot

DB = r"C:\Users\Viorel Proteasa\Zotero\zotero.sqlite"
c = sqlite3.connect(f"file:{DB}?mode=ro&immutable=1", uri=True).cursor()
ZSTOR = os.path.join(zot.ZDIR, "storage")

amap = json.load(open("extract/ann_by_filehash.json", encoding="utf-8"))
print("Mendeley filehash-uri cu adnotari:", len(amap))

def sha1(fp):
    h = hashlib.sha1()
    with open(fp, "rb") as f:
        for ch in iter(lambda: f.read(1048576), b""):
            h.update(ch)
    return h.hexdigest()

rows = c.execute("SELECT ia.itemID, i.key, ia.path FROM itemAttachments ia "
                 "JOIN items i ON i.itemID=ia.itemID "
                 "WHERE ia.contentType='application/pdf' AND ia.path LIKE 'storage:%'").fetchall()
print("atasamente PDF de hash-uit:", len(rows))

h2att = defaultdict(list)
done = 0
for iid, key, path in rows:
    fp = os.path.join(ZSTOR, key, path[len("storage:"):])
    if not os.path.exists(fp):
        continue
    try:
        h2att[sha1(fp)].append(iid)
        done += 1
    except Exception:
        pass
print("hash-uite:", done, "| sha1 distincte:", len(h2att))
json.dump({h: v for h, v in h2att.items()}, open("extract/zotero_sha1_to_attach.json", "w"))

hit = [h for h in amap if h in h2att]
tot = sum(len(amap[h]) for h in hit)
mine = sum(1 for h in hit for x in amap[h] if x["author"] is None)
theirs = sum(1 for h in hit for x in amap[h] if x["author"])
print("\n=== ACOPERIRE ===")
print(f"filehash adnotate gasite in Zotero: {len(hit)} / {len(amap)}")
print(f"adnotari plasabile: {tot}  (ale mele {mine}, ale studentilor {theirs})")
missing = [h for h in amap if h not in h2att]
print(f"filehash lipsa (PDF neimportat): {len(missing)} -> {sum(len(amap[h]) for h in missing)} adnotari")
# how many Zotero attachments share the same content (dupes needing consolidation)
multi = {h: v for h, v in h2att.items() if len(v) > 1}
print(f"\nsha1 cu MAI MULTE atasamente in Zotero (acelasi PDF de 2+ ori): {len(multi)}")
print(f"  atasamente implicate: {sum(len(v) for v in multi.values())}")
annmulti = sum(len(amap[h]) for h in multi if h in amap)
print(f"  dintre ele, adnotate in Mendeley: {sum(1 for h in multi if h in amap)} sha1 -> {annmulti} adnotari")
