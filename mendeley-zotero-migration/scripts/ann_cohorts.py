# -*- coding: utf-8 -*-
"""Identify the three annotation cohorts by dateAdded: pre-existing (user's own Zotero
work), mine (hand migration, 2026-07-14 evening), and Zotero's Mendeley import (07-15)."""
import sqlite3, sys, os, json
from collections import Counter
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\Viorel Proteasa\.claude\skills\zotero-citations\scripts")
import zot

DB = os.path.join(zot.ZDIR, "zotero.sqlite")
c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True).cursor()

rows = c.execute("""SELECT an.itemID, i.dateAdded, an.authorName, an.parentItemID
                    FROM itemAnnotations an JOIN items i ON i.itemID=an.itemID""").fetchall()
print("total adnotari:", len(rows))
byday = Counter(r[1][:10] for r in rows)
print("\ndupa ziua adaugarii:")
for d, n in sorted(byday.items()):
    print(f"  {d}: {n}")

print("\ndupa ora (doar 07-14 si 07-15):")
byhour = Counter(r[1][:13] for r in rows if r[1][:10] in ("2026-07-14", "2026-07-15"))
for d, n in sorted(byhour.items()):
    print(f"  {d}h: {n}")

# author names per cohort
print("\nauthorName per zi:")
for d in sorted(byday):
    a = Counter(r[2] for r in rows if r[1][:10] == d)
    print(f"  {d}: {dict(a)}")
