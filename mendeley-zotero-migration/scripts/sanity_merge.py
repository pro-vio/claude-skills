# -*- coding: utf-8 -*-
"""Guard against over-merging: show the biggest groups, groups whose members have
different item types, and groups whose titles differ once you look at the raw text."""
import sqlite3, sys, os, json
from collections import Counter
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\Viorel Proteasa\.claude\skills\zotero-citations\scripts")
import zot

DB = os.path.join(zot.ZDIR, "zotero.sqlite")
c = sqlite3.connect(f"file:{DB}?mode=ro&immutable=1", uri=True).cursor()
plan = json.load(open("extract/merge_plan.json", encoding="utf-8"))

def info(iid):
    t = c.execute("""SELECT v.value FROM itemData d JOIN itemDataValues v ON v.valueID=d.valueID
        JOIN fields f ON f.fieldID=d.fieldID WHERE d.itemID=? AND f.fieldName IN ('title','nameOfAct','caseName') LIMIT 1""", (iid,)).fetchone()
    ty = c.execute("SELECT it.typeName FROM items i JOIN itemTypes it ON it.itemTypeID=i.itemTypeID WHERE i.itemID=?", (iid,)).fetchone()
    dt = c.execute("""SELECT v.value FROM itemData d JOIN itemDataValues v ON v.valueID=d.valueID
        JOIN fields f ON f.fieldID=d.fieldID WHERE d.itemID=? AND f.fieldName='date' LIMIT 1""", (iid,)).fetchone()
    au = c.execute("""SELECT cr.lastName FROM itemCreators ic JOIN creators cr ON cr.creatorID=ic.creatorID
        WHERE ic.itemID=? ORDER BY ic.orderIndex LIMIT 1""", (iid,)).fetchone()
    return (ty[0] if ty else "?", (t[0] if t else "(fara titlu)"), (dt[0] if dt else "-"), (au[0] if au else "-"))

sizes = Counter(len(l) + 1 for _, l in plan)
print("marimea grupurilor:", dict(sorted(sizes.items())))

print("\n=== cele mai mari 5 grupuri ===")
for master, losers in sorted(plan, key=lambda p: -len(p[1]))[:5]:
    ty, t, d, a = info(master)
    print(f"\n  MASTER {master} [{ty}] {a} ({d[:4]}) — {t[:65]}")
    for l in losers:
        ty2, t2, d2, a2 = info(l)
        print(f"    + {l} [{ty2}] {a2} ({d2[:4]}) — {t2[:65]}")

print("\n=== grupuri cu TIPURI diferite (suspecte) ===")
n = 0
for master, losers in plan:
    tys = {info(master)[0]} | {info(l)[0] for l in losers}
    if len(tys) > 1:
        n += 1
        if n <= 5:
            ty, t, d, a = info(master)
            print(f"  {sorted(tys)} — {t[:60]}")
print(f"  total: {n}")

print("\n=== grupuri cu AUTORI diferiti (suspecte) ===")
n = 0
for master, losers in plan:
    aus = {info(master)[3].lower()} | {info(l)[3].lower() for l in losers}
    if len(aus) > 1:
        n += 1
        if n <= 6:
            ty, t, d, a = info(master)
            print(f"  {sorted(aus)} — {t[:55]}")
print(f"  total: {n}")
