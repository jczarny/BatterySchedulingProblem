import time
import random as rd
import copy
from schedulers.base_scheduler import BaseBatteryScheduler, ScheduleResult, IterationLog
from models.battery import Battery
from models.terminal import Terminal
from helpers.general_helper import get_eta


class AntColonyScheduler(BaseBatteryScheduler):
    def __init__(self,
            num_ants: int = 50,
            iterations: int = 200,
            alpha: float = 1.0,
            beta: float = 1.0,
            decay: float = 0.1,
            p_best: float = 0.05,
            max_time_s: float = 5.00 * 60):
        self.num_ants = num_ants
        self.iterations = iterations
        self.alpha = alpha
        self.beta = beta
        self.decay = decay
        self.p_best = p_best
        self.max_time_s = max_time_s

        self.etas = None
        self.pheromones = None
        self.pheromone_min_val = 0.1
        self.pheromone_max_val = 1.0

        self.max_iters_without_improvement = 50

    def fit(self, terminal: Terminal, batteries: list[Battery]) -> ScheduleResult:
        self.etas = None
        self.pheromones = None
        t_s = time.time()

        self.pheromones = [[self.pheromone_max_val for _ in range(len(batteries))] for _ in range(len(batteries))]
        best_permutation_global = []
        best_permutation_global_iteration = 0
        lowest_makespan_global = float('inf')

        makespans_history = []
        for iteration in range(self.iterations):
            if time.time() - t_s > self.max_time_s:
                break

            best_permutation_local = []
            lowest_makespan_local = float('inf')
            paths = self.build_paths(batteries)
            for path in paths:
                clean_path = [copy.copy(b) for b in path]
                for b in clean_path:
                    b.start_time = None
                    b.completion_time = None

                terminal.load_batteries(clean_path)
                makespan = terminal.process()

                if lowest_makespan_local > makespan:
                    lowest_makespan_local = makespan
                    best_permutation_local = path

                if lowest_makespan_global > makespan:
                    lowest_makespan_global = makespan
                    best_permutation_global = path
                    best_permutation_global_iteration = iteration

            for i in range(len(batteries)):
                for j in range(len(batteries)):
                    self.pheromones[i][j] *= (1.0 - self.decay)

            self.update_pheromone_limits(lowest_makespan_local, len(batteries))

            pheromone_trail_value = 1.0 / lowest_makespan_local
            for step in range(len(best_permutation_local) - 1):
                current_idx = batteries.index(best_permutation_local[step])
                next_idx = batteries.index(best_permutation_local[step + 1])
                self.pheromones[current_idx][next_idx] += pheromone_trail_value

            for i in range(len(batteries)):
                for j in range(len(batteries)):
                    if self.pheromones[i][j] > self.pheromone_max_val:
                        self.pheromones[i][j] = self.pheromone_max_val
                    elif self.pheromones[i][j] < self.pheromone_min_val:
                        self.pheromones[i][j] = self.pheromone_min_val

            makespans_history.append(IterationLog(makespan=lowest_makespan_global, iteration=iteration, time_elapsed=time.time() - t_s))

            if iteration - best_permutation_global_iteration > self.max_iters_without_improvement:
                break


        t_e = time.time()
        return ScheduleResult(
            makespan = lowest_makespan_global,
            batteries = best_permutation_global,
            execution_time = t_e - t_s,
            history = makespans_history,
        )

    def build_paths(self, batteries: list[Battery]) -> list[list[Battery]]:
        if self.etas is None:
            self.etas = [get_eta(battery) for battery in batteries]

        paths = []
        starting_batteries = rd.choices(batteries, weights=self.etas, k=self.num_ants)

        for i in range(self.num_ants):
            unvisited_batteries = list(batteries)
            path = [starting_batteries[i]]
            unvisited_batteries.remove(starting_batteries[i])

            while unvisited_batteries:
                current_idx = batteries.index(path[-1])
                probabilities = []

                for battery in unvisited_batteries:
                    candidate_idx = batteries.index(battery)
                    tau = self.pheromones[current_idx][candidate_idx]
                    probability = (tau ** self.alpha) * (self.etas[candidate_idx] ** self.beta)
                    probabilities.append(probability)

                next_battery = rd.choices(unvisited_batteries, weights=probabilities, k=1)[0]
                path.append(next_battery)
                unvisited_batteries.remove(next_battery)

            paths.append(path)

        return paths

    def update_pheromone_limits(self, best_makespan: float, n_batteries: int) -> None:
        self.pheromone_max_val =  (1 / (1 - self.decay)) * (1 / best_makespan)

        p_dec = self.p_best ** (1.0 / n_batteries)
        avg = n_batteries / 2

        self.pheromone_min_val = (self.pheromone_max_val * (1.0 - p_dec)) / ((avg - 1.0) * p_dec)
        if self.pheromone_min_val > self.pheromone_max_val:
            self.pheromone_min_val = self.pheromone_max_val