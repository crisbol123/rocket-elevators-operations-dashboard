---
name: platform-conventions
description: Platform-wide conventions for the Rocket Elevators project — data files, generated artifacts, and cross-cutting rules.
user-invocable: false
---

## Generated Data Files

`data/predictions.csv` is a generated artifact produced by `intelligence/generate_predictions.ipynb`. Do not edit it manually. To update predictions, re-run the notebook from top to bottom (Restart Kernel and Run All), then restart the Go API so it reloads the file into memory at startup.
