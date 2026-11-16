"""Streamlit entry point for PawPal+ AI."""

from dataclasses import replace
from datetime import date, time
import logging

import streamlit as st

from examples import demo
from local_model import interpret_preference
from pawpal_system import CareRules, Owner, Pet, Scheduler, Task
from planning import KINDS, Proposal, clock, decide, looks_like_medication, minute, propose, snapshot

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")

st.set_page_config(page_title="PawPal+ AI", page_icon="🐾", layout="wide")
state = st.session_state
if "owner" not in state:
    state.owner = Owner(name="Pet Owner", available_time=240)
    state.audit = []
    state.applied = {}

owner = state.owner


def as_time(value: str | None) -> time | None:
    return time.fromisoformat(value) if value else None


def as_text(value: time | None) -> str | None:
    return value.strftime("%H:%M") if value is not None else None


def pet_label(index: int) -> str:
    pet = owner.pets[index]
    return f"{index + 1}. {pet.name} ({pet.breed})"


def task_label(option: tuple[int, int]) -> str:
    pet, index = option
    task = owner.pets[pet].tasks[index]
    return f"{pet_label(pet)} / {index + 1}. {task.name}"


def pending_tasks() -> list[tuple[int, int]]:
    return [(p, t) for p, pet in enumerate(owner.pets) for t, task in enumerate(pet.tasks)
            if not task.completed]


def render_task_form(pet: Pet, task: Task | None = None) -> None:
    saved = task or Task("", 20, "medium", "once")
    key = saved.task_id if task else "new"
    rules = saved.rules
    kind = st.selectbox("Care type", KINDS, index=KINDS.index(rules.kind), key=f"kind_{key}")
    with st.form(f"task_{key}"):
        fields = st.columns(3)
        name = fields[0].text_input("Task title", value=saved.name, max_chars=90, key=f"name_{key}")
        duration = fields[1].number_input("Duration (minutes)", min_value=1, max_value=1440,
                                          value=min(1440, max(1, int(saved.duration))), key=f"duration_{key}")
        priority = fields[2].selectbox("Priority", ("low", "medium", "high"),
                                       index=("low", "medium", "high").index(saved.priority), key=f"priority_{key}")
        description = st.text_input("Care notes (optional)", value=saved.description, max_chars=250)
        when = st.columns(3)
        day = when[0].date_input("Due date (optional)", value=saved.due_date)
        start = when[1].time_input("Start time (optional)", value=as_time(saved.time), step=60,
                                   key=f"start_{key}")
        frequencies = ("once", "daily", "weekly")
        frequency = when[2].selectbox("Frequency", frequencies,
                                      index=frequencies.index(saved.frequency) if saved.frequency in frequencies else 0)
        if kind in ("Medication", "Appointment"):
            fixed = True
        else:
            fixed = st.checkbox("Keep the start time fixed", value=rules.fixed)
        before = after = 0
        confirmed = False
        if kind == "Medication":
            confirmed = st.checkbox("I checked this fixed time against existing veterinary instructions",
                                    key=f"confirm_med_{key}_{saved.time}")
            if rules.kind == kind and rules.timing_confirmed:
                st.caption(f"The recorded time {saved.time} was previously confirmed. Confirm again for a new time.")
            st.caption("Use the prescribed timing for this reminder. Verify uncertain instructions with your veterinarian.")
        if kind == "Appointment":
            travel = st.columns(2)
            before = travel[0].number_input("Travel to appointment (minutes)", 0, 1440, rules.travel_before)
            after = travel[1].number_input("Return travel (minutes)", 0, 1440, rules.travel_after)
        with st.expander("Allowed start window"):
            window = st.columns(2)
            earliest = window[0].time_input("Earliest start (optional)", value=as_time(rules.earliest), step=60)
            latest = window[1].time_input("Latest start (optional)", value=as_time(rules.latest), step=60)
        clicked = st.form_submit_button("Save changes" if task else "Add task", type="primary",
                                        key="save_task" if task else "add_task")

    if not clicked:
        return
    if not name.strip():
        st.error("Enter a task title.")
        return
    if kind != "Medication" and looks_like_medication(name):
        st.error("Use the Medication care type for a medication reminder.")
        return
    if kind in ("Appointment", "Medication") and start is None:
        st.error("Enter a fixed start time.")
        return
    if fixed and start is None:
        st.error("Enter the start time to keep it fixed.")
        return
    if earliest is not None and latest is not None and earliest > latest:
        st.error("The latest start must be at or after the earliest start.")
        return

    if kind == "Medication" and rules.kind == kind and rules.timing_confirmed:
        confirmed = confirmed or as_text(start) == saved.time
    new_rules = CareRules(kind, fixed, as_text(earliest), as_text(latest), before, after, confirmed)
    values = dict(name=name.strip(), duration=duration, priority=priority,
                  frequency=frequency, description=description.strip(), time=as_text(start),
                  due_date=day, rules=new_rules)
    if task:
        task.update_task(**values, clear_time=start is None, clear_due_date=day is None)
    else:
        pet.add_task(Task(**values))
    st.success(f"Saved {name.strip()} for {pet.name}.")


def render_care() -> None:
    st.subheader("Pet profiles")
    with st.expander("Add a pet", expanded=not owner.pets, icon=":material/pets:"):
        with st.form("add_pet_form"):
            columns = st.columns((2, 2, 1))
            name = columns[0].text_input("Pet name", max_chars=50, key="pet_name")
            breed = columns[1].text_input("Breed or species", max_chars=50, key="pet_breed")
            age = columns[2].number_input("Age (years)", min_value=0, max_value=150, step=1, key="pet_age")
            add = st.form_submit_button("Add pet", type="primary", key="add_pet")
        if add:
            if name.strip() and breed.strip():
                owner.add_pet(Pet(name.strip(), breed.strip(), age))
                st.success(f"Added {name.strip()}.")
            else:
                st.error("Enter a pet name and breed or species.")
    if not owner.pets:
        st.info("Add a pet to start recording care tasks.")
        return

    selected = st.selectbox("Pet profile", options=range(len(owner.pets)), format_func=pet_label)
    pet = owner.pets[selected]
    st.caption(f"{pet.name} · {pet.breed} · {pet.age} years")
    st.subheader("Care tasks")
    with st.expander("Add care task", expanded=not pet.tasks, icon=":material/add_task:"):
        render_task_form(pet)
    open_tasks = pending_tasks()
    for_section = [option for option in open_tasks if option[0] == selected]
    if for_section:
        with st.expander("Edit care task", icon=":material/edit:"):
            edit = st.selectbox("Task to edit", options=for_section, format_func=task_label)
            render_task_form(pet, pet.tasks[edit[1]])
    if open_tasks:
        with st.expander("Complete a task", icon=":material/check_circle:"):
            with st.form("complete_task_form"):
                option = st.selectbox("Task to complete", options=open_tasks, format_func=task_label)
                finished_on = st.date_input("Completion date", value=date.today())
                completed = st.form_submit_button("Mark complete", key="complete_task_submit")
            if completed:
                p, t = option
                selected_pet = owner.pets[p]
                task = selected_pet.tasks[t]
                next_task = selected_pet.complete_task(task, finished_on)
                st.success(f"Completed {task.name} for {selected_pet.name}.")
                if next_task:
                    st.caption(f"Next occurrence due {next_task.due_date.isoformat()}.")

    st.subheader("Care task overview")
    scheduler = Scheduler(owner)
    filters = st.columns(2)
    names = [None, *dict.fromkeys(pet.name for pet in owner.pets)]
    pet_filter = filters[0].selectbox("Pet name filter", names, format_func=lambda n: n or "All pets")
    statuses = {"All tasks": None, "Incomplete": False, "Completed": True}
    status = filters[1].selectbox("Status filter", list(statuses))
    matches = {id(task) for task in scheduler.filter_tasks(pet_filter, statuses[status])}
    rows = sorted([
        {"Pet": pet_label(p), "Task": task.name, "Care type": task.rules.kind,
         "Date": str(task.due_date) if task.due_date else "Undated",
         "Start": task.time or "Untimed", "Minutes": task.duration, "Priority": task.priority,
         "Frequency": task.frequency, "Status": "Complete" if task.completed else "Open",
         "Notes": task.description}
        for p, profile in enumerate(owner.pets) for task in profile.tasks if id(task) in matches
    ], key=lambda row: (row["Start"] == "Untimed", row["Start"]))
    if rows:
        st.dataframe(rows, hide_index=True)
    else:
        st.info("No tasks match these filters.")
    warnings = scheduler.detect_conflicts()
    if warnings:
        with st.expander("Recorded time overlaps", expanded=True):
            for warning in warnings:
                st.warning(warning)


def render_timeline(proposal: Proposal) -> None:
    items = {item.key: item for item in proposal.request.items}
    rows = []
    for placement in proposal.placements:
        item = items[placement.key]
        rows.append({
            "Start": clock(placement.start),
            "End": clock(placement.start + item.duration),
            "Pet": item.pet, "Care task": item.name, "Type": item.kind,
            "Owner busy": f"{clock(placement.start - item.before)}–"
                          f"{clock(placement.start + item.duration + item.after)}",
        })
    st.dataframe(rows, hide_index=True)


def record(result: Proposal) -> None:
    state.audit = [*state.audit[-11:], (str(result.request.day), result.status, result.trace)]


def render_planner() -> None:
    st.subheader("Plan a day")
    st.caption("Review a daily proposal before you apply any task dates or times.")
    fields = st.columns(4)
    day = fields[0].date_input("Plan date", value=date.today(), key="plan_date")
    start = fields[1].time_input("Available from", time(7), step=60, key="available_from")
    end = fields[2].time_input("Available until", time(19), step=60, key="available_until")
    budget = fields[3].number_input("Care + travel budget (min)", min_value=1, max_value=1440,
                                    value=int(owner.available_time), key="care_budget")
    owner.update_availability(budget)
    labels = {"balanced": "Default", "earlier": "Earlier", "later": "Later"}
    preference = st.selectbox("Timing for untimed tasks", list(labels), format_func=labels.get)
    goal = ""
    with st.expander("Describe a timing preference with local AI", icon=":material/auto_awesome:"):
        goal = st.text_input("Soft timing preference (optional)", max_chars=180, key="goal",
                             placeholder="Leave untimed tasks until later in the day")
        st.caption("Use this for earlier or later timing. Enter fixed times and windows in the task fields.")
    request = snapshot(owner, day, minute(as_text(start)), minute(as_text(end)), preference)

    if st.button("Generate proposal", type="primary", key="generate_schedule"):
        with st.spinner("Checking the plan and revising conflicts…"):
            state.proposal = propose(request, goal, interpret_preference)
            state.proposal_goal = goal
            record(state.proposal)

    result = state.get("proposal")
    if result is not None:
        if result.initial_issues:
            with st.expander("What the first draft flagged", expanded=True):
                for message in result.initial_issues:
                    st.warning(message)
        for message in result.issues:
            st.error(message)
        for step in result.trace:
            if step.startswith("Local model"):
                st.caption(step)
        if result.ready:
            st.subheader("Proposed schedule")
            render_timeline(result)
            with st.expander("Why these times?", expanded=True):
                for explanation in result.explanations:
                    st.text(explanation)
            stale = request != result.request or goal != state.proposal_goal
            if stale:
                st.warning("Planning inputs changed. Generate a fresh proposal before approving.")
            actions = st.columns(2)
            approve = actions[0].button("Approve and apply", type="primary", disabled=stale, key="approve")
            reject = actions[1].button("Reject proposal", key="reject")
            if approve or reject:
                result = decide(result, owner, request, approve=approve)
                state.proposal = result
                record(result)
                if result.status == "approved":
                    state.applied[day] = result
                st.rerun()
        if result.status == "rejected":
            st.info("Proposal rejected. Your tasks were left as entered.")
        stages = "\n".join(result.trace)
        with st.expander("Validation and decision steps"):
            st.text(stages)

    applied = state.applied.get(day)
    if applied is not None:
        st.subheader("Applied schedule")
        st.success(f"Approved for {day.isoformat()}.")
        applied_starts = {row.key: row.start for row in applied.placements}
        applied_items = tuple(replace(item, preferred=applied_starts[item.key]) for item in applied.request.items)
        if request.items != applied_items:
            st.caption("This is the approved snapshot. Generate a new plan to account for current task changes.")
        render_timeline(applied)
    with st.expander("Decision history"):
        if not state.audit:
            st.caption("Proposals and decisions appear here.")
        for day_label, status, trace in reversed(state.audit):
            st.text(f"{day_label} · {status}\n" + "\n".join(trace))


with st.sidebar:
    st.markdown("### Your workspace")
    owner_name = st.text_input("Owner name", value=owner.name, max_chars=70, key="owner_name")
    if owner_name.strip():
        owner.name = owner_name.strip()
    else:
        st.warning("Enter an owner name.")
    st.caption("Pet profiles, plans, and activity history are stored for this session.")
    if not owner.pets and st.button("Load a sample day", icon=":material/science:", key="load_demo"):
        state.owner = demo("revised", date.today())
        state.owner.name = owner.name
        st.rerun()

st.title("PawPal+ AI")
st.caption("Intelligent Pet Care Planning Assistant")
st.info("For organizing pet care. Follow your veterinarian’s instructions for medication timing and doses.",
        icon=":material/info:")
care_tab, plan_tab = st.tabs(("Pets and tasks", "Daily planner"))
with care_tab:
    render_care()
with plan_tab:
    render_planner()
