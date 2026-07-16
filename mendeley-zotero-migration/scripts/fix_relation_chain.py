# -*- coding: utf-8 -*-
"""An item can be master in one group and loser in another; when it is deleted, the
dc:replaces rows it held become orphans and the citation chain Y -> X -> M breaks.
Re-point them at the surviving master instead of dropping them."""
import sqlite3, sys, os, re
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\Viorel Proteasa\.claude\skills\zotero-citations\scripts")
import zot

APPLY = "--apply" in sys.argv
DB = os.path.join(zot.ZDIR, "zotero.sqlite")
c = sqlite3.connect(f"file:{DB}?mode=ro" + ("" if APPLY else "&immutable=1"), uri=True).cursor()

orphans = c.execute("""SELECT itemID, predicateID, object FROM itemRelations
                       WHERE itemID NOT IN (SELECT itemID FROM items)""").fetchall()
print(f"relatii orfane: {len(orphans)}")

# key -> surviving item, via existing dc:replaces objects
def survivor_of(dead_item_id):
    """The dead item's own URI should appear as the object of some living master."""
    return None

fixes, drops = [], []
for iid, pid, obj in orphans:
    # find the master that swallowed `iid`: it holds a dc:replaces whose object ends with iid's key
    # iid's key is gone from items, so search the backups' knowledge: the object URIs we wrote.
    # Instead: find any living item whose dc:replaces object key matches an object we can trace.
    # Practical approach: re-attach the orphan's object to the master that replaced the orphan.
    row = c.execute("""SELECT ir.itemID FROM itemRelations ir WHERE ir.predicateID=1
                       AND ir.itemID IN (SELECT itemID FROM items)
                       AND ir.object = (SELECT object FROM itemRelations WHERE itemID=? AND predicateID=1 LIMIT 1)""",
                    (iid,)).fetchone()
    print(f"  orfan: item {iid} -> {obj[-12:]}")
    fixes.append((iid, pid, obj))

# Determine, for each orphan itemID, which living master replaced it. We stored, at merge
# time, (master, uri-of-loser). So: find living masters whose object URI key == the orphan's key.
# The orphan's key is unknown (row gone), so fall back on the pre-merge backup.
BAK = os.path.join(zot.ZDIR, "zotero.sqlite.pre-repair-audit-findings.bak")
b = sqlite3.connect(f"file:{BAK}?mode=ro&immutable=1", uri=True).cursor()
plan = []
for iid, pid, obj in orphans:
    r = b.execute("SELECT key FROM items WHERE itemID=?", (iid,)).fetchone()
    if not r:
        drops.append((iid, obj)); continue
    uri = f"http://zotero.org/users/1055731/items/{r[0]}"
    m = c.execute("""SELECT itemID FROM itemRelations WHERE predicateID=1 AND object=?
                     AND itemID IN (SELECT itemID FROM items)""", (uri,)).fetchone()
    if m:
        plan.append((m[0], obj, iid))
    else:
        drops.append((iid, obj))
print(f"\nde redirectionat catre masterul final: {len(plan)}")
for m, obj, old in plan:
    print(f"  {obj[-10:]} : item {old} (sters) -> master {m}")
print(f"de sters (fara master identificabil): {len(drops)}")

if not APPLY:
    print("\n[DRY RUN] --apply pentru a repara.")
    sys.exit(0)

with zot.write_session("fix-relation-chain") as w:
    for m, obj, old in plan:
        w.execute("INSERT OR IGNORE INTO itemRelations (itemID,predicateID,object) VALUES (?,1,?)", (m, obj))
    w.execute("DELETE FROM itemRelations WHERE itemID NOT IN (SELECT itemID FROM items)")
    print(f"Redirectionate {len(plan)} relatii; sterse {len(drops)} fara master.")
