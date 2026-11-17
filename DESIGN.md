# Planning design

The original Owner, Pet, and Task records continue to own care data. The planner takes an immutable snapshot of incomplete tasks for one date. It interprets an optional soft timing preference, tries the entered schedule, and checks every task against a separate validator. Conflicts trigger a constraint search, and the validator checks the revised result. Approval checks that inputs still match the snapshot and revalidates before applying any time or date.

One owner is modeled as one shared resource across all pets. Travel blocks that resource before and after a fixed appointment. Every included task is required. Priority weights only influence how far a flexible task can move from its preferred start. Medication has a fixed user-entered time and an explicit confirmation that existing instructions were checked. A scheduling conflict involving a fixed time is surfaced for the owner to resolve.

A no-cost local Qwen adapter can interpret a soft request about untimed tasks as earlier, later, balanced, or clarify. The application checks that closed response schema and provides a manual timing preference. The model receives only the timing preference, and Python owns executable constraints, user-visible explanations, and application of changes.

The current architecture is [architecture.mmd](diagrams/architecture.mmd). The inherited `uml_draft.mmd` and `uml_final.mmd` describe the historical Module 2 design; their unimplemented schedule-generation placeholder was replaced by the separate planning workflow in this final project.
