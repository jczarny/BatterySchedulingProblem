import time
from schedulers.base_scheduler import BaseBatteryScheduler, ScheduleResult, IterationLog
from models.battery import Battery
from models.terminal import Terminal


class LongestTimeProcessingScheduler(BaseBatteryScheduler):

    def fit(self, terminal: Terminal, batteries: list[Battery]) -> ScheduleResult:
        t_s = time.time_ns()

        sorted_batteries = sorted(batteries, key=lambda battery: battery.processing_time, reverse=True)
        terminal.load_batteries(sorted_batteries)
        makespan = terminal.process()

        t_e = time.time_ns()
        return ScheduleResult(
            makespan = makespan,
            batteries = batteries,
            execution_time = t_e - t_s,
            history = [IterationLog(makespan=makespan, iteration=0, time_elapsed=t_e - t_s)],
        )