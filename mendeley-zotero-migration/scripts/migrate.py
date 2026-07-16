# -*- coding: utf-8 -*-
"""Migration helpers layered on the zotero-citations motor (zot.py).
Adds: add_collection (hierarchy) and native annotation writing.
Nothing here edits the skill; it imports zot as a library."""
import os, sys, json
sys.path.insert(0, r"C:\Users\Viorel Proteasa\.claude\skills\zotero-citations\scripts")
import zot

def add_collection(cur, name, parent_id=None):
    """Create a Zotero collection. Returns collectionID."""
    cid = zot._next_id(cur, "collectionID", "collections")
    cur.execute(
        "INSERT INTO collections (collectionID,collectionName,parentCollectionID,"
        "clientDateModified,libraryID,key,version,synced) VALUES (?,?,?,?,?,?,0,0)",
        (cid, name, parent_id, zot.now(), zot.LIBRARY_ID, zot.newkey()))
    return cid

def add_tags(cur, item_id, tags):
    """Attach tags (type 0 = manual) to an item, reusing existing tag rows."""
    for name in tags:
        r=cur.execute("SELECT tagID FROM tags WHERE name=?",(name,)).fetchone()
        if r: tid=r[0]
        else:
            tid=zot._next_id(cur,"tagID","tags")
            cur.execute("INSERT INTO tags (tagID,name) VALUES (?,?)",(tid,name))
        cur.execute("INSERT OR IGNORE INTO itemTags (itemID,tagID,type) VALUES (?,?,0)",(item_id,tid))
