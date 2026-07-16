# -*- coding: utf-8 -*-
"""1. Item 1142 "Measuring integration in new countries of immigration" carries the
   author reversed (lastName='Anatolie', firstName='Coșciug'). Repoint it at a correctly
   spelled creator — the creators table is shared, so never edit the row in place.
2. Item 10387 ("済無No Title No Title") holds the Stinebrickner NBER paper, which item
   10284 already has with correct metadata — a redundant copy, safe to remove.
   Item 10393 is NOT touched: its PDF is Edward C. See's dissertation and exists nowhere
   else in the library.
"""
import sqlite3, sys, os, shutil
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\Viorel Proteasa\.claude\skills\zotero-citations\scripts")
import zot

APPLY = "--apply" in sys.argv
DB = os.path.join(zot.ZDIR, "zotero.sqlite")
ZSTOR = os.path.join(zot.ZDIR, "storage")
c = sqlite3.connect(f"file:{DB}?mode=ro" + ("" if APPLY else "&immutable=1"), uri=True).cursor()

print("=== 1. autor inversat pe item 1142 ===")
cur = c.execute("""SELECT cr.creatorID, cr.lastName, cr.firstName FROM itemCreators ic
    JOIN creators cr ON cr.creatorID=ic.creatorID WHERE ic.itemID=1142 AND ic.orderIndex=0""").fetchone()
print(f"  acum : lastName={cur[1]!r} firstName={cur[2]!r} (creatorID {cur[0]})")
print(f"  tinta: lastName='Coșciug' firstName='Anatolie'")

print("\n=== 2. item 10387 (copie redundanta a lui 10284) ===")
atts = [r[0] for r in c.execute("SELECT itemID FROM itemAttachments WHERE parentItemID=10387").fetchall()]
keys = []
if atts:
    q = ",".join("?" * len(atts))
    keys = [r[0] for r in c.execute(f"SELECT key FROM items WHERE itemID IN ({q})", atts).fetchall()]
notes = [r[0] for r in c.execute("SELECT itemID FROM itemNotes WHERE parentItemID=10387").fetchall()]
anns = []
if atts:
    q = ",".join("?" * len(atts))
    anns = [r[0] for r in c.execute(f"SELECT itemID FROM itemAnnotations WHERE parentItemID IN ({q})", atts).fetchall()]
print(f"  de sters: item 10387 + {len(atts)} atasament(e) + {len(notes)} note + {len(anns)} adnotari")
print(f"  articolul ramane pe item 10284 (metadate corecte)")
print("\n  item 10393 NU se atinge — teza lui Edward C. See, unica in biblioteca.")

if not APPLY:
    print("\n[DRY RUN] --apply pentru a aplica.")
    sys.exit(0)

ids = [10387] + atts + notes + anns
q = ",".join("?" * len(ids))
with zot.write_session("fix-author-and-redundant-junk") as w:
    # 1. correct creator (find-or-create; never mutate the shared row)
    cid = zot._creator_id(w, "Coșciug", "Anatolie", 0)
    w.execute("UPDATE itemCreators SET creatorID=? WHERE itemID=1142 AND orderIndex=0", (cid,))
    zot.touch(w, 1142)
    # 2. remove the redundant record
    for tbl in ("itemAnnotations", "itemNotes", "itemAttachments", "itemData", "itemCreators",
                "itemTags", "collectionItems", "deletedItems", "itemRelations"):
        try: w.execute(f"DELETE FROM {tbl} WHERE itemID IN ({q})", ids)
        except sqlite3.OperationalError: pass
    w.execute(f"DELETE FROM items WHERE itemID IN ({q})", ids)
    print(f"Autor corectat (creatorID {cid}); sters item 10387 + {len(ids)-1} randuri copil.")

n = 0
for k in keys:
    d = os.path.join(ZSTOR, k)
    if os.path.isdir(d):
        shutil.rmtree(d, ignore_errors=True); n += 1
print(f"Foldere storage sterse: {n}")
