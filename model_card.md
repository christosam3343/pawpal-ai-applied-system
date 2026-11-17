# PawPal+ AI model card and responsible-AI reflection

## Intended use

PawPal+ AI organizes the care tasks an owner has already chosen for multiple pets. A deterministic planning and verification loop runs with or without the optional language model. The language model classifies a brief preference for untimed flexible tasks. The owner reviews every proposed schedule before applying it.

## Model and configuration

Optional inference uses [Qwen2.5-0.5B-Instruct-GGUF](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF), Q4_K_M, revision `9217f5db79a29953eb74d5343926648285ec7e67`, served by llama.cpp b12444 at a fixed loopback address. The adapter requests a closed JSON object with one enum field, temperature 0, seed 42, a 48-token response limit, and a six-second network timeout. It validates the response before using it. The model receives the timing phrase only. Python computes the placements, enforces the constraints, and generates explanations from checked inputs and outputs.

## Limitations and bias

The model is small and was evaluated on one live English timing example. It may misread idioms, multiple goals, or preferences written in another language. There is no accuracy claim for real users across languages. The planner assumes that one caregiver must handle all tasks in a single day. It gives greater priority to the timing preferences of tasks the owner rated higher. By putting untimed tasks at the midpoint by default, it may assign inconvenient slots within wide windows. Owners with irregular availability or multiple caregivers must represent their situation conservatively.

## Misuse and safeguards

A user could assume that a feasible schedule makes a medical choice appropriate, classify a reminder incorrectly, or supply inaccurate time and travel estimates. The app requires a verified fixed medication time, protects it during revision, flags common medication terms entered under another category, and blocks an infeasible result. The classification rule is incomplete and depends on honest task labeling. The owner should use existing veterinary instructions. The model can neither edit a dose nor write to the schedule. The approval gate checks the latest records and the actual schedule before writing. Operational logs record states and counts without recording pet names or the timing phrase. Session history includes scheduling decisions and stays with the local session.

## Evaluation results

| Case | Criterion | Observed result |
| --- | --- | --- |
| Normal day | Preserve the recorded breakfast and add a feasible walk time | 07:30 breakfast and 13:15 walk, approved |
| Revisable conflict | Detect travel overlap, preserve fixed times, verify the new plan | Walk moved from 08:00 to 07:25. Medication stayed 07:55 and the vet stayed 08:30 |
| Missing confirmation | Block the plan and preserve all records | Blocked at input validation |
| Infeasible fixed conflict | Keep confirmed medication and appointment times when they conflict | CP-SAT returned INFEASIBLE. Approval was unavailable |
| Live timing goal | Evening phrasing changes the untimed walk and retains breakfast | Walk moved from the default 13:15 to 17:30. Breakfast stayed 07:30 |

The predefined harness passed 5/5 with the local model enabled. The automated suite passed 96 cases. Schema rejection, timeout, connection failure, and fallback behavior were exercised using injected test failures. No owner or veterinarian study was conducted. [Raw scenario run](evidence/scenarios.txt)

## What surprised us in reliability testing

The 08:30 appointment initially looks compatible with an 08:15 reminder if only appointment starts are compared. Reserving travel from 08:00 makes the verified 08:15 reminder and the visit incompatible for one owner, even after moving the walk. The same workflow therefore needs a repair path and a refusal path. A separate approval test also showed how an edited task can invalidate a previously valid proposal.

## How Codex was used

Codex inspected the inherited code and baseline tests, drafted the planning architecture, implemented and exercised the planner and UI, debugged the checks, and recorded the evidence. Christo Thomas supplied his Module 2 project, the intended workflow, and access to the grading instructions. He directed the implementation, requested verification against every requirement, and asked for the checklist and documentation to reflect completed work. The accepted and revised suggestions below describe decisions implemented during that assisted development session, rather than claiming independent manual development or a user study.

**Accepted suggestion.** Recheck the proposed placements and live request at approval. This preserved the rule that a proposal is only applied after review and prevented a changed task from causing a partial or stale update. The stale-input and tampered-placement tests exercise both checks.

**Revised suggestion.** The first generated AppTest used `AppTest.from_file("app.py")`, assuming the path was relative to the command's project directory. Streamlit 1.67 resolved it relative to the test file, and all four UI tests failed before loading the app. The test now resolves the project root from `__file__`. The four checks then ran against the actual Streamlit entry point.

## Future improvements

Expand the language evaluation, test accessibility with owners, and support locally persisted schedules, multiple caregivers, and more detailed availability. A veterinary reviewer could assess reminder wording and task intake before broader distribution.
