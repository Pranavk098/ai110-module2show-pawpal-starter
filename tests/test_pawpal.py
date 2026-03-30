# ─────────────────────────────────────────────────────────────
#  tests/test_pawpal.py  –  Unit Tests for PawPal+ System
#  Tests core scheduling logic and data model integrity.
# ─────────────────────────────────────────────────────────────

import pytest
from pawpal_system import Pet, Owner, Task, ScheduledTask, Schedule, Scheduler


# ── Pet Tests ──────────────────────────────────────────────────

class TestPet:
    def test_pet_creation(self):
        """Pet can be created with name and species."""
        pet = Pet(name="Buddy", species="dog")
        assert pet.name == "Buddy"
        assert pet.species == "dog"

    def test_pet_repr(self):
        """Pet.__repr__() returns readable string."""
        pet = Pet(name="Whisker", species="cat")
        assert "Whisker" in repr(pet)
        assert "cat" in repr(pet)


# ── Task Tests ─────────────────────────────────────────────────

class TestTask:
    def test_task_creation_valid(self):
        """Task can be created with valid priority."""
        task = Task(title="Morning Walk", duration_minutes=30, priority="high")
        assert task.title == "Morning Walk"
        assert task.duration_minutes == 30
        assert task.priority == "high"

    def test_task_invalid_priority_raises_error(self):
        """Task with invalid priority raises ValueError immediately."""
        with pytest.raises(ValueError) as exc_info:
            Task(title="Bad Task", duration_minutes=10, priority="urgent")
        assert "Invalid priority" in str(exc_info.value)

    def test_task_priority_rank_high(self):
        """task.priority_rank() returns 3 for 'high' priority."""
        task = Task(title="Vet Visit", duration_minutes=60, priority="high")
        assert task.priority_rank() == 3

    def test_task_priority_rank_medium(self):
        """task.priority_rank() returns 2 for 'medium' priority."""
        task = Task(title="Playtime", duration_minutes=20, priority="medium")
        assert task.priority_rank() == 2

    def test_task_priority_rank_low(self):
        """task.priority_rank() returns 1 for 'low' priority."""
        task = Task(title="Nap Time", duration_minutes=45, priority="low")
        assert task.priority_rank() == 1

    def test_task_negative_duration_raises_error(self):
        """Task with non-positive duration raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            Task(title="Invalid", duration_minutes=-5, priority="high")
        assert "positive integer" in str(exc_info.value)

    def test_task_zero_duration_raises_error(self):
        """Task with zero duration raises ValueError."""
        with pytest.raises(ValueError):
            Task(title="Invalid", duration_minutes=0, priority="high")


# ── ScheduledTask Tests ────────────────────────────────────────

class TestScheduledTask:
    def test_scheduled_task_end_minute(self):
        """ScheduledTask.end_minute() computes start + duration correctly."""
        task = Task(title="Walk", duration_minutes=30, priority="high")
        scheduled = ScheduledTask(task=task, start_minute=60)
        assert scheduled.end_minute() == 90

    def test_scheduled_task_time_label(self):
        """ScheduledTask.time_label() formats time range correctly."""
        task = Task(title="Walk", duration_minutes=30, priority="high")
        scheduled = ScheduledTask(task=task, start_minute=0)
        label = scheduled.time_label()
        assert "8:00 AM" in label
        assert "8:30 AM" in label
        assert "to" in label


# ── Schedule Tests ─────────────────────────────────────────────

class TestSchedule:
    def test_schedule_add_task(self):
        """Schedule.add_task() increases scheduled_tasks count and total_minutes_used."""
        schedule = Schedule()
        task = Task(title="Walk", duration_minutes=30, priority="high")
        st = ScheduledTask(task=task, start_minute=0)

        schedule.add_task(st)

        assert len(schedule.scheduled_tasks) == 1
        assert schedule.total_minutes_used == 30

    def test_schedule_skip_task(self):
        """Schedule.skip_task() records skipped tasks with reason."""
        schedule = Schedule()
        task = Task(title="Walk", duration_minutes=30, priority="high")

        schedule.skip_task(task, "Not enough time available")

        assert len(schedule.skipped_tasks) == 1
        assert schedule.skipped_tasks[0][0] == task
        assert schedule.skipped_tasks[0][1] == "Not enough time available"

    def test_schedule_is_empty_true(self):
        """Schedule.is_empty() returns True when no tasks scheduled."""
        schedule = Schedule()
        assert schedule.is_empty() is True

    def test_schedule_is_empty_false(self):
        """Schedule.is_empty() returns False when tasks are scheduled."""
        schedule = Schedule()
        task = Task(title="Walk", duration_minutes=30, priority="high")
        st = ScheduledTask(task=task, start_minute=0)
        schedule.add_task(st)
        assert schedule.is_empty() is False


# ── Scheduler Tests ────────────────────────────────────────────

class TestScheduler:
    def test_scheduler_sorts_by_priority(self):
        """Scheduler._sort_by_priority() orders tasks high→medium→low."""
        buddy = Pet(name="Buddy", species="dog")
        owner = Owner(name="Jordan", available_minutes=999, pets=[buddy])

        low_task = Task(title="Nap", duration_minutes=10, priority="low")
        high_task = Task(title="Walk", duration_minutes=10, priority="high")
        med_task = Task(title="Play", duration_minutes=10, priority="medium")

        scheduler = Scheduler(owner=owner, tasks=[low_task, high_task, med_task])
        sorted_tasks = scheduler._sort_by_priority(scheduler.tasks)

        # Check order: high, medium, low
        assert sorted_tasks[0].priority == "high"
        assert sorted_tasks[1].priority == "medium"
        assert sorted_tasks[2].priority == "low"

    def test_scheduler_fits_in_window_true(self):
        """Scheduler._fits_in_window() returns True when task fits."""
        buddy = Pet(name="Buddy", species="dog")
        owner = Owner(name="Jordan", available_minutes=100, pets=[buddy])
        scheduler = Scheduler(owner=owner, tasks=[])

        task = Task(title="Walk", duration_minutes=30, priority="high")
        # Already used 50 min, task needs 30 → fits
        assert scheduler._fits_in_window(task, used=50) is True

    def test_scheduler_fits_in_window_false(self):
        """Scheduler._fits_in_window() returns False when task doesn't fit."""
        buddy = Pet(name="Buddy", species="dog")
        owner = Owner(name="Jordan", available_minutes=100, pets=[buddy])
        scheduler = Scheduler(owner=owner, tasks=[])

        task = Task(title="Walk", duration_minutes=30, priority="high")
        # Already used 80 min, task needs 30 → doesn't fit
        assert scheduler._fits_in_window(task, used=80) is False

    def test_scheduler_generate_schedules_high_priority_first(self):
        """Scheduler prioritizes high-priority tasks in the schedule."""
        buddy = Pet(name="Buddy", species="dog")
        owner = Owner(name="Jordan", available_minutes=50, pets=[buddy])

        high_task = Task(title="Vet Visit", duration_minutes=30, priority="high")
        low_task = Task(title="Walk", duration_minutes=40, priority="low")

        scheduler = Scheduler(owner=owner, tasks=[low_task, high_task])
        schedule = scheduler.generate()

        # High task should be scheduled despite being second in input list
        assert len(schedule.scheduled_tasks) == 1
        assert schedule.scheduled_tasks[0].task.title == "Vet Visit"
        assert low_task in [t for t, _ in schedule.skipped_tasks]

    def test_scheduler_generate_respects_time_budget(self):
        """Scheduler never exceeds owner's available_minutes."""
        buddy = Pet(name="Buddy", species="dog")
        owner = Owner(name="Jordan", available_minutes=60, pets=[buddy])

        tasks = [
            Task(title="Walk", duration_minutes=30, priority="high"),
            Task(title="Feed", duration_minutes=20, priority="high"),
            Task(title="Play", duration_minutes=20, priority="medium"),
        ]

        scheduler = Scheduler(owner=owner, tasks=tasks)
        schedule = scheduler.generate()

        # Should not exceed 60 minutes
        assert schedule.total_minutes_used <= 60

    def test_scheduler_generate_empty_schedule_when_no_time(self):
        """Scheduler produces empty schedule when owner has 0 available minutes."""
        buddy = Pet(name="Buddy", species="dog")
        owner = Owner(name="Jordan", available_minutes=0, pets=[buddy])

        task = Task(title="Walk", duration_minutes=30, priority="high")
        scheduler = Scheduler(owner=owner, tasks=[task])
        schedule = scheduler.generate()

        assert schedule.is_empty() is True
        assert len(schedule.skipped_tasks) == 1

    def test_scheduler_records_skip_reason(self):
        """Scheduler provides clear reason when skipping tasks."""
        buddy = Pet(name="Buddy", species="dog")
        owner = Owner(name="Jordan", available_minutes=20, pets=[buddy])

        task = Task(title="Long Walk", duration_minutes=60, priority="high")
        scheduler = Scheduler(owner=owner, tasks=[task])
        schedule = scheduler.generate()

        assert len(schedule.skipped_tasks) == 1
        task_skipped, reason = schedule.skipped_tasks[0]
        assert "60" in reason  # should mention needed duration
        assert "20" in reason  # should mention available


# ── Integration Tests ──────────────────────────────────────────

class TestIntegration:
    def test_full_workflow_end_to_end(self):
        """Full workflow: create owner/pets, add tasks, generate schedule."""
        # Setup
        buddy = Pet(name="Buddy", species="dog")
        whisker = Pet(name="Whisker", species="cat")
        owner = Owner(name="Jordan", available_minutes=90, pets=[buddy, whisker])

        tasks = [
            Task(title="Morning Walk", duration_minutes=30, priority="high"),
            Task(title="Feed Breakfast", duration_minutes=15, priority="high"),
            Task(title="Playtime", duration_minutes=45, priority="medium"),
        ]

        # Execute
        scheduler = Scheduler(owner=owner, tasks=tasks)
        schedule = scheduler.generate()

        # Assert
        assert not schedule.is_empty()
        assert len(schedule.scheduled_tasks) >= 2
        assert schedule.total_minutes_used <= owner.available_minutes
        assert schedule.summary()  # should not raise
