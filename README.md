# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Smarter Scheduling

Beyond the basic greedy priority pass, PawPal+ includes several algorithmic improvements that make the scheduler more realistic and robust.

### Fill-the-gap second pass
After the initial priority pass, any minutes left over are used to rescue tasks that were skipped only because a large high-priority task consumed the budget. Tasks are retried in priority order, so the most important skipped task gets the first shot at leftover time.

### Dependency ordering
Tasks can declare prerequisites via `depends_on`. The scheduler runs a topological sort (Kahn's algorithm with a priority-weighted min-heap) before placing any tasks, guaranteeing that a task like "Give Medicine" always follows "Feed Breakfast" — no matter how priority sorting would otherwise arrange them.

### Time windows
Each task supports an `earliest_start_minute` and a `deadline_minute`. The scheduler advances its internal clock to honour earliest-start constraints and skips tasks outright when they cannot finish before their deadline.

### Buffer gaps
`Owner.buffer_minutes` inserts a mandatory rest period between every scheduled task — useful for walks that need cool-down time or appointments that require travel.

### Recurring tasks
Tasks with a `recurrence` of `"daily"` or `"weekly"` automatically spawn a clone for the next occurrence the moment they are marked complete. Call `Scheduler.collect_next_occurrences()` to retrieve the upcoming task list.

### Conflict detection
The scheduler runs three advisory checks after building the schedule and attaches warnings without ever removing tasks:

| Check | What it catches |
|---|---|
| **Time-window overlap** | Two tasks whose `preferred_time` windows overlap (pre-schedule) |
| **Double-feeding guard** | Two feeding tasks placed fewer than 120 minutes apart |
| **Exercise-after-meal** | An exercise task starting within 30 minutes of a feeding task for a dog |

### Sort and filter helpers
- `sort_by_time()` — order any task list by `preferred_time` ("HH:MM"), with un-timed tasks sorted to the end.
- `filter_by_status()` — return only `"pending"`, `"done"`, or `"skipped"` tasks.
- `filter_by_pet()` — return only tasks assigned to a specific pet (case-insensitive).

---

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.
