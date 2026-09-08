import itertools
import time
import math
import copy
from schedulers.base_scheduler import BaseBatteryScheduler, ScheduleResult, IterationLog
from models.battery import Battery
from models.terminal import Terminal


class BruteForceScheduler(BaseBatteryScheduler):
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
        best_permutation = []
        lowest_makespan = float('inf')

        counter = 0
        for path in itertools.permutations(batteries):
            if self.time_limit_reached(t_s) or self.solution_limit_reached():
                break

            clean_path = [copy.copy(b) for b in path]
            for b in clean_path:
                b.start_time = None
                b.completion_time = None

            terminal.load_batteries(clean_path)
            makespan = terminal.process()

            if makespan < lowest_makespan:
                lowest_makespan = makespan
                best_permutation = clean_path

            counter += 1
            self.solution_count = counter
            if(counter % 300000 == 0):
                print(f"Iter counter: {(counter / math.factorial(len(batteries)))*100:.2f}%")

        t_e = time.time()
        return ScheduleResult(
            makespan=lowest_makespan,
            batteries=best_permutation,
            execution_time=t_e - t_s,
            history=[IterationLog(makespan=lowest_makespan, iteration=counter, time_elapsed=t_e - t_s, solution_count=self.solution_count)],
            solution_count=self.solution_count,
        )
