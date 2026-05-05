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
