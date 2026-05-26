---
description: Load when editing HTML files in platform/ — HTMX interaction patterns for the Rocket Elevators operations dashboard.
---

# HTMX Patterns

- Use HTMX attributes (`hx-get`, `hx-post`, etc.) for all dynamic interactions
- Endpoints return HTML fragments, not JSON — never return raw data from an HTMX-triggered endpoint
