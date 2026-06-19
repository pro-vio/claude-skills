# -*- coding: utf-8 -*-
"""
zot.py — token-minimal Zotero helper (portable).

Two jobs:
  1. Read Zotero offline (zotero.sqlite, read-only) — find items, PDF paths, user id.
  2. Write NATIVE annotations / edit fields directly in zotero.sqlite (Zotero CLOSED + backup).

Why direct sqlite: the local Zotero API (port 23119) is READ-ONLY for items
(POST -> "Endpoint does not support method"). The connector endpoint
(/connector/saveItems) creates NEW items live, but editing/moving existing items
and writing annotations must go through the DB. Local-only library (no sync) =
safe to write directly; bump items.version + synced=0 so a later sync is clean.

Config (env, with sane defaults):
  ZOTERO_DIR   -> default ~/Zotero  (holds zotero.sqlite + storage/)

CLI:
  python zot.py find "<query>"     # locate items by title/creator -> (key,title,attachKey,pdf)
  python zot.py userid             # print the library user id (for the web-API URLs)
"""
import sqlite3, sys, os, json, random, datetime, urllib.request
try: sys.stdout.reconfigure(encoding="utf-8")  # Windows cp1252 consoles crash on diacritics/emoji prints
except Exception: pass

ZDIR = os.environ.get("ZOTERO_DIR", os.path.expanduser("~/Zotero"))
DB = os.path.join(ZDIR, "zotero.sqlite")
STORAGE = os.path.join(ZDIR, "storage")
CLAUDE_COLOR = "#a28ae5"  # purple — convention: color encodes the annotation author
KEYCHARS = "23456789ABCDEFGHIJKLMNPQRSTUVWXYZ"

def _ro():
    """Read-only, immutable connection — safe to open while Zotero is RUNNING."""
    return sqlite3.connect(f"file:{DB}?mode=ro&immutable=1", uri=True)
def newkey():
    return ''.join(random.choice(KEYCHARS) for _ in range(8))
def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

def zotero_running():
    try: urllib.request.urlopen("http://127.0.0.1:23119/", timeout=3); return True
    except Exception: return False

def detect_user_id():
    """Best-effort: the library user id used in web-API URLs. Reads zotero.sqlite settings.
    Returns str or None (fall back to ZOTERO_USER_ID env / explicit arg)."""
    env = os.environ.get("ZOTERO_USER_ID")
    if env: return env
    try:
        c = _ro().cursor()
        for sql in (
            "SELECT value FROM settings WHERE setting='account' AND key='userID'",
            "SELECT userID FROM users LIMIT 1",
        ):
            try:
                r = c.execute(sql).fetchone()
                if r and r[0]: return str(r[0]).strip('"')
            except sqlite3.Error:
                continue
    except Exception:
        pass
    return None

def find(query):
    """Find items by title/nameOfAct/creator. -> [(itemKey, title, attachKey, pdfPath)]."""
    c = _ro().cursor()
    rows = c.execute("""
      SELECT DISTINCT i.itemID, i.key,
        (SELECT idv.value FROM itemData d JOIN itemDataValues idv ON idv.valueID=d.valueID
           JOIN fields f ON f.fieldID=d.fieldID WHERE d.itemID=i.itemID
           AND f.fieldName IN ('title','nameOfAct') LIMIT 1) t
      FROM items i WHERE i.itemTypeID NOT IN (1,3)
        AND (EXISTS(SELECT 1 FROM itemData d JOIN itemDataValues v ON v.valueID=d.valueID
                    WHERE d.itemID=i.itemID AND v.value LIKE ?)
             OR EXISTS(SELECT 1 FROM itemCreators ic JOIN creators cr ON cr.creatorID=ic.creatorID
                       WHERE ic.itemID=i.itemID AND cr.lastName LIKE ?))
    """, (f"%{query}%", f"%{query}%")).fetchall()
    out = []
    for iid, key, title in rows:
        att = c.execute("""SELECT ai.key, ia.path FROM itemAttachments ia
                           JOIN items ai ON ai.itemID=ia.itemID
                           WHERE ia.parentItemID=? AND ia.contentType='application/pdf' LIMIT 1""",
                        (iid,)).fetchone()
        ak = att[0] if att else None
        path = os.path.join(STORAGE, ak, att[1][len('storage:'):]) if att else None
        out.append((key, title, ak, path))
    return out

# ---- direct-write helpers (Zotero CLOSED) ----
def open_rw():
    """Open zotero.sqlite for writing. Refuses if Zotero is running."""
    if zotero_running():
        raise SystemExit("ABORT: Zotero pare DESCHIS (23119 răspunde). Închide-l întâi + fă backup.")
    return sqlite3.connect(DB)

def get_value(cur, value):
    """itemDataValues.value is UNIQUE — return existing valueID or insert a new one."""
    r = cur.execute("SELECT valueID FROM itemDataValues WHERE value=?", (value,)).fetchone()
    if r: return r[0]
    nv = cur.execute("SELECT COALESCE(MAX(valueID),0) FROM itemDataValues").fetchone()[0] + 1
    cur.execute("INSERT INTO itemDataValues (valueID,value) VALUES (?,?)", (nv, value))
    return nv

def set_field(cur, item_id, field_id, value):
    """Upsert one itemData field. Returns 'UPDATE' or 'INSERT'."""
    vid = get_value(cur, value)
    n = cur.execute("UPDATE itemData SET valueID=? WHERE itemID=? AND fieldID=?",
                    (vid, item_id, field_id)).rowcount
    if n == 0:
        cur.execute("INSERT INTO itemData (itemID,fieldID,valueID) VALUES (?,?,?)",
                    (item_id, field_id, vid))
    return "UPDATE" if n else "INSERT"

def touch(cur, item_id):
    """Mark an item dirty so the next sync picks it up cleanly."""
    t = now()
    cur.execute("UPDATE items SET version=version+1, synced=0, dateModified=?, clientDateModified=? WHERE itemID=?",
                (t, t, item_id))

def field_id(cur, field_name):
    r = cur.execute("SELECT fieldID FROM fields WHERE fieldName=?", (field_name,)).fetchone()
    return r[0] if r else None

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "userid"
    if cmd == "find":
        for r in find(sys.argv[2]): print(r)
    elif cmd == "userid":
        print(detect_user_id() or "(nedetectat — setează ZOTERO_USER_ID sau dă --user-id)")
