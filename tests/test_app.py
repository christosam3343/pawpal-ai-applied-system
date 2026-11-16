from datetime import time
from pathlib import Path

from streamlit.testing.v1 import AppTest


def open_app():
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py").run()
    assert not app.exception
    return app


def sample_day():
    app = open_app()
    app.button(key="load_demo").click().run()
    assert not app.exception
    return app


def test_streamlit_approval_and_rejection():
    app = sample_day()
    app.button(key="generate_schedule").click().run()
    assert app.session_state["proposal"].ready
    assert app.session_state["owner"].pets[0].tasks[0].time == "08:00"
    app.button(key="reject").click().run()
    assert not app.exception and app.session_state["proposal"].status == "rejected"
    assert app.session_state["owner"].pets[0].tasks[0].time == "08:00"
    app.button(key="generate_schedule").click().run()
    app.button(key="approve").click().run()
    assert not app.exception and app.session_state["proposal"].status == "approved"
    assert app.session_state["owner"].pets[0].tasks[0].time == "07:25"


def test_streamlit_disables_stale_approval_and_blocks_empty_plan():
    app = open_app()
    app.button(key="generate_schedule").click().run()
    assert app.session_state["proposal"].status == "blocked"
    app.button(key="load_demo").click().run()
    app.button(key="generate_schedule").click().run()
    app.time_input(key="available_from").set_value(time(7, 30)).run()
    assert not app.exception
    assert app.button(key="approve").disabled


def test_editing_medication_time_requires_a_fresh_confirmation():
    app = sample_day()
    selectors = [widget for widget in app.selectbox if widget.label == "Task to edit"]
    selectors[0].set_value((0, 1)).run()
    owner = app.session_state["owner"]
    task = owner.pets[0].tasks[1]
    app.time_input(key=f"start_{task.task_id}").set_value(time(7, 50))
    app.button(key="save_task").click().run()
    assert not app.exception
    assert task.time == "07:50" and not task.rules.timing_confirmed
    app.button(key="generate_schedule").click().run()
    assert app.session_state["proposal"].status == "blocked"


def test_add_and_complete_custom_recurring_task():
    app = open_app()
    app.text_input(key="pet_name").set_value("Nori")
    app.text_input(key="pet_breed").set_value("Terrier")
    app.button(key="add_pet").click().run()
    app.text_input(key="name_new").set_value("Morning walk")
    frequency = next(widget for widget in app.selectbox if widget.label == "Frequency")
    frequency.set_value("daily")
    app.button(key="add_task").click().run()
    app.button(key="complete_task_submit").click().run()
    assert not app.exception
    tasks = app.session_state["owner"].pets[0].tasks
    assert len(tasks) == 2 and tasks[0].completed and not tasks[1].completed
