import time
import random as rd
from schedulers.base_scheduler import ScheduleResult, IterationLog
from schedulers.genetic_algorithm_base_sheduler import GeneticAlgorithmScheduler
from models.battery import Battery
from models.terminal import Terminal

class TwoPhaseGAScheduler(GeneticAlgorithmScheduler):
    def __init__(self,
                 population_size: int = 150,
                 iterations: int = 500,
                 crossover_rate: float = 0.95,
                 mutation_rate: float = 0.15,
                 survival_rate: float = 0.05,
                 tournament_size: int = 2,
                 mutation_iters: int = 1,
                 pop_f_ratio: float = 0.1,
                 phase1_duration: int = 15,
                 phase2_duration: int = 15,
                 max_time_s: float = 5.00 * 60):

        super().__init__(
            population_size=population_size,
            iterations=iterations,
            crossover_rate=crossover_rate,
            mutation_rate=mutation_rate,
            survival_rate=survival_rate,
            tournament_size=tournament_size,
            mutation_iters=mutation_iters,
            max_time_s=max_time_s
        )
        self.pop_f_ratio = pop_f_ratio
        self.phase1_duration = phase1_duration
        self.phase2_duration = phase2_duration
        self.max_iters_without_improvement = 100

    def fit(self, terminal: Terminal, batteries: list[Battery]) -> ScheduleResult:
        self.terminal = terminal
        start_time = time.time_ns()

        population = self.initialize_population(terminal, batteries)
        makespans = [self.evaluate_makespan(individual) for individual in population]

        global_best_makespan = float('inf')
        global_best_schedule = []
        best_permutation_global_iteration = 0
        makespans_history = []

        f_size = int(self.population_size * self.pop_f_ratio)

        current_phase = 1
        phase_iter_counter = 0

        for iteration in range(self.iterations):
            if time.time() - start_time > self.max_time_s:
                break

            population_with_makespans = list(zip(population, makespans))
            population_with_makespans.sort(key=lambda pair: pair[1])

            local_best_makespan = population_with_makespans[0][1]
            if local_best_makespan < global_best_makespan:
                global_best_makespan = local_best_makespan
                global_best_schedule = list(population_with_makespans[0][0])
                best_permutation_global_iteration = iteration

            makespans_history.append(IterationLog(makespan=global_best_makespan, iteration=iteration, time_elapsed=time.time() - start_time))

            phase_iter_counter += 1
            if current_phase == 1 and phase_iter_counter > self.phase1_duration:
                current_phase = 2
                phase_iter_counter = 1
            elif current_phase == 2 and phase_iter_counter > self.phase2_duration:
                current_phase = 1
                phase_iter_counter = 1

            pop_f = population_with_makespans[:f_size]
            pop_minus_f = population_with_makespans[f_size:]

            new_population = []

            children_needed = self.population_size - len(new_population)
            parent_pool = []

            if current_phase == 1:
                parent_pool.extend([ind[0] for ind in pop_f])

            while len(parent_pool) < children_needed:
                parent_pool.append(self.tournament_selection(pop_minus_f))

            while len(new_population) < self.population_size:
                p1 = rd.choice(parent_pool)
                p2 = rd.choice(parent_pool)

                while p1 == p2:
                    p2 = rd.choice(parent_pool)

                if rd.random() < self.crossover_rate:
                    child1, child2 = self.crossover(p1, p2)
                else:
                    child1, child2 = list(p1), list(p2)

                new_population.append(self.mutation(child1))
                if len(new_population) < self.population_size:
                    new_population.append(self.mutation(child2))

            population = new_population[:self.population_size]
            makespans = [self.evaluate_makespan(i) for i in population]

            if iteration - best_permutation_global_iteration > self.max_iters_without_improvement:
                break

        population_with_makespans = list(zip(population, makespans))
        final_best_pair = min(population_with_makespans, key=lambda pair: pair[1])

        if final_best_pair[1] < global_best_makespan:
            global_best_makespan = final_best_pair[1]
            global_best_schedule = list(final_best_pair[0])
            makespans_history[-1] = global_best_makespan

        end_time = time.time_ns()

        return ScheduleResult(
            makespan=global_best_makespan,
            batteries=global_best_schedule,
            execution_time=end_time - start_time,
            history=makespans_history,
        )