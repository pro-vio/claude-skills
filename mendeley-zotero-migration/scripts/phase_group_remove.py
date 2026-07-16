# -*- coding: utf-8 -*-
import sys, json, os, shutil, sqlite3
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\Viorel Proteasa\.claude\skills\zotero-citations\scripts")
import zot
targets=json.load(open("extract/group_cleanup.json"))["pure_group_zids"]
DB=r"C:\Users\Viorel Proteasa\Zotero\zotero.sqlite"
ZSTOR=os.path.join(zot.ZDIR,"storage")

def descendants(cur, tids):
    q=",".join("?"*len(tids))
    atts=[r[0] for r in cur.execute(f"SELECT itemID FROM itemAttachments WHERE parentItemID IN ({q})",tids).fetchall()]
    notes=[r[0] for r in cur.execute(f"SELECT itemID FROM itemNotes WHERE parentItemID IN ({q})",tids).fetchall()]
    anns=[]
    if atts:
        qa=",".join("?"*len(atts))
        anns=[r[0] for r in cur.execute(f"SELECT itemID FROM itemAnnotations WHERE parentItemID IN ({qa})",atts).fetchall()]
    return atts, notes, anns

con=sqlite3.connect(f"file:{DB}?mode=ro&immutable=1",uri=True); cur=con.cursor()
atts,notes,anns=descendants(cur,targets)
# storage keys for attachments
att_keys=[]
if atts:
    qa=",".join("?"*len(atts))
    att_keys=[r[0] for r in cur.execute(f"SELECT key FROM items WHERE itemID IN ({qa})",atts).fetchall()]
con.close()
allids=set(targets)|set(atts)|set(notes)|set(anns)
print(f"Pure-group items: {len(targets)}")
print(f"  + attachments: {len(atts)} | child notes: {len(notes)} | annotations: {len(anns)}")
print(f"  TOTAL item rows to delete: {len(allids)}")
print(f"  storage folders to remove: {len(att_keys)}")

if "--apply" not in sys.argv:
    print("[DRY RUN] --apply to delete.")
    sys.exit(0)

ids=list(allids); q=",".join("?"*len(ids))
with zot.write_session("mendeley-remove-groups") as cur:
    for tbl in ("itemAnnotations","itemNotes","itemAttachments","itemData","itemCreators",
                "itemTags","collectionItems","deletedItems","itemRelations"):
        try: cur.execute(f"DELETE FROM {tbl} WHERE itemID IN ({q})",ids)
        except sqlite3.OperationalError: pass
    # annotations reference parents already deleted; also purge any annotations whose parent is a deleted attachment
    cur.execute(f"DELETE FROM items WHERE itemID IN ({q})",ids)
    print(f"Deleted {len(ids)} item rows across tables.")
# remove storage folders
removed=0
for k in att_keys:
    d=os.path.join(ZSTOR,k)
    if os.path.isdir(d):
        shutil.rmtree(d,ignore_errors=True); removed+=1
print(f"Removed {removed} storage folders.")
