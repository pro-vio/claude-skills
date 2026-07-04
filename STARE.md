# STARE — claude-skills (marketplace pro-vio/claude-skills)

*Ultima actualizare: 2026-07-04, sesiunea "chat dedicat skill-urilor".*

## Versiuni curente

| Plugin | Versiune | Ultimul commit |
|---|---|---|
| `zotero-citations` | 1.6.2 | `adc8204` — fix cache miss permanent pe atașamente legate |
| `scriere` | 1.3.0 | `7ca9431` — allowlist batch citire/validare docx |

## Ce s-a făcut azi (sesiune lungă, recap)

**zotero-citations** — cea mai mare parte a lucrului:
1. **v1.4.0–1.4.1**: `write_session` batch (un singur ciclu close/reopen Zotero pentru multe scrieri), rețetă legislație RO (cdep.ro), `zot.NOT_TRASHED` (interogările trebuie să excludă coșul explicit — descoperit real: 2 scan-uri "citite" erau deja în coș din iunie).
2. **v1.5.0**: overlay OCR invizibil peste scan-uri (RapidOCR + PyMuPDF `render_mode=3`) — **ask-first**, niciodată silențios; estimare timp/tokeni înainte de a întreba.
3. **v1.6.0**: cache de text extras din PDF, ca **notă-copil în Zotero** (nu fișier local — decizie explicită a userului: "voiam să fie toate într-un loc, nu împrăștiate prin proiecte"), keyed pe hash de conținut.
4. **v1.6.1**: fix bug real — batch de 81 scrieri într-un `write_session` pica 81/81 cu "database is locked" (a doua conexiune DB deschisă cât timp una era neconfirmată). Reparat: un singur cursor pe toată sesiunea.
5. **v1.6.2**: fix bug real #2 — atașamentele **legate** (linked file) au `storageHash` mereu `NULL`; scrierea brută a `None` în notă o făcea permanent "stale" (`"None" == None` → `False`). Fix: hash propriu (md5) ca rezervă. Reparate 13 note deja stricate (găsite într-un folder de coordonare a unei teze, scrise de altă sesiune care folosise deja skill-ul publicat).

Rezultat: 81 + 13 = 94 atașamente PDF din bibliotecă au acum cache de text funcțional, populat direct din conținutul deja bun din Zotero (căutarea pe disc a arătat că fișierele `.md`/`.txt` risipite prin proiecte nu aduceau nimic peste ce era deja în Zotero — unele chiar mai slabe, cu erori OCR).

**scriere**:
- v1.2.0 (mai devreme azi, sesiune anterioară): `add_comment` (comentarii ancorate pe paragraf) + `_paras()` pe `body.iter(w:p)` (prinde paragrafe din `w:sdt`/exporturi Google Docs).
- v1.3.0 (azi): `references/runtime-optimization.md` — allowlist batch pentru citire/validare docx (python, pandoc, pip install lxml — deja globale), regula rulare/conținut specifică (accept/reject-ul din Word e deja poarta de conținut).

## ⚠️ Lucru în desfășurare, NU al meu — nu suprascrie

`plugins/scriere/skills/scriere/scripts/docx_track.py` **diverge** între copia locală
(`~/.claude/skills/scriere/scripts/docx_track.py`, 641 linii) și marketplace (557 linii,
la v1.2.0). Copia locală a fost modificată azi la 20:28, de o **altă sesiune paralelă**
(probabil coordonarea tezelor — vezi `Documents/claude_2026_coordonare/`), neterminată.
**Nu propaga acest fișier până nu se confirmă că munca e gata** — verifică mtime din nou
înainte de orice `cp` batch spre marketplace.

## Lecții/bug-uri reale prinse din folosire (nu din recitire de cod)

Toate documentate și în memoria auto (`~/.claude/projects/.../memory/`):
- `feedback_zotero_batch_locking.md` — locking la scrieri batch
- `feedback_zotero_cache_linked_attachments.md` — storageHash NULL pe atașamente legate
- `feedback_pdf_text_cache_zotero.md` — motivația centralizării în Zotero
- `feedback_propagare_doar_fisiere_atinse.md` — verifică mtime înainte de a propaga batch

## Ce urmează (opțional, neprogramat)

- Propagarea `docx_track.py` când cealaltă sesiune termină (verifică mtime / întreabă userul).
- Eventual: extindere `additionalDirectories` în `~/.claude/settings.json` pentru foldere de
  proiect unde se lucrează frecvent cu scriere (discutat, respins pentru acum — userul a ales
  doar documentarea, nu extinderea directoarelor).
