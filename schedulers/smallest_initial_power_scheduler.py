import time
from schedulers.base_scheduler import BaseBatteryScheduler, ScheduleResult, IterationLog
from models.battery import Battery
from models.terminal import Terminal

class SmallestInitialPowerScheduler(BaseBatteryScheduler):
    def __init__(
            self,
            max_time_s: float | None = None,
            min_solutions: int = 0,
            max_solutions: int | None = None):
        self.max_time_s = max_time_s
        self.min_solutions = min_solutions
        self.max_solutions = max_solutions
        self.solution_count = 0

    def fit(self, terminal: Terminal, batteries: list[Battery]) -> ScheduleResult:
        t_s = time.time()
        self.solution_count = 0

        sorted_batteries = sorted(batteries, key=lambda battery: battery.initial_power_consumption)
        terminal.load_batteries(sorted_batteries)
        makespan = terminal.process()
        self.solution_count = 1

        t_e = time.time()
        return ScheduleResult(
            makespan = makespan,
            batteries = sorted_batteries,
            execution_time = t_e - t_s,
            history=[IterationLog(makespan=makespan, iteration=0, time_elapsed=t_e - t_s, solution_count=self.solution_count)],
            solution_count=self.solution_count,
        )
