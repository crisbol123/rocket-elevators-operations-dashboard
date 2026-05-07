# AI Workflow Baseline

## Ai Tools
I often use Claude (web interface) and GPT-5.2-Codex via GitHub Copilot.

## Use cases
- Generating code from defined requirements e.g., I provide a spec and ask for an implementation.
- Brainstorming alternatives for architecture decisions in my projects.

## Typical interaction
I start with a short system role and a clear prompt, then paste requirements and expected output. A typical session lasts 10–20 minutes, iterating on responses. For example, in my network configuration project, I ask the model to translate human intents into device configuration snippets, then I review and adapt the output before using it.

## What works
Defining the prompt well: setting a role, specifying the expected output, and adding constraints clearly. Addding examples to the Prompt has helped too, this is called Few-Shot.

## What doesn’t
Sometimes the model forgets context I already provided, which is frustrating.

## Confidence level
- Confidence (1–5): 3
- Verification: I review the code and outputs to ensure they match what I expected.

## AI Log

### Task 3 — Dashboard specification

**Task**: Task 3 (Dashboard specification)

**Prompt**: "Create a technical specification for the Rocket Elevators Operations Dashboard. It must define layout, data sources and join logic, summary metrics, detail table columns and behavior, visual style, and data assumptions. The spec must be explicit and must not leave open choices or alternatives."

**What happened**: Copilot first produced a spec but left some optional choices, including wording like "for example" and "e.g." in a few places. That made the output slightly ambiguous for a spec that needs fixed decisions. I asked for stricter definitions, and it removed the open-ended phrasing and set exact values.

**What I would change**: I would be more explicit from the start that no alternatives are allowed and that every UI and data rule must be fixed (colors, labels, formats, and text). Being this specific avoids follow-up corrections and results in a cleaner, unambiguous specification.

### Task 4 — Tailwind class specificity

**Task**: Task 4 (Tailwind class definitions)

**Prompt**: "Add explicit Tailwind CSS class definitions for the final dashboard so the UI is deterministic and not open to interpretation."

**What happened**: When Tailwind classes are not defined precisely, the outputs vary across different prompts and responses, which is not the goal for a fixed UI spec. I asked for exact class lists so the result is consistent.

**What I would change**: I will always require explicit Tailwind class lists for every UI element to prevent inconsistent results between prompts.
