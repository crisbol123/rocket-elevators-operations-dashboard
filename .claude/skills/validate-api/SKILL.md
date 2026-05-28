---
name: validate-api
description: Validates a live Rocket Elevators API endpoint against the spec. Pass the endpoint path as argument.
user-invocable: true
argument-hint: /api/elevators
context: fork
agent: api-validator
---

Validate the endpoint `$ARGUMENTS` against the spec in `docs/api_spec.md`. The Go API is running on `localhost:${GO_API_PORT:-8081}`.
