# -*- coding: utf-8 -*-
"""For each import<->original duplicate pair, what does each side carry?
Decides which side should be the merge master."""
import sqlite3, sys, os, json
from collections import Counter
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\Viorel Proteasa\.claude\skills\zotero-citations\scripts")
import zot

DB = os.path.join(zot.ZDIR, "zotero.sqlite")
c = sqlite3.connect(f"file:{DB}?mode=ro&immutable=1", uri=True).cursor()
plan = json.load(open("extract/dedup_plan.json", encoding="utf-8"))
pairs = plan["dupes"]          # [importID, originalID, how]

def shape(iid):
    pdfs = [r[0] for r in c.execute("SELECT itemID FROM itemAttachments WHERE parentItemID=? AND contentType='application/pdf'", (iid,)).fetchall()]
    ann = 0
    if pdfs:
        q = ",".join("?" * len(pdfs))
        ann = c.execute(f"SELECT COUNT(*) FROM itemAnnotations WHERE parentItemID IN ({q})", pdfs).fetchone()[0]
    cols = [r[0] for r in c.execute("SELECT collectionID FROM collectionItems WHERE itemID=?", (iid,)).fetchall()]
    notes = c.execute("SELECT COUNT(*) FROM itemNotes WHERE parentItemID=?", (iid,)).fetchone()[0]
    tags = c.execute("SELECT COUNT(*) FROM itemTags WHERE itemID=?", (iid,)).fetchone()[0]
    return {"pdf": len(pdfs), "ann": ann, "cols": cols, "notes": notes, "tags": tags}

stats = Counter()
both_pdf = 0
detail = []
for imp, orig, how in pairs:
    si, so = shape(imp), shape(orig)
    if si["pdf"] and so["pdf"]: both_pdf += 1
    stats[f"import pdf={min(si['pdf'],2)} / orig pdf={min(so['pdf'],2)}"] += 1
    stats["import are adnotari" if si["ann"] else "import fara adnotari"] += 1
    stats["orig are adnotari" if so["ann"] else "orig fara adnotari"] += 1
    stats["orig e in colectii" if so["cols"] else "orig fara colectii"] += 1
    detail.append((imp, orig, how, si, so))

print(f"perechi: {len(pairs)}")
print(f"\nambele au PDF: {both_pdf}")
print("\ndistributie:")
for k, v in stats.most_common():
    print(f"  {v:4}  {k}")

tot_imp_ann = sum(d[3]["ann"] for d in detail)
tot_orig_ann = sum(d[4]["ann"] for d in detail)
print(f"\nadnotari pe copiile din IMPORT: {tot_imp_ann}")
print(f"adnotari pe itemele TALE vechi: {tot_orig_ann}")
orig_in_cols = sum(1 for d in detail if d[4]["cols"])
print(f"iteme vechi aflate in colectiile tale: {orig_in_cols}")

print("\n--- 5 exemple ---")
for imp, orig, how, si, so in detail[:5]:
    t = c.execute("""SELECT v.value FROM itemData d JOIN itemDataValues v ON v.valueID=d.valueID
        JOIN fields f ON f.fieldID=d.fieldID WHERE d.itemID=? AND f.fieldName IN ('title','nameOfAct') LIMIT 1""", (orig,)).fetchone()
    print(f"  [{how}] {(t[0] if t else '?')[:60]}")
    print(f"     import({imp}): pdf={si['pdf']} ann={si['ann']} cols={len(si['cols'])} note={si['notes']} tag={si['tags']}")
    print(f"     al tau({orig}): pdf={so['pdf']} ann={so['ann']} cols={len(so['cols'])} note={so['notes']} tag={so['tags']}")
