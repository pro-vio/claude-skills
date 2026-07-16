# -*- coding: utf-8 -*-
"""Same PDF bytes on different items: strong duplicate evidence, but not proof — an
identical file can also mean a MISFILED attachment (we already found Denning's item
carrying Xing Xia's thesis). Classify: compatible title+author -> safe to merge;
clearly different works -> flag for the user."""
import sqlite3, sys, os, json, re
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\Viorel Proteasa\.claude\skills\zotero-citations\scripts")
import zot, fitz

DB = os.path.join(zot.ZDIR, "zotero.sqlite")
ZSTOR = os.path.join(zot.ZDIR, "storage")
c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True).cursor()
audit = json.load(open("extract/audit.json", encoding="utf-8"))

# probe item 9106's PDF beyond page 1
print("=== item 9106: PDF fara text pe pagina 1 ===")
r = c.execute("""SELECT i.key, ia.path FROM itemAttachments ia JOIN items i ON i.itemID=ia.itemID
    WHERE ia.parentItemID=9106 AND ia.contentType='application/pdf' LIMIT 1""").fetchone()
if r:
    fp = os.path.join(ZSTOR, r[0], r[1][len("storage:"):])
    d = fitz.open(fp)
    print(f"  fisier: {os.path.basename(fp)} ({d.page_count} pagini)")
    for p in range(0, min(6, d.page_count)):
        t = d[p].get_text().strip()
        if t:
            print(f"  --- primul text, pagina {p+1} ---")
            print("   " + t[:400].replace("\n", "\n   "))
            break
    else:
        print("  (niciun text in primele pagini — scan fara OCR)")
    d.close()

def title(iid):
    r = c.execute("""SELECT v.value FROM itemData d JOIN itemDataValues v ON v.valueID=d.valueID
        JOIN fields f ON f.fieldID=d.fieldID WHERE d.itemID=? AND f.fieldName IN ('title','nameOfAct','caseName') LIMIT 1""", (iid,)).fetchone()
    return r[0] if r else ""
def au(iid):
    r = c.execute("""SELECT cr.lastName FROM itemCreators ic JOIN creators cr ON cr.creatorID=ic.creatorID
        WHERE ic.itemID=? ORDER BY ic.orderIndex LIMIT 1""", (iid,)).fetchone()
    return re.sub(r"[^a-z]", "", (r[0] or "").lower()) if r else None
def norm(s):
    s = re.sub(r"<[^>]+>", " ", str(s or ""))
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()

def tok(s):
    return set(norm(s).split())

safe, flag = [], []
for h, ids in audit["cross"].items():
    ids = [i for i in ids if c.execute("SELECT 1 FROM items WHERE itemID=?", (i,)).fetchone()]
    if len(ids) < 2:
        continue
    ts = [tok(title(i)) for i in ids]
    aus = [au(i) for i in ids]
    # title overlap: one a subset of the other, or Jaccard >= .6
    ok = True
    for i in range(len(ts)):
        for j in range(i + 1, len(ts)):
            a, b = ts[i], ts[j]
            if not a or not b:
                ok = False; continue
            inter = len(a & b); union = len(a | b)
            if not (a <= b or b <= a or (union and inter / union >= 0.6)):
                ok = False
    known = [x for x in aus if x]
    for i in range(len(known)):
        for j in range(i + 1, len(known)):
            x, y = known[i], known[j]
            if x != y and x not in y and y not in x:
                ok = False
    (safe if ok else flag).append(ids)

print(f"\n=== CLASIFICARE ({len(audit['cross'])} continuturi partajate) ===")
print(f"  duplicate SIGURE (titlu+autor compatibile): {len(safe)} grupuri, {sum(len(x) for x in safe)} iteme")
print(f"  de SEMNALAT (lucrari diferite cu acelasi fisier): {len(flag)} grupuri")
for ids in flag:
    print(f"\n    ---")
    for i in ids:
        print(f"    {i}: {au(i) or '-'} — {title(i)[:64]}")
json.dump({"safe": safe, "flag": flag}, open("extract/cross_plan.json", "w"))
