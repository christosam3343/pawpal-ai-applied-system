# PawPal+ AI project audit

The [Week 9 assignment](https://courses.codepath.org/courses/ai110/unit/9#!projects) and the [Project 4 rubric](https://courses.codepath.org/courses/ai110/pages/grading#heading-project-4-applied-ai-system) were inspected while signed in. The rubric has 21 required points and up to eight stretch points. The statuses below describe implementation and observed verification. CodePath assigns the grade.

## Milestones

| Milestone | Result and verification | Commit |
| --- | --- | --- |
| 1 · Requirements and setup | Reviewed assignment sections 0–7 and the stretch rubric. Confirmed the requested destination was empty, cloned the original main history, created a public empty GitHub repo, verified the new origin, and pushed. The original suite ran from the clone with the old interpreter and bytecode/cache writes disabled. All 49 passed. | `6564410` |
| 2 · Architecture and AI choice | Designed a verified planning loop with CP-SAT revision, a separate validator, human approval, and optional local structured inference. The rubric accepts multi-step planning or integrated reliability and does not expressly require an external model API. | `39ef09c` |
| 3 · Implementation | Streamlit uses the planner directly. A clean browser session on the final server loaded the sample day, found the walk/travel conflict, revised it, rejected the first proposal, generated again, and applied after approval. | `f349488` |
| 4 · Reliability | 96 pytest cases passed. The predefined harness passed 4/4 offline and 5/5 with live Qwen. The fifth case changed the untimed walk from 13:15 to 17:30. | `6087da4` |
| 5 · Evidence and documentation | Mermaid CLI 11.12.0 generated `assets/architecture.svg` from the required `.mmd`. Reviewed the resulting SVG labels. README includes setup and actual execution excerpts. Model Card records limitations, risks, actual testing, and AI collaboration. | `959a96b` |
| 6 · Presentation and preparation | Six offline browser slides and timed notes verified through all slide positions. Portfolio entry includes the public repository link and student reflection draft. Final course audit and checklist updates are recorded below. | `f27dd89` and this audit commit |

## Required rubric items

| ID | Requirement | Status | Files | Verification and evidence | Commit |
| --- | --- | --- | --- | --- | --- |
| B1 | Identify the previous project | PASS | `README.md` | Names and links Module 2 PawPal+. | `959a96b` |
| B2 | Describe the base goal and capabilities | PASS | `README.md` | Summarizes profiles, manually timed tasks, recurrence, sorting, filtering, and warnings in three sentences including extension context. | `959a96b` |
| B3 | Set accurate context for the extension | PASS | `README.md`, original `app.py`, original `pawpal_system.py` | Original generator was disabled in the app and the backend placeholder raised `NotImplementedError`. New app proposes and revises times. | `959a96b` |
| A1 | Add a substantial AI feature | PASS | `planning.py`, `local_model.py` | Plan, validate, revise with constraint search, and independently verify. Optional live model affects untimed task placement. | `f349488` |
| A2 | Integrate the feature into the main app | PASS | `app.py`, `tests/test_app.py` | Generate proposal and approval call the same functions as the scenario harness. Browser and AppTest both exercised the workflow. | `f349488`, `6087da4` |
| A3 | Demonstrate a meaningful change in behavior | PASS | `evidence/scenarios.txt` | First draft detected a travel conflict, revision changed the walk to 07:25, and verified approval applied it. Live timing inference changed the untimed walk to 17:30. | `6087da4` |
| D1 | Provide Mermaid source | PASS | `diagrams/architecture.mmd`, `assets/architecture.svg` | Mermaid CLI rendered the source successfully as SVG. | `39ef09c`, `959a96b` |
| D2 | Illustrate input, processing, and output | PASS | `diagrams/architecture.mmd` | Diagram traces care data to draft, check, revision, review, and applied schedule. | `39ef09c` |
| D3 | Match the implemented system and review points | PASS | `diagrams/architecture.mmd`, `app.py`, `planning.py` | Checked branches for optional model, invalid inputs, validation, repair, owner review, logging, and final schedule against code. | `39ef09c`, `f349488` |
| E1 | Provide a working end-to-end interface or script | PASS | `app.py`, `evaluate.py` | Live Streamlit app and CLI harness both ran. The browser observed the revised proposal, rejection, and applied schedule. | `f349488`, `6087da4` |
| E2 | Include runnable commands and captured output | PASS | `README.md`, `evidence/scenarios.txt` | README includes shell commands and four fenced examples quoted from or summarized against the committed run. | `959a96b` |
| E3 | Respond consistently to at least 2–3 inputs | PASS | `evaluate.py`, `tests/test_planning.py` | All four offline inputs passed. The same problem was regenerated four times in a regression test. The separately configured live model suite passed 5/5. | `6087da4` |
| G1 | Include a functional evaluation or guardrail mechanism | PASS | `planning.py`, `tests/`, `evaluate.py` | Blocks missing, unsupported, overlapping, and stale records. Captures status in the session and runtime log. | `f349488`, `6087da4` |
| G2 | Show that the mechanism improves reliability | PASS | `evidence/scenarios.txt`, `tests/test_planning.py` | The first invalid draft was repaired and rechecked. Infeasible inputs and tampered approvals left records unwritten. | `6087da4` |
| G3 | Show guardrail behavior in Markdown | PASS | `README.md`, `model_card.md` | Fenced missing-confirmation example and evaluation table document inputs, observed behavior, and outcome. | `959a96b` |
| W1 | Explain project goals and new functionality | PASS | `README.md` | Includes why the app exists, its capabilities, a component overview, design choices, guardrails, and future work. | `959a96b` |
| W2 | Explain how to install, run, and test | PASS | `README.md`, `requirements.txt` | Python 3.14 venv, pinned application packages, Streamlit, test and harness commands, and reproducible local model configuration are documented. `pip check` passed. | `f349488`, `959a96b` |
| W3 | Include sample inputs and outputs | PASS | `README.md`, `evidence/scenarios.txt` | Normal, revised, missing-confirmation, and live model examples are in the README. Full JSON lines include an infeasible fifth case. | `6087da4`, `959a96b` |
| R1 | Explain how AI was used during development | PASS | `model_card.md` | Records Codex's architecture, implementation, debugging, and evidence work. | `959a96b` |
| R2 | Identify accepted and revised AI suggestions | PASS | `model_card.md` | Accepted approval-time revalidation. Revised the generated AppTest entry path after four setup failures. 96 tests passed after the correction. | `6087da4`, `959a96b` |
| R3 | Reflect on limits and improvements | PASS | `model_card.md` | Addresses single caregiver and day, potential language bias, misuse, safeguards, an observed surprise, and future evaluation. | `959a96b` |

## Assignment checklist and handoff

| Section | Status | Related files and evidence |
| --- | --- | --- |
| 0 · Environment | PASS | New public repo was initially empty. Clone retained 18 original main-history commits. Origin was checked before every push. The venv is isolated and environment, cache, credential, model, and local data patterns are ignored. Architecture export is in `assets/`, source in `diagrams/`. GitHub API reported `private: false`. Main files and multiple commits are present on GitHub. |
| 1 · Functionality | PASS | `app.py`, `planning.py`, `pawpal_system.py`, `local_model.py`. Browser and tests verified the app; retained legacy CLI, filtering, task completion, and recurrence. New app adds editing, travel and time windows, cross-pet planning, validation, approval, and decision history. |
| 2 · Architecture | PASS | 3/3 editable items checked. Source rendered via Mermaid CLI. Diagram identifies components, flow and review points. |
| 3 · Documentation | PASS | 8/8 editable items checked. README, execution logs, and Model Card verified against the working project. |
| 4 · Reliability | PASS | `evidence/pytest.txt` records 96 passes. `evidence/scenarios.txt` records 5/5 with the local model, including the guardrails and before/after outputs. |
| 5 · Reflection and ethics | PASS | 4/4 editable items checked. Actual development and testing decisions are in `model_card.md`. |
| 6 · Presentation and portfolio | PASS | 3/3 required editable items checked. `presentation/index.html` has six slides. `speaker_notes.md` is timed for six minutes. `portfolio.md` includes the link and draft reflection. Optional Loom remains unchecked. |
| 7 · Submission materials | PASS | GitHub branch, public visibility, runnable code, README, Model Card, Mermaid, text evidence, and meaningful commits verified. No final submission was made. |
| 7 · Posted deadline | WARNING | The portal listed November 16, 2026 at 2:59 a.m. EST. Work and pushes occurred later. The project owner indicated submission was still possible. Final submission status is pending. |

The 18 editable required checklist selections were verified in the portal. The three presentation selections remained checked in a newly opened tab. The portal exposes 20 disabled entries under Goals and Preparing Your Project Environment. Their work status is covered above. Functionality, evaluation, and submission sections are prose requirements and do not offer editable checklist controls. The optional Mermaid Live Editor setup entry did not apply because rendering used Mermaid CLI.

The original local and remote main branches were both verified at `d0f842b9139a23319e1620d5e93b14fd054bd6ef`, and the original worktree was clean after implementation. The final public repo is [pawpal-ai-applied-system](https://github.com/christosam3343/pawpal-ai-applied-system). Run `git log -1 --oneline -- PROJECT_PROGRESS.md` to identify this audit commit.

## Optional features

| Stretch item | Status | Evidence |
| --- | --- | --- |
| Agentic workflow enhancement | PASS | `ai_interactions.md` links the committed intermediate planning, validation, and decision traces. |
| Test harness or evaluation script | PASS | `python evaluate.py` prints a pass/fail result for each fixed scenario and a summary. The live model run recorded a 5/5 summary. |
| RAG enhancement | Not attempted | The app implements planning and verification. |
| Fine-tuning or specialization | Not claimed | The local model uses structured prompting. No separate evaluation against an unprompted model was conducted. |
| Loom | Not recorded | Text execution evidence and the six-minute presentation are available. |
