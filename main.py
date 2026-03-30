# ─────────────────────────────────────────────────────────────
#  main.py  -  PawPal+ Demo Runner  (v2)
#  Each scenario exercises a different set of new features.
# ─────────────────────────────────────────────────────────────

from datetime import date
from pawpal_system import Pet, Owner, Task, Scheduler


# ═════════════════════════════════════════════════════════════
#  DISPLAY HELPERS
# ═════════════════════════════════════════════════════════════

def print_header(label: str) -> None:
    print(f"\n{'*' * 60}")
    print(f"  SCENARIO: {label}")
    print(f"{'*' * 60}\n")


def print_owner_summary(owner: Owner) -> None:
    pet_names = ", ".join(p.name for p in owner.pets) or "none"
    print(f"  Owner       : {owner.name}")
    print(f"  Pets        : {pet_names}")
    print(f"  Budget      : {owner.available_minutes} min")
    print(f"  Day starts  : {owner.day_start_hour}:00")
    print(f"  Buffer/gap  : {owner.buffer_minutes} min between tasks")


def print_task_table(tasks: list) -> None:
    print(f"  {'PRIORITY':<8}  {'CATEGORY':<10}  {'TITLE':<28}  DUR   PET")
    print(f"  {'-'*8}  {'-'*10}  {'-'*28}  {'-'*5}  {'-'*10}")
    for t in tasks:
        pet_name = t.pet.name if t.pet else "-"
        dep_tag  = " [has deps]" if t.depends_on else ""
        rec_tag  = f" [{t.recurrence}]" if t.is_recurring() else ""
        print(
            f"  {t.priority.upper():<8}  {t.category:<10}  "
            f"{t.title + dep_tag + rec_tag:<28}  {t.duration_minutes:<5}  {pet_name}"
        )


def print_schedule(owner: Owner, schedule) -> None:
    print("=" * 60)
    print(f"  PawPal+ Daily Schedule  --  {owner.name}")
    print("=" * 60)

    # ── scheduled tasks ───────────────────────────────────────
    used  = schedule.total_minutes_used
    total = owner.available_minutes
    if not schedule.is_empty():
        bar_n      = int((used / total) * 24) if total else 0
        bar        = "#" * bar_n + "-" * (24 - bar_n)
        efficiency = schedule.efficiency_score(total)

        print(f"\n  Scheduled  ({len(schedule.scheduled_tasks)} tasks, "
              f"{used}/{total} min)")
        print(f"  [{bar}] {efficiency}% efficient\n")

        for idx, st in enumerate(schedule.scheduled_tasks, 1):
            t       = st.task
            pet_tag = f"  [{t.pet.name}]" if t.pet else ""
            rec_tag = f"  ({t.recurrence})" if t.is_recurring() else ""
            print(f"  {idx}. [{t.priority.upper():6}] {t.title}{pet_tag}{rec_tag}")
            print(f"       Category : {t.category}")
            print(f"       Duration : {t.duration_minutes} min")
            print(f"       Time     : {st.time_label(owner.day_start_hour)}")
            print()
    else:
        print("\n  No tasks could be scheduled in the available time.\n")

    # ── skipped tasks ─────────────────────────────────────────
    if schedule.skipped_tasks:
        print("-" * 60)
        print(f"  Skipped  ({len(schedule.skipped_tasks)} tasks)\n")
        for task, reason in schedule.skipped_tasks:
            print(f"  [SKIP] {task.title}  ({task.duration_minutes} min, {task.priority})")
            print(f"         {reason}")
            print()

    # ── warnings ──────────────────────────────────────────────
    if schedule.warnings:
        print("-" * 60)
        print(f"  Warnings  ({len(schedule.warnings)})\n")
        for w in schedule.warnings:
            print(f"  [!] [{w.warning_type}]")
            print(f"      {w.message}")
            print()

    # ── priority breakdown ────────────────────────────────────
    bd = schedule.priority_breakdown()
    print("-" * 60)
    print("  Priority breakdown:")
    for level in ("high", "medium", "low"):
        s = bd[level]["scheduled"]
        k = bd[level]["skipped"]
        print(f"    {level.upper():<6}  scheduled={s}  skipped={k}")

    print("=" * 60)


def run_scenario(label: str, owner: Owner, tasks: list,
                 extra_demo=None) -> object:
    """
    Run scheduler + print results.
    Returns the Schedule object so callers can inspect it further.
    """
    print_header(label)

    if not tasks:
        print("  No tasks provided.")
        return None
    if owner.available_minutes <= 0:
        print(f"  {owner.name} has 0 free minutes today.")
        return None

    print_owner_summary(owner)
    print()
    print("  Tasks submitted:")
    print_task_table(tasks)
    print()

    schedule = Scheduler(owner=owner, tasks=tasks).generate()
    print_schedule(owner, schedule)

    if extra_demo:
        extra_demo(schedule, owner)

    return schedule


# ═════════════════════════════════════════════════════════════
#  NEXT-DAY RECURRING HELPER  (used in Scenario 5)
# ═════════════════════════════════════════════════════════════

def _show_next_day(schedule) -> None:
    """Print the auto-generated task list for tomorrow."""
    next_tasks = schedule.get_recurring_tasks_for_next_day()
    print(f"\n  --- Tomorrow's auto-generated task list ({len(next_tasks)} tasks) ---")
    for t in next_tasks:
        # Check whether this task was skipped today (if so it was promoted)
        was_skipped = any(task.title == t.title for task, _ in schedule.skipped_tasks)
        tag = " [PRIORITY PROMOTED - was skipped today]" if was_skipped else ""
        print(f"  {t.priority.upper():<6} {t.title}{tag}")


# ═════════════════════════════════════════════════════════════
#  SHARED PETS
# ═════════════════════════════════════════════════════════════

buddy   = Pet(name="Buddy",   species="dog", age=3)
whisker = Pet(name="Whisker", species="cat", age=5,
              health_notes="Sensitive stomach - 2 small meals only")


# ═════════════════════════════════════════════════════════════
#  SCENARIOS
# ═════════════════════════════════════════════════════════════

if __name__ == "__main__":

    # ─────────────────────────────────────────────────────────
    #  SCENARIO 1
    #  Features: B1 pet-tagging, B3 categories, C1-C3 filters,
    #            F1 efficiency score, F2 priority breakdown
    # ─────────────────────────────────────────────────────────
    tasks_s1 = [
        Task("Morning Walk",        30, "high",   pet=buddy,   category="exercise"),
        Task("Feed Buddy Breakfast", 10, "high",   pet=buddy,   category="feeding"),
        Task("Feed Whisker",         10, "high",   pet=whisker, category="feeding"),
        Task("Litter Box Clean",     10, "high",   pet=whisker, category="hygiene"),
        Task("Playtime with Buddy",  20, "medium", pet=buddy,   category="play"),
        Task("Brush Whisker",        15, "medium", pet=whisker, category="grooming"),
        Task("Training Tricks",      15, "low",    pet=buddy,   category="training"),
        Task("Leisurely Stroll",     40, "low",    pet=buddy,   category="exercise"),
    ]

    def demo_filters(schedule, owner):
        print("\n  --- Filter demos ---")
        buddy_tasks = schedule.tasks_for_pet(buddy)
        print(f"  Buddy's scheduled tasks ({len(buddy_tasks)}):")
        for st in buddy_tasks:
            print(f"    - {st.task.title}")

        exercise = schedule.tasks_by_category("exercise")
        print(f"\n  Exercise tasks scheduled ({len(exercise)}):")
        for st in exercise:
            print(f"    - {st.task.title}  ({st.time_label(owner.day_start_hour)})")

        high_tasks = schedule.tasks_by_priority("high")
        print(f"\n  High-priority tasks scheduled ({len(high_tasks)}):")
        for st in high_tasks:
            print(f"    - {st.task.title}")

    run_scenario(
        label="Pet-tagged tasks + filters (90 min, 5 min buffer)",
        owner=Owner("Jordan", available_minutes=90, pets=[buddy, whisker],
                    day_start_hour=8, buffer_minutes=5),
        tasks=tasks_s1,
        extra_demo=demo_filters,
    )

    # ─────────────────────────────────────────────────────────
    #  SCENARIO 2
    #  Features: B5 depends_on, A4 topological sort
    #  "Give medicine" must happen AFTER "Feed Breakfast"
    # ─────────────────────────────────────────────────────────
    feed_breakfast = Task("Feed Breakfast",  10, "high",   pet=buddy, category="feeding")
    give_medicine  = Task("Give Medicine",    5, "high",   pet=buddy, category="medical",
                          depends_on=[feed_breakfast])   # B5: dep declared here
    evening_walk   = Task("Evening Walk",    25, "medium", pet=buddy, category="exercise")
    groom_buddy    = Task("Groom Buddy",     20, "medium", pet=buddy, category="grooming")

    run_scenario(
        label="Task dependencies  --  Medicine only AFTER Breakfast  (A4/B5)",
        owner=Owner("Jordan", available_minutes=70, pets=[buddy],
                    day_start_hour=7),
        tasks=[give_medicine, feed_breakfast, evening_walk, groom_buddy],
        # Note: give_medicine is listed FIRST but the scheduler must
        # put feed_breakfast before it because of the dependency.
    )

    # ─────────────────────────────────────────────────────────
    #  SCENARIO 3
    #  Features: D2 double-feeding warning, D3 exercise-after-meal
    # ─────────────────────────────────────────────────────────
    tasks_s3 = [
        Task("Feed Buddy Breakfast", 10, "high",   pet=buddy,   category="feeding"),
        Task("Morning Run",          20, "high",   pet=buddy,   category="exercise"),
        Task("Feed Buddy Lunch",     10, "medium", pet=buddy,   category="feeding"),
        Task("Afternoon Walk",       30, "low",    pet=buddy,   category="exercise"),
    ]

    run_scenario(
        label="Conflict detection  --  Double feeding + walk after meal  (D2/D3)",
        owner=Owner("Jordan", available_minutes=120, pets=[buddy]),
        tasks=tasks_s3,
    )

    # ─────────────────────────────────────────────────────────
    #  SCENARIO 4
    #  Features: A3 time-windows (earliest_start + deadline)
    # ─────────────────────────────────────────────────────────
    tasks_s4 = [
        Task("Morning Walk",    30, "high",   pet=buddy,
             earliest_start_minute=0,
             deadline_minute=60),          # must finish within first hour
        Task("Vet Appointment", 45, "high",  pet=buddy,
             earliest_start_minute=120,    # can't start before 2 hours in
             deadline_minute=180),         # must finish within 3 hours
        Task("Feed Breakfast",  10, "high",  pet=buddy,   category="feeding"),
        Task("Groom Buddy",     20, "medium",pet=buddy,   category="grooming"),
        Task("Nap Time",        60, "low",   pet=whisker),
    ]

    run_scenario(
        label="Time-window enforcement  --  earliest_start + deadline  (A3)",
        owner=Owner("Jordan", available_minutes=180, pets=[buddy, whisker],
                    day_start_hour=9),
        tasks=tasks_s4,
    )

    # ─────────────────────────────────────────────────────────
    #  SCENARIO 5
    #  Features: B2 recurring tasks, F4 next-day carry-forward
    # ─────────────────────────────────────────────────────────
    tasks_s5 = [
        Task("Feed Buddy",      10, "high",   pet=buddy,   category="feeding",
             recurrence="daily"),
        Task("Feed Whisker",    10, "high",   pet=whisker, category="feeding",
             recurrence="daily"),
        Task("Morning Walk",    30, "high",   pet=buddy,   category="exercise",
             recurrence="daily"),
        Task("Weekly Groom",    40, "medium", pet=buddy,   category="grooming",
             recurrence="weekly"),
        Task("Vet Checkup",     60, "medium", pet=buddy,   category="medical",
             recurrence="monthly"),
        Task("Play Session",    25, "low",    pet=whisker, category="play",
             recurrence="daily"),
    ]

    def demo_recurring(schedule, owner):
        next_tasks = schedule.get_recurring_tasks_for_next_day()
        print(f"\n  --- Tomorrow's recurring task list ({len(next_tasks)} tasks) ---")
        for t in next_tasks:
            print(f"  {t.priority.upper():<6} {t.title}")

    run_scenario(
        label="Recurring tasks + next-day carry-forward  (B2/F4)",
        owner=Owner("Jordan", available_minutes=70, pets=[buddy, whisker]),
        tasks=tasks_s5,
        extra_demo=lambda sched, own: _show_next_day(sched),
    )

    # ─────────────────────────────────────────────────────────
    #  SCENARIO 6
    #  Features: A1 fill-the-gap, D4 duplicate detection
    # ─────────────────────────────────────────────────────────
    tasks_s6 = [
        Task("Morning Walk",    50, "high",   pet=buddy,   category="exercise"),
        Task("Morning Walk",    50, "high",   pet=buddy,   category="exercise"),  # D4 duplicate
        Task("Feed Breakfast",  10, "high",   pet=buddy,   category="feeding"),
        Task("Quick Cuddle",    15, "medium", pet=whisker, category="play"),
        Task("Treat Training",  10, "low",    pet=buddy,   category="training"),
    ]
    # With 80 min budget: "Morning Walk" (50) + "Feed Breakfast" (10) = 60 min used.
    # 20 min left.  Greedy would skip "Quick Cuddle" (15 min skipped? no, 15 fits).
    # The fill-gap pass rescues "Treat Training" (10 min) if it was skipped.

    run_scenario(
        label="Fill-the-gap + duplicate detection  (A1/D4)",
        owner=Owner("Jordan", available_minutes=80, pets=[buddy, whisker]),
        tasks=tasks_s6,
    )

    # ─────────────────────────────────────────────────────────
    #  SCENARIO 7
    #  Features: B4 status tracking, C4 pending/done filters,
    #            E1 custom day-start hour
    # ─────────────────────────────────────────────────────────
    tasks_s7 = [
        Task("Early Morning Walk", 30, "high",   pet=buddy,   category="exercise"),
        Task("Feed Buddy",         10, "high",   pet=buddy,   category="feeding"),
        Task("Groom Buddy",        20, "medium", pet=buddy,   category="grooming"),
        Task("Play with Whisker",  15, "low",    pet=whisker, category="play"),
    ]

    def demo_status(schedule, owner):
        # Simulate completing the first two tasks
        for st in schedule.scheduled_tasks[:2]:
            st.mark_done()

        pending   = schedule.pending_tasks()
        completed = schedule.completed_tasks()

        print(f"\n  --- Status tracking demo (first 2 tasks marked done) ---")
        print(f"  Completed ({len(completed)}):")
        for st in completed:
            print(f"    [DONE]    {st.task.title}")
        print(f"  Still pending ({len(pending)}):")
        for st in pending:
            print(f"    [PENDING] {st.task.title}")

    run_scenario(
        label="Status tracking + 6 AM day-start  (B4/C4/E1)",
        owner=Owner("Jordan", available_minutes=90, pets=[buddy, whisker],
                    day_start_hour=6),
        tasks=tasks_s7,
        extra_demo=demo_status,
    )

    # ─────────────────────────────────────────────────────────
    #  SCENARIO 8
    #  Features: sort_by_time(), filter_by_status(), filter_by_pet()
    #
    #  Tasks are added DELIBERATELY out of chronological order.
    #  We first print them as entered, then sorted, then filtered.
    # ─────────────────────────────────────────────────────────
    print_header("Sort by time + Filter by status / pet  (sort_by_time / filter_by_pet / filter_by_status)")

    # Tasks entered out of order on purpose
    s8_tasks = [
        Task("Evening Walk",        25, "medium", pet=buddy,
             category="exercise",   preferred_time="18:30"),
        Task("Litter Box Clean",    10, "high",   pet=whisker,
             category="hygiene",    preferred_time="07:00"),
        Task("Give Flea Medicine",   5, "high",   pet=buddy,
             category="medical",    preferred_time="09:15"),
        Task("Afternoon Nap",       30, "low",    pet=whisker,
             category="other",      preferred_time="13:00"),
        Task("Feed Buddy Dinner",   10, "high",   pet=buddy,
             category="feeding",    preferred_time="17:00"),
        Task("Morning Walk",        30, "high",   pet=buddy,
             category="exercise",   preferred_time="07:30"),
        Task("Feed Whisker Lunch",  10, "medium", pet=whisker,
             category="feeding",    preferred_time="12:00"),
        Task("Training Session",    20, "low",    pet=buddy,
             category="training",   preferred_time=None),     # no time set
    ]

    owner_s8 = Owner("Jordan", available_minutes=120,
                     pets=[buddy, whisker], day_start_hour=7)

    scheduler_s8 = Scheduler(owner=owner_s8, tasks=s8_tasks)

    # ── Step A: Print tasks as entered (unordered) ────────────
    print("  STEP A — Tasks as entered (out of chronological order):")
    print(f"  {'#':<3}  {'TIME':<6}  {'PRIORITY':<8}  {'TITLE':<25}  PET")
    print(f"  {'-'*3}  {'-'*6}  {'-'*8}  {'-'*25}  {'-'*10}")
    for i, t in enumerate(s8_tasks, 1):
        time_display = t.preferred_time if t.preferred_time else "-- :--"
        print(f"  {i:<3}  {time_display:<6}  {t.priority.upper():<8}  {t.title:<25}  {t.pet.name if t.pet else '-'}")

    # ── Step B: Sort by preferred_time using sort_by_time() ──
    sorted_tasks = scheduler_s8.sort_by_time()

    print(f"\n  STEP B — After sort_by_time()  [lambda key: (int(HH), int(MM))]:")
    print(f"  {'#':<3}  {'TIME':<6}  {'PRIORITY':<8}  {'TITLE':<25}  PET")
    print(f"  {'-'*3}  {'-'*6}  {'-'*8}  {'-'*25}  {'-'*10}")
    for i, t in enumerate(sorted_tasks, 1):
        time_display = t.preferred_time if t.preferred_time else "no time"
        print(f"  {i:<3}  {time_display:<8}  {t.priority.upper():<8}  {t.title:<25}  {t.pet.name if t.pet else '-'}")

    # ── Step C: Generate schedule + simulate partial completion
    schedule_s8 = scheduler_s8.generate()

    # Mark first 3 scheduled tasks as done to demo status filtering
    for st in schedule_s8.scheduled_tasks[:3]:
        st.mark_done()

    all_tasks_flat = s8_tasks  # the full pool for status filtering

    print(f"\n  STEP C — Schedule generated. First 3 tasks marked DONE.")
    print(f"           Simulating mid-day: some tasks done, rest still pending.")

    # ── Step D: filter_by_status ──────────────────────────────
    print(f"\n  STEP D — filter_by_status('done'):")
    done_tasks = scheduler_s8.filter_by_status("done")
    if done_tasks:
        for t in done_tasks:
            print(f"    [DONE]    {t.title}  ({t.pet.name if t.pet else '-'})")
    else:
        print("    (none)")

    print(f"\n  STEP D — filter_by_status('pending'):")
    pending_tasks = scheduler_s8.filter_by_status("pending")
    if pending_tasks:
        for t in pending_tasks:
            print(f"    [PENDING] {t.title}  ({t.pet.name if t.pet else '-'})")
    else:
        print("    (none)")

    print(f"\n  STEP D — filter_by_status('skipped'):")
    skipped_tasks = scheduler_s8.filter_by_status("skipped")
    if skipped_tasks:
        for t in skipped_tasks:
            print(f"    [SKIPPED] {t.title}  ({t.pet.name if t.pet else '-'})")
    else:
        print("    (none)")

    # ── Step E: filter_by_pet ─────────────────────────────────
    print(f"\n  STEP E — filter_by_pet('Buddy')  [case-insensitive]:")
    buddy_tasks = scheduler_s8.filter_by_pet("buddy")   # lowercase on purpose
    for t in buddy_tasks:
        time_display = t.preferred_time if t.preferred_time else "no time"
        print(f"    [{t.status.upper():7}] {t.title:<25}  @ {time_display}")

    print(f"\n  STEP E — filter_by_pet('Whisker'):")
    whisker_tasks = scheduler_s8.filter_by_pet("Whisker")
    for t in whisker_tasks:
        time_display = t.preferred_time if t.preferred_time else "no time"
        print(f"    [{t.status.upper():7}] {t.title:<25}  @ {time_display}")

    print()

    # ---------------------------------------------------------
    #  SCENARIO 9
    #  Features: due_date on Task, _next_due_date() via timedelta,
    #            mark_done() auto-spawning next occurrence,
    #            Scheduler.collect_next_occurrences()
    # ---------------------------------------------------------
    print_header("Auto next-occurrence via timedelta  (due_date / mark_done / collect_next_occurrences)")

    today = date.today()

    # Owner with plenty of time so all tasks get scheduled
    owner_s9 = Owner(
        name="Riley",
        available_minutes=120,
        pets=[buddy, whisker],
        day_start_hour=8,
    )

    # Mix of daily, weekly, and non-recurring tasks, all due today
    tasks_s9 = [
        Task("Feed Buddy Morning",   10, "high",   pet=buddy,
             category="feeding",   recurrence="daily",  due_date=today),
        Task("Morning Walk",         20, "high",   pet=buddy,
             category="exercise",  recurrence="daily",  due_date=today),
        Task("Weekly Groom Buddy",   30, "medium", pet=buddy,
             category="grooming",  recurrence="weekly", due_date=today),
        Task("One-off Vet Visit",    45, "high",   pet=whisker,
             category="medical",   recurrence="none",   due_date=today),
        Task("Feed Whisker Morning", 10, "high",   pet=whisker,
             category="feeding",   recurrence="daily",  due_date=today),
    ]

    print_owner_summary(owner_s9)
    print()
    print("  Tasks submitted:")
    print_task_table(tasks_s9)
    print()

    scheduler_s9 = Scheduler(owner=owner_s9, tasks=tasks_s9)
    schedule_s9  = scheduler_s9.generate()

    print_schedule(owner_s9, schedule_s9)

    # Mark every scheduled task as done
    print("\n  --- Marking all scheduled tasks as DONE ---")
    for st in schedule_s9.scheduled_tasks:
        st.mark_done()
        print(f"  [DONE] {st.task.title}")

    # Collect auto-generated next occurrences
    next_occurrences = scheduler_s9.collect_next_occurrences()

    # Print the next-occurrence table
    print(f"\n  --- Next-occurrence tasks ({len(next_occurrences)} recurring tasks) ---")
    print()

    # Column widths
    col_title    = 24
    col_rec      = 8
    col_orig     = 12
    col_next     = 12
    col_delta    = 10

    header = (
        f"  {'TITLE':<{col_title}}  "
        f"{'RECUR':<{col_rec}}  "
        f"{'ORIG DATE':<{col_orig}}  "
        f"{'NEXT DATE':<{col_next}}  "
        f"{'TIMEDELTA':<{col_delta}}"
    )
    divider = (
        f"  {'-'*col_title}  "
        f"{'-'*col_rec}  "
        f"{'-'*col_orig}  "
        f"{'-'*col_next}  "
        f"{'-'*col_delta}"
    )

    print(header)
    print(divider)

    for t in next_occurrences:
        # Find the original task (parent) by matching title
        parent = next(
            (orig for orig in tasks_s9 if orig.title == t.title),
            None,
        )
        orig_date = parent.due_date.isoformat() if parent else "?"
        next_date = t.due_date.isoformat()

        # Describe the timedelta that was applied
        rec = t.recurrence
        if rec == "daily":
            delta_label = "+1 day"
        elif rec == "weekly":
            delta_label = "+7 days"
        elif rec == "monthly":
            delta_label = "+30 days"
        else:
            delta_label = "n/a"

        print(
            f"  {t.title:<{col_title}}  "
            f"{rec:<{col_rec}}  "
            f"{orig_date:<{col_orig}}  "
            f"{next_date:<{col_next}}  "
            f"{delta_label:<{col_delta}}"
        )

    print()

    # ─────────────────────────────────────────────────────────
    #  SCENARIO 10
    #  Feature: D1 — time-window overlap detection
    #
    #  Tasks are given preferred_time values that deliberately
    #  overlap so the Scheduler emits overlap warnings.
    #
    #  Overlaps planted in this scenario:
    #    A) "Buddy Bath"   09:00-09:30  vs
    #       "Morning Walk" 09:15-09:35  → 15-min overlap (same pet)
    #
    #    B) "Buddy Bath"   09:00-09:30  vs
    #       "Feed Whisker" 09:00-09:10  → 10-min overlap (different pets)
    #
    #    C) "Vet Visit"    10:00-10:45  has no overlap (clean window)
    # ─────────────────────────────────────────────────────────
    print_header("Time-window overlap detection  (D1 / _check_time_overlaps)")

    tasks_s10 = [
        # preferred_time="09:00", duration=30 → window [09:00, 09:30)
        Task("Buddy Bath",       30, "high",
             pet=buddy,   category="grooming",
             preferred_time="09:00"),

        # preferred_time="09:15", duration=20 → window [09:15, 09:35)
        # Overlaps "Buddy Bath" by 15 min — SAME pet conflict
        Task("Morning Walk",     20, "medium",
             pet=buddy,   category="exercise",
             preferred_time="09:15"),

        # preferred_time="09:00", duration=10 → window [09:00, 09:10)
        # Overlaps "Buddy Bath" by 10 min — DIFFERENT pet conflict
        Task("Feed Whisker",     10, "high",
             pet=whisker, category="feeding",
             preferred_time="09:00"),

        # preferred_time="10:00", duration=45 → window [10:00, 10:45)
        # Clean window — no overlap with any other task
        Task("Vet Visit",        45, "high",
             pet=whisker, category="medical",
             preferred_time="10:00"),
    ]

    owner_s10 = Owner("Jordan", available_minutes=120,
                      pets=[buddy, whisker], day_start_hour=9)

    # ── Show tasks and their intended time windows ─────────────
    print("  Tasks and their intended preferred_time windows:\n")
    print(f"  {'TASK':<20}  {'PET':<8}  {'START':<6}  {'DUR':>4}  END")
    print(f"  {'-'*20}  {'-'*8}  {'-'*6}  {'-'*4}  {'-'*6}")
    for t in tasks_s10:
        if t.preferred_time:
            h, m  = t.preferred_time.split(":")
            start = int(h) * 60 + int(m)
            end_m = start + t.duration_minutes
            end_h = end_m // 60
            end_s = f"{end_h}:{end_m % 60:02d}"
        else:
            end_s = "n/a"
        pet_name = t.pet.name if t.pet else "-"
        print(f"  {t.title:<20}  {pet_name:<8}  {t.preferred_time or 'n/a':<6}  "
              f"{t.duration_minutes:>4}  {end_s}")

    print()

    # ── Run scheduler — warnings fire inside generate() ───────
    scheduler_s10 = Scheduler(owner=owner_s10, tasks=tasks_s10)
    schedule_s10  = scheduler_s10.generate()

    # ── Print the full schedule (shows warnings section) ──────
    print_schedule(owner_s10, schedule_s10)

    # ── Zoom in: print only the overlap warnings with detail ──
    overlap_warnings = [w for w in schedule_s10.warnings
                        if w.warning_type == "time_overlap"]

    print(f"\n  --- Overlap warnings only ({len(overlap_warnings)} detected) ---\n")
    if overlap_warnings:
        for idx, w in enumerate(overlap_warnings, 1):
            print(f"  [{idx}] {w.message}")
            if len(w.tasks) == 2:
                a, b = w.tasks
                print(f"      Task A: '{a.title}'  |  pet: {a.pet.name if a.pet else '-'}"
                      f"  |  time: {a.preferred_time}  |  dur: {a.duration_minutes} min")
                print(f"      Task B: '{b.title}'  |  pet: {b.pet.name if b.pet else '-'}"
                      f"  |  time: {b.preferred_time}  |  dur: {b.duration_minutes} min")
            print()
    else:
        print("  (no overlaps found)")

    print("\n  Have a great day with your pets!\n")


# ─────────────────────────────────────────────────────────────
#  Helper used by scenario 5 (defined outside if-block so the
#  lambda can reference it cleanly)
# ─────────────────────────────────────────────────────────────

def _show_next_day(schedule):
    next_tasks = schedule.get_recurring_tasks_for_next_day()
    print(f"\n  --- Tomorrow's auto-generated task list ({len(next_tasks)} tasks) ---")
    promotion = {"low": "medium", "medium": "high", "high": "high"}
    for t in next_tasks:
        # Find original priority before promotion
        original = next(
            (task.priority for task, _ in schedule.skipped_tasks
             if task.title == t.title),
            t.priority
        )
        promoted = original != t.priority
        tag = " [PRIORITY PROMOTED - was skipped today]" if promoted else ""
        print(f"  {t.priority.upper():<6} {t.title}{tag}")
