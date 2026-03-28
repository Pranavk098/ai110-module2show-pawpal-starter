class Pet:
    def __init__(self, name: str, species: str):
        self.name = name
        self.species = species


class Owner:
    def __init__(self, name: str, available_minutes: int, pets: list):
        self.name = name
        self.available_minutes = available_minutes
        self.pets = pets  # List[Pet]


class Task:
    def __init__(self, title: str, duration_minutes: int, priority: str):
        self.title = title
        self.duration_minutes = duration_minutes
        self.priority = priority  # "low", "medium", or "high"

    def priority_rank(self) -> int:
        pass


class ScheduledTask:
    def __init__(self, task: Task, start_minute: int):
        self.task = task
        self.start_minute = start_minute

    def end_minute(self) -> int:
        pass


class Schedule:
    def __init__(self):
        self.scheduled_tasks = []   # List[ScheduledTask]
        self.skipped_tasks = []     # List[tuple(Task, reason: str)]
        self.total_minutes_used = 0

    def add_task(self, st: ScheduledTask) -> None:
        pass

    def skip_task(self, task: Task, reason: str) -> None:
        pass


class Scheduler:
    def __init__(self, owner: Owner, tasks: list):
        self.owner = owner
        self.tasks = tasks  # List[Task]

    def generate(self) -> Schedule:
        pass

    def _sort_by_priority(self, tasks: list) -> list:
        pass

    def _fits_in_window(self, task: Task, used: int) -> bool:
        pass
