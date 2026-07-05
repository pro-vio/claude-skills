# Runtime optimization: frictionless Zotero process control

Tested and validated 2026-07-03 (Windows 11, Zotero 7, Claude Code desktop). Goal: **one
permission accept from the user at setup, zero prompts afterwards** for everything that is
*running software* — while every *content* decision (what enters an analysis corpus, what gets
cited) stays with the user.

## The rulare / conținut split (design principle)

| Layer | Examples | Who decides |
|---|---|---|
| **Rulare** (running) | start/stop/restart Zotero, ping the local API, run skill scripts, pandoc renders | Claude, autonomously, after a one-time allowlist accept |
| **Conținut** (content) | corpus inclusion when a hit doesn't match the search spec 100%, citing, editing items | the user, always |

## One-time allowlist (user-level `~/.claude/settings.json`)

Rules are **prefix-matched**, so the skill must always issue commands in these exact canonical
shapes. Adjust paths per machine.

```json
"permissions": {
  "allow": [
    "Bash(curl -s http://127.0.0.1:23119/*)",
    "Bash(curl -s \"http://127.0.0.1:23119/*)",
    "Bash(curl -s http://localhost:23119/*)",
    "Bash(curl -s \"http://localhost:23119/*)",
    "Bash(tasklist *)",
    "Bash(python *)",
    "Bash(pandoc *)",
    "Bash(grep *)", "Bash(ls *)", "Bash(ls)", "Bash(head *)", "Bash(tail *)",
    "Bash(wc *)", "Bash(find *)", "Bash(sed -n *)", "Bash(diff *)",
    "Bash(echo *)", "Bash(cd *)", "Bash(mkdir *)", "Bash(cp *)",
    "Bash(git status*)", "Bash(git log*)", "Bash(git diff*)", "Bash(git remote*)", "Bash(git rev-parse*)",
    "WebSearch",
    "WebFetch",
    "PowerShell(Start-Process \"C:\\Program Files\\Zotero\\zotero.exe\")",
    "PowerShell(taskkill /IM zotero.exe)",
    "PowerShell(tasklist *)"
  ],
  "additionalDirectories": [
    "<the project folders the analysis reads/writes>",
    "C:\\Users\\<user>\\Zotero"
  ]
}
```

**v2 lessons (first live run generated a pile of prompts the v1 list missed):**
- Rules are **literal prefix matches**: `curl -s "http://…"` (quoted URL) does NOT match a rule
  written for the unquoted form — allow both spellings, or standardize and never deviate.
- **Pipes and `&&` chains prompt if ANY segment is unlisted** (`curl … | python -c …` needs
  `python` allowed too). Narrow per-script python rules don't survive real work (inline `-c`,
  scratchpad scripts) — either allow `Bash(python *)` or accept prompts.
- Read-only utilities (`grep`, `ls`, `head`, `tail`, `wc`, `find`, `sed -n`, `diff`, read-only
  `git`) each need their own rule.
- `Edit`/`Write` outside the session's project dir prompt — list the working folders (and the
  Zotero data dir, for DB backup/restore) in `permissions.additionalDirectories`.
- Deliberately NOT allowlisted: `rm`, `taskkill /F`, bare `sed`/`cat` (can write via `-i`/redirect),
  `git commit/push` — destructive or publishing actions stay behind a prompt.

Deliberate safety boundary: **force kill is NOT allowlisted.** `taskkill /F /IM zotero.exe` can
corrupt `zotero.sqlite`, so it still requires an explicit user accept. Same philosophy for any
direct DB write: graceful close → backup `zotero.sqlite` → write → restart → verify (see §F of
SKILL.md and `zotero-schema.md`).

**v3 lessons (aggregated accept-monitor pass across all concurrent sessions, 2026-07-05):** these
are command-**shape** problems, not missing rules — the base commands were already allowlisted,
so don't add new entries for them; fix the shape instead, in every session, not just one.

- **Never invoke Python via heredoc** (`python - <<'EOF' ... EOF`), even inside a `cd X && ...`
  chain. This was **half of all prompts in one day's aggregate log (54/106)** — `cd`, `pandoc`,
  and `python` are each individually allowlisted, but the permission matcher splits a compound
  command on `&&` and checks each segment; the heredoc form doesn't match `Bash(python *)` cleanly
  inside a chain the way a plain `python script.py` does. Fix: write the script to a scratch
  `.py` file first (via the Write tool), then a single simple `cd X && python script.py` — no
  heredoc, ever. See `feedback_forma_python_encoding` in project memory for the fuller writeup.
- **A literal `\|` (regex alternation) inside a quoted grep pattern** — including inside a real
  `ls … | grep "…\|…"` pipe — gets misread by the same segment-splitter as an additional shell
  pipe boundary, producing a fake trailing "segment" that matches nothing. ~12/106 prompts in the
  same aggregate pass. Fix: split into two separate `grep` calls instead of one pattern with `\|`,
  when running through the Bash tool. Low stakes (grep is read-only) — skip the workaround if a
  single occasional prompt doesn't bother you.

## Canonical commands (always these shapes, or the prefix rules won't match)

| Action | Command |
|---|---|
| Start Zotero | `Start-Process "C:\Program Files\Zotero\zotero.exe"` (PowerShell) |
| Graceful stop | `taskkill /IM zotero.exe` (PowerShell; **never** `/F` unprompted) |
| Is it running? | `tasklist //FI "IMAGENAME eq zotero.exe"` (Bash) |
| Wait for API after start | `curl -s http://127.0.0.1:23119/connector/ping --retry 15 --retry-delay 2 --retry-all-errors -o /dev/null -w "HTTP %{http_code}\n"` |
| Read library | `curl -s "http://127.0.0.1:23119/api/users/<userID>/items?..."` |

Notes from testing:
- Cold start to API-up took well under the 15×2 s retry budget.
- Graceful `taskkill` (no `/F`) closed the main process cleanly; one child PID reported
  "can only be terminated forcefully" but exited with its parent — **verify with `tasklist`
  instead of escalating to `/F`.**

## DB-write protocol (lessons from the live run, 2026-07-03)

Three failure modes surfaced during the first real corpus-ingestion run (8 statutes, 8 PDFs,
16 highlights, 17 notes). All three are now part of the protocol:

1. **Shutdown race — the expensive one.** After a graceful `taskkill /IM zotero.exe`, a residual
   Zotero process can flush its own state to `zotero.sqlite` *after* your write, silently
   discarding it (one UPDATE pass was lost this way). Protocol: poll until **all** `zotero.exe`
   processes are gone **and** no `zotero.sqlite-journal` / `-wal` file remains, wait a settle
   beat, write, **re-read from disk to verify the commit landed**, and only then restart Zotero.
2. **Notes: write plain text, not HTML.** Note HTML written directly to `itemNotes` is
   escaped/sanitized at the next Zotero startup (wrapped in `zotero-note znv1`, tags shown as
   literals). Store plain text with blank-line paragraph breaks — Zotero wraps it into proper
   `<p>` paragraphs itself and the result is stable across restarts.
3. **The local API does not list annotations.** `GET /api/users/<uid>/items/<attKey>/children`
   omits annotation items, so a zero result does NOT mean the highlights failed. Verify in the DB
   (`itemAnnotations` joined to `items.dateAdded`) or visually in the Zotero reader.

### One close/reopen per task — batch every write (the expensive-cycle lesson, 2026-07-04)

A single graceful close + restart costs **~2–4 min** (backup, poll-until-quiescent, the API-ping
budget). A run that inserted 10 references + a statute took **three** such cycles (~10 min of pure
protocol) because it closed → wrote → reopened → *then* read a collection key → had to close again.
The fix is ordering + batching, now encapsulated in `zot.write_session` (see `zotero-schema.md`):

- **Resolve everything you can while Zotero is OPEN, before the first close.** Collection ids
  (`zot.find_collection`, read-only), csljson lookups, which items already exist — all read live.
- **Then ONE `write_session`** covering every insert/edit/attach/filing for the task. It does
  wait-until-quiescent → backup → write → verify-on-disk internally. Never close→write→reopen→
  read→close→write; that is two cycles doing one job.
- **Pure creation doesn't need a close at all:** `POST /connector/saveItems` (Zotero open, HTTP
  201). Use the closed `write_session` only when the batch also edits existing items, attaches
  PDFs, or moves things — operations the API refuses.
- **Downloading source text** (statute PDFs, etc.) is orthogonal to the write cycle — do it up
  front, before closing Zotero, so the closed window stays as short as possible. For RO
  legislation see `references/ro-legislation-fetch.md` (cdep.ro works; just.ro/paywalls don't).

## Accept monitor — one optimization proposal per iteration

Allowlists decay: real work invents command shapes the rules don't match (see v2 lessons). So the
skill ships a **permission-prompt monitor** and a per-iteration review ritual.

**Wiring (one-time, per machine)** — `scripts/log_perm.py` logs every permission prompt (= every
accept the user is asked for) to `~/.claude/perm-requests.jsonl`. Hook it in
`~/.claude/settings.json`:

```json
"hooks": {
  "PermissionRequest": [{"hooks": [{"type": "command", "async": true, "timeout": 10,
    "command": "python \"C:\\Users\\<user>\\.claude\\skills\\zotero-citations\\scripts\\log_perm.py\" PermissionRequest"}]}],
  "PermissionDenied": [{"hooks": [{"type": "command", "async": true, "timeout": 10,
    "command": "python \"C:\\Users\\<user>\\.claude\\skills\\zotero-citations\\scripts\\log_perm.py\" PermissionDenied"}]}]
}
```

The hook only observes (no stdout → cannot alter the permission decision; `async` → never delays
the prompt). `PermissionDenied` entries mark commands the user REFUSED — never propose allowlisting
those.

**The log is machine-wide by design.** The hook fires once per Claude Code *process*, so
`~/.claude/perm-requests.jsonl` interleaves every concurrent session — and that's the point when
the same person runs the same skills across many projects: one shared log means one place to spot
a recurring prompt and fix it everywhere at once, instead of re-discovering the same missing rule
project by project. **Default to aggregating across all sessions**, not filtering to one.

Each entry still carries a `session` field (last 8 chars of the hook's `session_id`) — not for
excluding other sessions, but as optional provenance when it's useful to know *where* a pattern
came from (e.g. "this Bash shape shows up in 3 different projects → allowlist it globally" vs.
"only ever this one project → maybe that project's own `.claude/settings.json` is the right
place"). Only filter to a single `session` value when someone explicitly asks about one specific
project's prompts in isolation — that's the exception, not the default read of the log.

**Ritual (end of every iteration, or when the user asks "de ce am dat atâtea accept-uri?"):**

1. Read `~/.claude/perm-requests.jsonl` in full; keep entries newer than the last review, **across
   all sessions** (don't filter by `session` unless the user specifically wants one project isolated).
2. Cluster them by command class (same executable + same shape), separating denied ones out.
3. For each accepted cluster propose EXACTLY ONE fix — an allowlist rule, a command-shape
   standardization (so an existing prefix rule matches), or an `additionalDirectories` entry.
   Never propose rules crossing the safety boundaries (`rm`, `taskkill /F`, bare `sed`/`cat`,
   `git commit/push`).
4. The user approves per proposal → apply to `~/.claude/settings.json`.
5. Rotate: append the reviewed entries to `~/.claude/perm-requests.reviewed.jsonl`, truncate the
   live log. Target: next iteration runs with zero accepts outside the safety boundaries.

## Acceptance test (re-run after any change to the rules or on a new machine)

A full cycle that must complete with **zero permission prompts**:

1. `tasklist` → note whether Zotero is running.
2. If closed: start it → ping with retries → expect `HTTP 200`.
3. Graceful stop → `tasklist` must show no `zotero.exe` (do NOT force-kill if a child PID
   complains; re-check first).
4. Start again → ping `HTTP 200` → API read (`/api/users/<userID>/items?limit=1`) `HTTP 200`.

Result 2026-07-03: PASS — all four steps, no prompts, no force kill needed.

## Portability checklist (propagating to another machine)

- [ ] Find `zotero.exe` path (`C:\Program Files\Zotero\` typical on Windows) and fix it in the rules.
- [ ] Replace `<user>` in the script-path rules.
- [ ] Detect the library user id (`python scripts/zot.py userid`) for API URLs.
- [ ] Run the acceptance test above.
- macOS/Linux equivalents: `open -a Zotero` / `zotero &`, `osascript -e 'quit app "Zotero"'` /
  `pkill -TERM -x zotero` (graceful), same curl rules; adjust allowlist tool names accordingly.
