"""Synthetic care records used by the app's demo and evaluation harness."""

from datetime import date

from pawpal_system import CareRules, Owner, Pet, Task

DEMO_DATE = date(2026, 11, 16)


def demo(scenario: str, day: date = DEMO_DATE) -> Owner:
    owner = Owner("Demo owner", 240)
    biscuit = Pet("Biscuit", "Golden retriever", 3)
    luna = Pet("Luna", "Domestic shorthair", 2)
    owner.add_pet(biscuit)
    owner.add_pet(luna)

    if scenario in ("normal", "timing-goal"):
        luna.add_task(Task("Breakfast", 15, "high", "daily", time="07:30",
                           due_date=day, rules=CareRules("Feeding")))
        biscuit.add_task(Task("Walk", 30, "medium", "daily", due_date=day,
                              rules=CareRules("Walk", earliest="09:00", latest="17:30")))
        return owner

    biscuit.add_task(Task("Morning walk", 30, "low", "daily", time="08:00",
                          due_date=day, rules=CareRules("Walk", earliest="07:00", latest="11:30")))
    biscuit.add_task(Task("Recorded medication reminder", 5, "high", "daily",
                          time="07:55" if scenario == "revised" else "08:15",
                          due_date=day, rules=CareRules("Medication", timing_confirmed=scenario != "guardrail")))
    luna.add_task(Task("Vet appointment", 30, "high", "once", time="08:30", due_date=day,
                       rules=CareRules("Appointment", travel_before=30, travel_after=30)))
    return owner
