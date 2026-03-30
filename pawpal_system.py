# ─────────────────────────────────────────────────────────────
#  pawpal_system.py  -  PawPal+ Logic Layer  (v2)
#  All backend classes live here.  No UI code.
#
#  Improvements implemented vs v1:
#    A1  Fill-the-gap second scheduling pass
#    A3  Time-window enforcement (earliest_start / deadline)
#    A4  Dependency ordering via topological sort
#    A5  Configurable buffer time between tasks
#    B1  Pet association on every Task
#    B2  Recurring tasks + next-day carry-forward
#    B3  Task categories (feeding / exercise / grooming / ...)
#    B4  Task status tracking  (pending / done / skipped)
#    B5  Task dependencies (depends_on list)
#    C1  Schedule.tasks_for_pet()
#    C2  Schedule.tasks_by_priority()
#    C3  Schedule.tasks_by_category()
#    C4  Schedule.pending_tasks() / completed_tasks()
#    C5  Schedule.tasks_sorted_by_start()
#    D2  Double-feeding conflict warning
#    D3  Exercise-after-meal conflict warning (dogs)
#    D4  Duplicate task-title warning
#    E1  Configurable day-start hour on Owner
#    E3  Pet age + health_notes
#    F1  Schedule.efficiency_score()
#    F2  Schedule.priority_breakdown()
#    F4  Schedule.get_recurring_tasks_for_next_day()
# ─────────────────────────────────────────────────────────────

import heapq
import json
from datetime import date, timedelta


# ═════════════════════════════════════════════════════════════
#  1. Pet
# ═════════════════════════════════════════════════════════════
class Pet:
    """
    Represents a single pet.

    age          -- (E3) years old; 0 means unspecified
    health_notes -- (E3) free-text notes, e.g. 'arthritis - avoid long runs'
    """

    def __init__(self,
                 name: str,
                 species: str,
                 age: int = 0,
                 health_notes: str = ""):
        self.name         = name
        self.species      = species
        self.age          = age           # E3
        self.health_notes = health_notes  # E3
        self.tasks: list  = []            # tasks assigned to this pet

    def add_task(self, task) -> None:
        """Assign a task to this pet and track it in the pet's task list."""
        if task not in self.tasks:
            self.tasks.append(task)
        task.pet = self

    def remove_task(self, task) -> None:
        """Remove a task from this pet's task list and unassign if linked."""
        if task in self.tasks:
            self.tasks.remove(task)
        if getattr(task, "pet", None) == self:
            task.pet = None

    def list_tasks(self) -> list:
        """Return a shallow copy of this pet's assigned tasks."""
        return list(self.tasks)

    def __repr__(self) -> str:
        notes = f", notes={self.health_notes!r}" if self.health_notes else ""
        return (
            f"Pet(name={self.name!r}, species={self.species!r}, "
            f"tasks={len(self.tasks)}{notes})"
        )


# ═════════════════════════════════════════════════════════════
#  2. Owner
# ═════════════════════════════════════════════════════════════
class Owner:
    """
    Represents the person using the app.

    available_minutes -- hard daily time budget
    day_start_hour    -- (E1) what hour the schedule begins  (default 8 = 8 AM)
    buffer_minutes    -- (A5) mandatory rest gap between every task
    """

    def __init__(self,
                 name: str,
                 available_minutes: int,
                 pets: list,
                 day_start_hour: int = 8,
                 buffer_minutes: int = 0):
        self.name              = name
        self.available_minutes = available_minutes
        self.pets              = pets            # List[Pet]
        self.day_start_hour    = day_start_hour  # E1
        self.buffer_minutes    = buffer_minutes  # A5

    def __repr__(self) -> str:
        pet_names = [p.name for p in self.pets]
        return (
            f"Owner(name={self.name!r}, "
            f"available_minutes={self.available_minutes}, "
            f"pets={pet_names}, "
            f"day_start={self.day_start_hour}:00, "
            f"buffer={self.buffer_minutes}min)"
        )

    @staticmethod
    def _task_to_dict(task: "Task") -> dict:
        """Serialize one Task to a JSON-safe dictionary."""
        return {
            "title": task.title,
            "duration_minutes": task.duration_minutes,
            "priority": task.priority,
            "pet": task.pet.name if task.pet else None,
            "category": task.category,
            "recurrence": task.recurrence,
            "earliest_start_minute": task.earliest_start_minute,
            "deadline_minute": task.deadline_minute,
            "depends_on": [dep.title for dep in task.depends_on],
            "status": task.status,
            "preferred_time": task.preferred_time,
            "due_date": task.due_date.isoformat() if task.due_date else None,
        }

    @staticmethod
    def _task_from_dict(task_data: dict, pet_by_name: dict) -> "Task":
        """Build one Task from dictionary data (dependency links added later)."""
        due_raw = task_data.get("due_date")
        due_date = date.fromisoformat(due_raw) if due_raw else date.today()
        pet_name = task_data.get("pet")

        task = Task(
            title=task_data["title"],
            duration_minutes=int(task_data["duration_minutes"]),
            priority=task_data["priority"],
            pet=pet_by_name.get(pet_name),
            category=task_data.get("category", "other"),
            recurrence=task_data.get("recurrence", "none"),
            earliest_start_minute=int(task_data.get("earliest_start_minute", 0)),
            deadline_minute=task_data.get("deadline_minute"),
            depends_on=[],
            preferred_time=task_data.get("preferred_time"),
            due_date=due_date,
        )

        status = task_data.get("status", "pending")
        task.status = status if status in Task.VALID_STATUSES else "pending"
        return task

    def save_to_json(self, tasks: list, filepath: str = "data.json") -> None:
        """
        Save owner, pets, and tasks to a JSON file.

        Args:
            tasks (list): Task objects currently in memory.
            filepath (str): Target file path (default: data.json).
        """
        data = {
            "owner": {
                "name": self.name,
                "available_minutes": self.available_minutes,
                "day_start_hour": self.day_start_hour,
                "buffer_minutes": self.buffer_minutes,
            },
            "pets": [
                {
                    "name": pet.name,
                    "species": pet.species,
                    "age": pet.age,
                    "health_notes": pet.health_notes,
                }
                for pet in self.pets
            ],
            "tasks": [self._task_to_dict(task) for task in tasks],
        }

        with open(filepath, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=2)

    @classmethod
    def load_from_json(cls, filepath: str = "data.json"):
        """
        Load owner, pets, and tasks from a JSON file.

        Returns:
            tuple[Owner, list]: Reconstructed owner and task list.
        """
        with open(filepath, "r", encoding="utf-8") as file:
            data = json.load(file)

        owner_data = data.get("owner")
        pets_data = data.get("pets", [])
        tasks_data = data.get("tasks", [])

        if not owner_data:
            raise ValueError("Saved data is missing owner information.")

        pets = [
            Pet(
                name=pet_data["name"],
                species=pet_data["species"],
                age=int(pet_data.get("age", 0)),
                health_notes=pet_data.get("health_notes", ""),
            )
            for pet_data in pets_data
        ]
        pet_by_name = {pet.name: pet for pet in pets}

        owner = cls(
            name=owner_data["name"],
            available_minutes=int(owner_data["available_minutes"]),
            pets=pets,
            day_start_hour=int(owner_data.get("day_start_hour", 8)),
            buffer_minutes=int(owner_data.get("buffer_minutes", 0)),
        )

        tasks = [cls._task_from_dict(task_data, pet_by_name) for task_data in tasks_data]
        task_by_title = {task.title: task for task in tasks}

        for task, task_data in zip(tasks, tasks_data):
            dep_titles = task_data.get("depends_on", [])
            task.depends_on = [
                task_by_title[dep_title]
                for dep_title in dep_titles
                if dep_title in task_by_title
            ]

        # Rebuild per-pet task collections from loaded tasks.
        for pet in pets:
            pet.tasks = []
        for task in tasks:
            if task.pet is not None:
                task.pet.add_task(task)

        return owner, tasks


# ═════════════════════════════════════════════════════════════
#  3. Task
# ═════════════════════════════════════════════════════════════
class Task:
    """
    One care activity with full metadata.

    Original fields
      title, duration_minutes, priority

    New fields
      pet                   (B1)  which Pet this task is for (None = any)
      category              (B3)  type of activity
      recurrence            (B2)  how often it repeats
      earliest_start_minute (A3)  cannot start before this offset from day-start
      deadline_minute       (A3)  must FINISH by this offset (None = no deadline)
      depends_on            (B5)  List[Task] that must run first
      status                (B4)  'pending' | 'done' | 'skipped'
    """

    VALID_PRIORITIES  = {"low", "medium", "high"}
    VALID_CATEGORIES  = {
        "feeding", "exercise", "grooming", "medical",
        "play", "training", "hygiene", "other",
    }
    VALID_RECURRENCES = {"none", "daily", "weekly", "monthly"}
    VALID_STATUSES    = {"pending", "done", "skipped"}

    def __init__(self,
                 title: str,
                 duration_minutes: int,
                 priority: str,
                 pet=None,
                 category: str = "other",
                 recurrence: str = "none",
                 earliest_start_minute: int = 0,
                 deadline_minute: int = None,
                 depends_on: list = None,
                 preferred_time: str = None,
                 due_date: "date" = None):

        # ── input validation ──────────────────────────────────
        if priority not in self.VALID_PRIORITIES:
            raise ValueError(
                f"Invalid priority '{priority}'. "
                f"Choose from {self.VALID_PRIORITIES}."
            )
        if duration_minutes <= 0:
            raise ValueError("duration_minutes must be a positive integer.")
        if category not in self.VALID_CATEGORIES:
            raise ValueError(
                f"Invalid category '{category}'. "
                f"Choose from {self.VALID_CATEGORIES}."
            )
        if recurrence not in self.VALID_RECURRENCES:
            raise ValueError(
                f"Invalid recurrence '{recurrence}'. "
                f"Choose from {self.VALID_RECURRENCES}."
            )
        if deadline_minute is not None and deadline_minute <= earliest_start_minute:
            raise ValueError(
                "deadline_minute must be greater than earliest_start_minute."
            )
        if preferred_time is not None:
            # Validate "HH:MM" format  (e.g. "08:30", "14:00")
            parts = preferred_time.split(":")
            if (len(parts) != 2
                    or not parts[0].isdigit()
                    or not parts[1].isdigit()
                    or not (0 <= int(parts[0]) <= 23)
                    or not (0 <= int(parts[1]) <= 59)):
                raise ValueError(
                    f"preferred_time '{preferred_time}' is not valid. "
                    f"Use 24-hour 'HH:MM' format, e.g. '08:30' or '14:00'."
                )

        # ── core fields ───────────────────────────────────────
        self.title            = title
        self.duration_minutes = duration_minutes
        self.priority         = priority

        # ── new fields ────────────────────────────────────────
        self.pet                   = pet                  # B1
        self.category              = category             # B3
        self.recurrence            = recurrence           # B2
        self.earliest_start_minute = earliest_start_minute  # A3
        self.deadline_minute       = deadline_minute      # A3
        self.depends_on: list      = depends_on or []     # B5
        self.status                = "pending"            # B4
        self.preferred_time        = preferred_time       # sort_by_time key

        # ── due_date / next-occurrence fields ─────────────────
        # due_date defaults to today if not supplied
        self.due_date        = due_date if due_date is not None else date.today()
        # next_occurrence is populated by mark_done() for recurring tasks
        self.next_occurrence = None

    # ── priority helper ───────────────────────────────────────

    def priority_rank(self) -> int:
        """
        Convert the string priority label into a sortable integer.

        Mapping:
            "high"   -> 3
            "medium" -> 2
            "low"    -> 1

        Higher numbers sort first when the list is reversed, which is how
        Scheduler._sort_by_priority() and _topological_sort() both ensure
        that important tasks are attempted before less critical ones.

        Returns:
            int: 1, 2, or 3 corresponding to the task's priority level.
        """
        return {"high": 3, "medium": 2, "low": 1}[self.priority]

    # ── B4: status helpers ────────────────────────────────────

    def _next_due_date(self) -> "date":
        """
        Use timedelta to calculate the due date for the next occurrence.
          daily   -> self.due_date + timedelta(days=1)
          weekly  -> self.due_date + timedelta(weeks=1)
          monthly -> self.due_date + timedelta(days=30)  (approximation)
          none    -> returns None
        """
        if self.recurrence == "daily":
            return self.due_date + timedelta(days=1)
        if self.recurrence == "weekly":
            return self.due_date + timedelta(weeks=1)
        if self.recurrence == "monthly":
            return self.due_date + timedelta(days=30)
        return None

    def mark_done(self) -> None:
        """
        Mark this task as completed.
        For recurring tasks, automatically creates a next-occurrence clone
        whose due_date is calculated via _next_due_date() / timedelta.
        The clone is stored on self.next_occurrence for collection by
        Scheduler.collect_next_occurrences().
        """
        self.status = "done"
        # Auto-create next occurrence for recurring tasks
        if self.is_recurring():
            next_date = self._next_due_date()
            # Pass the pre-calculated next date into the clone
            self.next_occurrence = self.clone_for_next_occurrence(due_date=next_date)
        else:
            self.next_occurrence = None

    def mark_skipped(self) -> None:
        """
        Mark this task as skipped.

        Called by Schedule.skip_task() when the Scheduler decides a task
        cannot be placed — either because no time remains, the deadline
        would be missed, or the task was deliberately excluded.

        Sets status to "skipped". Does not create a next_occurrence because
        skipped recurring tasks are handled separately by
        Schedule.get_recurring_tasks_for_next_day() with priority promotion.
        """
        self.status = "skipped"

    def reset(self) -> None:
        """
        Reset this task's status back to 'pending'.

        Used exclusively by Scheduler._fill_gaps() when a task that was
        initially skipped in the greedy pass is later rescued and added to
        the schedule in the second pass. Resetting ensures the task does
        not appear as 'skipped' in status filters after it has been
        successfully placed.
        """
        self.status = "pending"

    # ── B2: recurrence helpers ────────────────────────────────

    def is_recurring(self) -> bool:
        """
        Return True if this task repeats on any schedule.

        A task is recurring when its recurrence field is anything other
        than "none". Valid recurring values are "daily", "weekly", and
        "monthly". This flag is checked by mark_done() to decide whether
        to auto-generate a next occurrence, and by Schedule methods to
        build tomorrow's task list.

        Returns:
            bool: True for daily / weekly / monthly tasks, False otherwise.
        """
        return self.recurrence != "none"

    def clone_for_next_occurrence(self, due_date: "date" = None) -> "Task":
        """
        Return a fresh copy of this task with status reset to 'pending'.
        Used by Schedule.get_recurring_tasks_for_next_day() and mark_done().

        due_date -- if provided, the clone receives this already-calculated
                    next date; otherwise defaults to date.today().
        """
        return Task(
            title=self.title,
            duration_minutes=self.duration_minutes,
            priority=self.priority,
            pet=self.pet,
            category=self.category,
            recurrence=self.recurrence,
            earliest_start_minute=self.earliest_start_minute,
            deadline_minute=self.deadline_minute,
            depends_on=list(self.depends_on),
            preferred_time=self.preferred_time,
            due_date=due_date,
        )

    def __repr__(self) -> str:
        pet_tag  = f", pet={self.pet.name!r}" if self.pet else ""
        time_tag = f", time={self.preferred_time!r}" if self.preferred_time else ""
        # Show due_date only when it is not today (avoids clutter in normal output)
        date_tag = (
            f", due={self.due_date.isoformat()}"
            if self.due_date != date.today()
            else ""
        )
        return (
            f"Task(title={self.title!r}, "
            f"duration={self.duration_minutes}min, "
            f"priority={self.priority!r}, "
            f"category={self.category!r}"
            f"{pet_tag}{time_tag}{date_tag})"
        )


# ═════════════════════════════════════════════════════════════
#  4. ScheduledTask
# ═════════════════════════════════════════════════════════════
class ScheduledTask:
    """
    A Task that has been accepted into the Schedule.
    Carries a start_minute so the UI can display a timeline.
    """

    def __init__(self, task: Task, start_minute: int):
        self.task         = task
        self.start_minute = start_minute  # minutes offset from day_start_hour

    def end_minute(self) -> int:
        """
        Calculate the minute offset at which this task finishes.

        Adds the task's duration to its start_minute. Both values are
        expressed as integer minutes counted from the owner's day_start_hour,
        so the result is also in that same relative unit.

        Example:
            start_minute=30, duration=20  ->  end_minute() == 50
            (If day starts at 8 AM: started at 8:30, finished at 8:50)

        Returns:
            int: The minute offset at which this scheduled task ends.
        """
        return self.start_minute + self.task.duration_minutes

    def time_label(self, day_start_hour: int = 8) -> str:
        """
        Human-readable time range, e.g. '8:30 AM to 9:00 AM'.
        Pass day_start_hour from Owner to get the correct wall-clock time.
        """
        def fmt(minutes: int) -> str:
            total = day_start_hour * 60 + minutes
            h     = (total // 60) % 24
            m     = total % 60
            period   = "AM" if h < 12 else "PM"
            display_h = h if 1 <= h <= 12 else (h - 12 if h > 12 else 12)
            return f"{display_h}:{m:02d} {period}"

        return f"{fmt(self.start_minute)} to {fmt(self.end_minute())}"

    def mark_done(self) -> None:
        """
        Mark the underlying Task as completed via delegation.

        Delegates to Task.mark_done(), which sets status to 'done' and,
        for recurring tasks, automatically populates task.next_occurrence
        with a cloned Task whose due_date is advanced by the appropriate
        timedelta (1 day for daily, 7 days for weekly, 30 days for monthly).

        Call this from the UI or from main.py after the owner physically
        completes an activity. Use Scheduler.collect_next_occurrences()
        afterward to retrieve any auto-generated follow-up tasks.
        """
        self.task.mark_done()

    def __repr__(self) -> str:
        return (
            f"ScheduledTask(task={self.task.title!r}, "
            f"start={self.start_minute}min, "
            f"end={self.end_minute()}min, "
            f"status={self.task.status!r})"
        )


# ═════════════════════════════════════════════════════════════
#  5. ConflictWarning
# ═════════════════════════════════════════════════════════════
class ConflictWarning:
    """
    Advisory warning raised by the Scheduler.
    Does NOT prevent a task from being scheduled — it is informational only.

    warning_type -- short machine-readable label
    message      -- human-readable explanation
    tasks        -- list of Task objects involved (optional)
    """

    def __init__(self, warning_type: str, message: str, tasks: list = None):
        self.warning_type = warning_type
        self.message      = message
        self.tasks: list  = tasks or []

    def __repr__(self) -> str:
        return (
            f"ConflictWarning(type={self.warning_type!r}, "
            f"message={self.message!r})"
        )


# ═════════════════════════════════════════════════════════════
#  6. Schedule
# ═════════════════════════════════════════════════════════════
class Schedule:
    """
    The final output of the Scheduler.
    Holds scheduled tasks, skipped tasks, and conflict warnings.
    """

    def __init__(self):
        self.scheduled_tasks: list = []  # List[ScheduledTask]
        self.skipped_tasks:   list = []  # List[tuple(Task, reason: str)]
        self.total_minutes_used: int = 0
        self.warnings:        list = []  # List[ConflictWarning]

    # ── mutators ──────────────────────────────────────────────

    def add_task(self, st: ScheduledTask) -> None:
        """
        Accept a ScheduledTask into this schedule and update the time counter.

        Appends the ScheduledTask to scheduled_tasks and adds its duration
        to total_minutes_used. Called by Scheduler.generate() each time a
        task successfully fits within the owner's available time budget.

        Args:
            st (ScheduledTask): The placed task, already holding its
                                start_minute and a reference to the Task.
        """
        self.scheduled_tasks.append(st)
        self.total_minutes_used += st.task.duration_minutes

    def skip_task(self, task: Task, reason: str) -> None:
        """
        Record a task that could not be scheduled, along with the reason why.

        Stores a (Task, reason_string) tuple in skipped_tasks and calls
        task.mark_skipped() so the Task object's own status reflects the
        outcome. The reason string is shown in the UI and in summary() to
        give the owner a transparent explanation (e.g. "Not enough time -
        needs 30 min but only 10 min remaining").

        Args:
            task   (Task): The task that was excluded from the schedule.
            reason (str):  Human-readable explanation of why it was skipped.
        """
        self.skipped_tasks.append((task, reason))
        task.mark_skipped()

    def add_warning(self, warning: ConflictWarning) -> None:
        """
        Attach an advisory ConflictWarning to this schedule.

        Warnings are informational only — they do not prevent tasks from
        being scheduled or cause any exception. They surface issues such as
        time-window overlaps (D1), double feedings (D2), exercise after
        meals (D3), and duplicate task titles (D4).

        Args:
            warning (ConflictWarning): The warning object to attach.
        """
        self.warnings.append(warning)

    # ── basic helper ──────────────────────────────────────────

    def is_empty(self) -> bool:
        """
        Return True when no tasks were successfully scheduled.

        Used by the UI and main.py to detect the edge case where the
        owner's time budget is too small for even a single task, or where
        every task was skipped due to deadline violations.

        Returns:
            bool: True if scheduled_tasks is empty, False otherwise.
        """
        return len(self.scheduled_tasks) == 0

    # ── C1: filter by pet ─────────────────────────────────────

    def tasks_for_pet(self, pet: Pet) -> list:
        """
        Return all scheduled tasks assigned to a specific Pet object.

        Uses identity comparison (==) against task.pet. Tasks whose pet
        field is None are excluded. Useful for displaying a per-pet
        breakdown or for computing how much of the day is devoted to one
        animal when the owner has multiple pets.

        Args:
            pet (Pet): The Pet instance to filter by.

        Returns:
            list[ScheduledTask]: Scheduled tasks whose task.pet == pet.
        """
        return [st for st in self.scheduled_tasks if st.task.pet == pet]

    # ── C2: filter by priority ────────────────────────────────

    def tasks_by_priority(self, priority: str) -> list:
        """
        Return all scheduled tasks at the given priority level.

        Args:
            priority (str): One of "high", "medium", or "low".

        Returns:
            list[ScheduledTask]: Scheduled tasks whose task.priority
                                 matches the requested level.
        """
        return [
            st for st in self.scheduled_tasks
            if st.task.priority == priority
        ]

    # ── C3: filter by category ────────────────────────────────

    def tasks_by_category(self, category: str) -> list:
        """
        Return all scheduled tasks belonging to the given category.

        Valid categories mirror Task.VALID_CATEGORIES: "feeding",
        "exercise", "grooming", "medical", "play", "training",
        "hygiene", "other". Useful for producing a category-level
        summary (e.g. "all feeding tasks today").

        Args:
            category (str): The category label to filter by.

        Returns:
            list[ScheduledTask]: Scheduled tasks whose task.category
                                 matches the requested value.
        """
        return [
            st for st in self.scheduled_tasks
            if st.task.category == category
        ]

    # ── C4: filter by status ──────────────────────────────────

    def pending_tasks(self) -> list:
        """
        Return scheduled tasks that have not yet been completed.

        A task's status starts as "pending" and remains so until the owner
        calls mark_done() on it. This filter is useful for mid-day
        progress checks: "what do I still have left to do?"

        Returns:
            list[ScheduledTask]: Scheduled tasks whose task.status
                                 is "pending".
        """
        return [
            st for st in self.scheduled_tasks
            if st.task.status == "pending"
        ]

    def completed_tasks(self) -> list:
        """
        Return scheduled tasks that the owner has already marked done.

        A task reaches "done" status when ScheduledTask.mark_done() or
        Task.mark_done() is called. This filter complements pending_tasks()
        and is useful for building a "completed" section in the UI.

        Returns:
            list[ScheduledTask]: Scheduled tasks whose task.status
                                 is "done".
        """
        return [
            st for st in self.scheduled_tasks
            if st.task.status == "done"
        ]

    # ── C5: sort by start time ────────────────────────────────

    def tasks_sorted_by_start(self) -> list:
        """
        Return scheduled tasks ordered by start_minute ascending.

        The greedy scheduler already places tasks in roughly chronological
        order, but this method guarantees strict chronological ordering
        regardless of how tasks ended up in scheduled_tasks (including
        tasks rescued by the fill-the-gap second pass, which are appended
        at the end of the list). Used internally by _check_conflicts() and
        _check_time_overlaps() so they compare adjacent time slots correctly.

        Returns:
            list[ScheduledTask]: A new list sorted by start_minute,
                                 earliest first. The original list is
                                 not modified.
        """
        return sorted(self.scheduled_tasks, key=lambda st: st.start_minute)

    # ── F1: efficiency score ──────────────────────────────────

    def efficiency_score(self, available_minutes: int) -> float:
        """
        Percentage of the owner's time budget that was filled.
        Returns a float between 0.0 and 100.0.
        """
        if available_minutes <= 0:
            return 0.0
        return round((self.total_minutes_used / available_minutes) * 100, 1)

    # ── F2: priority breakdown ────────────────────────────────

    def priority_breakdown(self) -> dict:
        """
        Returns per-priority counts of scheduled vs. skipped tasks.
        Example: {'high': {'scheduled': 3, 'skipped': 0}, ...}
        """
        bd = {p: {"scheduled": 0, "skipped": 0} for p in ("high", "medium", "low")}
        for st in self.scheduled_tasks:
            bd[st.task.priority]["scheduled"] += 1
        for task, _ in self.skipped_tasks:
            bd[task.priority]["skipped"] += 1
        return bd

    # ── remaining minutes ─────────────────────────────────────

    def remaining_minutes(self, available_minutes: int) -> int:
        """
        Calculate how many free minutes are left in the owner's day.

        Subtracts total_minutes_used from the owner's available_minutes
        budget. Returns 0 rather than a negative number in the unlikely
        case that buffer time caused an overshoot.

        Args:
            available_minutes (int): The owner's total daily time budget
                                     (Owner.available_minutes).

        Returns:
            int: Minutes still available, always >= 0.
        """
        return max(0, available_minutes - self.total_minutes_used)

    # ── F4: recurring task carry-forward ─────────────────────

    def get_recurring_tasks_for_next_day(self) -> list:
        """
        Build a fresh task list for tomorrow from any recurring tasks.

        Rules:
          - Recurring tasks that ran today  -> cloned as-is (same priority)
          - Recurring tasks that were SKIPPED today -> cloned with priority
            promoted one level (low->medium, medium->high) so they jump
            the queue tomorrow.
        """
        next_day   = []
        promotion  = {"low": "medium", "medium": "high", "high": "high"}

        for st in self.scheduled_tasks:
            if st.task.is_recurring():
                next_day.append(st.task.clone_for_next_occurrence())

        for task, _ in self.skipped_tasks:
            if task.is_recurring():
                clone          = task.clone_for_next_occurrence()
                clone.priority = promotion[task.priority]  # F4: promote
                next_day.append(clone)

        return next_day

    # ── summary ───────────────────────────────────────────────

    def summary(self) -> str:
        """
        Build and return a plain-text summary of the entire schedule.

        Produces three sections:
            1. Scheduled tasks — title, priority, duration for each accepted task.
            2. Skipped tasks   — title and the reason each task was excluded.
            3. Warnings        — any ConflictWarning messages attached during
                                 scheduling (overlaps, double-feedings, etc.).

        Intended for CLI output (main.py) and quick debugging. The Streamlit
        UI uses the structured data directly rather than calling this method.

        Returns:
            str: A multi-line string with all three sections, separated by
                 blank lines and labelled headers.
        """
        lines = []
        lines.append(
            f"--- Scheduled ({len(self.scheduled_tasks)} tasks, "
            f"{self.total_minutes_used} min used) ---"
        )
        if self.scheduled_tasks:
            for st in self.scheduled_tasks:
                pet_tag = f" [{st.task.pet.name}]" if st.task.pet else ""
                lines.append(
                    f"  [{st.task.priority.upper():6}] "
                    f"{st.task.title}{pet_tag}  "
                    f"({st.task.duration_minutes} min)"
                )
        else:
            lines.append("  (none)")

        lines.append(f"\n--- Skipped ({len(self.skipped_tasks)} tasks) ---")
        if self.skipped_tasks:
            for task, reason in self.skipped_tasks:
                lines.append(f"  [SKIP] {task.title} - {reason}")
        else:
            lines.append("  (none)")

        if self.warnings:
            lines.append(f"\n--- Warnings ({len(self.warnings)}) ---")
            for w in self.warnings:
                lines.append(f"  [WARN][{w.warning_type}] {w.message}")

        return "\n".join(lines)

    def __repr__(self) -> str:
        return (
            f"Schedule(scheduled={len(self.scheduled_tasks)}, "
            f"skipped={len(self.skipped_tasks)}, "
            f"minutes_used={self.total_minutes_used}, "
            f"warnings={len(self.warnings)})"
        )


# ═════════════════════════════════════════════════════════════
#  7. Scheduler
# ═════════════════════════════════════════════════════════════
class Scheduler:
    """
    The scheduling engine.

    Full pipeline (called once per generate()):
      Step 1  D4  Duplicate-title detection
      Step 2  A4  Topological sort (dependencies) with priority tie-breaking
      Step 3  A3/A5  Greedy pass honouring time-windows and buffer gaps
      Step 4  A1  Fill-the-gap second pass over time-skipped tasks
      Step 5  D2/D3  Post-schedule conflict detection
    """

    def __init__(self, owner: Owner, tasks: list):
        self.owner = owner
        self.tasks = tasks   # List[Task]

    # ── public entry point ────────────────────────────────────

    def generate(self) -> Schedule:
        """
        Run the full five-step scheduling pipeline and return a Schedule.

        Step 1 — Duplicate detection (D4)
            Scans self.tasks for repeated title strings and attaches a
            ConflictWarning for each duplicate found. Both copies are still
            eligible for scheduling.

        Step 2 — Dependency-aware sort (A4 / B5)
            Runs _topological_sort() which uses Kahn's algorithm with a
            max-priority min-heap. This guarantees that if Task B lists
            Task A in its depends_on list, A always appears before B in the
            output. Within each dependency level, higher-priority tasks are
            served first. If a circular dependency is detected, falls back
            to a plain priority sort and attaches a warning.

        Step 3 — Greedy scheduling pass (A3 / A5)
            Iterates through the sorted task list and attempts to place each
            task sequentially:
              - If earliest_start_minute is in the future, advances the
                internal clock to that minute first.
              - If a deadline_minute is set and the task cannot finish in
                time, skips it with a deadline-violation reason.
              - If the task fits within the remaining budget, creates a
                ScheduledTask and advances the clock by duration + buffer.
              - Otherwise records the task as skipped with a time-remaining
                explanation.

        Step 4 — Fill-the-gap second pass (A1)
            After the greedy pass, any remaining free time is offered to
            tasks that were skipped purely due to time constraints (not
            deadline violations). Tasks are re-tried highest-priority first.

        Step 5 — Post-schedule conflict detection (D1 / D2 / D3)
            Calls _check_conflicts() which in turn calls:
              _check_time_overlaps() — preferred_time window collisions
              double-feeding guard   — two feeding tasks < 2 hours apart
              exercise-after-meal    — dog walked < 30 min after eating

        Returns:
            Schedule: Fully populated with scheduled_tasks, skipped_tasks,
                      and any advisory warnings.
        """
        schedule = Schedule()

        # Step 1 — duplicate detection (D4)
        self._check_duplicates(schedule)

        # Step 2 — dependency-aware, priority-weighted sort (A4 / B5)
        try:
            sorted_tasks = self._topological_sort(self.tasks)
        except ValueError as exc:
            # Circular dependency: fall back to plain priority sort and warn
            sorted_tasks = self._sort_by_priority(self.tasks)
            schedule.add_warning(ConflictWarning(
                "circular_dependency",
                f"Circular dependency detected ({exc}). "
                f"Falling back to priority-only ordering."
            ))

        # Step 3 — greedy scheduling pass (A3 / A5)
        minutes_used = 0
        buffer       = self.owner.buffer_minutes  # A5

        for task in sorted_tasks:

            # A3: respect earliest-start — advance the clock if needed
            if minutes_used < task.earliest_start_minute:
                minutes_used = task.earliest_start_minute

            # A3: deadline check — would we miss it?
            if task.deadline_minute is not None:
                projected_end = minutes_used + task.duration_minutes
                if projected_end > task.deadline_minute:
                    schedule.skip_task(
                        task,
                        f"Would miss deadline - must finish by min "
                        f"{task.deadline_minute} but would end at min {projected_end}"
                    )
                    continue

            if self._fits_in_window(task, minutes_used):
                st = ScheduledTask(task=task, start_minute=minutes_used)
                schedule.add_task(st)
                minutes_used += task.duration_minutes
                if buffer > 0:
                    minutes_used += buffer  # A5: insert rest gap
            else:
                remaining = self.owner.available_minutes - minutes_used
                reason = (
                    f"No time left in the day "
                    f"(0 min remaining out of "
                    f"{self.owner.available_minutes} min available)"
                    if remaining <= 0 else
                    f"Not enough time - needs {task.duration_minutes} min "
                    f"but only {remaining} min remaining"
                )
                schedule.skip_task(task, reason)

        # Step 4 — fill-the-gap second pass (A1)
        self._fill_gaps(schedule, minutes_used)

        # Step 5 — post-schedule conflict checks (D2 / D3)
        self._check_conflicts(schedule)

        return schedule

    # ── collect next occurrences ──────────────────────────────

    def collect_next_occurrences(self) -> list:
        """
        Collect all auto-generated next-occurrence tasks from the current
        task pool.  Call this after tasks have been marked done via mark_done().

        Returns a list of Task objects sorted by due_date ascending
        (nearest date first).

        Only tasks whose next_occurrence attribute is not None are included;
        these are set automatically by Task.mark_done() for recurring tasks.
        """
        occurrences = [
            task.next_occurrence
            for task in self.tasks
            if task.next_occurrence is not None
        ]
        # Sort by due_date so the nearest upcoming task appears first
        occurrences.sort(key=lambda t: t.due_date)
        return occurrences

    # ── A1: fill-the-gap second pass ─────────────────────────

    def _fill_gaps(self, schedule: Schedule, minutes_used: int) -> None:
        """
        Second-pass scheduler that rescues tasks skipped due to insufficient
        time.

        After the greedy priority pass (Step 3 of generate()), some tasks may
        have been skipped only because a larger high-priority task consumed
        the budget before they were reached. This method checks the remaining
        free minutes and attempts to place those tasks in priority order.

        Algorithm (A1):
            1. Compute remaining = available_minutes - minutes_used.
               If <= 0, return immediately — nothing can fit.
            2. Collect skipped entries whose reason contains
               "Not enough time" or "No time left" (time-budget skips).
               Deadline violations are intentionally excluded: their window
               has already closed.
            3. Sort the candidates by priority_rank() descending so that
               the most important tasks get rescued first.
            4. Greedily place each candidate that fits in the remaining
               budget, appending a ScheduledTask directly to
               schedule.scheduled_tasks and updating total_minutes_used.
            5. Call task.reset() on each rescued task so its status
               reverts from "skipped" to "pending".
            6. Remove rescued entries from schedule.skipped_tasks.

        Note: this method mutates both ``schedule`` and the individual Task
        objects in-place. ``minutes_used`` is a local variable; the caller's
        counter is NOT updated.

        Args:
            schedule (Schedule): The partially built schedule produced by the
                                 greedy pass. Modified in-place.
            minutes_used (int):  Minutes already consumed at the end of the
                                 greedy pass.
        """
        if self.owner.available_minutes - minutes_used <= 0:
            return

        # Collect only time-based skips (not deadline violations)
        time_skipped = [
            (task, reason)
            for task, reason in list(schedule.skipped_tasks)
            if "Not enough time" in reason or "No time left" in reason
        ]

        if not time_skipped:
            return

        # Try highest-priority skipped tasks first
        time_skipped.sort(key=lambda x: x[0].priority_rank(), reverse=True)

        rescued = []
        for task, reason in time_skipped:
            if minutes_used + task.duration_minutes <= self.owner.available_minutes:
                st = ScheduledTask(task=task, start_minute=minutes_used)
                # Append directly — avoids double-counting total_minutes_used
                schedule.scheduled_tasks.append(st)
                schedule.total_minutes_used += task.duration_minutes
                task.reset()           # undo "skipped" -> back to "pending"
                minutes_used += task.duration_minutes
                if self.owner.buffer_minutes > 0:
                    minutes_used += self.owner.buffer_minutes
                rescued.append((task, reason))

        # Remove rescued entries from the skipped list
        for item in rescued:
            if item in schedule.skipped_tasks:
                schedule.skipped_tasks.remove(item)

    # ── A4 / B5: topological sort with priority tie-breaking ──

    def _topological_sort(self, tasks: list) -> list:
        """
        Order tasks so that every dependency appears before the task that
        requires it, while still favouring higher-priority tasks when
        multiple tasks are simultaneously "ready".

        Algorithm (A4 / B5) — Kahn's with a priority-weighted min-heap:
            1. Build an adjacency list and in-degree table from each task's
               ``depends_on`` list. Only edges where *both* endpoints are in
               the current task set are counted (external dependencies are
               ignored silently).
            2. Seed a min-heap with all tasks whose in-degree is 0.
               Heap entries are (-priority_rank, counter, task_id) so that
               heapq (a min-heap) pops the *highest*-priority ready task
               first; counter breaks ties by insertion order for stability.
            3. On each iteration, pop the best ready task, append it to the
               result, and decrement the in-degree of its dependants. Any
               dependant whose in-degree reaches 0 is pushed onto the heap.
            4. If the result contains fewer tasks than the input, a cycle
               exists — raise ValueError naming the remaining tasks.

        Complexity: O(n log n) — each task is pushed/popped once; the heap
        operations dominate.

        Args:
            tasks (list[Task]): Tasks to sort. May include tasks with no
                                dependencies; those are returned in
                                priority order relative to each other.

        Returns:
            list[Task]: Tasks in dependency-safe, priority-weighted order.

        Raises:
            ValueError: If a circular dependency is detected among the tasks.
        """
        task_set  = {id(t) for t in tasks}
        in_degree = {id(t): 0   for t in tasks}
        adj       = {id(t): []  for t in tasks}
        by_id     = {id(t): t   for t in tasks}

        for task in tasks:
            for dep in task.depends_on:
                if id(dep) in task_set:
                    adj[id(dep)].append(id(task))
                    in_degree[id(task)] += 1

        # heap entry: (-priority_rank, insertion_counter, task_id)
        # negative rank so that heapq (min-heap) serves highest priority first
        counter = 0
        heap    = []
        for t in tasks:
            if in_degree[id(t)] == 0:
                heapq.heappush(heap, (-t.priority_rank(), counter, id(t)))
                counter += 1

        result = []
        while heap:
            _, _, tid = heapq.heappop(heap)
            result.append(by_id[tid])
            for nid in adj[tid]:
                in_degree[nid] -= 1
                if in_degree[nid] == 0:
                    heapq.heappush(
                        heap,
                        (-by_id[nid].priority_rank(), counter, nid)
                    )
                    counter += 1

        if len(result) != len(tasks):
            raise ValueError("Circular dependency detected in task graph.")

        return result

    # ── D4: duplicate-title detection ────────────────────────

    def _check_duplicates(self, schedule: Schedule) -> None:
        """
        Scan self.tasks for repeated titles and attach a warning for each pair.

        Normalises each title by stripping whitespace and converting to
        lowercase before comparing, so "Morning Walk" and "morning walk"
        are treated as duplicates. Both tasks remain in the pool and will
        be scheduled if time allows — this is advisory only.

        Algorithm:
            Single pass through self.tasks using a dict (seen) keyed on the
            normalised title. O(n) time, O(n) space.

        Args:
            schedule (Schedule): The schedule being built; warnings are
                                 attached here via schedule.add_warning().
        """
        seen = {}
        for task in self.tasks:
            key = task.title.strip().lower()
            if key in seen:
                schedule.add_warning(ConflictWarning(
                    "duplicate_task",
                    f"Duplicate task title: '{task.title}' appears more than once. "
                    f"Both will be scheduled if time allows.",
                    [seen[key], task]
                ))
            else:
                seen[key] = task

    # ── D1: preferred_time overlap detection ─────────────────

    def _check_time_overlaps(self, schedule: Schedule) -> None:
        """
        D1: Detect when two tasks have preferred_time values whose
            [start, start + duration) windows overlap.

        Strategy — lightweight, warning-only (never crashes):
          1. Collect every task that has a preferred_time set.
          2. Convert each "HH:MM" string to minutes-since-midnight so
             we can do plain integer arithmetic.
          3. For every unique pair (A, B) check the standard interval
             overlap condition:
                 A.start < B.end  AND  B.start < A.end
             If true, the two tasks occupy the same clock time.
          4. Calculate the exact overlap in minutes for the message.
          5. Emit a ConflictWarning — program keeps running normally.

        This check is pet-agnostic: it fires for same-pet overlaps
        (owner trying to do two things with Buddy at once) AND for
        different-pet overlaps (owner physically cannot be in two
        places at the same time).

        Called by _check_conflicts() after the schedule is built.
        """

        # Only examine tasks that carry an explicit preferred_time
        timed = [t for t in self.tasks if t.preferred_time]

        if len(timed) < 2:
            return   # nothing to compare

        def _to_minutes(hhmm: str) -> int:
            """Convert 'HH:MM' to an integer number of minutes since midnight."""
            h, m = hhmm.split(":")
            return int(h) * 60 + int(m)

        # Check every unique pair — O(n^2) but task lists are small
        for i in range(len(timed)):
            for j in range(i + 1, len(timed)):
                a = timed[i]
                b = timed[j]

                a_start = _to_minutes(a.preferred_time)
                a_end   = a_start + a.duration_minutes   # exclusive end
                b_start = _to_minutes(b.preferred_time)
                b_end   = b_start + b.duration_minutes   # exclusive end

                # Overlap condition:  A starts before B ends
                #                     AND B starts before A ends
                if a_start < b_end and b_start < a_end:
                    overlap_min = min(a_end, b_end) - max(a_start, b_start)

                    pet_a = a.pet.name if a.pet else "no pet"
                    pet_b = b.pet.name if b.pet else "no pet"

                    # Same pet vs different pet changes the message tone
                    if a.pet and b.pet and a.pet == b.pet:
                        context = (
                            f"Both tasks belong to {pet_a} — "
                            f"you cannot do two things with the same pet at once."
                        )
                    else:
                        context = (
                            f"Tasks belong to different pets "
                            f"({pet_a} and {pet_b}) — "
                            f"you cannot be in two places at the same time."
                        )

                    schedule.add_warning(ConflictWarning(
                        "time_overlap",
                        f"OVERLAP ({overlap_min} min): "
                        f"'{a.title}' ({a.preferred_time}, {a.duration_minutes} min) "
                        f"overlaps with "
                        f"'{b.title}' ({b.preferred_time}, {b.duration_minutes} min). "
                        f"{context}",
                        [a, b]
                    ))

    # ── D2 / D3: post-schedule conflict checks ────────────────

    def _check_conflicts(self, schedule: Schedule) -> None:
        """
        Run all post-schedule conflict checks and attach advisory warnings.

        Delegates to three sub-checkers, each responsible for one class of
        conflict:

        D1 — _check_time_overlaps()
            Compares preferred_time windows across all tasks in self.tasks.
            Fires before the schedule is inspected so it catches conflicts
            even for tasks that were not ultimately placed (e.g. skipped).

        D2 — Double-feeding guard
            Walks the ordered list of scheduled feeding tasks and warns
            when any two are placed fewer than 120 minutes apart.

        D3 — Exercise-after-meal guard (dogs only)
            Checks whether any exercise task for a dog starts within
            30 minutes of a feeding task ending. Applies only to dogs
            because this guideline is species-specific.

        None of these checks remove tasks or raise exceptions. Every issue
        is surfaced as a ConflictWarning attached to the schedule.

        Args:
            schedule (Schedule): The fully built schedule; warnings are
                                 appended to schedule.warnings.
        """
        # D1 — time-window overlap (runs on the raw task list, not schedule)
        self._check_time_overlaps(schedule)

        ordered   = schedule.tasks_sorted_by_start()
        feedings  = [st for st in ordered if st.task.category == "feeding"]
        exercises = [st for st in ordered if st.task.category == "exercise"]

        # D2 — double-feeding guard
        for i in range(len(feedings)):
            for j in range(i + 1, len(feedings)):
                gap = feedings[j].start_minute - feedings[i].end_minute()
                if gap < 120:
                    schedule.add_warning(ConflictWarning(
                        "double_feeding",
                        f"'{feedings[i].task.title}' and "
                        f"'{feedings[j].task.title}' are only {gap} min apart "
                        f"(recommended gap is at least 120 min).",
                        [feedings[i].task, feedings[j].task]
                    ))

        # D3 — exercise-after-meal guard (dogs only)
        for ex in exercises:
            pet = ex.task.pet
            if pet and pet.species.lower() == "dog":
                for ft in feedings:
                    gap = ex.start_minute - ft.end_minute()
                    if 0 <= gap < 30:
                        schedule.add_warning(ConflictWarning(
                            "exercise_after_meal",
                            f"'{ex.task.title}' starts only {gap} min after "
                            f"'{ft.task.title}'. "
                            f"Dogs need at least 30 min rest after eating.",
                            [ft.task, ex.task]
                        ))

    # ── public sort / filter helpers ─────────────────────────

    def sort_by_time(self, tasks: list = None) -> list:
        """
        Sort tasks by their preferred_time attribute ("HH:MM" string).

        How the lambda works:
          - Split "HH:MM" on ":" to get ["HH", "MM"].
          - Convert both parts to int → (hour, minute) tuple.
          - Python compares tuples element-by-element, so (8, 30) < (14, 0).
          - Tasks with no preferred_time set receive sentinel (24, 0) so they
            always sort to the end rather than raising an error.

        Example:
            tasks = [Task(..., preferred_time="14:00"),
                     Task(..., preferred_time="08:30"),
                     Task(..., preferred_time=None)]
            sort_by_time(tasks)
            # → [08:30 task, 14:00 task, None task]
        """
        source = tasks if tasks is not None else self.tasks

        def _time_key(task: Task) -> tuple:
            if not task.preferred_time:
                return (24, 0)                        # no time → go last
            h, m = task.preferred_time.split(":")
            return (int(h), int(m))                   # ("08","30") → (8, 30)

        return sorted(source, key=lambda t: _time_key(t))

    def filter_by_status(self, status: str, tasks: list = None) -> list:
        """
        Return only tasks whose .status matches the requested value.

        Valid statuses: 'pending' | 'done' | 'skipped'

        Usage:
            scheduler.filter_by_status("done")
            scheduler.filter_by_status("skipped", tasks=my_list)
        """
        if status not in Task.VALID_STATUSES:
            raise ValueError(
                f"Invalid status '{status}'. "
                f"Choose from {Task.VALID_STATUSES}."
            )
        source = tasks if tasks is not None else self.tasks
        return [t for t in source if t.status == status]

    def filter_by_pet(self, pet_name: str, tasks: list = None) -> list:
        """
        Return only tasks whose pet name matches pet_name (case-insensitive).
        Tasks with no pet assigned are excluded.

        Usage:
            scheduler.filter_by_pet("Buddy")
            scheduler.filter_by_pet("whisker", tasks=my_list)
        """
        source = tasks if tasks is not None else self.tasks
        return [
            t for t in source
            if t.pet and t.pet.name.lower() == pet_name.strip().lower()
        ]

    # ── private helpers ───────────────────────────────────────

    def _sort_by_priority(self, tasks: list) -> list:
        """
        Return a new list of tasks sorted from highest to lowest priority.

        Uses Python's built-in ``sorted()``, which is stable: tasks that share
        the same priority_rank() value retain their original relative order.
        This stability ensures that insertion order acts as a deterministic
        tie-breaker — no two runs of the scheduler will produce a different
        ordering for equal-priority tasks.

        Priority mapping (from Task.priority_rank):
            "high"   → 3
            "medium" → 2
            "low"    → 1

        Args:
            tasks (list[Task]): Tasks to sort. The original list is not
                                modified.

        Returns:
            list[Task]: New list ordered high → medium → low.
        """
        return sorted(tasks, key=lambda t: t.priority_rank(), reverse=True)

    def _fits_in_window(self, task: Task, used: int) -> bool:
        """
        Check whether a task can be appended without exceeding the owner's
        total available time.

        The check is a simple integer comparison:
            used + task.duration_minutes <= owner.available_minutes

        It does *not* account for buffer gaps (those are added after a task
        is confirmed to fit), and it does not check deadline_minute — the
        caller (generate) handles deadline enforcement separately.

        Args:
            task (Task): The candidate task to place next.
            used (int):  Minutes already consumed by previously placed tasks
                         plus any buffer gaps that have been inserted.

        Returns:
            bool: True if the task fits; False if it would overflow the
                  owner's day.
        """
        return (used + task.duration_minutes) <= self.owner.available_minutes
