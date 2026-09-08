from abc import ABC, abstractmethod
import time
from models.battery import Battery
from models.terminal import Terminal

class IterationLog:
    makespan: float
    iteration: int
    time_elapsed: float
    solution_count: int

    def __init__(
            self,
            makespan: float,
            iteration: int,
            time_elapsed: float,
            solution_count: int = 0):
        self.makespan = makespan
        self.iteration = iteration
        self.time_elapsed = time_elapsed
        self.solution_count = solution_count


class ScheduleResult:
    def __init__(
            self,
            makespan: float,
            batteries: list[Battery],
            execution_time: float,
            history: list[IterationLog],
            solution_count: int = 0):
        self.makespan = makespan
        self.batteries = batteries
        self.execution_time = execution_time
        self.history = history
        self.solution_count = solution_count

class BaseBatteryScheduler(ABC):
    min_solutions: int = 0
    max_solutions: int | None = None
    solution_count: int = 0

    def solution_limit_reached(self) -> bool:
        return self.max_solutions is not None and self.solution_count >= self.max_solutions

    def time_limit_reached(self, start_time: float) -> bool:
        max_time_s = getattr(self, "max_time_s", None)
        return (
                max_time_s is not None
                and time.time() - start_time > max_time_s
                and self.solution_count >= self.min_solutions
        )

    def can_stop_on_no_improvement(self) -> bool:
        return self.solution_count >= self.min_solutions

    @abstractmethod
    def fit(self, terminal: Terminal, batteries: list[Battery]) -> ScheduleResult:
        pass
