---
name: sample-endpoint
description: Hits a live Rocket Elevators API endpoint and returns a formatted JSON example block ready to paste into docs/api_spec.md. Use this in Step 1 of /new-endpoint before writing spec examples.
user-invocable: true
argument-hint: /api/fleet/stats
---

Hit the live endpoint and produce a spec-ready example block.

**Step 1 — Call the endpoint:**

```bash
curl -s http://localhost:${GO_API_PORT:-8081}$ARGUMENTS
```

If the server is not running, say so and stop.

**Step 2 — Format the response:**

- If the response is a JSON **object**: pretty-print it as-is.
- If the response is a JSON **array** with more than 2 items: show only the first 2 elements, then add a comment line `// ... N total items` so the reader knows the list was truncated.
- If the response is an **error** (`{"error": "..."`): report the error and stop — the server or endpoint is broken.

**Step 3 — Output exactly this block, nothing else:**

```
#### Example Response

\`\`\`json
<formatted response here>
\`\`\`
```

This output is ready to paste directly into the `## 5. Task Breakdown` section of `docs/api_spec.md` under the correct endpoint.
