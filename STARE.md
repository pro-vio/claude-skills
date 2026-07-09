# STARE — claude-skills (marketplace pro-vio/claude-skills)

*Ultima actualizare: 2026-07-08, sesiunea "chat dedicat skill-urilor" (continuare).*

## Versiuni curente

| Plugin | Versiune | Ultimul commit |
|---|---|---|
| `zotero-citations` | 1.6.6 | `b0434cf` — `prefetch_collection.py`, cache PDF în lot pe o colecție |
| `scriere` | 1.3.0 | `7ca9431` — allowlist batch citire/validare docx |
| `factsheet-teza` | — (skill personal, NU publicat în marketplace) | doar în `~/.claude/skills/factsheet-teza` |

## Sesiunea 2026-07-08 (recap)

Monitorizat o sesiune paralelă care folosea skill-ul personal `factsheet-teza` (generare fișe de
pre-susținere pentru studenți, nu publicat în marketplace) — 319 prompturi noi de permisiune,
din care ~96 direct legate de fact sheet.

1. **Investigație "database is locked" — găsită cauza reală**: nu regresia de conexiune dublă
   deja reparată (v1.6.1), ci Zotero redeschis fizic în timpul rulării unui `write_session`
   (verifică o singură dată, la intrare). Vezi `feedback_zotero_locked_reopened_mid_run.md`.
2. **Fix greșit, corectat cu date reale**: am presupus că prompturile repetate pe scratchpad
   erau din cauza formei căii (scurtă Windows `VIOREL~1` / POSIX `/c/Users/...`) și am adăugat
   variante în `additionalDirectories` — verificat empiric ORE mai târziu că NU a funcționat.
   A doua descoperire: regulile `PowerShell(... *)` cu wildcard nu se potrivesc DELOC (proiectul
   avea deja 1173 reguli exacte acumulate în `settings.local.json`, dovadă indirectă). Fix real:
   am eliminat variabilitatea din comanda `verify_pdf.ps1` (argumente `-Src`/`-Out` implicite
   fixe într-un folder `_stage/`, apelant face `cp` întâi) — testat efectiv prin Word COM, nu
   doar citit codul. Detalii + lecția „nu insista pe aceeași strategie" în
   `feedback_forma_cale_scurta_posix.md`.
3. **Corectare de conținut**: nu insera niciodată citate din referatul coordonatorului în
   fact sheet-ul unui student (linie roșie, reacție dură la Grădinaru v2) — întărit explicit în
   `factsheet-teza/SKILL.md`. Vezi `feedback_fara_citate_referat_in_factsheet.md`.
4. **Verificat, nu doar presupus**: `factsheet-teza` deja compune corect cu `scriere` (deschide
   skill-ul separat peste docx-ul curat pentru track-changes/comentarii, nu reinventează nimic) —
   nimic de consolidat acolo.

## Sesiunea 2026-07-05 (recap)

Fir principal: monitorizarea prompturilor de permisiune agregată pe TOATE sesiunile/proiectele
(nu doar cea curentă — corectare explicită a userului, vezi `feedback_monitor_agregare_toate_sesiuni.md`),
apoi o cerere de "skill de evaluare" din tiparul de coordonare a tezelor 2026, restrânsă de user
la un scop mult mai mic: elimină click-urile de permisiune la verificarea surselor unei teze.

1. **v1.6.3–1.6.5**: `log_perm.py` loghează `session_id` (provenance opțională, nu filtru implicit);
   corectat de la "filtrează pe sesiune" la "agregă pe toate" (v1.6.4); documentate două bug-uri de
   *formă* a comenzilor care rup potrivirea de permisiuni — heredoc Python în lanțuri `&&` (54/106
   prompturi) și `\|` scăpat într-un pattern grep citat (~12/106) — fix la formă, nu regulă nouă de
   allowlist (v1.6.5).
2. `~/.claude/settings.json`: adăugate `Temp\claude` (friction Read pe scratchpad, 25/120 prompturi)
   și `Documents\claude_2026_coordonare` (foldere de studenți) în `additionalDirectories`.
3. **Scope-narrowing**: cererea inițială "construiește un skill de evaluare din chat-ul Desiree" a
   fost redusă de user la "să nu mai dau click pt fiecare sursă" — verdictul de notare/comentariile
   rămân judecăți per-teză (nu se automatizează). Plan aprobat în Plan Mode, executat integral.
4. **v1.6.6**: `prefetch_collection.py` — populează cache-ul de text pentru toate atașamentele unei
   colecții Zotero într-un singur `write_session`, ca verificarea ulterioară a citatelor unei teze
   să nu mai ceară niciun prompt nou. Bug real întâlnit la testare: "database is locked" pe toate
   cele 12 atașamente, deși codul (un singur cursor) era deja corect — cauza reală era Zotero
   redeschis fizic în timpul rulării (proces separat, nu conexiune SQLite dublă în script). Fix
   operațional (închide Zotero, rulează până la capăt, redeschide după), documentat în
   `references/pdf-text-cache.md` și `feedback_zotero_locked_reopened_mid_run.md`.

## Sesiunea 2026-07-04 (recap, arhivat)

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
- `feedback_zotero_batch_locking.md` — locking la scrieri batch (conexiune dublă în script)
- `feedback_zotero_cache_linked_attachments.md` — storageHash NULL pe atașamente legate
- `feedback_pdf_text_cache_zotero.md` — motivația centralizării în Zotero
- `feedback_propagare_doar_fisiere_atinse.md` — verifică mtime înainte de a propaga batch
- `feedback_monitor_agregare_toate_sesiuni.md` — monitorul agregă, nu filtrează pe sesiune
- `feedback_forma_python_encoding.md` — niciodată heredoc Python, apel direct `python script.py`
- `feedback_grep_escaped_pipe_permisiuni.md` — `\|` scăpat în grep citat rupe potrivirea
- `feedback_scope_narrowing_friction_vs_skill.md` — nu formaliza judecăți per-teză ca skill
- `feedback_zotero_locked_reopened_mid_run.md` — "database is locked" poate fi Zotero redeschis
  fizic în timpul rulării, nu doar bugul de conexiune dublă din script

## Ce urmează (opțional, neprogramat)

- Propagarea `docx_track.py` când cealaltă sesiune termină (verifică mtime / întreabă userul).
- Eventual: extindere `additionalDirectories` în `~/.claude/settings.json` pentru foldere de
  proiect unde se lucrează frecvent cu scriere (discutat, respins pentru acum — userul a ales
  doar documentarea, nu extinderea directoarelor).
