# -*- coding: utf-8 -*-
"""Two repairs after the merge/dedup:

1. dc:replaces — Zotero's own merge records, on the master, the URI of every item it
   swallowed, so Word/LibreOffice citations pointing at the old key still resolve. My
   merge deleted 286 items (38 of them the user's originals, which may well be cited)
   without that. Rebuild the relations from the pre-merge backup.
2. 13 notes were left parentless when their attachment was collapsed as a duplicate.
   Reattach them to the item that attachment belonged to.
"""
import sqlite3, sys, os, json
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\Viorel Proteasa\.claude\skills\zotero-citations\scripts")
import zot

ZDIR = zot.ZDIR
DB = os.path.join(ZDIR, "zotero.sqlite")
BAK_MERGE = os.path.join(ZDIR, "zotero.sqlite.pre-merge-duplicate-items.bak")
BAK_PDF = os.path.join(ZDIR, "zotero.sqlite.pre-dedup-pdf-attachments.bak")
USERID = 1055731
APPLY = "--apply" in sys.argv

live = sqlite3.connect(f"file:{DB}?mode=ro" + ("" if APPLY else "&immutable=1"), uri=True).cursor()
bm = sqlite3.connect(f"file:{BAK_MERGE}?mode=ro&immutable=1", uri=True).cursor()
bp = sqlite3.connect(f"file:{BAK_PDF}?mode=ro&immutable=1", uri=True).cursor()

# ---- 1. dc:replaces for merged-away items ----
plan = json.load(open("extract/merge_plan.json", encoding="utf-8"))
orig_ids = {x["zid"] for x in json.load(open("extract/zotero_ids.json", encoding="utf-8"))}
rels = []
n_orig = 0
for master, losers in plan:
    for l in losers:
        r = bm.execute("SELECT key FROM items WHERE itemID=?", (l,)).fetchone()
        if not r:
            continue
        uri = f"http://zotero.org/users/{USERID}/items/{r[0]}"
        rels.append((master, uri))
        if l in orig_ids:
            n_orig += 1
# skip ones already present
existing = {(a, b) for a, b in live.execute("SELECT itemID, object FROM itemRelations WHERE predicateID=1").fetchall()}
rels = [x for x in rels if x not in existing]
print(f"dc:replaces de adaugat: {len(rels)}  (din care {n_orig} pentru itemele tale ORIGINALE, potential citate)")

# ---- 2. orphan notes ----
orphans = [r[0] for r in live.execute(
    "SELECT itemID FROM itemNotes WHERE parentItemID IS NOT NULL AND parentItemID NOT IN (SELECT itemID FROM items)").fetchall()]
fix_notes = []
for nid in orphans:
    old_parent = live.execute("SELECT parentItemID FROM itemNotes WHERE itemID=?", (nid,)).fetchone()[0]
    # old_parent was an attachment collapsed as duplicate -> find the item it hung off
    r = bp.execute("SELECT parentItemID FROM itemAttachments WHERE itemID=?", (old_parent,)).fetchone()
    if r and r[0]:
        still = live.execute("SELECT 1 FROM items WHERE itemID=?", (r[0],)).fetchone()
        if still:
            fix_notes.append((nid, r[0]))
print(f"note orfane: {len(orphans)} -> reatasabile la itemul lor: {len(fix_notes)}")

if not APPLY:
    print("\n[DRY RUN] --apply pentru a repara.")
    sys.exit(0)

with zot.write_session("fix-relations-and-orphan-notes") as w:
    for master, uri in rels:
        w.execute("INSERT OR IGNORE INTO itemRelations (itemID,predicateID,object) VALUES (?,1,?)", (master, uri))
    for nid, parent in fix_notes:
        w.execute("UPDATE itemNotes SET parentItemID=? WHERE itemID=?", (parent, nid))
        zot.touch(w, nid)
    print(f"Adaugate {len(rels)} relatii dc:replaces; reatasate {len(fix_notes)} note.")
