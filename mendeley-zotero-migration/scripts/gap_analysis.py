# -*- coding: utf-8 -*-
"""Per annotated PDF (by SHA1): compare what Mendeley has (mine vs students')
against what Zotero's import actually placed. Quantifies the gap to fill."""
import sqlite3, sys, os, json
from collections import Counter
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\Viorel Proteasa\.claude\skills\zotero-citations\scripts")
import zot

DB = os.path.join(zot.ZDIR, "zotero.sqlite")
c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True).cursor()
amap = json.load(open("extract/ann_by_filehash.json", encoding="utf-8"))
h2att = json.load(open("extract/zotero_sha1_to_attach.json", encoding="utf-8"))

tot_mine = tot_theirs = tot_db = 0
gap_mine = gap_theirs = 0
buckets = Counter()
detail = []
for h, lst in amap.items():
    atts = h2att.get(h)
    if not atts:
        continue
    m_mine = sum(1 for x in lst if x["author"] is None)
    m_theirs = sum(1 for x in lst if x["author"])
    q = ",".join("?" * len(atts))
    dbn = c.execute(f"SELECT COUNT(*) FROM itemAnnotations WHERE parentItemID IN ({q})", atts).fetchone()[0]
    tot_mine += m_mine; tot_theirs += m_theirs; tot_db += dbn
    # crude: import brings only the user's own -> expect dbn ~= m_mine
    if dbn == 0 and m_theirs and not m_mine:
        buckets["doar-student, import n-a adus nimic"] += 1
        gap_theirs += m_theirs
    elif dbn == 0 and m_mine:
        buckets["ale mele, dar import n-a adus nimic"] += 1
        gap_mine += m_mine; gap_theirs += m_theirs
    else:
        if m_theirs:
            buckets["mixt (are ale mele in DB, lipsesc ale studentilor)"] += 1
            gap_theirs += m_theirs
        else:
            buckets["doar ale mele, aduse"] += 1
        if dbn < m_mine:
            gap_mine += (m_mine - dbn)
    detail.append((h, m_mine, m_theirs, dbn))

print("=== MENDELEY vs ZOTERO (pe PDF-urile adnotate prezente) ===")
print(f"Mendeley: {tot_mine} ale mele + {tot_theirs} ale studentilor = {tot_mine+tot_theirs}")
print(f"Zotero DB pe aceleasi PDF-uri: {tot_db}")
print("\ndistributie:")
for k, v in buckets.most_common():
    print(f"  {v:4}  {k}")
print(f"\nGOL ESTIMAT de completat:")
print(f"  adnotari ale studentilor lipsa: ~{gap_theirs}")
print(f"  adnotari ale mele lipsa:        ~{gap_mine}")
# a few examples where db has more than mendeley (import added extra?)
extra = [d for d in detail if d[3] > d[1] + d[2]]
print(f"\nPDF-uri unde DB are MAI MULTE decat Mendeley: {len(extra)} (ex: {extra[:3]})")
