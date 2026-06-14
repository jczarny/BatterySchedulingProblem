import time
import random as rd
import math
from schedulers.base_scheduler import BaseBatteryScheduler, ScheduleResult, IterationLog
from models.battery import Battery
from helpers.general_helper import generate_neh_ss2_initial_solution, generate_greedy_initial_solution
from models.terminal import Terminal


class TabuSearchScheduler(BaseBatteryScheduler):
    def __init__(self,
                 iterations: int = 1000,
                 neighbourhood_size: int = 40,
                 dynamic_tenure: bool = True,
                 base_tabu_tenure: int = 15,
                 no_improve_diversify: int = 50,
                 diversification_factor: float = 0.25,
                 apply_neh_ss2: bool = False,
                 max_time_s: float = 5.00 * 60):
        self.iterations = iterations
        self.neighbourhood_size = neighbourhood_size
        self.base_tabu_tenure = base_tabu_tenure
        self.no_improve_diversify = no_improve_diversify
        self.dynamic_tenure = dynamic_tenure
        self.diversification_factor = diversification_factor
        self.apply_neh_ss2 = apply_neh_ss2
        self.max_time_s = max_time_s
        self.terminal = None
        self.max_iters_without_improvement = 4*no_improve_diversify

    def fit(self, terminal: Terminal, batteries: list[Battery]) -> ScheduleResult:
        self.terminal = terminal
        t_s = time.time_ns()
        n = len(batteries)

        if self.apply_neh_ss2:
            best_solution = generate_neh_ss2_initial_solution(terminal, batteries)
        else:
            best_solution = generate_greedy_initial_solution(batteries)

        terminal.load_batteries(best_solution)
        best_makespan = terminal.process()

        tabu_dict = {}
        current_solution = list(best_solution)
        makespans_history = [IterationLog(makespan=best_makespan, iteration=-1, time_elapsed=time.time())]
        iters_without_improvement = 0

        for current_iteration in range(self.iterations):
            if time.time() - t_s > self.max_time_s:
                break

            neighbour_swaps = self.generate_neighbourhood_swaps(current_solution)
            neighbour_swaps.sort(key=lambda x: x[3])

            iteration_improved = False

            for swap in neighbour_swaps:
                id1, id2, neighbour_solution, makespan = swap
                next_swap_allowed_iteration = tabu_dict.get((id1, id2), 0)

                is_aspiration_met = makespan < best_makespan
                is_not_tabu = current_iteration >= next_swap_allowed_iteration

                if is_not_tabu or is_aspiration_met:
                    if is_aspiration_met:
                        best_makespan = makespan
                        best_solution = neighbour_solution
                        iteration_improved = True

                    tabu_dict[id1, id2] = current_iteration + self.get_current_tenure(n, iters_without_improvement)
                    current_solution = neighbour_solution
                    break

            if iteration_improved:
                iters_without_improvement = 0
            else:
                iters_without_improvement += 1

            makespans_history.append(IterationLog(makespan=best_makespan, iteration=current_iteration, time_elapsed=time.time() - t_s))

            if iters_without_improvement % self.no_improve_diversify == 0 and iters_without_improvement > 0:
                current_solution = self.diversify(best_solution)
                tabu_dict = {}

            if iters_without_improvement >= self.max_iters_without_improvement:
                break

        t_e = time.time_ns()
        return ScheduleResult(
            makespan=best_makespan,
            batteries=best_solution,
            execution_time=t_e - t_s,
            history=makespans_history,
        )

    def generate_neighbourhood_swaps(self, current_solution: list[Battery]) -> list:
        neighbour_swaps = []
        n = len(current_solution)

        for _ in range(self.neighbourhood_size):
            idx1, idx2 = rd.sample(range(n), 2)
            if idx1 > idx2:
                idx1, idx2 = idx2, idx1
    
            neighbour_solution = list(current_solution)
            neighbour_solution[idx1], neighbour_solution[idx2] = neighbour_solution[idx2], neighbour_solution[idx1]

            self.terminal.load_batteries(neighbour_solution)
            makespan = self.terminal.process()

            neighbour_swaps.append([
                neighbour_solution[idx1].id,
                neighbour_solution[idx2].id,
                neighbour_solution,
                makespan
            ])

        return neighbour_swaps

    def diversify(self, current_solution: list[Battery]) -> list[Battery]:
        diversified_solution = list(current_solution)
        n = len(current_solution)
        batteries_to_shuffle = max(2, int(self.diversification_factor * len(current_solution)))

        for _ in range(batteries_to_shuffle):
            idx_from, idx_to = rd.sample(range(n), 2)
            battery = diversified_solution.pop(idx_from)
            diversified_solution.insert(idx_to, battery)

        return diversified_solution

    def get_current_tenure(self, n_batteries: int, iters_without_improvement: int) -> int:
        if not self.dynamic_tenure:
            return self.base_tabu_tenure

        current_tenure = self.base_tabu_tenure + int(math.sqrt(n_batteries))
        stagnation_penalty = iters_without_improvement // 10
        return max(5, current_tenure + stagnation_penalty)