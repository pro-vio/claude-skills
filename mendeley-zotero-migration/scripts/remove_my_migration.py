# -*- coding: utf-8 -*-
"""Remove the whole hand-built migration (items, their attachments/notes/annotations,
and the 112 collections created in phase 2), leaving: the user's original 461 items
+ Zotero's official Mendeley import. Idempotent; dry-run by default."""
import sqlite3, sys, json, os, shutil
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\Viorel Proteasa\.claude\skills\zotero-citations\scripts")
import zot

DB = os.path.join(zot.ZDIR, "zotero.sqlite")
ZSTOR = os.path.join(zot.ZDIR, "storage")

m2z = json.load(open("extract/mid_to_zid.json", encoding="utf-8"))
my_items = sorted(set(m2z.values()))
my_cols = json.load(open("extract/folder_map.json", encoding="utf-8"))["created_collection_ids"]

con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
cur = con.cursor()

q = ",".join("?" * len(my_items))
present = [r[0] for r in cur.execute(f"SELECT itemID FROM items WHERE itemID IN ({q})", my_items).fetchall()]
atts = [r[0] for r in cur.execute(f"SELECT itemID FROM itemAttachments WHERE parentItemID IN ({q})", my_items).fetchall()]
notes = [r[0] for r in cur.execute(f"SELECT itemID FROM itemNotes WHERE parentItemID IN ({q})", my_items).fetchall()]
# EVERY attachment I created (attach_ids.json) — incl. the ones I put on the user's
# pre-existing items, which are NOT children of my items.
mine_att_all = sorted(set(json.load(open("extract/attach_ids.json", encoding="utf-8")).values()))
qm = ",".join("?" * len(mine_att_all))
mine_att_present = [r[0] for r in cur.execute(f"SELECT itemID FROM items WHERE itemID IN ({qm})", mine_att_all).fetchall()]
atts = sorted(set(atts) | set(mine_att_present))

# MY annotations are on the USER'S pre-existing attachments (matched by md5), so they are
# not descendants of my items. Identify them by the migration's dateAdded day (verified
# cohorts: 07-14 = mine 1725; 07-15 = Zotero's import; earlier = the user's own).
anns = [r[0] for r in cur.execute(
    "SELECT an.itemID FROM itemAnnotations an JOIN items i ON i.itemID=an.itemID "
    "WHERE i.dateAdded LIKE '2026-07-14%'").fetchall()]
att_keys = []
if atts:
    qa = ",".join("?" * len(atts))
    anns += [r[0] for r in cur.execute(f"SELECT itemID FROM itemAnnotations WHERE parentItemID IN ({qa})", atts).fetchall()]
    anns = sorted(set(anns))
    att_keys = [r[0] for r in cur.execute(f"SELECT key FROM items WHERE itemID IN ({qa})", atts).fetchall()]

qc = ",".join("?" * len(my_cols))
cols_present = [r[0] for r in cur.execute(f"SELECT collectionID FROM collections WHERE collectionID IN ({qc})", my_cols).fetchall()]
filings = cur.execute(f"SELECT COUNT(*) FROM collectionItems WHERE collectionID IN ({qc})", my_cols).fetchone()[0]
# sanity: make sure none of my collections is a parent of a NON-mine collection (would orphan it)
foreign_kids = cur.execute(
    f"SELECT COUNT(*) FROM collections WHERE parentCollectionID IN ({qc}) AND collectionID NOT IN ({qc})", my_cols + my_cols).fetchone()[0]
con.close()

allids = sorted(set(present) | set(atts) | set(notes) | set(anns))
print("=== DE STERS (migrarea manuala) ===")
print(f"  iteme mele prezente : {len(present)}")
print(f"  atasamente          : {len(atts)}  (+{len(att_keys)} foldere storage)")
print(f"  note-copil          : {len(notes)}")
print(f"  adnotari            : {len(anns)}")
print(f"  TOTAL randuri items : {len(allids)}")
print(f"  colectii            : {len(cols_present)}  ({filings} filari)")
print(f"  colectii straine sub ale mele (trebuie 0): {foreign_kids}")
if foreign_kids:
    print("ABORT: as orfana colectii care nu-mi apartin"); sys.exit(1)

if "--apply" not in sys.argv:
    print("\n[DRY RUN] --apply pentru a sterge.")
    sys.exit(0)

qi = ",".join("?" * len(allids))
with zot.write_session("remove-manual-migration") as w:
    for tbl in ("itemAnnotations", "itemNotes", "itemAttachments", "itemData",
                "itemCreators", "itemTags", "collectionItems", "deletedItems", "itemRelations"):
        try:
            w.execute(f"DELETE FROM {tbl} WHERE itemID IN ({qi})", allids)
        except sqlite3.OperationalError:
            pass
    w.execute(f"DELETE FROM items WHERE itemID IN ({qi})", allids)
    # collections: filings first, then the collections themselves (children before parents)
    w.execute(f"DELETE FROM collectionItems WHERE collectionID IN ({qc})", my_cols)
    w.execute(f"DELETE FROM collections WHERE collectionID IN ({qc})", my_cols)
    print(f"Sters: {len(allids)} randuri items + {len(cols_present)} colectii.")

removed = 0
for k in att_keys:
    d = os.path.join(ZSTOR, k)
    if os.path.isdir(d):
        shutil.rmtree(d, ignore_errors=True)
        removed += 1
print(f"Foldere storage sterse: {removed}")
