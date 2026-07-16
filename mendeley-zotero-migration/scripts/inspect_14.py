# -*- coding: utf-8 -*-
"""Re-derive the 14 author-incompatible groups the merge skipped, and dump enough
detail to judge each: are they the same work (editor-vs-chapter-author metadata) or
genuinely different works that share a title/junk DOI?"""
import sqlite3, sys, os, json, re
from collections import defaultdict
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\Viorel Proteasa\.claude\skills\zotero-citations\scripts")
import zot

DB = os.path.join(zot.ZDIR, "zotero.sqlite")
c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True).cursor()
NT = "i.itemID NOT IN (SELECT itemID FROM deletedItems)"

rows = c.execute(f"""SELECT i.itemID FROM items i JOIN itemTypes it ON it.itemTypeID=i.itemTypeID
                     WHERE it.typeName NOT IN ('attachment','note','annotation') AND {NT}""").fetchall()
items = {r[0]: {} for r in rows}
for iid, fn, val in c.execute("""SELECT d.itemID, f.fieldName, v.value FROM itemData d
        JOIN itemDataValues v ON v.valueID=d.valueID JOIN fields f ON f.fieldID=d.fieldID""").fetchall():
    if iid in items:
        items[iid][fn] = val

author1 = {}
for iid, last in c.execute("""SELECT ic.itemID, cr.lastName FROM itemCreators ic
        JOIN creators cr ON cr.creatorID=ic.creatorID WHERE ic.orderIndex=0""").fetchall():
    author1[iid] = re.sub(r"[^a-z]", "", (last or "").lower()) or None

def ndoi(s):
    if not s: return None
    m = re.search(r"10\.\d{4,9}/\S+", str(s), re.I)
    return m.group(0).rstrip(".").lower() if m else None
def ntitle(s):
    if not s: return None
    s = re.sub(r"<[^>]+>", " ", str(s))
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip() or None
def yr(s):
    m = re.search(r"\d{4}", str(s or "")); return m.group(0) if m else None

groups = defaultdict(list)
for iid, f in items.items():
    t = f.get("title") or f.get("nameOfAct") or f.get("caseName")
    tt = ntitle(t)
    if not tt: continue
    doi = ndoi(f.get("DOI")) or ndoi(f.get("extra"))
    a1 = author1.get(iid)
    key = ("doi", doi, tt) if doi else (("ty", tt, yr(f.get("date")), a1) if a1 else ("ty0", tt, yr(f.get("date"))))
    groups[key].append(iid)

def compatible(ids):
    known = [author1.get(i) for i in ids if author1.get(i)]
    for i in range(len(known)):
        for j in range(i + 1, len(known)):
            a, b = known[i], known[j]
            if a != b and a not in b and b not in a:
                return False
    return True

review = {k: v for k, v in groups.items() if len(v) > 1 and not compatible(v)}
print(f"grupuri de verificat: {len(review)}\n")

def creators(iid):
    return c.execute("""SELECT ct.creatorType, cr.lastName, cr.firstName FROM itemCreators ic
        JOIN creators cr ON cr.creatorID=ic.creatorID JOIN creatorTypes ct ON ct.creatorTypeID=ic.creatorTypeID
        WHERE ic.itemID=? ORDER BY ic.orderIndex""", (iid,)).fetchall()
def ty(iid):
    return c.execute("SELECT it.typeName FROM items i JOIN itemTypes it ON it.itemTypeID=i.itemTypeID WHERE i.itemID=?", (iid,)).fetchone()[0]
def pdfann(iid):
    p = [r[0] for r in c.execute("SELECT itemID FROM itemAttachments WHERE parentItemID=? AND contentType='application/pdf'", (iid,)).fetchall()]
    a = 0
    if p:
        q = ",".join("?" * len(p))
        a = c.execute(f"SELECT COUNT(*) FROM itemAnnotations WHERE parentItemID IN ({q})", p).fetchone()[0]
    return len(p), a

for n, (k, ids) in enumerate(sorted(review.items(), key=lambda kv: str(kv[0])), 1):
    print("=" * 92)
    print(f"[{n}] cheie: {k[0]} {str(k[1])[:70]}")
    for iid in ids:
        f = items[iid]
        np, na = pdfann(iid)
        cr = creators(iid)
        cs = "; ".join(f"{t[:3]}:{l}{', ' + fn if fn else ''}" for t, l, fn in cr[:4])
        print(f"  --- item {iid} [{ty(iid)}] pdf={np} ann={na}")
        print(f"      titlu : {str(f.get('title') or f.get('nameOfAct') or '')[:80]}")
        print(f"      autori: {cs[:100]}")
        print(f"      an={f.get('date','-')[:10]} | container: {str(f.get('publicationTitle') or f.get('bookTitle') or f.get('proceedingsTitle') or '-')[:50]}")
        print(f"      pag={f.get('pages','-')} | DOI={str(f.get('DOI') or '-')[:45]} | publisher={str(f.get('publisher') or '-')[:30]}")
    print()
