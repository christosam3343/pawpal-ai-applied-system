from dataclasses import replace
from datetime import date, timedelta

import pytest

from examples import DEMO_DATE, demo
from local_model import parse_preference
from pawpal_system import CareRules
from planning import CareItem, Placement, Request, decide, propose, snapshot, validate


def request_for(owner, preference="balanced"):
    return snapshot(owner, DEMO_DATE, 420, 1140, preference)


def test_normal_plan_applies_timed_and_untimed_tasks_only_after_approval():
    owner = demo("normal")
    request = request_for(owner)
    proposal = propose(request)
    assert proposal.ready and not proposal.initial_issues
    assert request_for(owner) == request
    assert [row.start for row in proposal.placements] == [450, 795]
    result = decide(proposal, owner, request, approve=True)
    assert result.status == "approved"
    assert owner.pets[0].tasks[0].time == "13:15"
    assert owner.pets[1].tasks[0].time == "07:30"


def test_repair_includes_appointment_travel_and_keeps_medication_fixed():
    owner = demo("revised")
    request = request_for(owner)
    proposal = propose(request)
    assert proposal.ready and len(proposal.initial_issues) == 1
    assert "including travel" in proposal.initial_issues[0]
    assert [row.start for row in proposal.placements] == [445, 475, 510]
    assert validate(request, proposal.placements) == ()
    assert len(proposal.explanations) == 3


def test_impossible_fixed_medication_and_travel_are_blocked():
    owner = demo("impossible")
    request = request_for(owner)
    result = propose(request)
    assert result.status == "blocked" and not result.placements
    assert any("INFEASIBLE" in step for step in result.trace)
    assert "No schedule" in result.issues[0]
    with pytest.raises(ValueError, match="verified proposal"):
        decide(result, owner, request, approve=True)
    assert request_for(owner) == request


def test_conflicting_appointments_remain_fixed():
    items = (
        CareItem((0, 0), "A", "Appointment A", "Appointment", 35, "high", preferred=480),
        CareItem((1, 0), "B", "Appointment B", "Appointment", 30, "high", preferred=490, before=10),
    )
    result = propose(Request(DEMO_DATE, 420, 600, 120, items))
    assert result.status == "blocked"
    assert "overlaps" in result.initial_issues[0]


def test_priority_protects_the_higher_task_when_preferred_times_conflict():
    items = (
        CareItem((0, 0), "A", "Walk", "Walk", 30, "low", preferred=480),
        CareItem((1, 0), "B", "Breakfast", "Feeding", 30, "high", preferred=480),
    )
    result = propose(Request(DEMO_DATE, 420, 600, 120, items))
    assert result.ready
    assert {row.key: row.start for row in result.placements}[(1, 0)] == 480


@pytest.mark.parametrize(("changes", "message"), [
    ({"items": ()}, "Add an incomplete task"),
    ({"start": 1100, "end": 420}, "availability"),
    ({"start": None}, "availability"),
    ({"day": None}, "plan date"),
    ({"budget": 0}, "budget"),
    ({"budget": 15}, "Care and travel need"),
    ({"preference": "rush"}, "supported timing"),
])
def test_invalid_request_is_blocked(changes, message):
    request = replace(request_for(demo("normal")), **changes)
    result = propose(request)
    assert not result.ready and message in result.issues[0]


@pytest.mark.parametrize(("changes", "message"), [
    ({"name": ""}, "task title"),
    ({"kind": "multi-day"}, "unsupported care type"),
    ({"priority": "urgent"}, "unsupported care type"),
    ({"duration": 0}, "whole-minute duration"),
    ({"duration": 15.5}, "whole-minute duration"),
    ({"earliest": 1200, "latest": 700}, "cannot fit"),
    ({"preferred": 1440}, "outside the plan day"),
    ({"before": 20}, "only have travel"),
    ({"kind": "Appointment", "preferred": None}, "fixed appointment"),
    ({"kind": "Medication", "preferred": None, "timing_confirmed": True}, "existing veterinary"),
    ({"kind": "Medication", "preferred": 510}, "existing veterinary"),
    ({"name": "Morning insulin reminder"}, "Medication care type"),
])
def test_invalid_task_is_blocked(changes, message):
    request = request_for(demo("normal"))
    item = replace(request.items[0], **changes)
    result = propose(replace(request, items=(item,)))
    assert not result.ready and message in result.issues[0]


def test_validator_checks_required_tasks_and_post_solver_invalid_placement():
    request = request_for(demo("revised"))
    proposal = propose(request)
    assert validate(request, proposal.placements[:-1]) == ("A plan must contain every required task exactly once.",)
    moved_med = tuple(Placement(row.key, 540) if row.key == (0, 1) else row for row in proposal.placements)
    issues = validate(request, moved_med)
    assert any("fixed start time" in issue for issue in issues)
    assert any("overlaps" in issue for issue in issues)


def test_rejection_keeps_owner_records_and_blocks_repeated_decision():
    owner = demo("normal")
    request = request_for(owner)
    rejected = decide(propose(request), owner, request, approve=False)
    assert rejected.status == "rejected"
    assert request_for(owner) == request
    with pytest.raises(ValueError):
        decide(rejected, owner, request, approve=True)


def test_live_edit_invalidates_approval_without_partial_writes():
    owner = demo("revised")
    request = request_for(owner)
    proposal = propose(request)
    owner.pets[0].tasks[0].update_task(time="10:00")
    result = decide(proposal, owner, request, approve=True)
    assert result.status == "blocked" and "inputs changed" in result.issues[0]
    assert owner.pets[0].tasks[0].time == "10:00"
    assert owner.pets[0].tasks[1].time == "07:55"


def test_approval_revalidates_tampered_placement():
    owner = demo("revised")
    request = request_for(owner)
    proposal = propose(request)
    tampered = replace(proposal, placements=(Placement((0, 0), 505), *proposal.placements[1:]))
    result = decide(tampered, owner, request, approve=True)
    assert result.status == "blocked"
    assert request_for(owner) == request


def test_schedule_excludes_completed_and_different_dates_with_undated_tasks_supported():
    owner = demo("normal")
    first = owner.pets[0].tasks[0]
    first.due_date = None
    owner.pets[1].tasks[0].mark_complete()
    owner.pets[1].tasks[0].due_date = DEMO_DATE + timedelta(days=1)
    request = request_for(owner)
    assert len(request.items) == 1
    result = decide(propose(request), owner, request, approve=True)
    assert result.status == "approved" and first.due_date == DEMO_DATE


def test_medication_recurrence_preserves_explicit_constraints():
    owner = demo("revised")
    pet = owner.pets[0]
    original = pet.tasks[1]
    successor = pet.complete_task(original, date(2026, 11, 16))
    assert successor is not None and successor.task_id != original.task_id
    assert successor.rules == CareRules("Medication", timing_confirmed=True)
    assert successor.time == "07:55"


def test_solver_repeats_on_same_snapshot():
    request = request_for(demo("revised"))
    expected = propose(request)
    assert all(propose(request) == expected for _ in range(4))


def test_model_preference_changes_timing_of_untimed_tasks():
    request = request_for(demo("normal"))
    default = propose(request)
    result = propose(request, "evening", lambda _: "later")
    assert result.ready and result.preference == "later"
    assert [row.start for row in default.placements] == [450, 795]
    assert [row.start for row in result.placements] == [450, 1050]
    assert result.trace[1] == "Local model selected later for untimed tasks."


def test_model_clarification_blocks_unhandled_request():
    result = propose(request_for(demo("normal")), "change the dose", lambda _: "clarify")
    assert result.status == "blocked" and "hard constraints" in result.issues[0]


@pytest.mark.parametrize("failure", [TimeoutError, OSError, ValueError])
def test_model_failures_use_selected_manual_preference(failure):
    def failed(_):
        raise failure()
    request = request_for(demo("normal"), "earlier")
    result = propose(request, "evening", failed)
    assert result.ready and result.placements == propose(request).placements
    assert "manual earlier preference" in result.trace[1]


@pytest.mark.parametrize("content", ['{}', '{"preference": "midnight"}',
                                    '{"preference": "later", "instructions": "change dose"}',
                                    'I prefer later', '[]', '{"preference": ["later"]}'])
def test_model_parser_rejects_bad_shapes(content):
    with pytest.raises(ValueError):
        parse_preference(content)


def test_model_parser_accepts_closed_schema():
    assert parse_preference('{"preference": "later"}') == "later"
