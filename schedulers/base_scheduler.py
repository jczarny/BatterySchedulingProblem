from abc import ABC, abstractmethod
from models.battery import Battery
from models.terminal import Terminal

class IterationLog:
    makespan: float
    iteration: int
    time_elapsed: float

    def __init__(
            self,
            makespan: float,
            iteration: int,
            time_elapsed: float):
        self.makespan = makespan
        self.iteration = iteration
        self.time_elapsed = time_elapsed


class ScheduleResult:
    def __init__(
            self,
            makespan: float,
            batteries: list[Battery],
            execution_time: float,
            history: list[IterationLog]):
        self.makespan = makespan
        self.batteries = batteries
        self.execution_time = execution_time
        self.history = history

class BaseBatteryScheduler(ABC):
    @abstractmethod
    def fit(self, terminal: Terminal, batteries: list[Battery]) -> ScheduleResult:
        pass