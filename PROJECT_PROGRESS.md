# PawPal+ AI project progress

[Week 9 assignment](https://courses.codepath.org/courses/ai110/unit/9#!projects) and [Project 4 rubric](https://courses.codepath.org/courses/ai110/pages/grading#heading-project-4-applied-ai-system) were reviewed in the authenticated course page. The rubric has 21 required points across seven categories and up to eight stretch points. It accepts either an integrated multi-step planning workflow or an integrated reliability mechanism. It does not expressly require an external model API.

## Milestone 1 | Requirements and baseline

- The Module 2 source and its GitHub main branch both pointed to `d0f842b9139a23319e1620d5e93b14fd054bd6ef`. The original worktree was clean.
- The final project was cloned from that local main branch with its 18 reachable commits. Existing models, CLI, tests, UML, reflection, and AI interaction record were inspected. Test command from the clone, using the existing interpreter, was `python -B -m pytest -p no:cacheprovider -q`. Result was **49 passed**. Bytecode and pytest cache writes were disabled.
- The original supports multiple pets, filtering, manual task times, recurring completion, and warning-only overlap checks. `Scheduler.generate_schedule` raises `NotImplementedError`; Streamlit disabled the corresponding button. The final project extends this baseline.
- The new public repository was created under `christosam3343` with no initialization files. `git ls-remote origin` returned no refs before the first push.
- CodePath lists the deadline as **November 16, 2026 at 2:59 a.m. EST**. This build began after that time. Any late submission acceptance belongs to the course.
