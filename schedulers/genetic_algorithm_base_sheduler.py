import time
import random as rd
import math
from schedulers.base_scheduler import BaseBatteryScheduler, ScheduleResult, IterationLog
from helpers.general_helper import generate_neh_ss2_initial_solution, generate_greedy_initial_solution
from models.battery import Battery
from models.terminal import Terminal


class GeneticAlgorithmScheduler(BaseBatteryScheduler):
    def __init__(self,
                 population_size: int = 150,
                 iterations: int = 500,
                 crossover_rate: float = 0.95,
                 mutation_rate: float = 0.15,
                 survival_rate: float = 0.01,
                 tournament_size: int = 2,
                 mutation_iters: int = 1,
                 apply_neh_ss2: bool = False,
                 max_time_s: float = 5.00 * 60):
        self.population_size = population_size
        self.iterations = iterations
        self.crossover_rate = crossover_rate
        self.mutation_rate = mutation_rate
        self.tournament_size = tournament_size
        self.survival_rate = survival_rate
        self.mutation_iters = mutation_iters
        self.apply_neh_ss2 = apply_neh_ss2
        self.max_time_s = max_time_s

        self.max_iters_without_improvement = 100
        self.terminal = None

    def fit(self, terminal: Terminal, batteries: list[Battery]) -> ScheduleResult:
        self.terminal = terminal
        start_time = time.time()

        population = self.initialize_population(terminal, batteries)
        makespans = [self.evaluate_makespan(individual) for individual in population]

        global_best_makespan = float('inf')
        global_best_schedule = []
        best_permutation_global_iteration = 0
        makespans_history = []

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

            new_population = []

            num_survivors = math.ceil(self.survival_rate * self.population_size)
            for i in range(num_survivors):
                new_population.append(list(population_with_makespans[i][0]))

            while len(new_population) < self.population_size:
                parent1 = self.tournament_selection(population_with_makespans)
                parent2 = self.tournament_selection(population_with_makespans)

                if rd.random() < self.crossover_rate:
                    child1, child2 = self.crossover(parent1, parent2)
                else:
                    child1, child2 = parent1, parent2

                child1 = self.mutation(child1)
                child2 = self.mutation(child2)

                new_population.append(child1)
                new_population.append(child2)

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

        end_time = time.time()

        return ScheduleResult(
            makespan=global_best_makespan,
            batteries=global_best_schedule,
            execution_time=end_time - start_time,
            history=makespans_history,
        )

    def initialize_population(self, terminal: Terminal, batteries: list[Battery]) -> list[list[Battery]]:
        population = []

        if self.apply_neh_ss2:
            heuristic_schedule = generate_neh_ss2_initial_solution(terminal, batteries)
        else:
            heuristic_schedule = generate_greedy_initial_solution(batteries)
        population.append(heuristic_schedule)

        for _ in range(self.population_size - 1):
            random_schedule = list(batteries)
            rd.shuffle(random_schedule)
            population.append(random_schedule)

        return population

    def tournament_selection(self, population_with_makespans: list[tuple[list[Battery], float]]) -> Battery:
        tournament_candidates = rd.sample(population_with_makespans, self.tournament_size)
        winner = min(tournament_candidates, key=lambda candidate: candidate[1])
        return winner[0]

    def crossover(self, parent1: list[Battery], parent2: list[Battery]) -> tuple[list[Battery], list[Battery]]:
        length = len(parent1)
        child1 = [None] * length
        child2 = [None] * length
        start_idx, end_idx = sorted(rd.sample(range(length), 2))

        child1[start_idx:end_idx] = parent1[start_idx:end_idx]
        child2[start_idx:end_idx] = parent2[start_idx:end_idx]

        child1_set = set(child1[start_idx:end_idx])
        child2_set = set(child2[start_idx:end_idx])

        parent1_remnants = [i for i in parent1 if i not in child2_set]
        parent2_remnants = [i for i in parent2 if i not in child1_set]

        p1_idx = p2_idx = 0
        for i in range(length):
            if child1[i] is None:
                child1[i] = parent2_remnants[p2_idx]
                p2_idx += 1

            if child2[i] is None:
                child2[i] = parent1_remnants[p1_idx]
                p1_idx += 1

        return child1, child2

    def mutation(self, schedule: list[Battery]) -> list[Battery]:
        if rd.random() < self.mutation_rate:
            new_schedule = list(schedule)
            for _ in range(self.mutation_iters):
                idx1, idx2 = rd.sample(range(len(new_schedule)), 2)
                new_schedule[idx1], new_schedule[idx2] = new_schedule[idx2], new_schedule[idx1]
            return new_schedule
        return schedule

    def evaluate_makespan(self, sequence: list[Battery]) -> float:
        self.terminal.load_batteries(sequence)
        return self.terminal.process()