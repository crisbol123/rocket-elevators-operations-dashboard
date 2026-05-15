## AND-102 Task 7: Executive Report

**Rocket Elevators — Operations Dashboard**
**Prepared for:** Operations Team
**Date:** May 14, 2026

---

## 1. Data Integration Summary

Four datasets were merged into a single unified fleet DataFrame saved as `data/merged_elevator_data.csv`.

| Dataset | Format | Records |
|---|---|---|
| license.csv | CSV | 45,383 |
| installed.json | JSON | 46,936 |
| altered.json | JSON | 31,619 |
| inspection.csv | CSV | 143,181 |

**Merge process (3 steps):**

**Merge 1 — License + Installed (inner join):** Devices were matched on their elevating device number. Only devices with an ACTIVE or PENDING_RENEWAL license were kept, filtering out 2,086 inactive records. A location validation step using Canadian postal codes removed 143 rows where the license and installed records pointed to different addresses, leaving 43,154 rows.

**Merge 2 — + Altered (left join):** Alteration records were added. Since one device can have multiple alteration events, some devices generated multiple rows. The final shape after this merge was 52,339 rows.

**Merge 3 — + Inspections (left join with aggregation):** The inspection dataset had 143,181 records because each device can have many inspections over its lifetime — on average 3.5, with some reaching 24. Rather than joining directly (which would have created one row per inspection and exploded the DataFrame to ~180K rows), all inspection records were first collapsed into a single summary row per device: total inspections, first and last inspection date, pass rate, and last inspection outcome. Those summary columns were then added to the existing 52,339-row DataFrame without adding any new rows — only new columns.

**Final dataset:** 52,339 rows × 34 columns.

**Data quality issues found:**
- Device Type in installed.json had undocumented suffixes (-P, -E on Freight Elevator) with only 28 total occurrences — consolidated into a single Freight Elevator category.
- Three single-occurrence device types (Material Lift - ATD, Special Installation, Power Type Manlift) were mapped to an Other category to avoid misleading sparse categories.
- Alteration contractor name and several alteration columns are null for all 52,339 rows — these appear to be fields not yet populated in the source system.

---

## 2. Incident Analysis Findings

The free-text narratives from 2,445 incident reports in `data/incident.json` were analyzed using TF-IDF vectorization and K-Means clustering. After cleaning the text with spaCy (lowercase, stop word removal, lemmatization), narratives were grouped into 5 clusters.

**Results:**

| Cluster | Incident Type | Count | Share |
|---|---|---|---|
| 3 | Mechanical failures (oil, rope, car drop) | 816 | 33.4% |
| 0 | Door-related injuries | 623 | 25.5% |
| 2 | Pipe burst / hoistway flooding | 369 | 15.1% |
| 4 | Leveling issues / trip-and-fall | 330 | 13.5% |
| 1 | Water / flooding in pit | 307 | 12.6% |



Mechanical failures are the single largest category and carry the highest consequence risk — oil leaks, rope failures, and car drops can all lead to service outages or serious injuries. Door incidents are the second most common and are largely preventable through door sensor calibration and maintenance. Water intrusion across the two flooding clusters accounts for 27.7% of all incidents combined, pointing to building plumbing and drainage as a recurring upstream cause. Leveling incidents are frequent and low-severity individually, but represent a consistent fall hazard for elderly passengers.

---

## 3. Token Cost Analysis

Sessions were tracked using the Claude Code status bar configured in Task 4, running on Claude Sonnet 4.6.

| Task | Input Tokens | Output Tokens | Cache Read | Cache Creation | Estimated Cost |
|---|---|---|---|---|---|
| Task 5 — ETL Pipeline | 83,068 | 15 | 81,900 | 1,167 | ~$0.029 |
| Task 6 — NLP Analysis | 49,473 | 208 | 49,306 | 166 | ~$0.019 |


**Task 5 was the most expensive session.** It had 68% more input tokens than Task 6, driven by a longer conversation with more turns, larger file outputs from the notebook, and the accumulated context of loading and inspecting four datasets. The output token count was low (15) because most responses were code-heavy with short explanatory text.

**Cost-reducing action:** During Task 6, a subagent was used to research the LDA vs. K-Means decision. This kept the exploration out of the main session context, avoiding the cost of loading that research into every subsequent turn. The effect was visible in Task 6's lower cache creation (166 vs. 1,167 in Task 5), meaning less new context was being written to cache on each request.

---

## 4. Recommendations

**1. Prioritize door mechanism maintenance across the fleet.**
Door-related incidents account for 25.5% of all reports and are among the most preventable. A targeted inspection cycle for door sensors, closing force calibration, and edge protection on devices with repeat door incidents would directly reduce this category.

**2. Flag buildings with recurring water incidents for joint review with property management.**
The two water-related clusters together represent 27.7% of all incidents. These are not elevator malfunctions — they are building plumbing failures that damage elevator infrastructure. Identifying the buildings where water incidents repeat and escalating to property management is a higher-leverage intervention than servicing the elevators in isolation.
