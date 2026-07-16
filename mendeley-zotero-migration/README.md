# Migrare Mendeley → Zotero (sesiunea 2026-07-14)

Artefacte durabile ale migrării integrale a bibliotecii personale Mendeley în Zotero.
Recap complet în `../STARE.md` și în memoria auto `project_mendeley_zotero_migrare.md`.

## Ce e aici

- **`scripts/`** — toate scripturile de extragere, reconciliere și scriere (fazele 1–5 + curățenii).
- **`extract/`** — datele extrase și hărțile intermediare (JSON). Cel mai important:
  - `mendeley_local.json` (16 MB) — **întreaga bază Mendeley parsată**: 2825 documente, 112 foldere,
    2218 fișiere, **4731 adnotări** (inclusiv cele ~2987 de pe PDF-uri care există doar în cloud
    Mendeley), note, taguri, grupuri. Aceasta e copia care contează dacă dezinstalezi Mendeley.
  - `mid_to_zid.json` — mapare UUID document Mendeley → itemID Zotero (pt re-rulări).
  - `reconcile.json`, `create_plan.json`, `folder_map.json`, `attach_plan.json`, `group_cleanup.json`,
    `storage_md5.json`, `valid_fields.json` — hărți intermediare.
- **`shims/`** — `snappy.py` / `zstd.py` peste `cramjam` (Python 3.14 nu are wheels native).
- **`mendeley-indexeddb-raw/`** (49 MB) — **copie brută a bazei locale Mendeley** (LevelDB + blob-uri
  externe V8-serializate). Sursa completă din care s-a derivat totul; permite re-extragere cu altă logică.

## Cum s-a extras (dacă trebuie refăcut)

```
pip install --no-deps dfindexeddb ; pip install cramjam
# cu shims/ în PYTHONPATH:
#   dfindexeddb.indexeddb.chromium.record.FolderReader pe leveldb
#   blink.V8ScriptValueDecoder.FromBytes pe blob-urile externe -> string JSON
```
Vezi `scripts/extract_all2.py`.

## Ce a rămas de făcut

Toate itemele/colecțiile/atașamentele/adnotările **locale** sunt deja în Zotero (comise, cu backup-uri
`~/Zotero/zotero.sqlite.pre-mendeley-*.bak`). Rămân **~1832 PDF-uri care există doar în cloud Mendeley**
și cele ~2987 adnotări de pe ele. Pentru a le aduce:
1. Forțează Mendeley să descarce toate fișierele local (în `%APPDATA%\Mendeley Reference Manager\userfiles`),
2. Re-rulează `scripts/phase4_plan.py` + `phase4.py` (atașare) și `phase5.py` + `phase5b.py` (adnotări) —
   mașinăria e idempotentă (sare peste ce e deja atașat/adnotat).

Motorul de scriere e `zotero-citations/scripts/zot.py` (`write_session` = backup + Zotero-închis + commit);
`scripts/migrate.py` adaugă `add_collection` / `add_tags`; `scripts/annconv.py` = conversia adnotărilor.
