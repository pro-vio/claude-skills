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
import sqlite3, sys, os, json, random, datetime, urllib.request, time, shutil, hashlib
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

# A trashed item stays in `items`/`itemAttachments` with all its rows intact — Zotero
# soft-deletes via this junction table, not by removing the row. Any read query that
# means "active library content" must exclude it explicitly, or trashed parents AND
# trashed attachments (independently — an attachment can be trashed while its parent
# is not, e.g. a scan superseded by a text-native duplicate) silently reappear as if live.
NOT_TRASHED = "itemID NOT IN (SELECT itemID FROM deletedItems)"

def find(query):
    """Find items by title/nameOfAct/creator. -> [(itemKey, title, attachKey, pdfPath)].
    Excludes trashed items/attachments (see NOT_TRASHED)."""
    c = _ro().cursor()
    rows = c.execute(f"""
      SELECT DISTINCT i.itemID, i.key,
        (SELECT idv.value FROM itemData d JOIN itemDataValues idv ON idv.valueID=d.valueID
           JOIN fields f ON f.fieldID=d.fieldID WHERE d.itemID=i.itemID
           AND f.fieldName IN ('title','nameOfAct') LIMIT 1) t
      FROM items i WHERE i.itemTypeID NOT IN (1,3) AND i.{NOT_TRASHED}
        AND (EXISTS(SELECT 1 FROM itemData d JOIN itemDataValues v ON v.valueID=d.valueID
                    WHERE d.itemID=i.itemID AND v.value LIKE ?)
             OR EXISTS(SELECT 1 FROM itemCreators ic JOIN creators cr ON cr.creatorID=ic.creatorID
                       WHERE ic.itemID=i.itemID AND cr.lastName LIKE ?))
    """, (f"%{query}%", f"%{query}%")).fetchall()
    out = []
    for iid, key, title in rows:
        att = c.execute(f"""SELECT ai.key, ia.path FROM itemAttachments ia
                           JOIN items ai ON ai.itemID=ia.itemID
                           WHERE ia.parentItemID=? AND ia.contentType='application/pdf'
                             AND ai.{NOT_TRASHED} LIMIT 1""",
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

# ---- batched write cycle (do ALL writes for a task in ONE close/reopen) ----
# Every graceful close + restart of Zotero costs ~2-4 min (backup, poll-until-clean,
# API-ping budget). So: resolve every collection key you need with find_collection()
# while Zotero is still OPEN, then do a SINGLE write_session covering all items,
# attachments and collection filings. Do NOT close→write→reopen→read→close→write again.
LIBRARY_ID = 1  # personal library

def wait_until_quiescent(tries=20, delay=1.0):
    """Block until it is safe to write: Zotero's API is down AND no -wal/-journal
    lingers (a residual process flushing after your write silently discards it —
    the shutdown-race lesson). Raises if Zotero is still serving after the budget."""
    for _ in range(tries):
        journ = [DB + s for s in ("-wal", "-journal") if os.path.exists(DB + s)]
        if not zotero_running() and not journ:
            return True
        time.sleep(delay)
    if zotero_running():
        raise SystemExit("ABORT: Zotero încă răspunde pe 23119 — închide-l (taskkill /IM zotero.exe, fără /F) și reia.")
    return True  # process down but journal lingered; caller proceeds (backup already taken)

def backup(tag):
    """Checkpoint zotero.sqlite -> zotero.sqlite.pre-<tag>.bak. Returns the path."""
    dst = f"{DB}.pre-{tag}.bak"
    shutil.copy2(DB, dst)
    return dst

class write_session:
    """One batched DB-write cycle (Zotero CLOSED). Encapsulates the whole protocol:
    wait-until-quiescent -> backup -> open_rw -> (your writes) -> commit -> re-read
    from disk to verify the commit landed.

        with zot.write_session("roman-ana") as cur:
            sid = zot.add_item(cur, "statute", {"nameOfAct": "...", "codeNumber": "57/1968",
                                                "dateEnacted": "1968-00-00 1968"}, collection_id=cid)
            zot.attach_pdf(cur, sid, "/path/Legea_57_1968.pdf")
            zot.add_item(cur, "webpage", {"title": "Servicii", "url": "..."},
                         creators=[("author", "LOGS Grup de Inițiative Sociale")], collection_id=cid)

    Exceptions inside the block roll back and re-raise (nothing is written). Resolve
    collection ids with find_collection() BEFORE the block, while Zotero is open."""
    def __init__(self, tag, verify=True):
        self.tag, self.verify, self.bak = tag, verify, None
    def __enter__(self):
        wait_until_quiescent()
        self.bak = backup(self.tag)
        self.con = open_rw(); self.cur = self.con.cursor()
        return self.cur
    def __exit__(self, exc_type, exc, tb):
        if exc_type:
            self.con.rollback(); self.con.close(); return False  # re-raise
        self.con.commit(); self.con.close()
        if self.verify:
            n = _ro().execute("SELECT COUNT(*) FROM items WHERE synced=0").fetchone()[0]
            print(f"OK write_session '{self.tag}': committed; {n} item(s) pending sync; backup {os.path.basename(self.bak)}")
        return False

# ---- create-item building blocks (use inside write_session) ----
def item_type_id(cur, type_name):
    r = cur.execute("SELECT itemTypeID FROM itemTypes WHERE typeName=?", (type_name,)).fetchone()
    return r[0] if r else None

def find_collection(name):
    """(key, collectionID) for a collection by display name, or None. Uses a read-only
    connection, so it is safe to call while Zotero is RUNNING — resolve ids here first."""
    r = _ro().execute("SELECT key, collectionID FROM collections WHERE collectionName=?", (name,)).fetchone()
    return (r[0], r[1]) if r else None

def attachment_path(key):
    """Full filesystem path for an attachment key: resolves both an imported
    stored copy ('storage:<file>' -> storage/<key>/<file>) and a LINKED file
    (path is already absolute — no storage/ copy, and storageHash is always
    NULL for these, since Zotero doesn't own/hash a file it doesn't manage).
    Read-only; works whether Zotero is open or not. None if no such attachment."""
    r = _ro().execute("SELECT path FROM itemAttachments WHERE itemID=(SELECT itemID FROM items WHERE key=?)",
                       (key,)).fetchone()
    if not r or not r[0]:
        return None
    path = r[0]
    return os.path.join(STORAGE, key, path[len("storage:"):]) if path.startswith("storage:") else path

def _next_id(cur, col, table):
    return cur.execute(f"SELECT COALESCE(MAX({col}),0)+1 FROM {table}").fetchone()[0]

def _creator_id(cur, last, first, field_mode):
    r = cur.execute("SELECT creatorID FROM creators WHERE lastName=? AND firstName=? AND fieldMode=?",
                    (last, first, field_mode)).fetchone()
    if r: return r[0]
    nid = _next_id(cur, "creatorID", "creators")
    cur.execute("INSERT INTO creators (creatorID,firstName,lastName,fieldMode) VALUES (?,?,?,?)",
                (nid, first, last, field_mode))
    return nid

def _set_creators(cur, item_id, creators):
    """creators = [(creatorType, "Whole Institution Name")]  -> literal (fieldMode 1)
                  [(creatorType, lastName, firstName)]        -> personal (fieldMode 0)"""
    for idx, cre in enumerate(creators):
        ctype = cre[0]
        if len(cre) == 2:            # literal / institutional author
            last, first, fmode = cre[1], "", 1
        else:
            last, first, fmode = cre[1], cre[2], 0
        ctid = cur.execute("SELECT creatorTypeID FROM creatorTypes WHERE creatorType=?", (ctype,)).fetchone()
        if not ctid: raise ValueError(f"unknown creator type {ctype!r}")
        cid = _creator_id(cur, last, first, fmode)
        cur.execute("INSERT INTO itemCreators (itemID,creatorID,creatorTypeID,orderIndex) VALUES (?,?,?,?)",
                    (item_id, cid, ctid[0], idx))

def add_to_collection(cur, item_id, collection_id):
    oi = cur.execute("SELECT COALESCE(MAX(orderIndex),0)+1 FROM collectionItems WHERE collectionID=?",
                     (collection_id,)).fetchone()[0]
    cur.execute("INSERT OR IGNORE INTO collectionItems (collectionID,itemID,orderIndex) VALUES (?,?,?)",
                (collection_id, item_id, oi))

def add_item(cur, type_name, fields, creators=None, collection_id=None):
    """Create a new item. fields = {fieldName: value} (empty/None skipped);
    creators see _set_creators; files into collection_id if given. Returns itemID.
    Tip: for pure *creation* with Zotero OPEN you can instead POST /connector/saveItems
    (HTTP 201, no close). Use this path when the same batch also edits/attaches."""
    tid = item_type_id(cur, type_name)
    if tid is None: raise ValueError(f"unknown item type {type_name!r}")
    iid = _next_id(cur, "itemID", "items"); t = now()
    cur.execute("INSERT INTO items (itemID,itemTypeID,dateAdded,dateModified,clientDateModified,libraryID,key,version,synced) "
                "VALUES (?,?,?,?,?,?,?,0,0)", (iid, tid, t, t, t, LIBRARY_ID, newkey()))
    for fname, val in (fields or {}).items():
        if val is None or val == "": continue
        fid = field_id(cur, fname)
        if fid is None: raise ValueError(f"unknown field {fname!r}")
        set_field(cur, iid, fid, str(val))
    if creators: _set_creators(cur, iid, creators)
    if collection_id is not None: add_to_collection(cur, iid, collection_id)
    return iid

def attach_pdf(cur, parent_item_id, pdf_path):
    """Stored-copy PDF attachment: create the attachment item, copy the file to
    storage/<key>/, set linkMode 0 (imported_file), md5 storageHash, storageModTime."""
    if not os.path.exists(pdf_path): raise FileNotFoundError(pdf_path)
    tid = item_type_id(cur, "attachment")
    iid = _next_id(cur, "itemID", "items"); key = newkey(); t = now()
    cur.execute("INSERT INTO items (itemID,itemTypeID,dateAdded,dateModified,clientDateModified,libraryID,key,version,synced) "
                "VALUES (?,?,?,?,?,?,?,0,0)", (iid, tid, t, t, t, LIBRARY_ID, key))
    fname = os.path.basename(pdf_path)
    dstdir = os.path.join(STORAGE, key); os.makedirs(dstdir, exist_ok=True)
    shutil.copy2(pdf_path, os.path.join(dstdir, fname))
    with open(pdf_path, "rb") as fh: md5 = hashlib.md5(fh.read()).hexdigest()
    mtime = int(os.path.getmtime(pdf_path) * 1000)
    cur.execute("INSERT INTO itemAttachments (itemID,parentItemID,linkMode,contentType,path,storageModTime,storageHash) "
                "VALUES (?,?,?,?,?,?,?)", (iid, parent_item_id, 0, "application/pdf", "storage:"+fname, mtime, md5))
    return iid

# ---- child notes (summaries, caches) ----
# Zotero supports notes as children of an ATTACHMENT (not just of the top-level
# bibliographic item) — this is the same mechanism its PDF-reader sidebar uses
# for "add note from annotations". Write PLAIN TEXT; Zotero wraps it in its own
# <div class="zotero-note znv1"> at next startup and stably re-renders as <p>
# paragraphs from then on. Do not write HTML directly — it gets escaped/shown
# as literal tags (see zotero-schema.md "Child note").
def add_child_note(cur, parent_item_id, note_text):
    """Create a new plain-text child note. Returns the new note's itemID."""
    tid = item_type_id(cur, "note")
    iid = _next_id(cur, "itemID", "items"); t = now()
    cur.execute("INSERT INTO items (itemID,itemTypeID,dateAdded,dateModified,clientDateModified,libraryID,key,version,synced) "
                "VALUES (?,?,?,?,?,?,?,0,0)", (iid, tid, t, t, t, LIBRARY_ID, newkey()))
    cur.execute("INSERT INTO itemNotes (itemID,parentItemID,note,title) VALUES (?,?,?,?)",
                (iid, parent_item_id, note_text, ""))
    return iid

def find_child_notes(parent_item_id):
    """[(noteItemID, key, note_text)] for all child notes of a parent (item or
    attachment). Read-only — safe while Zotero is running."""
    return _ro().execute("SELECT itemID, key, note FROM items JOIN itemNotes USING(itemID) "
                          "WHERE parentItemID=?", (parent_item_id,)).fetchall()

def update_note(cur, note_item_id, note_text):
    """Overwrite an existing note's plain-text content in place (no duplicate note)."""
    cur.execute("UPDATE itemNotes SET note=? WHERE itemID=?", (note_text, note_item_id))
    touch(cur, note_item_id)

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "userid"
    if cmd == "find":
        for r in find(sys.argv[2]): print(r)
    elif cmd == "userid":
        print(detect_user_id() or "(nedetectat — setează ZOTERO_USER_ID sau dă --user-id)")
