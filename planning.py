"""Generate, independently verify, and review a one-day care plan."""

from dataclasses import dataclass, replace
from datetime import date
from itertools import combinations
import logging
import re
from typing import Callable

from ortools.sat.python import cp_model

from pawpal_system import Owner, Task

LOGGER = logging.getLogger(__name__)
DAY = 1440
MAX_TASKS = 30
PRIORITY = {"low": 0, "medium": 1, "high": 2}
KINDS = ("Feeding", "Walk", "Appointment", "Medication", "Other")
PREFERENCES = ("balanced", "earlier", "later")


def clock(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def minute(value: str | None) -> int | None:
    Task._validate_time(value)
    if value is None:
        return None
    return 60 * int(value[:2]) + int(value[3:])


@dataclass(frozen=True)
class CareItem:
    key: tuple[int, int]
    pet: str
    name: str
    kind: str
    duration: int
    priority: str
    preferred: int | None = None
    fixed: bool = False
    earliest: int | None = None
    latest: int | None = None
    before: int = 0
    after: int = 0
    timing_confirmed: bool = False
    source_id: str = ""

    @property
    def label(self) -> str:
        return f"{self.pet} / {self.name}"


@dataclass(frozen=True)
class Request:
    day: date
    start: int
    end: int
    budget: int
    items: tuple[CareItem, ...]
    preference: str = "balanced"


@dataclass(frozen=True)
class Placement:
    key: tuple[int, int]
    start: int


@dataclass(frozen=True)
class Proposal:
    request: Request
    placements: tuple[Placement, ...] = ()
    initial_issues: tuple[str, ...] = ()
    issues: tuple[str, ...] = ()
    explanations: tuple[str, ...] = ()
    trace: tuple[str, ...] = ()
    preference: str = "balanced"
    status: str = "blocked"

    @property
    def ready(self) -> bool:
        return self.status == "pending" and not self.issues


def snapshot(owner: Owner, day: date, start: int, end: int, preference: str) -> Request:
    """Read the active records for one plan, including undated tasks."""
    items = []
    for p, pet in enumerate(owner.pets):
        for t, task in enumerate(pet.tasks):
            if task.completed or task.due_date not in (None, day):
                continue
            rules = task.rules
            duration = task.duration
            if isinstance(duration, float) and duration.is_integer():
                duration = int(duration)
            items.append(CareItem(
                key=(p, t), pet=f"{pet.name} (pet {p + 1})", name=task.name, kind=rules.kind,
                duration=duration, priority=task.priority, preferred=minute(task.time),
                fixed=rules.fixed or rules.kind in ("Medication", "Appointment"),
                earliest=minute(rules.earliest), latest=minute(rules.latest),
                before=rules.travel_before, after=rules.travel_after,
                timing_confirmed=rules.timing_confirmed, source_id=task.task_id,
            ))
    return Request(day, start, end, owner.available_time, tuple(items), preference)


def looks_like_medication(name: str) -> bool:
    return bool(re.search(r"\b(?:meds?|medication|pills?|insulin|doses?)\b", name, re.I))


def bounds(item: CareItem, request: Request) -> tuple[int, int]:
    earliest = max(request.start + item.before, item.earliest or 0)
    latest = min(request.end - item.duration - item.after,
                 item.latest if item.latest is not None else DAY - 1)
    return earliest, latest


def input_issues(request: Request) -> tuple[str, ...]:
    if type(request.day) is not date:
        return ("Choose a plan date.",)
    if (type(request.start) is not int or type(request.end) is not int
            or not 0 <= request.start < request.end <= DAY):
        return ("Choose an availability window within a single day, with end after start.",)
    if type(request.budget) is not int or not 1 <= request.budget <= DAY:
        return ("Set a care-time budget of 1 to 1440 whole minutes.",)
    if request.preference not in PREFERENCES:
        return ("Choose a supported timing preference.",)
    if not request.items:
        return ("Add an incomplete task due on the plan date, or leave its date blank.",)
    if len(request.items) > MAX_TASKS:
        return (f"Plan at most {MAX_TASKS} tasks on one date.",)

    issues = []
    keys = {item.key for item in request.items}
    source_ids = [item.source_id for item in request.items if item.source_id]
    if len(keys) != len(request.items) or len(source_ids) != len(set(source_ids)):
        issues.append("Each task must appear once in a plan.")

    for item in request.items:
        label = item.label
        if not item.name.strip() or not item.pet.strip():
            issues.append(f"{label} needs a task title and a pet.")
        if item.kind not in KINDS or item.priority not in PRIORITY:
            issues.append(f"{label} has an unsupported care type or priority.")
        if type(item.duration) is not int or not 1 <= item.duration <= DAY:
            issues.append(f"{label} needs a positive whole-minute duration.")
            continue
        if any(type(travel) is not int or not 0 <= travel <= DAY
               for travel in (item.before, item.after)):
            issues.append(f"{label} has invalid travel minutes.")
            continue
        if item.kind != "Appointment" and (item.before or item.after):
            issues.append(f"{label} can only have travel time on appointments.")
        values = (item.preferred, item.earliest, item.latest)
        if any(value is not None and (type(value) is not int or not 0 <= value < DAY)
               for value in values):
            issues.append(f"{label} has a time outside the plan day.")
            continue
        if item.kind != "Medication" and looks_like_medication(item.name):
            issues.append(f"{label} needs the Medication care type.")
        if item.kind == "Medication" and (not item.timing_confirmed or item.preferred is None):
            issues.append(f"{label} needs a fixed time confirmed against existing veterinary instructions.")
        if item.kind == "Appointment" and item.preferred is None:
            issues.append(f"{label} needs a fixed appointment time.")
        if item.fixed and item.preferred is None and item.kind not in ("Appointment", "Medication"):
            issues.append(f"{label} needs a fixed start time.")
        earliest, latest = bounds(item, request)
        if earliest > latest:
            issues.append(f"{label} cannot fit its time window and travel within owner availability.")

    if not issues:
        total = sum(item.duration + item.before + item.after for item in request.items)
        if total > request.budget:
            issues.append(f"Care and travel need {total} minutes. The budget is {request.budget} minutes.")
    return tuple(issues)


def is_fixed(item: CareItem) -> bool:
    return item.fixed or item.kind in ("Appointment", "Medication")


def validate(request: Request, placements: tuple[Placement, ...]) -> tuple[str, ...]:
    """Check actual placements without relying on the solver's constraints."""
    issues = list(input_issues(request))
    if issues:
        return tuple(issues)
    starts = {row.key: row.start for row in placements}
    if len(starts) != len(placements) or starts.keys() != {item.key for item in request.items}:
        return ("A plan must contain every required task exactly once.",)
    blocks = []
    for item in request.items:
        start = starts[item.key]
        if type(start) is not int:
            issues.append(f"{item.label} must start at a whole minute.")
            continue
        occupied_start = start - item.before
        occupied_end = start + item.duration + item.after
        if (occupied_start < request.start or occupied_end > request.end
                or (item.earliest is not None and start < item.earliest)
                or (item.latest is not None and start > item.latest)):
            issues.append(f"{item.label} falls outside its supported window or owner availability.")
        if is_fixed(item) and start != item.preferred:
            issues.append(f"{item.label} must keep its fixed start time.")
        blocks.append((occupied_start, occupied_end, item.label))

    for (a, b, name), (c, d, other) in combinations(sorted(blocks), 2):
        if a < d and c < b:
            issues.append(
                f"{name} ({clock(a)}–{clock(b)}) overlaps {other} ({clock(c)}–{clock(d)}), including travel."
            )
    return tuple(issues)


def target(item: CareItem, request: Request, preference: str) -> int:
    if item.preferred is not None:
        return item.preferred
    earliest, latest = bounds(item, request)
    if preference == "earlier":
        return earliest
    if preference == "later":
        return latest
    return (earliest + latest) // 2


def revise(request: Request, preference: str) -> tuple[tuple[Placement, ...], str]:
    """Search feasible starts and minimize priority-weighted timing deviations."""
    model = cp_model.CpModel()
    starts = []
    intervals = []
    costs = []
    priority_scale = len(request.items) * DAY + 1
    for index, item in enumerate(request.items):
        earliest, latest = bounds(item, request)
        start = model.new_int_var(earliest, latest, f"start_{index}")
        if is_fixed(item):
            model.add(start == item.preferred)
        duration = item.duration + item.before + item.after
        intervals.append(model.new_fixed_size_interval_var(start - item.before, duration, f"care_{index}"))
        deviation = model.new_int_var(0, DAY, f"deviation_{index}")
        model.add_abs_equality(deviation, start - target(item, request, preference))
        costs.append(deviation * priority_scale ** PRIORITY[item.priority])
        starts.append(start)
    model.add_no_overlap(intervals)
    model.minimize(sum(costs))

    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = 0
    solver.parameters.max_deterministic_time = 0.25
    status = solver.solve(model)
    name = solver.status_name(status)
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return tuple(Placement(item.key, solver.value(start))
                     for item, start in zip(request.items, starts, strict=True)), name
    return (), name


def explain(request: Request, placements: tuple[Placement, ...], preference: str) -> tuple[str, ...]:
    starts = {row.key: row.start for row in placements}
    explanations = []
    for item in sorted(request.items, key=lambda item: starts[item.key]):
        start = starts[item.key]
        if is_fixed(item):
            reason = f"kept the confirmed fixed time at {clock(start)}" if item.kind == "Medication" else (
                f"kept the fixed time at {clock(start)}"
            )
        elif item.preferred is None:
            reason = f"placed at {clock(start)} within the allowed window ({preference} timing preference)"
        elif start == item.preferred:
            reason = f"kept the preferred time at {clock(start)}"
        else:
            reason = (f"moved from {clock(item.preferred)} to {clock(start)} "
                      f"to fit the full plan ({item.priority} priority)")
        if item.before or item.after:
            reason += f" and reserved {item.before} min outbound and {item.after} min return travel"
        explanations.append(f"{item.label} {reason}.")
    return tuple(explanations)


def _blocked(request: Request, issues: tuple[str, ...], trace: list[str],
             initial: tuple[str, ...] = ()) -> Proposal:
    LOGGER.warning("proposal_blocked issues=%d stage=%s", len(issues), trace[-1])
    return Proposal(request, initial_issues=initial, issues=issues, trace=tuple(trace))


def propose(request: Request, goal: str = "", interpret: Callable[[str], str] | None = None) -> Proposal:
    issues = input_issues(request)
    if issues:
        return _blocked(request, issues, ["Input validation failed."])
    trace = [f"Input validation passed for {len(request.items)} tasks."]
    preference = request.preference
    if goal.strip():
        if interpret is None or len(goal) > 180:
            return _blocked(request, ("Use a short soft timing preference or choose it manually.",),
                            trace + ["Timing goal unavailable."])
        try:
            suggestion = interpret(goal)
            if suggestion == "clarify":
                return _blocked(request, ("Choose the timing preference manually and enter hard constraints in task fields.",),
                                trace + ["Model requested clarification."])
            if suggestion not in PREFERENCES:
                raise ValueError("Unexpected model preference")
            preference = suggestion
            trace.append(f"Local model selected {preference} for untimed tasks.")
        except (OSError, ValueError) as error:
            LOGGER.warning("local_model_fallback error=%s", type(error).__name__)
            trace.append(f"Local model unavailable or invalid. Used the manual {preference} preference.")

    draft = tuple(Placement(item.key, target(item, request, preference)) for item in request.items)
    initial = validate(request, draft)
    trace.append(f"Initial candidate validation found {len(initial)} issue(s).")
    if initial:
        draft, status = revise(request, preference)
        trace.append(f"Constraint search returned {status}.")
        if not draft:
            message = ("No schedule fits all required times, windows, and travel. "
                       "Review the fixed commitments and flexible windows."
                       if status == "INFEASIBLE" else
                       "Search could not verify a schedule. Narrow the windows or reduce the number of tasks.")
            return _blocked(request, (message,), trace, initial)
        issues = validate(request, draft)
        if issues:
            return _blocked(request, issues, trace + ["Revised candidate failed validation."], initial)
        trace.append("Revised candidate passed independent validation.")

    trace.append("Awaiting owner review.")
    LOGGER.info("proposal_ready tasks=%d initial_issues=%d preference=%s", len(draft), len(initial), preference)
    return Proposal(request, tuple(sorted(draft, key=lambda row: row.start)), initial,
                    explanations=explain(request, draft, preference), trace=tuple(trace),
                    preference=preference, status="pending")


def decide(proposal: Proposal, owner: Owner, current: Request, approve: bool) -> Proposal:
    """Apply all dates and times only after approval and a fresh validation."""
    if not proposal.ready:
        raise ValueError("Only a verified proposal awaiting review can be decided.")
    if not approve:
        LOGGER.info("proposal_rejected tasks=%d", len(proposal.placements))
        return replace(proposal, status="rejected", trace=proposal.trace + ("Owner rejected the proposal.",))

    live = snapshot(owner, current.day, current.start, current.end, current.preference)
    issues = ("Planning inputs changed. Generate a fresh proposal.",) if (
        current != proposal.request or live != current
    ) else validate(live, proposal.placements)
    if issues:
        LOGGER.warning("approval_blocked issues=%d", len(issues))
        return replace(proposal, status="blocked", issues=tuple(issues),
                       trace=proposal.trace + ("Approval checks failed.",))

    changes = [(owner.pets[p].tasks[t], clock(row.start))
               for row in proposal.placements for p, t in (row.key,)]
    for task, start in changes:
        task.update_task(time=start, due_date=live.day)
    LOGGER.info("proposal_applied tasks=%d", len(changes))
    return replace(proposal, status="approved", trace=proposal.trace + ("Owner approved. Revalidation passed and times were applied.",))
