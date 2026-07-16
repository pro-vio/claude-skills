# -*- coding: utf-8 -*-
"""Merge the 11 groups (of the 14 the author-guard held back) that I inspected one by
one and confirmed are the same work. They only looked author-incompatible because the
guard compared the FIRST CREATOR, which for a book chapter is often the book's editor
rather than the chapter's author (Curaj vs Proteasa, della Porta vs Oliver).

Master is the user's original item in every group here, so citations keep resolving;
dc:replaces is recorded for each item swallowed. Three groups are deliberately NOT here
(book-vs-chapter, junk records, a mis-attributed DOI) — reported to the user instead.
"""
import sqlite3, sys, os, json
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\Viorel Proteasa\.claude\skills\zotero-citations\scripts")
import zot

USERID = 1055731
GROUPS = [   # (master, [losers], eticheta)
    (20,   [9819],                 "Selective Incentives (della Porta = editor, Oliver = autor)"),
    (1159, [13066],                "Participatory Budgeting"),
    (1264, [12577],                "Unraveled Practices of Participatory Budgeting"),
    (1250, [11198],                "How to Cope with GDPR (capitolul lui Proteasa)"),
    (1236, [7103],                 "Policy Incentives and Research Productivity"),
    (1275, [12066],                "Relating Quality and Funding (Miroiu)"),
    (1179, [13010],                "Does Max Weber's notion of authority"),
    (1135, [1402, 1423, 13358],    "Covert Research Ethics"),
    (1160, [11835],                "Labour market assessment Ukrainian refugees"),
    (1142, [12025],                "Measuring integration in new countries"),
    (15,   [13287],                "The IAD Framework (Weible = editor, Schlager = autor)"),
]
APPLY = "--apply" in sys.argv
DB = os.path.join(zot.ZDIR, "zotero.sqlite")
c = sqlite3.connect(f"file:{DB}?mode=ro" + ("" if APPLY else "&immutable=1"), uri=True).cursor()

print("=== CONTOPIRE (verificate manual) ===")
tot = 0
for master, losers, label in GROUPS:
    alive = [l for l in losers if c.execute("SELECT 1 FROM items WHERE itemID=?", (l,)).fetchone()]
    if not c.execute("SELECT 1 FROM items WHERE itemID=?", (master,)).fetchone():
        print(f"  !! master {master} nu exista — sar peste: {label}")
        continue
    ann = 0
    for l in alive:
        p = [r[0] for r in c.execute("SELECT itemID FROM itemAttachments WHERE parentItemID=?", (l,)).fetchall()]
        if p:
            q = ",".join("?" * len(p))
            ann += c.execute(f"SELECT COUNT(*) FROM itemAnnotations WHERE parentItemID IN ({q})", p).fetchone()[0]
    tot += len(alive)
    print(f"  {master} <- {alive}  ({ann} adnotari se muta)  {label}")
print(f"\ntotal iteme de contopit: {tot}")

if not APPLY:
    print("\n[DRY RUN] --apply pentru a contopi.")
    sys.exit(0)

with zot.write_session("merge-verified-14") as w:
    done = 0
    for master, losers, label in GROUPS:
        if not w.execute("SELECT 1 FROM items WHERE itemID=?", (master,)).fetchone():
            continue
        for l in losers:
            r = w.execute("SELECT key FROM items WHERE itemID=?", (l,)).fetchone()
            if not r:
                continue
            uri = f"http://zotero.org/users/{USERID}/items/{r[0]}"
            w.execute("UPDATE itemAttachments SET parentItemID=? WHERE parentItemID=?", (master, l))
            w.execute("UPDATE itemNotes SET parentItemID=? WHERE parentItemID=?", (master, l))
            for (cid,) in w.execute("SELECT collectionID FROM collectionItems WHERE itemID=?", (l,)).fetchall():
                oi = w.execute("SELECT COALESCE(MAX(orderIndex),0)+1 FROM collectionItems WHERE collectionID=?", (cid,)).fetchone()[0]
                w.execute("INSERT OR IGNORE INTO collectionItems (collectionID,itemID,orderIndex) VALUES (?,?,?)", (cid, master, oi))
            for (tid,) in w.execute("SELECT tagID FROM itemTags WHERE itemID=?", (l,)).fetchall():
                w.execute("INSERT OR IGNORE INTO itemTags (itemID,tagID,type) VALUES (?,?,0)", (master, tid))
            for tbl in ("itemData", "itemCreators", "itemTags", "collectionItems", "deletedItems", "itemRelations"):
                try: w.execute(f"DELETE FROM {tbl} WHERE itemID=?", (l,))
                except sqlite3.OperationalError: pass
            w.execute("DELETE FROM items WHERE itemID=?", (l,))
            w.execute("INSERT OR IGNORE INTO itemRelations (itemID,predicateID,object) VALUES (?,1,?)", (master, uri))
            done += 1
        zot.touch(w, master)
    print(f"Contopite {done} iteme.")
