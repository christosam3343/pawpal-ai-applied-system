"""Run fixed synthetic scenarios through the same planner as Streamlit."""

import argparse
import json
import logging

from examples import DEMO_DATE, demo
from local_model import interpret_preference
from planning import Request, clock, decide, propose, snapshot, validate

SCENARIOS = ("normal", "revised", "guardrail", "impossible", "timing-goal")
GOAL = "Save the flexible activities for the evening."


def task_inputs(request: Request) -> list[dict]:
    return [
        {"pet": item.pet, "task": item.name, "type": item.kind, "priority": item.priority,
         "duration_min": item.duration, "entered_start": clock(item.preferred) if item.preferred is not None else None,
         "start_window": [clock(value) if value is not None else None for value in (item.earliest, item.latest)],
         "fixed": item.fixed, "outbound_min": item.before, "return_min": item.after,
         "medication_time_confirmed": item.timing_confirmed}
        for item in request.items
    ]


def run_case(name: str) -> dict:
    owner = demo(name)
    request = snapshot(owner, DEMO_DATE, 420, 1140, "balanced")
    goal = GOAL if name == "timing-goal" else ""
    proposal = propose(request, goal, interpret_preference)
    reference = propose(request) if goal else None
    verified = proposal.ready and not validate(request, proposal.placements)
    untouched_before = snapshot(owner, DEMO_DATE, 420, 1140, "balanced") == request
    result = decide(proposal, owner, request, approve=True) if verified else proposal
    current = snapshot(owner, DEMO_DATE, 420, 1140, "balanced")
    items = {item.key: item for item in current.items}
    persisted = result.status == "approved" and all(
        items[row.key].preferred == row.start for row in result.placements
    )
    checks = {
        "normal": verified and persisted and not result.initial_issues,
        "revised": verified and persisted and len(result.initial_issues) == 1
                   and any("Revised candidate passed" in step for step in result.trace)
                   and [row.start for row in result.placements] == [445, 475, 510],
        "guardrail": result.status == "blocked" and any("confirmed" in issue for issue in result.issues)
                     and current == request,
        "impossible": result.status == "blocked" and bool(result.initial_issues) and current == request
                      and any("INFEASIBLE" in step for step in result.trace),
        "timing-goal": verified and persisted and result.preference == "later"
                       and reference is not None and reference.ready
                       and [row.start for row in reference.placements] == [450, 795]
                       and [row.start for row in result.placements] == [450, 1050],
    }
    input_items = {item.key: item for item in request.items}
    return {
        "scenario": name, "result": "PASS" if checks[name] and untouched_before else "FAIL",
        "input": {"day": str(request.day), "availability": [clock(request.start), clock(request.end)],
                  "budget_min": request.budget, "timing_goal": goal or None, "tasks": task_inputs(request)},
        "proposal": [
            [input_items[row.key].name, clock(row.start), clock(row.start + input_items[row.key].duration)]
            for row in result.placements
        ],
        "default_starts": [clock(row.start) for row in reference.placements] if reference else None,
        "initial_issues": result.initial_issues,
        "final_issues": result.issues,
        "explanations": result.explanations,
        "trace": result.trace,
        "unchanged_before_approval": untouched_before,
        "decision": result.status,
        "recorded_starts": [[item.name, clock(item.preferred) if item.preferred is not None else None]
                            for item in current.items],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=SCENARIOS)
    parser.add_argument("--with-model", action="store_true", help="Include live loopback model inference")
    args = parser.parse_args()

    logging.getLogger("planning").addHandler(logging.NullHandler())
    logging.getLogger("planning").propagate = False
    chosen = (args.scenario,) if args.scenario else SCENARIOS if args.with_model else SCENARIOS[:-1]
    outputs = [run_case(name) for name in chosen]
    for output in outputs:
        print(json.dumps(output, ensure_ascii=True))
    passed = sum(output["result"] == "PASS" for output in outputs)
    print(f"Summary: {passed}/{len(outputs)} scenarios passed")
    return int(passed != len(outputs))


if __name__ == "__main__":
    raise SystemExit(main())
