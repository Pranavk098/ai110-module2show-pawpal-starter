# ─────────────────────────────────────────────────────────────
#  test_pawpal.py  –  Unit tests for pawpal_system.py
#  Run with:  python -m unittest test_pawpal -v
# ─────────────────────────────────────────────────────────────

import unittest
from pawpal_system import Pet, Owner, Task, ScheduledTask, Schedule, Scheduler


# ══════════════════════════════════════════════════════════════
#  Pet
# ══════════════════════════════════════════════════════════════
class TestPet(unittest.TestCase):

    def test_attributes_stored_correctly(self):
        pet = Pet("Buddy", "dog")
        self.assertEqual(pet.name, "Buddy")
        self.assertEqual(pet.species, "dog")

    def test_repr_contains_name_and_species(self):
        pet = Pet("Whisker", "cat")
        self.assertIn("Whisker", repr(pet))
        self.assertIn("cat", repr(pet))


# ══════════════════════════════════════════════════════════════
#  Owner
# ══════════════════════════════════════════════════════════════
class TestOwner(unittest.TestCase):

    def setUp(self):
        self.buddy   = Pet("Buddy",   "dog")
        self.whisker = Pet("Whisker", "cat")

    def test_attributes_stored_correctly(self):
        owner = Owner("Jordan", 90, [self.buddy, self.whisker])
        self.assertEqual(owner.name, "Jordan")
        self.assertEqual(owner.available_minutes, 90)
        self.assertEqual(len(owner.pets), 2)

    def test_pets_list_is_accessible(self):
        owner = Owner("Jordan", 90, [self.buddy])
        self.assertEqual(owner.pets[0].name, "Buddy")

    def test_owner_with_no_pets(self):
        owner = Owner("Alex", 60, [])
        self.assertEqual(owner.pets, [])


# ══════════════════════════════════════════════════════════════
#  Task
# ══════════════════════════════════════════════════════════════
class TestTask(unittest.TestCase):

    def test_valid_high_priority(self):
        t = Task("Morning Walk", 30, "high")
        self.assertEqual(t.priority_rank(), 3)

    def test_valid_medium_priority(self):
        t = Task("Playtime", 20, "medium")
        self.assertEqual(t.priority_rank(), 2)

    def test_valid_low_priority(self):
        t = Task("Leisurely Stroll", 40, "low")
        self.assertEqual(t.priority_rank(), 1)

    def test_invalid_priority_raises_value_error(self):
        with self.assertRaises(ValueError):
            Task("Bad Task", 10, "urgent")

    def test_zero_duration_raises_value_error(self):
        with self.assertRaises(ValueError):
            Task("Empty Task", 0, "low")

    def test_negative_duration_raises_value_error(self):
        with self.assertRaises(ValueError):
            Task("Negative Task", -5, "high")

    def test_attributes_stored_correctly(self):
        t = Task("Feed Breakfast", 15, "high")
        self.assertEqual(t.title, "Feed Breakfast")
        self.assertEqual(t.duration_minutes, 15)
        self.assertEqual(t.priority, "high")


# ══════════════════════════════════════════════════════════════
#  ScheduledTask
# ══════════════════════════════════════════════════════════════
class TestScheduledTask(unittest.TestCase):

    def setUp(self):
        self.task = Task("Morning Walk", 30, "high")

    def test_end_minute_is_start_plus_duration(self):
        st = ScheduledTask(self.task, start_minute=0)
        self.assertEqual(st.end_minute(), 30)   # 0 + 30

    def test_end_minute_mid_day(self):
        st = ScheduledTask(self.task, start_minute=45)
        self.assertEqual(st.end_minute(), 75)   # 45 + 30

    def test_time_label_at_day_start(self):
        # start=0 means 8:00 AM, end=30 means 8:30 AM
        st = ScheduledTask(self.task, start_minute=0)
        label = st.time_label()
        self.assertIn("8:00 AM", label)
        self.assertIn("8:30 AM", label)

    def test_time_label_crosses_into_next_hour(self):
        # start=45 → 8:45 AM,  end=75 → 9:15 AM
        st = ScheduledTask(self.task, start_minute=45)
        label = st.time_label()
        self.assertIn("8:45 AM", label)
        self.assertIn("9:15 AM", label)

    def test_time_label_crosses_noon(self):
        # start=240 → 12:00 PM (8AM + 240min = 12PM)
        st = ScheduledTask(self.task, start_minute=240)
        label = st.time_label()
        self.assertIn("PM", label)


# ══════════════════════════════════════════════════════════════
#  Schedule
# ══════════════════════════════════════════════════════════════
class TestSchedule(unittest.TestCase):

    def setUp(self):
        self.task1 = Task("Morning Walk",   30, "high")
        self.task2 = Task("Feed Breakfast", 15, "high")
        self.task3 = Task("Playtime",       45, "medium")

    def test_starts_empty(self):
        s = Schedule()
        self.assertTrue(s.is_empty())
        self.assertEqual(s.total_minutes_used, 0)
        self.assertEqual(len(s.scheduled_tasks), 0)
        self.assertEqual(len(s.skipped_tasks), 0)

    def test_add_task_updates_total_minutes(self):
        s = Schedule()
        st = ScheduledTask(self.task1, 0)
        s.add_task(st)
        self.assertEqual(s.total_minutes_used, 30)
        self.assertEqual(len(s.scheduled_tasks), 1)

    def test_add_multiple_tasks_accumulates_minutes(self):
        s = Schedule()
        s.add_task(ScheduledTask(self.task1, 0))   # 30 min
        s.add_task(ScheduledTask(self.task2, 30))  # 15 min
        self.assertEqual(s.total_minutes_used, 45)
        self.assertEqual(len(s.scheduled_tasks), 2)

    def test_skip_task_records_reason(self):
        s = Schedule()
        s.skip_task(self.task3, "Not enough time")
        self.assertEqual(len(s.skipped_tasks), 1)
        skipped_task, reason = s.skipped_tasks[0]
        self.assertEqual(skipped_task.title, "Playtime")
        self.assertEqual(reason, "Not enough time")

    def test_is_empty_false_after_add(self):
        s = Schedule()
        s.add_task(ScheduledTask(self.task1, 0))
        self.assertFalse(s.is_empty())

    def test_summary_contains_scheduled_and_skipped(self):
        s = Schedule()
        s.add_task(ScheduledTask(self.task1, 0))
        s.skip_task(self.task3, "No time left")
        summary = s.summary()
        self.assertIn("Morning Walk", summary)
        self.assertIn("Playtime",    summary)
        self.assertIn("No time left", summary)


# ══════════════════════════════════════════════════════════════
#  Scheduler
# ══════════════════════════════════════════════════════════════
class TestScheduler(unittest.TestCase):

    def setUp(self):
        buddy        = Pet("Buddy", "dog")
        self.owner90 = Owner("Jordan", 90,  [buddy])
        self.owner0  = Owner("Alex",   0,   [buddy])
        self.owner99 = Owner("Sam",    999, [buddy])

        self.tasks = [
            Task("Morning Walk",    30, "high"),
            Task("Feed Breakfast",  15, "high"),
            Task("Playtime",        45, "medium"),
            Task("Groom and Brush", 20, "medium"),
            Task("Training",        25, "low"),
        ]

    # ── _sort_by_priority ─────────────────────────────────────

    def test_sort_puts_high_first(self):
        scheduler = Scheduler(self.owner90, self.tasks)
        sorted_t  = scheduler._sort_by_priority(self.tasks)
        self.assertEqual(sorted_t[0].priority, "high")
        self.assertEqual(sorted_t[1].priority, "high")

    def test_sort_puts_low_last(self):
        scheduler = Scheduler(self.owner90, self.tasks)
        sorted_t  = scheduler._sort_by_priority(self.tasks)
        self.assertEqual(sorted_t[-1].priority, "low")

    def test_sort_does_not_mutate_original_list(self):
        original_order = [t.title for t in self.tasks]
        scheduler = Scheduler(self.owner90, self.tasks)
        scheduler._sort_by_priority(self.tasks)
        self.assertEqual([t.title for t in self.tasks], original_order)

    # ── _fits_in_window ───────────────────────────────────────

    def test_fits_when_exactly_at_limit(self):
        task      = Task("Exactly Fits", 90, "high")
        scheduler = Scheduler(self.owner90, [])
        self.assertTrue(scheduler._fits_in_window(task, used=0))

    def test_does_not_fit_when_one_over(self):
        task      = Task("One Over", 91, "high")
        scheduler = Scheduler(self.owner90, [])
        self.assertFalse(scheduler._fits_in_window(task, used=0))

    def test_does_not_fit_when_budget_is_zero(self):
        task      = Task("Any Task", 10, "low")
        scheduler = Scheduler(self.owner0, [])
        self.assertFalse(scheduler._fits_in_window(task, used=0))

    # ── generate ──────────────────────────────────────────────

    def test_normal_90_min_budget(self):
        # High (30) + High (15) + Medium (45) = 90 — exactly fills budget
        # Medium (20) and Low (25) must be skipped
        schedule = Scheduler(self.owner90, self.tasks).generate()
        self.assertEqual(len(schedule.scheduled_tasks), 3)
        self.assertEqual(len(schedule.skipped_tasks),  2)
        self.assertEqual(schedule.total_minutes_used,  90)

    def test_high_priority_tasks_scheduled_first(self):
        schedule = Scheduler(self.owner90, self.tasks).generate()
        titles   = [st.task.title for st in schedule.scheduled_tasks]
        self.assertIn("Morning Walk",   titles)
        self.assertIn("Feed Breakfast", titles)

    def test_zero_available_minutes_skips_all(self):
        schedule = Scheduler(self.owner0, self.tasks).generate()
        self.assertTrue(schedule.is_empty())
        self.assertEqual(len(schedule.skipped_tasks), len(self.tasks))

    def test_large_budget_schedules_everything(self):
        tasks    = [Task("Vet Visit", 60, "high"), Task("Walk", 20, "low")]
        schedule = Scheduler(self.owner99, tasks).generate()
        self.assertEqual(len(schedule.scheduled_tasks), 2)
        self.assertEqual(len(schedule.skipped_tasks),  0)
        self.assertEqual(schedule.total_minutes_used,  80)

    def test_skipped_reason_no_time_left(self):
        # Use up all time with one task, then the rest should say "No time left"
        tasks = [
            Task("Big Task",   90, "high"),
            Task("Small Task", 10, "low"),
        ]
        schedule = Scheduler(self.owner90, tasks).generate()
        _, reason = schedule.skipped_tasks[0]
        self.assertIn("No time left", reason)

    def test_skipped_reason_not_enough_time(self):
        # Leave only 10 min, try to add a 25-min task
        tasks = [
            Task("First",  80, "high"),
            Task("Second", 25, "medium"),
        ]
        schedule = Scheduler(self.owner90, tasks).generate()
        _, reason = schedule.skipped_tasks[0]
        self.assertIn("25 min", reason)
        self.assertIn("10 min remaining", reason)

    def test_start_minutes_are_sequential(self):
        # Each task's start = previous task's end
        tasks    = [Task("A", 20, "high"), Task("B", 15, "high")]
        schedule = Scheduler(self.owner90, tasks).generate()
        self.assertEqual(schedule.scheduled_tasks[0].start_minute, 0)
        self.assertEqual(schedule.scheduled_tasks[1].start_minute, 20)

    def test_single_task_exactly_fills_budget(self):
        tasks    = [Task("Perfect Fit", 90, "high")]
        schedule = Scheduler(self.owner90, tasks).generate()
        self.assertEqual(len(schedule.scheduled_tasks), 1)
        self.assertEqual(schedule.total_minutes_used, 90)

    def test_empty_task_list_produces_empty_schedule(self):
        schedule = Scheduler(self.owner90, []).generate()
        self.assertTrue(schedule.is_empty())
        self.assertEqual(schedule.skipped_tasks, [])


# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    unittest.main(verbosity=2)
