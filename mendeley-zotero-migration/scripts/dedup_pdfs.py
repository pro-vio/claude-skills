# -*- coding: utf-8 -*-
"""Per item: collapse PDF attachments holding the SAME content (sha1).

Keeper = the copy carrying the most annotations. Any annotation the losers hold and the
keeper lacks is moved over (dedup by the order-independent bbox signature); then the
loser attachment and its storage folder go. Only ever collapses within one item, and
only when the bytes are identical. Dry-run by default.
"""
import sqlite3, sys, os, json, shutil, hashlib
from collections import defaultdict
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\Viorel Proteasa\.claude\skills\zotero-citations\scripts")
import zot

DB = os.path.join(zot.ZDIR, "zotero.sqlite")
ZSTOR = os.path.join(zot.ZDIR, "storage")
APPLY = "--apply" in sys.argv
con = sqlite3.connect(f"file:{DB}?mode=ro" + ("" if APPLY else "&immutable=1"), uri=True)
c = con.cursor()

def sha1(fp):
    h = hashlib.sha1()
    with open(fp, "rb") as f:
        for ch in iter(lambda: f.read(1048576), b""):
            h.update(ch)
    return h.hexdigest()

def sig(typ, pos):
    p = json.loads(pos) if isinstance(pos, str) else pos
    rs = p.get("rects") or [[0, 0, 0, 0]]
    return (typ, p.get("pageIndex"), len(rs),
            round(min(r[0] for r in rs)), round(min(r[1] for r in rs)),
            round(max(r[2] for r in rs)), round(max(r[3] for r in rs)))

rows = c.execute("""SELECT ia.itemID, ia.parentItemID, i.key, ia.path FROM itemAttachments ia
                    JOIN items i ON i.itemID=ia.itemID
                    WHERE ia.contentType='application/pdf' AND ia.parentItemID IS NOT NULL
                      AND ia.path LIKE 'storage:%'""").fetchall()
byparent = defaultdict(list)
for aid, parent, key, path in rows:
    byparent[parent].append((aid, key, path))

plan = []      # (keeper, loser, [annotations to move])
for parent, atts in byparent.items():
    if len(atts) < 2:
        continue
    byhash = defaultdict(list)
    for aid, key, path in atts:
        fp = os.path.join(ZSTOR, key, path[len("storage:"):])
        if not os.path.exists(fp):
            continue
        try:
            byhash[sha1(fp)].append((aid, key))
        except Exception:
            pass
    for h, group in byhash.items():
        if len(group) < 2:
            continue
        counts = {aid: c.execute("SELECT COUNT(*) FROM itemAnnotations WHERE parentItemID=?", (aid,)).fetchone()[0]
                  for aid, _ in group}
        keeper = sorted(group, key=lambda g: (-counts[g[0]], g[0]))[0][0]
        keep_sigs = set()
        for typ, pos in c.execute("SELECT type,position FROM itemAnnotations WHERE parentItemID=?", (keeper,)).fetchall():
            try: keep_sigs.add(sig(typ, pos))
            except Exception: pass
        for aid, key in group:
            if aid == keeper:
                continue
            move = []
            for annid, typ, pos in c.execute("SELECT itemID,type,position FROM itemAnnotations WHERE parentItemID=?", (aid,)).fetchall():
                try:
                    s = sig(typ, pos)
                except Exception:
                    continue
                if s not in keep_sigs:
                    keep_sigs.add(s)
                    move.append(annid)
            plan.append((keeper, aid, key, move))

n_move = sum(len(m) for _, _, _, m in plan)
print("=== DEDUP PDF (in interiorul aceluiasi item, continut identic) ===")
print(f"atasamente de eliminat : {len(plan)}")
print(f"iteme afectate         : {len(set(p for p, atts in byparent.items() if len(atts) > 1))}")
print(f"adnotari MUTATE pe cel pastrat: {n_move}")
print(f"adnotari care ar fi fost duplicate (raman, se sterg cu atasamentul): "
      f"{sum(1 for k, a, key, m in plan for _ in c.execute('SELECT 1 FROM itemAnnotations WHERE parentItemID=?', (a,)).fetchall()) - n_move}")

if not APPLY:
    print("\n[DRY RUN] --apply pentru a curata.")
    sys.exit(0)

con.close()
keys_removed = []
with zot.write_session("dedup-pdf-attachments") as w:
    for keeper, loser, key, move in plan:
        for annid in move:
            w.execute("UPDATE itemAnnotations SET parentItemID=? WHERE itemID=?", (keeper, annid))
        # whatever annotations remain on the loser are duplicates of the keeper's
        rest = [r[0] for r in w.execute("SELECT itemID FROM itemAnnotations WHERE parentItemID=?", (loser,)).fetchall()]
        if rest:
            q = ",".join("?" * len(rest))
            w.execute(f"DELETE FROM itemAnnotations WHERE itemID IN ({q})", rest)
            w.execute(f"DELETE FROM items WHERE itemID IN ({q})", rest)
        for tbl in ("itemAttachments", "itemData", "itemTags", "collectionItems", "deletedItems", "itemRelations", "itemNotes"):
            try: w.execute(f"DELETE FROM {tbl} WHERE itemID=?", (loser,))
            except sqlite3.OperationalError: pass
        w.execute("DELETE FROM items WHERE itemID=?", (loser,))
        keys_removed.append(key)
        zot.touch(w, keeper)
    print(f"Eliminate {len(plan)} atasamente duplicate; mutate {n_move} adnotari.")

removed = 0
for k in keys_removed:
    d = os.path.join(ZSTOR, k)
    if os.path.isdir(d):
        shutil.rmtree(d, ignore_errors=True); removed += 1
print(f"Foldere storage sterse: {removed}")
