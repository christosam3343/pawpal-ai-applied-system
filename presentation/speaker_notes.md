# PawPal+ AI · 6-minute speaking notes

## 0:00–0:40 · PawPal+ AI

Introduce the app as a way to coordinate feeding, walks, appointments, and existing reminders across multiple pets. Use the question “What has to move if I need to leave at 8 for an 8:30 vet visit?” to introduce the demo.

## 0:40–1:25 · Module 2 and the scheduling problem

The original project held pet profiles, sorted manually timed tasks, warned about recorded overlaps, and created recurring tasks on completion. Show how a warning alone still leaves the owner to find an alternative. Point out that the new workflow takes availability, windows, and travel into account across pets.

## 1:25–2:25 · Architecture

Walk from Streamlit to the daily snapshot. The planner checks a draft, calls CP-SAT when necessary, and independently checks the resulting schedule. Fixed times and owner availability are enforced in Python. Explain that the optional model interprets a narrow timing preference and can influence untimed tasks. The owner can inspect the explanation and must approve the plan before stored dates or times change.

## 2:25–4:15 · Live demonstration

Start Streamlit before the presentation and open a fresh session. Click **Load a sample day**, **Daily planner**, then **Generate proposal**. Show that the 08:30 appointment occupies 08:00–09:30 with travel. The walk moves from 08:00 to 07:25. The 07:55 medication reminder and the 08:30 appointment keep their fixed times.

Click **Reject proposal** and observe the rejection message. Generate the proposal again and click **Approve and apply**. Open **Decision history** to show the stored outcomes. If the app is unavailable, open the recorded `revised` scenario in [the execution logs](../evidence/scenarios.txt).

## 4:15–5:15 · Reliability and local model result

Report the 96 passing pytest cases and the 5/5 predefined scenarios, including the live local-model test. Describe how the evening phrase changes the untimed walk from 13:15 to 17:30 and leaves breakfast at 07:30. A missing medication confirmation blocks planning. A confirmed 08:15 medication time during travel also blocks the plan for a single caregiver.

## 5:15–6:00 · Limits and what changed during development

The model can misinterpret language, and the solver models one owner and one day. Profiles last for the session. Explain why verifying again at approval matters after an edit. End with the public repo and the text-based examples a reviewer can reproduce.
