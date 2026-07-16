# STARE — claude-skills (marketplace pro-vio/claude-skills)

*Ultima actualizare: 2026-07-16 (a doua sesiune, runda 2) — toate deciziile pending executate: split Chelcea, 30 merge-uri same-PDF, OCR Public Goods, Denning→thesis.*

## HANDOFF 2026-07-16 — de unde continuă chatul nou

**Obiectiv curent:** lucrăm cu skill-ul `zotero-citations` și îl îmbunătățim. Task concret care-l exersează: iteme cu 2+ PDF pe My Library.

### EXECUTAT în sesiunea a doua (16.07, backup `zotero.sqlite.pre-split-glued-items.bak`)

Planul B+A aplicat într-un singur `write_session`, verificat cu `audit_library.py` după (0 orfane la toate verificările):
- **B:** cei 4 loseri redundanți (atașamente 671, 690, 962, 887 — 0 adnotări fiecare) la COȘ.
- **A:** itemul 10313 (titlu-gunoi japonez, autor fictiv „Bandile") SPART în 3 teze cu metadate citite din PDF, apoi la coș:
  - 14809 Walstrum, *Essays on Human Capital Investment*, PhD, Univ. of Illinois at Chicago, 2015 (att 10406, 109p);
  - 14810 Gaulke, *Essays on Enrollment and Persistence in Higher Education*, PhD, Univ. of Wisconsin–Madison, 2015 (att 10314, 138p, ProQuest 3718047);
  - 14811 Gonzalez, *Three Essays on the Economics of Education*, PhD, Columbia, 2015 (att 10496, 200p).
  - capitolul din 6047 → bookSection nou 14812: Curaj, Deca & Hâj, *Romanian Higher Education in 2009–2013…*, pp. 1–24, DOI 10.1007/978-3-319-08054-3_1 (att 6168); cartea 6047 păstrează att 6048 (3 adnotări).
  - Itemele noi filate în colecțiile părinților vechi (212 IV_article, 131 Mendeley); niciun duplicat pre-existent (verificat; „Three Essays on the Economics of *Higher* Education" = teza lui Xia, alt document).

### EXECUTAT în runda 2 (16.07 seara, backup `zotero.sqlite.pre-pending-batch-2.bak`)

Userul a răspuns pe puncte la lista pending; aplicat totul într-un singur `write_session`, audit după = 0 orfane:
- **Chelcea 341** — cele 2 scanuri erau capitole distincte (confirmate vizual): bookSection 14813 *Interviul* pp. 210–222 (scan 540) + 14814 *Analiza de conținut* pp. 442–470 (scan 531); cartea 341 rămâne (fără PDF).
- **Ordinele 553/558** — păstrată doar versiunea completă (126p/98p); copiile scurte 554/559 la coș.
- **Denning 10397** — retipat `thesis`, University of Texas at Austin (confirmat pe CV-ul lui de la UT Austin), pages→numPages.
- **Grupurile same-PDF (fost „39", recalculat 36 fără trash)** — verificate una câte una pe conținut (pag. 1 + metadate): **30 merge-uri** (32 iteme contopite, `dc:replaces` pe master → total 415 relații; metadate îmbogățite: DOI-uri de capitol, editorii reali la Handbook Admin Data, cartea Miroiu&Cerkez 1363 reparată); **6 atașamente greșit-filate** la coș (1274 Welch, 1346 Dragoș, 1358 Oxford Handbook, 1361 Etemadi, 1363, 8298 Rauhvargers — fișierul aparținea altui item, bytes identice verificate); DOI-uri copiate greșit scoase de pe 13154 și 8300. Colaps post-merge: 32 copii byte-identice la coș.
- **OCR Public Goods (item 21)** — overlay RapidOCR pe scanul 6532 (17p, 1263 blocuri, text invizibil; backup-ul scanului original în scratchpad); scanul cu 15 adnotări e acum keeper căutabil; copia text 23 la coș. Cache-ul text NU avea OCR pe scanuri (doar pe copia text) — verificat la cererea userului.
- **Lăsate deliberat:** item **92** Legea 153/2011 — ambele copii au adnotări (12 pe originalul 2011, 1 pe forma consolidată 2023 = alte texte legale, nu duplicate); item **6110** Differentiation Theory — AMBELE copii sunt scanuri 519p adnotate (3/5 adn), OCR ar dura ore → userul a zis „lasă așa"; item **507** Scientific Management — rivali adnotați (explicat userului, decizie amânată); **C** (122, 341→rezolvat, 553/558→rezolvat, 7722) în forma decisă.
- **Fantomele 7 (fostele „PDF-uri adnotate absente") — REZOLVATE.** Indiciul userului: itemele-părinte aveau deja o copie vie a aceluiași document pe alt atașament. Verificat empiric că e aceeași redare (textul highlight-urilor extras din copia vie la coordonatele adnotării: 61/63 potriviri), apoi mutate DOAR adnotările lipsă (dedup pe semnătura bbox): 71 mutate, 113 erau deja pe copiile vii (recuperarea „+316" din migrare); fantomele la coș. **Fantome rămase: 0** (backup `pre-phantom7-annotations`).
- Git: `.gitignore` completat (date personale excluse: library.bib, extract/, mendeley-indexeddb-raw/, .claude/); comise scripturile migrării (`b2a7642`).

*Context istoric (deciziile de dinaintea rundei 2):*

**Skill ÎMBUNĂTĂȚIT (Pista B, gata + validat pe biblioteca reală):**
- `scripts/audit_library.py` — health-check read-only (integritate, **fantome linkMode**, PDF-uri duble clasificate text/scan, metadate). `--json findings.json` alimentează reconcilierea.
- `scripts/reconcile_attachments.py` — colapsare cu prioritate editabil/OCR, NU pierde adnotări; garda „paginație divergentă (>1p) = alt document"; scan adnotat → candidat OCR (nu la coș); fantome-cu-adnotări păstrate.
- `references/zotero-schema.md` — gotcha „Phantom attachments" (imported_file fără hash/folder = cauza „Cannot change attachment linkMode") + rețeta reconciliere.
- `SKILL.md` — secțiune „library audit & duplicate-attachment reconciliation" + 2 scripturi în resurse.
- Bug reparat în reconcile: raporta len(phantoms) nu numărul real trimis la coș.

**APLICAT pe bibliotecă (Zotero închis, backup `zotero.sqlite.pre-reconcile-attachments.bak`):**
159 fantome + 15 copii redundante (aceeași paginație, 0 adnotări) → la COȘ. 7 fantome PĂSTRATE
(au adnotări sincronizate, fișier pe alt device — lasă-le să se descarce). Integritate 0 orfane.
**DE TESTAT DE USER:** redeschide Zotero + sync → eroarea „Cannot change attachment linkMode" ar trebui dispărută.

- **C. Păstrează AMBELE (nu-s duplicate)** — lăsate așa: 122 HCL 266/2016 (corp 4p + anexă 2p); 553 Ordin 6560/2012 (65p vs 126p mai completă); 558 Ordin 6129/2016 (61p vs 98p); 341 Metodologia (2 scanuri 29/13p); 7722 Charter UVT (2 scanuri 90/16p). La 553/558 opțional: păstrează doar versiunea mai completă.
- *Scanuri adnotate (candidat OCR, ask-first `ocr_overlay`):* item **21** Public Goods (scan att 6532, 15 adnotări) vs keeper text 23; item **6110** (scan 11348, 3 adn) vs keeper 6111. OCR pe scan → devine keeper editabil+adnotat.
- *Rivali text adnotați (decizie umană):* item **92** Legea 153/2011 (att 278 1adn / keeper 93 12adn); item **507** Scientific Management (att 13372 6adn / keeper 12409 5adn).

**Pasul următor propus:** OCR pe cele 2 scanuri adnotate (ask-first, pe rând), apoi decizia userului la cei 2 rivali; C rămâne cum e.

**Alte resturi vechi (neschimbate):** 6 PDF adnotate chiar absente (64 adn, listate — Granovetter cel mai valoros); colecțiile importului sub `Imported 7/15/2026...` (de promovat la rădăcină?); itemul Denning 10397 tipat journalArticle deși e teză; Mendeley încă instalat. Scripturi durabile în `Documents/claude-skills/mendeley-zotero-migration/` + skill-ul actualizat în `~/.claude/skills/zotero-citations/`.

---

*Sesiune anterioară: 2026-07-15, "migrare Mendeley→Zotero" — varianta A, import oficial.*

## Versiuni curente

| Plugin | Versiune | Ultimul commit |
|---|---|---|
| `zotero-citations` | 1.7.0 | `9e3e4f6` — `audit_library.py` + `reconcile_attachments.py`, gotcha fantome + rețeta de recuperare a adnotărilor |
| `scriere` | 1.3.0 | `7ca9431` — allowlist batch citire/validare docx |
| `factsheet-teza` | — (skill personal, NU publicat în marketplace) | doar în `~/.claude/skills/factsheet-teza` |
| `stil-proteasa` | — (skill personal, NU publicat în marketplace) | doar în `~/.claude/skills/stil-proteasa`; din 16.07 două registre pe limbă (EN Proteasa & Andreescu / RO Miroiu teorie politică) |

## Sesiunea 2026-07-15 — varianta A: import oficial Zotero + consolidare adnotări (PAUZĂ AICI)

Continuare directă a sesiunii 07-14. Userul a întrebat dacă nu cumva are toate PDF-urile local
(credea că setase Mendeley „download all"). **Verificat: nu.** Doar 373–423 fizic în `userfiles`
(1,19 GB), exact cele deschise vreodată (MRM descarcă lazy, la deschidere; date 2023→2026);
**1832 existau doar în cloud**. Fără vechi Mendeley Desktop, fără drive J:.

**Varianta 2 (token API din aplicație) — ABANDONATĂ, propunere proastă a mea.** Extragerea tokenului
de sesiune din token store-ul aplicației = extragere de credențiale; stratul de siguranță a blocat-o,
corect. Nu se ocolește cu alt tool. Documentat ca lecție.

**Varianta A aleasă și executată de user:** importatorul oficial Zotero (File → Import → Mendeley
online), userul s-a autentificat singur, a pus totul într-o colecție nouă. **NU s-a restaurat backup**
(importul pornise deja) — în schimb am șters chirurgical migrarea manuală, ceea ce a mers fiindcă
itemele mele și cele importate **nu se suprapuneau deloc** (0 comune).

Ce a adus importul (~2h, DB 115MB→338MB): **2197 iteme, 1893 PDF-uri din cloud, 3802 adnotări**,
113 colecții sub `Imported 7/15/2026` (ierarhia Mendeley completă).

1. **Șters migrarea manuală** (confirmat explicit de user, după ce clasificatorul a blocat prima
   încercare — scopul se lărgise față de „dă-i drumul"-ul inițial): 1817 iteme, 112 colecții,
   108 atașamente + foldere storage, 168 note, **1725 adnotări** (identificate pe `dateAdded`
   2026-07-14; cohorte verificate: 140 vechi ale userului = 45 proprii + 95 „Claude" din sesiuni
   anterioare / 1725 ale mele / 3802 ale importului). Rezultat: 0 rânduri orfane.
2. **Adnotările studenților — importul NU le aduce.** Doar pe ale userului (3505/3505). Cele 536 ale
   studenților lipseau integral. Extras `groupProfiles` → `profile_names.json` (32 profiluri → nume
   reale: Boboc, Borodachi, Pavlovschi, Ofiteru, Grădinaru, Deaconu, Zegoicea...). Inserate **493
   adnotări** (460 ale studenților + 33 ale userului ratate de import) cu `authorName` = numele
   studentului. **User a verificat vizual: numele apare.** Total adnotări acum: **4435** (555 atribuite).
3. **Două convenții ale importatorului, găsite prin dry-run (altfel dublam 2497 de adnotări):**
   - **caseta notei (type 2) e CENTRATĂ pe punctul Mendeley** `[x-11,y-11,x+11,y+11]`, nu ancorată cu
     colțul (măsurat: dx=dy=+11 pe 211/215 note). Migrarea mea de ieri avea notele decalate cu 11pt.
   - **highlight-urile multi-linie au casetele în altă ORDINE** decât `positions` din Mendeley →
     semnătura de dedup trebuie pe **bounding box peste toate casetele**, nu pe `rects[0]`.
   - importatorul păstrează **culoarea literală Mendeley** (`#faf4d1`), nu paleta Zotero (`#ffd400`).
   Convergență dry-run: 2960 → 1294 → 493. `annconv.py` reparat.
4. Legătura adnotare↔PDF se face pe **SHA1** (Mendeley `filehash` e sha1, nu md5) al conținutului.

**Stare Zotero acum: 2658 iteme (461 vechi ale userului + 2197 import), 127 colecții, 2476 atașamente
PDF, 4435 adnotări, 0 orfane.** Backup-uri `zotero.sqlite.pre-*.bak` pentru fiecare pas.

5. **DEDUP executat (confirmat de user).** Master = itemul VECHI al userului când grupul are unul —
   citările din Word/LO rețin cheia (userul scrie tot cu Zotero); copiile din import nu-s citate de
   nimic. Altfel master = copia din import cea mai bogată. **237 grupuri, 286 iteme contopite
   (2658 → 2372)**; mutate pe masteri 248 PDF-uri, 18 note, 394 filări de colecții, 476 taguri.
   Apoi **265 atașamente PDF duplicate** (conținut identic, în același item) eliminate, păstrat cel
   cu adnotări (216 iteme afectate, 4 adnotări mutate).
   - **⚠️ GARDA CARE A SALVAT TOTUL — un identificator SINGUR nu grupează niciodată.** Prima versiune
     (grupare pe DOI) a produs un grup de **18 cărți diferite** (Kahneman + Acemoglu + „Psihologia
     poporului român"...) din cauza DOI-ului fals `10.1017/CBO9781107415324.004`, pe care Mendeley îl
     lipește pe zeci de înregistrări fără legătură. Fix: cheia cere ȘI titlul; unde titlul e singura
     dovadă, cere ȘI autorul („Selective Incentives" există și de della Porta, și de Oliver). Plus o
     gardă de compatibilitate a autorului (egal sau substring — tolerează „European Commission" vs
     „European Commission, Directorate-General...") → **14 grupuri lăsate neatinse pentru verificare
     manuală de user** (unele par capitole unde un record are editorul cărții (Curaj) iar altul autorul
     capitolului (Proteasa, Miroiu, Vlăsceanu) — de decis de user, nu de ghicit).
6. **Reparate două probleme prinse la verificare:** (a) **38 din cele 461 iteme vechi au dispărut** —
   biblioteca veche avea duplicate interne, deci un „original" a devenit perdant; adăugate **286
   relații `dc:replaces`** (`itemRelations` predicateID=1, object=`http://zotero.org/users/1055731/items/<KEY>`,
   chei luate din backup) ca citările vechi să se redirecționeze spre master — exact ce face merge-ul
   nativ Zotero; (b) 13 note rămase orfane când atașamentul-părinte a fost colapsat → reatașate la item.
7. **Recuperare 316 adnotări în plus:** cele 42 PDF-uri „neaduse de import" erau în mare parte o iluzie —
   `filehash` din Mendeley e sha1-ul copiei din **cloud**, iar copia locală/importată are alt sha1
   (36/42). Remapate pe sha1-ul REAL → +316 adnotări (128 Irina Pavel, 111 Ofiteru, 35 Boboc...).

8. **Cele 14 grupuri „cu autori diferiți" — verificate una câte una: 11 erau duplicate reale.**
   Cauza falsului pozitiv era a mea: garda compara **primul creator**, care la un capitol de carte e
   adesea **editorul volumului**, nu autorul capitolului („Curaj vs Proteasa", „della Porta vs Oliver"
   — della Porta e editorul enciclopediei). Contopite 13 iteme (master = itemul vechi), +22 adnotări
   pe *IAD Framework*, +18 pe *Unraveled Practices*. **Lasate 3:** book-vs-chapter (9793/9797),
   2 înregistrări-placeholder, și Rauhvargers-vs-Stergiou (DOI mis-atribuit).
9. **„Șterge cele două înregistrări-gunoi" — una NU era gunoi.** Regula „uită-te la țintă înainte de
   ștergere" a salvat conținut: 10387 chiar era copie redundantă (articolul Stinebrickner exista corect
   pe 10284) → șters; **10393 ascundea teza lui Edward C. See, 175 pagini**, unicat în bibliotecă →
   reparat, nu șters. Iar „autorul greșit de la 10397" pe care îl semnalasem **nu exista**: itemul
   Denning era corect (abstractul lui despre taxele din Texas), **fișierul** era străin (teza lui Xing
   Xia) → item nou pentru Xia, Denning neatins. Corectat și autorul inversat pe 1142 (Coșciug, Anatolie).
10. **AUDIT COMPLET + reparații** (`audit_full.py`): 10+4 relații `dc:replaces` orfane (apar când un
    item e master într-un grup și perdant în altul → **redirecționate către masterul final**, nu șterse,
    ca să nu se rupă lanțul de citări); **DOI-ul fals Mendeley scos de pe 16 iteme + ISBN-ul fals
    `978-85-7811-079-6` de pe 16** (un identificator care apare pe 12 lucrări diferite nu e al niciuneia
    — ar fi produs DOI greșit în citări); încă **2 titluri-placeholder care ascundeau documente reale**
    reparate (9106 = *The Politics of Ethnicity in Central Europe*, ed. Karl Cordell, Macmillan 2000;
    10801 = *Better Regulation "Toolbox"*, Comisia Europeană 2017, 540 pag.); **85 grupuri same-PDF
    contopite** (87 iteme) din 124 — restul de 39 semnalate userului, nu atinse (fișier identic ≠
    duplicat: poate fi atașament greșit, ca la Denning/Xia).

**STARE FINALĂ: 2272 iteme, 127 colecții, 2110 atașamente PDF, 4741 adnotări (847 atribuite nominal),
387 dc:replaces, 0 orfane la toate cele 15 verificări, 0 fișiere lipsă de pe disc, 0 titluri-placeholder,
0 DOI-uri false.** Backup `zotero.sqlite.pre-*.bak` per pas. Artefacte: `mendeley-zotero-migration/`
(90 scripturi).

**RĂMÂNE (mic, toate raportate userului):**
- **6 PDF-uri adnotate chiar absente** (fără copie locală, neaduse de import) → 64 adnotări. Cel mai
  valoros: **Granovetter (1973), The Strength of Weak Ties** (25 adnotări, 13 ale userului).
- **39 grupuri same-PDF** cu titlu/autor incompatibile — de decis de user.
- **124 iteme fără autor** (multe legitime: rapoarte, legislație).
- 78 iteme în coșul Zotero; colecțiile importului sub `Imported 7/15/2026...` (de promovat la rădăcină?);
  itemul Denning (10397) tipat `journalArticle` deși e teză; Mendeley încă instalat.

## Sesiunea 2026-07-14 — migrare Mendeley→Zotero (faza 1, ÎNLOCUITĂ de importul oficial)

Cerere: tranziție totală de pe Mendeley pe Zotero, inclusiv DB, cu păstrarea adnotărilor. Sursa NU e
cloud-ul: baza locală Mendeley Reference Manager e o replică IndexedDB completă
(`%APPDATA%\Mendeley Reference Manager\IndexedDB\file__0.indexeddb.leveldb` + `.blob`; PDF-uri în
`userfiles\<fileId>.pdf`). Extras cu `dfindexeddb`+`cramjam` (shim-uri snappy/zstd) + `blink.V8ScriptValueDecoder`
pe blob-uri externe → `extract/mendeley_local.json`. Detalii metodă + inventar în memoria auto
`project_mendeley_zotero_migrare.md`.

**Executat integral (fazele 1–5 + curățenii), toate prin `zot.write_session` (backup automat, Zotero
închis), verificat pe DB după fiecare pas:**
1. Reconciliere: 2584 docs active (excluse 241 din trash) vs 461 iteme Zotero → 378 potrivite
   (DOI/titlu+an/titlu/ISBN), 1929 iteme NOI unice (după colapsarea a 277 duplicate interne Mendeley).
2. 112 foldere Mendeley recreate ca **colecții** cu ierarhia întreagă (faza 2); helper `add_collection`.
3. 1929 **iteme** create cu mapare tip+câmp Mendeley→Zotero (`build_spec.py` + `valid_fields.json`),
   + note de lectură + taguri, filate în colecții (faza 3).
4. 113 **PDF-uri locale** atașate (91 iteme noi + 19 potrivite fără PDF; conservator — nu atașez dacă
   itemul are deja un PDF), titluri lizibile din `file_name` (faza 4/4b).
5. **Adnotări native**: 1554 (faza5) + 171 union din duplicate interne (faza5b) = 1725 pe 155 PDF-uri
   locale (byte-identice md5 cu storage Zotero). Highlight → text extras din PDF pe coordonatele Mendeley
   (PyMuPDF; Mendeley bottom-left → Zotero), sticky → notă cu comentariul. `annconv.py`.
   **User a verificat vizual: highlights cad corect pe text.** 11 highlight fără text = PDF scanate.
6. **Grupuri Mendeley excluse** (cerință user): 3 grupuri „coordonare_2023-24/2025/2026" (owner, cu
   studenți). Colecțiile de grup NU fuseseră create. 112 iteme PUR de grup ȘTERSE hard (117 rânduri +
   5 fișiere storage); păstrate 128 mixte (au și membru personal) + 129 potrivite pe iteme personale.

Stare atinsă atunci: 2278 iteme, 126 colecții, 691 atașamente PDF, 1865 adnotări, 330 note, 0 orfane.
**⚠️ ȘTEARSĂ INTEGRAL pe 07-15** (vezi secțiunea de mai sus) — limitată la cele 373 PDF-uri locale, deci
înlocuită de importul oficial Zotero care aduce tot din cloud. Nu o reface; codul rămâne util ca
referință (mapare tip+câmp `build_spec.py`, `migrate.py`), iar `annconv.py` a fost reparat de atunci.

**Decizii user pe parcurs (ÎNCĂ VALABILE):** fără trash; **faza 6 (pin citekeys BBT) ABANDONATĂ**
(userul scrie tot cu Zotero direct, nu are manuscrise pe cheile Mendeley — NU re-propune);
grupurile pot rămâne cât timp nu dublează; adnotările userului ȘI ale studenților se păstrează ambele,
**cu condiția să fie diferențiate** (rezolvat prin `authorName`).

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
