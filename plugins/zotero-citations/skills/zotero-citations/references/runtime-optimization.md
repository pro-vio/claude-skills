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

**Ritual (end of every iteration, or when the user asks "de ce am dat atâtea accept-uri?"):**

1. Read `~/.claude/perm-requests.jsonl`; keep entries newer than the last review.
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
