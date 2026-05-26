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
