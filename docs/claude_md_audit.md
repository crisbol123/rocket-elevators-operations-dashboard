## AND-104 Task 1: CLAUDE.md Audit and Platform Conventions Skill

# CLAUDE.md Rule Audit

Audit of every rule written across Modules 1–3, categorized into: **always relevant**, **must always execute (hook)**, or **scoped to specific work (skill)**.

---

## Rule Inventory

**Rule 1: Use Python type hints in all function signatures**
Category: Always relevant
Applies to any Python code in the project — both `platform/` and `intelligence/` notebooks define functions where type hints are expected.

**Rule 2: Use HTMX attributes (`hx-get`, `hx-post`, etc.) for all dynamic interactions**
Category: Scoped to specific work (skill)
HTMX is only used in the `platform/` frontend; has no meaning in the intelligence layer or documentation.

**Rule 3: Jinja2 comments use `{# comment #}`, not `{{# comment #}}`**
Category: Scoped to specific work (skill)
Jinja2 templates exist only in `platform/templates/`; this syntax rule is meaningless outside that context.

**Rule 4: When asked about code, do not edit it unless explicitly instructed to do so**
Category: Always relevant
Applies to every file in the repo regardless of layer — a universal behavioral constraint.

**Rule 5: Never run `git commit` or `git push` unless the user explicitly says to commit or push**
Category: Must always execute (hook)
This guard must fire before every git write operation across all contexts; a hook is the only reliable way to enforce it automatically.


**Section: Server (FastAPI server location, run command, DataFrame setup, endpoints)**
Category: Scoped to specific work (skill)
All server reference material describes `platform/` infrastructure exclusively; it adds noise when working on notebooks or documentation.

---


## Migration Plan

Rules 2 and 3, plus the Server section, will be moved to separate skills:
- `.claude/skills/fastapi-server/SKILL.md` — server reference and endpoint documentation
- `.claude/skills/htmx-patterns/SKILL.md` — HTMX interaction conventions
- `.claude/skills/jinja2-templates/SKILL.md` — Jinja2 template syntax rules
Rules 1 and 4 stay in `CLAUDE.md`.  
Rule 5 will be implemented as a pre-tool hook.

---

## AND-104 Task 4: Hook Implementations

### Hook 1 — Auto-format Go files (PostToolUse)

Runs `gofmt -w` on any `.go` file after an edit. A CLAUDE.md rule isn't enough here because the model can still produce badly formatted output — the hook runs regardless of what the model does.

**Test:** Created a file with missing spaces and bad indentation, made a trivial edit, and the hook fixed everything automatically. No manual intervention.

---

### Hook 2 — Block git commit and push (PreToolUse)

Intercepts any Bash call containing `git commit` or `git push` and exits with code 2 before the command runs. This was already Rule 5 in the audit — it needs to be a hook because a CLAUDE.md rule can be ignored mid-session.

**Test:** The hook blocked my own test command the moment it saw `git commit` in the text. The bash command never executed.

---

### Hook 3 — Protect data/ files (PreToolUse)

Blocks any Edit or Write to a file inside `data/`. Those CSVs and JSON files are the source of truth for both platform and intelligence — if they get corrupted there's no easy recovery. A CLAUDE.md rule is advisory; this needs to be structural.

**Test:** Tried to edit `data/license.csv`. Hook blocked it with exit code 2, file untouched.

---

### Hook 4 — Task completion notification (Stop)

Fires an macOS notification with sound when Claude finishes a response. Can't be a rule because rules don't trigger OS events — only a Stop hook can do this.

**Test:** Verified visually during this session.

---

### Hook 5 — Verify Go build after every edit (PostToolUse)

Runs `go build ./...` after any `.go` edit. During Task 3, edits to handlers would silently break compilation and the error only showed up when restarting the server, sometimes several turns later. This hook surfaces it immediately.

A CLAUDE.md rule could ask the model to run build manually, but it gets skipped. A skill only loads context — it can't run commands post-edit. Only a PostToolUse hook solves this.

**Test:** Created `hooktest.go` with an undefined variable (using a non-`_test.go` name so `go build` actually picks it up). Hook output `./hooktest.go:5:7: undefined: undefinedVar` and exited 1. Error visible right away.
