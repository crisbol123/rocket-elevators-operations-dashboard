# AI Interaction Log

## Task 1 — Monorepo setup

Prompt: "Create a README.md for the Rocket Elevators Operations Dashboard. Include: 1) Project name. 2) A short paragraph describing an internal Ontario elevator dashboard that replaces spreadsheets and tracks overdue inspections. 3) A list of directories: /platform, /intelligence, /data, /docs."

What happened: Copilot CLI first checked whether the README already existed to avoid overwriting. It reported that the path did not exist, which looked like an error at first, but it was just a safety check before creating the file.

What I would change: I would be slightly more explicit about the business context, but for a README the summary was clear and helpful for a team to quickly understand the project.


## Task 3 — Dashboard specification

Prompt: "Create a technical specification for the Rocket Elevators Operations Dashboard. It must define layout, data sources and join logic, summary metrics, detail table columns and behavior, visual style, and data assumptions. The spec must be explicit and must not leave open choices or alternatives."

What happened: Copilot first produced a spec but left some optional choices, including wording like "for example" and "e.g." in a few places. That made the output slightly ambiguous for a spec that needs fixed decisions. I asked for stricter definitions, and it removed the open-ended phrasing and set exact values.

What I would change: I would be more explicit from the start that no alternatives are allowed and that every UI and data rule must be fixed (colors, labels, formats, and text). Being this specific avoids follow-up corrections and results in a cleaner, unambiguous specification.


## Task 3 — Dashboard specification (Tailwind classes)

Prompt: "Add explicit Tailwind CSS class definitions for the final dashboard so the UI is deterministic and not open to interpretation."

What happened: When Tailwind classes are not defined precisely, the outputs vary across different prompts and responses, which is not the goal for a fixed UI spec. I asked for exact class lists so the result is consistent.

What I would change: I will always require explicit Tailwind class lists for every UI element to prevent inconsistent results between prompts.


## Task 3 — Dashboard specification, iteration 2 (technology stack)

Prompt: "Review dashboard_spec.md and identify anything that is ambiguous or unspecified that would cause an AI to make an open choice when building the dashboard."

What happened: The spec did not define the technology stack. When asked to build the dashboard, the model had to decide between plain HTML, React, and Python on its own, which is an open choice that changes the entire implementation.

What I would change: Add a Technology Stack section to the spec from the beginning, fixing the implementation to a single static HTML file with Tailwind via CDN and vanilla JavaScript for sorting. This removes any ambiguity about what kind of file to produce.


## Task 3 — Dashboard specification, iteration 2 (table section title)

Prompt: "Review dashboard_spec.md and identify anything that is ambiguous or unspecified that would cause an AI to make an open choice when building the dashboard."

What happened: The spec defined the Tailwind classes for the table section title element but never specified what text it should display. The model would have to invent a label, leading to inconsistent results across prompts.

What I would change: Always include the exact display text for every labelled UI element in the spec. In this case, adding "display the text Elevator Fleet" next to the class definition removes the ambiguity completely.


## Task 3 — Dashboard specification, iteration 2 (active sidebar link)

Prompt: "Review dashboard_spec.md and identify anything that is ambiguous or unspecified that would cause an AI to make an open choice when building the dashboard."

What happened: The spec defined active and default sidebar link styles but never said which link should be active when the dashboard loads. The model would have to guess, and different runs produced different active links.

What I would change: State explicitly in the sidebar layout section which link is active. Since this is a single-page static file, the Dashboard link is always active and that should be fixed in the spec rather than left to interpretation.


## Task 3 — Dashboard specification, iteration 2 (output file location)

Prompt: "Review dashboard_spec.md and identify anything that is ambiguous or unspecified that would cause an AI to make an open choice when building the dashboard."

What happened: The spec described what to build but never said where to save the output file or what to name it. The model placed the file in different locations across sessions (index.html, dashboard.html, platform/dashboard.html).

What I would change: Include the exact output path in the Technology Stack section: platform/index.html. A spec that defines the deliverable must also define where the deliverable lives.


## Task 5 — Prompting Lab

Prompt: "INSTRUCTIONS: Analyze license.csv to gather only the information needed to perform later tasks. Focus on profiling the dataset first, not executing any tasks.

INPUTS: The file license.csv contains Ontario elevator license records.

CONSTRAINTS: Use only pandas methods. Show your reasoning step by step. Do not assume any column is unique without verifying programmatically. Do not perform any of the later tasks yet.

WHAT TO ANALYZE (must be included):

List all columns and their inferred data types.
Identify candidate unique identifier columns and verify uniqueness programmatically.
Inspect missing values per column (counts and percentages).
Profile the LICENSE STATUS column (unique values and counts).
Validate and parse LICENSE EXPIRY DATE format; report any invalid or missing dates.
Provide any data quality issues that would affect later analysis.

OUTPUT FORMAT: Python code in a Jupyter cell, followed by a one-paragraph justification of why this profiling is sufficient for later tasks."

What happened: During dataset profiling, some cells returned no visible output when there were no errors or matches, which made it look like something failed even though the code was fine.

What I would change: I will explicitly ask the model to print a confirmation message when a check finds nothing, so each cell always produces a clear result.


## Task 5 — Prompting Lab (classification prompt)

Prompt: "INSTRUCTIONS: Classify each unique LICENSE STATUS value as operational or non-operational, and explain your reasoning for each label.

INPUTS: The file license.csv contains Ontario elevator license records.

CONSTRAINTS: Use only pandas methods. Show your reasoning step by step. Do not assume unique values; extract them programmatically.

OUTPUT FORMAT: Python code in a Jupyter cell, followed by a one-paragraph justification of the classification rules you used."

What happened: If I did not explicitly tell the model to use the outputs from the dataset profiling step, it ignored that context and produced less grounded classifications.

What I would change: I will always instruct the model to reuse the profiling outputs (unique LICENSE STATUS values and counts) when writing the classification prompt.


## Task 6 — License Status Analysis (location extraction)

Prompt: "(b) Extract country and province from location column. The dataset contains a location column that combines geographic information. Extract the country and state/province into two new columns using a pandas string method and identify where the majority of elevators are located."

What happened: The prompt was simple, but if the model is not told to inspect the location column structure and patterns, it ended up returning province = NaN as the most frequent value, which does not make sense.

What I would change: Always ask the model to analyze the column format (tokens, positions, real examples) before extracting province and country.


## Task 6 — License Status Analysis (unique identifier selection)

Prompt: "Identify the unique identifier for each elevator based on the column checks."

What happened: The model hesitated between ElevatingDevicesNumber and ElevatingDevicesLicenseNumber because it only looked at uniqueness and did not consider which key actually links to other tables. The useful identifier is ElevatingDevicesNumber because it is the shared key across datasets.

What I would change: I would explicitly state that the identifier must be the one used to join with other tables, not just any unique column.




# Summary

Looking back across these sessions, there is a clear pattern that comes up again and again: the model does not tolerate gaps well. Whenever the prompt or spec leaves something open, the model fills the gap on its own, and that choice is essentially random. It might pick React one time and plain HTML another. It might name the output file index.html or dashboard.html or something else entirely. It is not that the model is doing something wrong. It is doing exactly what you asked, which is the problem. If you did not say where to save the file, it saves it somewhere. The lesson from Task 3 alone is that a spec without fixed values is not really a spec at all.

This is probably the biggest thing I took away from working through these tasks. Before these sessions I thought a prompt was good if it was clear about what you wanted. Now I think clarity is necessary but not sufficient. You also need completeness. There is a difference between a prompt that explains the goal and a prompt that removes every decision the model would otherwise have to make on its own. The Task 3 iterations make this very concrete. Each round found one more thing that was left open: the technology stack, the text inside a label, which sidebar link starts active, the file path for the output. None of these felt like big gaps when I first wrote the spec. But each one produced inconsistent results across runs.

The second pattern is about context. The model does not automatically carry forward what it learned in a previous step. When I profiled the dataset in Task 5 and then asked it to classify license statuses, it went back to first principles instead of using what we had already established. I had to explicitly tell it to reuse those outputs. This feels obvious in hindsight but it is easy to forget in practice because a human collaborator would naturally reference what was discussed earlier. The model does not do that unless you wire it in. The fix is simple, you just have to name the prior output in the next prompt, but you have to remember to do it.

There is also something interesting about how the model signals the absence of results. In the profiling task, when a check found nothing, the cell produced no output at all. That looks identical to a cell that did not run or threw a silent error. A person reviewing the notebook would not know whether the check passed cleanly or failed. I had assumed the model would always print something, but that assumption was wrong. Asking for explicit confirmation messages when a check finds nothing is a small thing but it matters a lot for readability and for debugging later.

The Task 6 identifier selection came down to a subtle distinction between statistical uniqueness and functional usefulness. Both columns were unique in the dataset, so from a pure data profiling standpoint either one could serve as an identifier. But only one of them was the join key for other tables, which makes it the right choice for downstream work. The model reasonably picked based on what the prompt asked. I asked it to identify a unique identifier, and it found one. I just had to be more specific about what unique identifier actually means in this context, which is the one that connects across datasets.

One thing that stood out in a smaller way was the Task 1 safety check, where Copilot verified that the file did not already exist before creating it. That looked like an error in the output, but it was actually a reasonable precaution. I mention this because it is easy to misread model behavior as a problem when it is actually doing something sensible. Reading the output carefully before concluding something went wrong is worth the extra seconds.

If I had to collapse all of this into a single working principle, it would be something like: the model is only as specific as your prompt, and prompts that leave anything open will produce outputs that vary. The practical checklist I have landed on is to define every label's exact text, every file's exact path, every technology choice, every classification rule, and to always name the prior context you want the model to carry forward. It sounds like a lot, but most of these only require one extra sentence in the prompt, and they save significantly more time than they cost by cutting down the rounds of correction.


## AND-102, Task 2 — Data Model (DeviceStatus exploration)

Prompt: "I am defining the status field in the Data Model for the dashboard spec. Before I write the allowed values, use a subagent to check installed.json and return all distinct values in the DeviceStatus column so I do not load the full dataset into the main session."

What happened: The subagent returned five distinct values: `Active`, `Customer Shutdown`, `Inactive`, `TSSA Shutdown`, and `Undergoing Major Alt`. These were not documented anywhere in the project. Having the exact values allowed me to define the `status` field in the Data Model precisely and raised a follow-up question: whether `Undergoing Major Alt` and `TSSA Shutdown` should be treated differently from `Inactive` in the Overdue Inspection logic. Keeping the exploration in a subagent avoided loading the full JSON dataset into the main session context.

What I would change: I would run this kind of data profiling at the start of every task that touches a new dataset, before writing any spec or code. Discovering that `TSSA Shutdown` exists only after defining the Data Model meant I had to reconsider the overdue logic retroactively. Profiling first would have surfaced that decision point earlier.


## AND-102, Task 2 — Data Model (LICENSESTATUS exploration)

Prompt: "I am defining the license_status field in the Data Model for the dashboard spec. Before I write the allowed values, use a subagent to check license.csv and return all distinct values in the LICENSESTATUS column with their counts, so I do not load the full dataset into the main session."

What happened: The subagent returned 11 distinct values: `ACTIVE` (42,665), `CANCELLED_NOT_RENEWED` (1,163), `PENDING_RENEWAL` (632), `TERMINATED` (475), `BY REQUEST` (337), `EXPIRED` (68), `HOLD_TSD` (24), `TERMINATED DECEASED` (6), `CANCELLED_BY_CUST_REQ` (6), `ENTERED` (4), and `CANCELLED` (3). The counts showed that the vast majority of records are `ACTIVE`, and that the remaining statuses are either administrative or edge cases. All values were added directly to the Data Model in the spec. Keeping the exploration in a subagent prevented the full CSV dataset from entering the main session context.

What I would change: Nothing significant. Requesting counts alongside the distinct values was the right call — it revealed that some statuses like `ENTERED` and `CANCELLED` are near-empty edge cases, which is useful context when deciding how to handle them in filtering logic.


## AND-102, Task 2 — Data Model (InspectionOutcome exploration)

Prompt: "I am defining the last_inspection_outcome field in the Data Model for the dashboard spec. Before I write the allowed values, use a subagent to check inspection.csv and return all distinct values in the InspectionOutcome column with their counts, so I do not load the full dataset into the main session."

What happened: The subagent returned over 30 distinct values, with `Follow up` (53,801) and `Passed` (25,716) being the most frequent. It also claimed some rows contained date strings instead of categorical values. That claim turned out to be wrong — a follow-up check against the raw file found zero rows matching a date pattern in that column. The incorrect finding was initially written into the spec and had to be removed after verification.

What I would change: Always verify subagent findings that describe data quality issues before writing them into a spec. The subagent summary described what it intended to find, not necessarily what was actually in the data.


## AND-102, Task 2 — Data Model (Device Type exploration)

Prompt: "I am defining the device_type field in the Data Model for the dashboard spec. Before I write the allowed values, use a subagent to check installed.json and return all distinct values in the Device Type column with their counts, so I do not load the full dataset into the main session."

What happened: The subagent returned 11 distinct values, with `Passenger Elevator` (42,405) being by far the most common, followed by `Freight Elevator` (2,912) and `LULA Elevator` (1,254). The remaining types are rare edge cases. All values were added to the Data Model. No data quality issues were found.

What I would change: Nothing. The pattern of using a subagent to profile a column before writing its allowed values into the spec is working consistently across all three datasets.