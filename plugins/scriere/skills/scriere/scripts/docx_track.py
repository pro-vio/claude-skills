# -*- coding: utf-8 -*-
"""docx_track — round-trip Word track-changes helper (author = "Claude").

Reusable core for the `scriere` skill. Operates on an UNPACKED .docx directory and
writes every edit as a tracked change (w:ins / w:del / w:pPrChange), so the human can
accept/reject each one in Word. Also does threaded comment replies and footnotes.

Typical use:

    from docx_track import Docx
    d = Docx.unpack("Manuscript.docx", "_work")   # reliable unzip (handles diacritics/§)
    d.replace("teh ", "the ", "typo")             # tracked del+ins
    d.insert_after_text("as outlined", " (Sandler 2015)", "cite")
    d.insert_after_ins("value sym", " (Olson [1965] 2003)", "cite after user ins")
    d.set_heading("Exploitation of the largest", 3, "promote to H3")
    d.reply_to_comment(13, "Inserted (Sandler 2015, 190).", "reply #13")
    d.add_footnote("Opinia Timișoarei", footnote_xml_runs, "press footnote")
    d.save()
    d.repack("Manuscript_track.docx")
    # then ALWAYS: validate_docx.py Manuscript_track.docx

Design notes / gotchas live in references/ooxml-track-changes.md — read it before
extending. Key ones: text is matched inside a SINGLE direct run (Word splits runs
arbitrarily; if a match misses, the phrase is split across runs — shorten the needle or
target the user's w:ins with insert_after_ins). Apostrophes in the source are usually
typographic ’ not ASCII '.
"""
import sys, os, copy, zipfile
from pathlib import Path
from lxml import etree

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# --- OOXML namespaces ---
W   = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W14 = "http://schemas.microsoft.com/office/word/2010/wordml"
W15 = "http://schemas.microsoft.com/office/word/2012/wordml"
W16 = "http://schemas.microsoft.com/office/word/2016/wordml/cid"
XS  = "{http://www.w3.org/XML/1998/namespace}space"
def w(t):   return f"{{{W}}}{t}"
def w14(t): return f"{{{W14}}}{t}"
def w15(t): return f"{{{W15}}}{t}"
def w16(t): return f"{{{W16}}}{t}"

_PARSER = etree.XMLParser(remove_blank_text=False)


class Docx:
    """An unpacked .docx under `root`. All edits are tracked changes by `author`."""

    def __init__(self, root, author="Claude", initials="C", date="2026-01-01T00:00:00Z"):
        self.root = Path(root)
        self.author = author
        self.initials = initials
        self.date = date
        self._id = 9000            # running id for w:ins/w:del/pPrChange + comment ids
        self._trees = {}           # filename -> parsed tree (lazy)
        self.log = []
        doc = self._tree("document.xml")
        self.body = doc.getroot().find(w("body"))

    # ---------- packing ----------
    @classmethod
    def unpack(cls, src, workdir, **kw):
        """Reliable unzip — NOT `unzip` (which leaves document.xml stale on §/diacritic paths)."""
        workdir = Path(workdir)
        if workdir.exists():
            import shutil
            shutil.rmtree(workdir, ignore_errors=True)
        workdir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(src) as z:
            z.extractall(workdir)
        return cls(workdir, **kw)

    def repack(self, out):
        """Rezip the working dir back into a .docx (saves pending trees first)."""
        self.save()
        out = Path(out)
        files = [p for p in self.root.rglob("*") if p.is_file()]
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            for p in files:
                z.write(p, p.relative_to(self.root).as_posix())
        return out

    # ---------- internals ----------
    def _tree(self, fn):
        if fn not in self._trees:
            self._trees[fn] = etree.parse(str(self.root / "word" / fn), _PARSER)
        return self._trees[fn]

    def _nid(self):
        self._id += 1
        return str(self._id)

    def _paras(self):
        return self.body.findall(w("p"))

    @staticmethod
    def _rtext(r):
        return "".join(x.text or "" for x in r.findall(w("t")))

    def _mk_t(self, text):
        r = etree.Element(w("r")); t = etree.SubElement(r, w("t")); t.text = text
        if text and (text[0] == " " or text[-1] == " "):
            t.set(XS, "preserve")
        return r

    def _ins(self, text):
        e = etree.Element(w("ins"))
        e.set(w("id"), self._nid()); e.set(w("author"), self.author); e.set(w("date"), self.date)
        e.append(self._mk_t(text)); return e

    def _del(self, text):
        e = etree.Element(w("del"))
        e.set(w("id"), self._nid()); e.set(w("author"), self.author); e.set(w("date"), self.date)
        dr = etree.SubElement(e, w("r")); dt = etree.SubElement(dr, w("delText")); dt.text = text
        if text and (text[0] == " " or text[-1] == " "):
            dt.set(XS, "preserve")
        return e

    # ---------- tracked text edits (on document.xml) ----------
    def replace(self, old, new, label=""):
        """Tracked replace: in the direct run containing `old`, del `old` + ins `new`.
        `new=""` makes it a pure tracked deletion."""
        for para in self._paras():
            for r in para.findall(w("r")):
                txt = self._rtext(r)
                if old in txt:
                    i = txt.find(old); pre, suf = txt[:i], txt[i + len(old):]
                    repl = []
                    if pre: repl.append(self._mk_t(pre))
                    repl.append(self._del(old))
                    if new: repl.append(self._ins(new))
                    if suf: repl.append(self._mk_t(suf))
                    idx = list(para).index(r); para.remove(r)
                    for k, e in enumerate(repl): para.insert(idx + k, e)
                    self.log.append(f"OK   {label or 'replace'}"); return True
        self.log.append(f"MISS {label or 'replace'}  («{old[:40]}»)"); return False

    def delete(self, text, label=""):
        """Tracked deletion of `text`."""
        return self.replace(text, "", label or "delete")

    def insert_after_text(self, prefix, text, label=""):
        """Insert `text` as a tracked insertion right after `prefix` (within its direct run)."""
        for para in self._paras():
            for r in para.findall(w("r")):
                txt = self._rtext(r)
                if prefix in txt:
                    i = txt.find(prefix) + len(prefix); pre, suf = txt[:i], txt[i:]
                    repl = [self._mk_t(pre), self._ins(text)]
                    if suf: repl.append(self._mk_t(suf))
                    idx = list(para).index(r); para.remove(r)
                    for k, e in enumerate(repl): para.insert(idx + k, e)
                    self.log.append(f"OK   {label or 'insert_after_text'}"); return True
        self.log.append(f"MISS {label or 'insert_after_text'}  (prefix «{prefix[:40]}»)"); return False

    def insert_after_ins(self, contains, text, label=""):
        """Insert a NEW tracked insertion right after the USER's w:ins run containing `contains`.
        Use when your anchor sits inside text the user already inserted (tracked), not a plain run."""
        for para in self._paras():
            for e in para.findall(w("ins")):
                if contains in "".join(t.text or "" for t in e.iter(w("t"))):
                    par = e.getparent(); par.insert(list(par).index(e) + 1, self._ins(text))
                    self.log.append(f"OK   {label or 'insert_after_ins'}"); return True
        self.log.append(f"MISS {label or 'insert_after_ins'}  (ins «{contains[:40]}»)"); return False

    def fix_in_ins(self, old, new, label=""):
        """Correct a typo INSIDE the user's own w:ins, in place (no nested tracking needed)."""
        for para in self._paras():
            for e in para.findall(w("ins")):
                for t in e.iter(w("t")):
                    if t.text and old in t.text:
                        t.text = t.text.replace(old, new)
                        self.log.append(f"OK   {label or 'fix_in_ins'} (in-ins)"); return True
        self.log.append(f"MISS {label or 'fix_in_ins'}"); return False

    def set_heading(self, needle, level=3, label=""):
        """Change the paragraph whose full text == `needle` to HeadingN (tracked via w:pPrChange),
        dropping list numbering. `needle` must match the paragraph's stripped text exactly."""
        for para in self._paras():
            if "".join(t.text or "" for t in para.iter(w("t"))).strip() == needle:
                ppr = para.find(w("pPr"))
                if ppr is None:
                    ppr = etree.Element(w("pPr")); para.insert(0, ppr)
                old_ppr = copy.deepcopy(ppr)
                ps = ppr.find(w("pStyle"))
                if ps is None:
                    ps = etree.Element(w("pStyle")); ppr.insert(0, ps)
                ps.set(w("val"), f"Heading{level}")
                np = ppr.find(w("numPr"))
                if np is not None: ppr.remove(np)
                ch = etree.SubElement(ppr, w("pPrChange"))
                ch.set(w("id"), self._nid()); ch.set(w("author"), self.author); ch.set(w("date"), self.date)
                inner = etree.SubElement(ch, w("pPr"))
                for el in old_ppr:
                    if el.tag != w("pPrChange"): inner.append(copy.deepcopy(el))
                self.log.append(f"OK   {label or 'set_heading'}"); return True
        self.log.append(f"MISS {label or 'set_heading'}  («{needle[:40]}»)"); return False

    # ---------- threaded comment replies ----------
    def reply_to_comment(self, parent_id, text, label=""):
        """Add a threaded reply (author = self.author) under existing comment `parent_id`.
        Touches comments.xml, commentsExtended.xml, commentsIds.xml, people.xml + the body anchor."""
        cr = self._tree("comments.xml").getroot()
        er = self._tree("commentsExtended.xml").getroot()
        ir = self._tree("commentsIds.xml").getroot()
        ppl = self._tree("people.xml").getroot()

        # register author once
        if not any(p.get(w15("author")) == self.author for p in ppl.findall(w15("person"))):
            pe = etree.SubElement(ppl, w15("person")); pe.set(w15("author"), self.author)
            pi = etree.SubElement(pe, w15("presenceInfo"))
            pi.set(w15("providerId"), "None"); pi.set(w15("userId"), self.author)

        def parent_paraid(pid):
            for c in cr.findall(w("comment")):
                if c.get(w("id")) == str(pid):
                    return c.find(w("p")).get(w14("paraId"))
        def in_body(tag, idv):
            for e in self.body.iter(w(tag)):
                if e.get(w("id")) == str(idv): return e
        def ref_run(idv):
            for r in self.body.iter(w("r")):
                for cf in r.findall(w("commentReference")):
                    if cf.get(w("id")) == str(idv): return r

        cid = self._nid()
        para_id = f"{(0x30000000 + int(cid)) & 0xFFFFFFFF:08X}"
        dur = f"{(0x31000000 + int(cid)) & 0xFFFFFFFF:08X}"
        ppara = parent_paraid(parent_id)
        if ppara is None:
            self.log.append(f"MISS {label or 'reply'} -> comment #{parent_id} not found"); return False

        # comments.xml: the reply comment
        c = etree.SubElement(cr, w("comment"))
        c.set(w("id"), cid); c.set(w("author"), self.author); c.set(w("date"), self.date); c.set(w("initials"), self.initials)
        p = etree.SubElement(c, w("p")); p.set(w14("paraId"), para_id); p.set(w14("textId"), "77777777")
        pp = etree.SubElement(p, w("pPr")); ps = etree.SubElement(pp, w("pStyle")); ps.set(w("val"), "CommentText")
        r1 = etree.SubElement(p, w("r")); rp = etree.SubElement(r1, w("rPr"))
        rsx = etree.SubElement(rp, w("rStyle")); rsx.set(w("val"), "CommentReference"); etree.SubElement(r1, w("annotationRef"))
        r2 = etree.SubElement(p, w("r")); t = etree.SubElement(r2, w("t")); t.text = text
        # commentsExtended.xml: link reply -> parent (this is what makes it threaded)
        ce = etree.SubElement(er, w15("commentEx"))
        ce.set(w15("paraId"), para_id); ce.set(w15("paraIdParent"), ppara); ce.set(w15("done"), "0")
        # commentsIds.xml
        ci = etree.SubElement(ir, w16("commentId")); ci.set(w16("paraId"), para_id); ci.set(w16("durableId"), dur)

        # body anchor: reuse the parent's comment range
        ps_ = in_body("commentRangeStart", parent_id); pe_ = in_body("commentRangeEnd", parent_id); pr_ = ref_run(parent_id)
        if ps_ is None or pe_ is None or pr_ is None:
            self.log.append(f"MISS {label or 'reply'} -> #{parent_id} body anchor missing"); return False
        cs = etree.Element(w("commentRangeStart")); cs.set(w("id"), cid)
        ps_.getparent().insert(ps_.getparent().index(ps_) + 1, cs)
        ce2 = etree.Element(w("commentRangeEnd")); ce2.set(w("id"), cid)
        pe_.getparent().insert(pe_.getparent().index(pe_), ce2)
        rr = etree.Element(w("r")); rpr = etree.SubElement(rr, w("rPr"))
        rs = etree.SubElement(rpr, w("rStyle")); rs.set(w("val"), "CommentReference")
        cref = etree.SubElement(rr, w("commentReference")); cref.set(w("id"), cid)
        pr_.getparent().insert(pr_.getparent().index(pr_) + 1, rr)
        self.log.append(f"OK   {label or 'reply'} -> #{parent_id} (id {cid})"); return True

    # ---------- footnotes ----------
    def add_footnote(self, anchor_text, footnote_text, label=""):
        """Insert a tracked footnote. A new footnote (FootnoteText) is added to footnotes.xml with
        `footnote_text`; a footnoteReference run (wrapped in w:ins so it's tracked) is placed right
        after `anchor_text` in the body. `footnote_text` is plain text (one paragraph)."""
        ft = self._tree("footnotes.xml").getroot()
        existing = [int(f.get(w("id"))) for f in ft.findall(w("footnote")) if f.get(w("id")) and f.get(w("id")).lstrip("-").isdigit()]
        fid = str((max(existing) + 1) if existing else 1)
        # footnotes.xml entry
        fn = etree.SubElement(ft, w("footnote")); fn.set(w("id"), fid)
        p = etree.SubElement(fn, w("p"))
        pp = etree.SubElement(p, w("pPr")); ps = etree.SubElement(pp, w("pStyle")); ps.set(w("val"), "FootnoteText")
        rref = etree.SubElement(p, w("r")); rpr = etree.SubElement(rref, w("rPr"))
        rs = etree.SubElement(rpr, w("rStyle")); rs.set(w("val"), "FootnoteReference")
        etree.SubElement(rref, w("footnoteRef"))
        rt = etree.SubElement(p, w("r")); t = etree.SubElement(rt, w("t")); t.text = " " + footnote_text
        t.set(XS, "preserve")
        # body: tracked reference run right after anchor_text
        for para in self._paras():
            for r in para.findall(w("r")):
                txt = self._rtext(r)
                if anchor_text in txt:
                    i = txt.find(anchor_text) + len(anchor_text); pre, suf = txt[:i], txt[i:]
                    refrun = etree.Element(w("r")); rp2 = etree.SubElement(refrun, w("rPr"))
                    rs2 = etree.SubElement(rp2, w("rStyle")); rs2.set(w("val"), "FootnoteReference")
                    fr = etree.SubElement(refrun, w("footnoteReference")); fr.set(w("id"), fid)
                    ins = etree.Element(w("ins"))
                    ins.set(w("id"), self._nid()); ins.set(w("author"), self.author); ins.set(w("date"), self.date)
                    ins.append(refrun)
                    repl = [self._mk_t(pre), ins]
                    if suf: repl.append(self._mk_t(suf))
                    idx = list(para).index(r); para.remove(r)
                    for k, e in enumerate(repl): para.insert(idx + k, e)
                    self.log.append(f"OK   {label or 'footnote'} (id {fid})"); return True
        # roll back the footnotes.xml entry if anchor not found
        ft.remove(fn)
        self.log.append(f"MISS {label or 'footnote'}  (anchor «{anchor_text[:40]}»)"); return False

    # ---------- save ----------
    def save(self):
        """Write every parsed tree back to disk."""
        for fn, tree in self._trees.items():
            tree.write(str(self.root / "word" / fn), xml_declaration=True, encoding="UTF-8", standalone=True)

    def report(self):
        ok = sum(1 for l in self.log if l.startswith("OK"))
        miss = sum(1 for l in self.log if l.startswith("MISS"))
        print("\n".join(self.log))
        print(f"\n== {ok} applied, {miss} missed ==")
        return miss == 0
