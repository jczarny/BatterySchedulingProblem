import time
import random as rd
from schedulers.base_scheduler import ScheduleResult, IterationLog
from schedulers.genetic_algorithm_base_sheduler import GeneticAlgorithmScheduler
from models.battery import Battery
from models.terminal import Terminal
from helpers.spv_helper import smallest_position_value_sort, align_continuous_position
from helpers.general_helper import get_eta

class BRKGA_R_LS_Scheduler(GeneticAlgorithmScheduler):

    def __init__(self,
                 population_size: int = 150,
                 iterations: int = 500,
                 crossover_rate: float = 0.95,
                 mutation_rate: float = 0.15,
                 survival_rate: float = 0.01,
                 tournament_size: int = 2,
                 mutation_iters: int = 1,
                 elite_percentage: float = 0.15,
                 mutant_percentage: float = 0.15,
                 elite_inheritance_prob: float = 0.65,
                 restarts_patience: int = 100,
                 ls_periodic_run_period: int = 100,
                 ls_range: int = 5,
                 max_time_s: float = 5.00 * 60):

        super().__init__(
            population_size=population_size,
            iterations=iterations,
            crossover_rate=crossover_rate,
            mutation_rate=mutation_rate,
            survival_rate=survival_rate,
            tournament_size=tournament_size,
            mutation_iters=mutation_iters,
            max_time_s=max_time_s,
        )

        self.elite_percentage = elite_percentage
        self.mutant_percentage = mutant_percentage
        self.elite_inheritance_prob = elite_inheritance_prob
        self.restarts_patience = restarts_patience
        self.ls_range = ls_range
        self.ls_periodic_run_period = ls_periodic_run_period
        self.max_iters_without_improvement = 100

    def fit(self, terminal: Terminal, batteries: list[Battery]) -> ScheduleResult:
        self.terminal = terminal
        start_time = time.time()
        num_dimensions = len(batteries)

        num_elite = int(self.population_size * self.elite_percentage)
        num_mutants = int(self.population_size * self.mutant_percentage)
        num_crossover = self.population_size - num_elite - num_mutants

        population_keys = [[rd.random() for _ in range(num_dimensions)] for _ in range(self.population_size)]

        sorted_indices_by_eta = sorted(range(num_dimensions), key=lambda i: get_eta(batteries[i]), reverse=True)
        for rank, original_index in enumerate(sorted_indices_by_eta):
            population_keys[0][original_index] = rank / num_dimensions

        global_best_makespan = float('inf')
        global_best_schedule = []
        global_best_keys = []
        best_permutation_global_iteration = 0
        makespans_history = []
        iters_without_improvement = 0

        for iteration in range(self.iterations):
            if time.time() - start_time > self.max_time_s:
                break

            decoded_population = []
            makespans = []

            for keys in population_keys:
                schedule = smallest_position_value_sort(keys, batteries)
                makespan = self.evaluate_makespan(schedule)
                decoded_population.append(schedule)
                makespans.append(makespan)

            population_scored = list(zip(population_keys, decoded_population, makespans))
            population_scored.sort(key=lambda x: x[2])

            current_best_keys, current_best_schedule, current_best_makespan = population_scored[0]

            if current_best_makespan < global_best_makespan:
                global_best_makespan = current_best_makespan
                global_best_schedule = list(current_best_schedule)
                global_best_keys = list(current_best_keys)
                best_permutation_global_iteration = iteration

                ls_schedule, ls_makespan = self.run_local_search(global_best_schedule, global_best_makespan)

                if ls_makespan < global_best_makespan:
                    global_best_makespan = ls_makespan
                    global_best_schedule = ls_schedule
                    global_best_keys = align_continuous_position(global_best_schedule, global_best_keys, batteries)
                    population_scored[0] = (list(global_best_keys), list(global_best_schedule), global_best_makespan)

                iters_without_improvement = 0
            else:
                if iteration % self.ls_periodic_run_period == 0 and iteration > 0:
                    ls_schedule, ls_makespan = self.run_local_search(global_best_schedule, global_best_makespan)
                    if ls_makespan < global_best_makespan:
                        global_best_makespan = ls_makespan
                        global_best_schedule = ls_schedule
                        global_best_keys = align_continuous_position(global_best_schedule, global_best_keys, batteries)
                        best_permutation_global_iteration = iteration
                        population_scored[0] = (list(global_best_keys), list(global_best_schedule), global_best_makespan)
                        iters_without_improvement = 0
                else:
                    iters_without_improvement += 1

            makespans_history.append(IterationLog(makespan=global_best_makespan, iteration=iteration, time_elapsed=time.time() - start_time))

            if iters_without_improvement >= self.restarts_patience:
                population_keys = [list(global_best_keys)] + [[rd.random() for _ in range(num_dimensions)] for _ in range(self.population_size - 1)]
                iters_without_improvement = 0
                continue

            next_population_keys = []

            elite_set = [ind[0] for ind in population_scored[:num_elite]]
            non_elite_set = [ind[0] for ind in population_scored[num_elite:]]

            next_population_keys.extend(elite_set)

            for _ in range(num_mutants):
                next_population_keys.append([rd.random() for _ in range(num_dimensions)])

            for _ in range(num_crossover):
                elite_parent = rd.choice(elite_set)
                non_elite_parent = rd.choice(non_elite_set)
                child_keys = []

                for d in range(num_dimensions):
                    if rd.random() < self.elite_inheritance_prob:
                        child_keys.append(elite_parent[d])
                    else:
                        child_keys.append(non_elite_parent[d])

                next_population_keys.append(child_keys)

            if iteration - best_permutation_global_iteration > self.max_iters_without_improvement:
                break
            population_keys = next_population_keys

        end_time = time.time()

        return ScheduleResult(
            makespan=global_best_makespan,
            batteries=global_best_schedule,
            execution_time=end_time - start_time,
            history=makespans_history,
        )

    def run_local_search(self, schedule: list[Battery], current_makespan: float) -> tuple[list[Battery], float]:
        best_schedule = list(schedule)
        best_makespan = current_makespan
        num_elements = len(schedule)
        is_improved = True

        while is_improved:
            is_improved = False

            for current_idx in range(num_elements):
                min_range = max(0, current_idx - self.ls_range)
                max_range = min(num_elements, current_idx + self.ls_range + 1)

                for target_idx in range(min_range, max_range):
                    if current_idx == target_idx:
                        continue

                    neighbour_schedule = list(best_schedule)
                    moving_job = neighbour_schedule.pop(current_idx)
                    neighbour_schedule.insert(target_idx, moving_job)

                    makespan = self.evaluate_makespan(neighbour_schedule)

                    if makespan < best_makespan:
                        best_makespan = makespan
                        best_schedule = neighbour_schedule
                        is_improved = True
                        break

                if is_improved:
                    break

        return best_schedule, best_makespan