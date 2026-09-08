import time
import random as rd
from schedulers.base_scheduler import ScheduleResult, IterationLog
from schedulers.genetic_algorithm_base_sheduler import GeneticAlgorithmScheduler
from models.battery import Battery
from models.terminal import Terminal

class TwoPhaseGAScheduler(GeneticAlgorithmScheduler):
    def __init__(self,
                 population_size: int = 100,
                 iterations: int = 1_000_000_000,
                 crossover_rate: float = 0.90,
                 mutation_rate: float = 0.15,
                 survival_rate: float = 0.05,
                 tournament_size: int = 5,
                 mutation_iters: int = 1,
                 pop_f_ratio: float = 0.2,
                 candidate_list_size: int | None = None,
                 phase1_duration: int = 15,
                 phase2_duration: int = 15,
                 max_time_s: float = 2.50 * 60,
                 min_solutions: int = 0,
                 max_solutions: int | None = None):

        super().__init__(
            population_size=population_size,
            iterations=iterations,
            crossover_rate=crossover_rate,
            mutation_rate=mutation_rate,
            survival_rate=survival_rate,
            tournament_size=tournament_size,
            mutation_iters=mutation_iters,
            max_time_s=max_time_s,
            min_solutions=min_solutions,
            max_solutions=max_solutions,
        )
        self.pop_f_ratio = pop_f_ratio
        self.candidate_list_size = candidate_list_size
        self.phase1_duration = phase1_duration
        self.phase2_duration = phase2_duration
        self.candidate_solution_list: list[tuple[list[Battery], float]] = []
        self.max_iters_without_improvement = 1_000_000_000

    def fit(self, terminal: Terminal, batteries: list[Battery]) -> ScheduleResult:
        self.terminal = terminal
        self.solution_count = 0
        self.candidate_solution_list = []
        start_time = time.time()

        population = self.initialize_population(terminal, batteries)
        makespans = []
        evaluated_population = []
        for individual in population:
            if self.solution_limit_reached():
                break

            makespans.append(self.evaluate_makespan(individual))
            evaluated_population.append(individual)
        population = evaluated_population

        global_best_makespan = float('inf')
        global_best_schedule = []
        best_permutation_global_iteration = 0
        makespans_history = []

        current_phase = 1
        phase_iter_counter = 0

        for iteration in range(self.iterations):
            if self.time_limit_reached(start_time) or self.solution_limit_reached():
                break

            population_with_makespans = list(zip(population, makespans))
            if not population_with_makespans:
                break

            population_with_makespans.sort(key=lambda pair: pair[1])
            self.update_candidate_solution_list(population_with_makespans)

            local_best_makespan = population_with_makespans[0][1]
            if local_best_makespan < global_best_makespan:
                global_best_makespan = local_best_makespan
                global_best_schedule = list(population_with_makespans[0][0])
                best_permutation_global_iteration = iteration

            makespans_history.append(IterationLog(makespan=global_best_makespan, iteration=iteration, time_elapsed=time.time() - start_time, solution_count=self.solution_count))

            phase_iter_counter += 1
            if current_phase == 1 and phase_iter_counter > self.phase1_duration:
                current_phase = 2
                phase_iter_counter = 1
            elif current_phase == 2 and phase_iter_counter > self.phase2_duration:
                current_phase = 1
                phase_iter_counter = 1

            parent_pool = self.build_parent_pool(
                population_with_makespans,
                parent_count=self.population_size,
                phase=current_phase,
            )
            population = self.create_next_population(parent_pool)
            makespans = []
            evaluated_population = []
            for individual in population:
                if self.solution_limit_reached():
                    break

                makespans.append(self.evaluate_makespan(individual))
                evaluated_population.append(individual)
            population = evaluated_population

            if iteration - best_permutation_global_iteration > self.max_iters_without_improvement and self.can_stop_on_no_improvement():
                break

        population_with_makespans = list(zip(population, makespans))
        self.update_candidate_solution_list(population_with_makespans)
        final_best_pair = min(population_with_makespans, key=lambda pair: pair[1]) if population_with_makespans else None

        if final_best_pair is not None and final_best_pair[1] < global_best_makespan:
            global_best_makespan = final_best_pair[1]
            global_best_schedule = list(final_best_pair[0])
        if makespans_history:
            makespans_history[-1].makespan = global_best_makespan
            makespans_history[-1].solution_count = self.solution_count

        end_time = time.time()

        return ScheduleResult(
            makespan=global_best_makespan,
            batteries=global_best_schedule,
            execution_time=end_time - start_time,
            history=makespans_history,
            solution_count=self.solution_count,
        )

    def create_next_population(self, parent_pool: list[list[Battery]]) -> list[list[Battery]]:
        selected_parents = list(parent_pool)
        rd.shuffle(selected_parents)
        new_population = []

        paired_parent_count = len(selected_parents) - len(selected_parents) % 2
        for index in range(0, paired_parent_count, 2):
            parent1 = selected_parents[index]
            parent2 = selected_parents[index + 1]

            if rd.random() < self.crossover_rate:
                child1, child2 = self.crossover(parent1, parent2)
            else:
                child1, child2 = list(parent1), list(parent2)

            new_population.append(self.mutation(child1))
            new_population.append(self.mutation(child2))

        if paired_parent_count < len(selected_parents):
            new_population.append(self.mutation(list(selected_parents[-1])))

        return new_population

    def crossover(self, parent1: list[Battery], parent2: list[Battery]) -> tuple[list[Battery], list[Battery]]:
        if len(parent1) < 2:
            return list(parent1), list(parent2)

        r1, r2 = sorted(rd.sample(range(1, len(parent1) + 1), 2))
        child1 = self.build_child(parent1, parent2, r1, r2)
        child2 = self.build_child(parent2, parent1, r1, r2)
        return child1, child2

    @staticmethod
    def build_child(
            mother: list[Battery],
            father: list[Battery],
            r1: int,
            r2: int) -> list[Battery]:
        child = list(mother[:r1])
        child_set = set(child)

        for battery in father:
            if battery not in child_set:
                child.append(battery)
                child_set.add(battery)
            if len(child) == r2:
                break

        for battery in mother[r1:]:
            if battery not in child_set:
                child.append(battery)
                child_set.add(battery)

        return child

    def mutation(self, schedule: list[Battery]) -> list[Battery]:
        if rd.random() >= self.mutation_rate or len(schedule) < 2:
            return schedule

        new_schedule = list(schedule)
        mutation_operators = (
            self.move_one_activity,
            self.exchange_activities,
            self.move_activity_group,
        )
        for _ in range(self.mutation_iters):
            rd.choice(mutation_operators)(new_schedule)

        return new_schedule

    @staticmethod
    def move_one_activity(schedule: list[Battery]):
        source_index, target_index = rd.sample(range(len(schedule)), 2)
        battery = schedule.pop(source_index)
        schedule.insert(target_index, battery)

    @staticmethod
    def exchange_activities(schedule: list[Battery]):
        first_index, second_index = rd.sample(range(len(schedule)), 2)
        schedule[first_index], schedule[second_index] = schedule[second_index], schedule[first_index]

    @staticmethod
    def move_activity_group(schedule: list[Battery]):
        if len(schedule) < 3:
            TwoPhaseGAScheduler.exchange_activities(schedule)
            return

        group_length = rd.randint(2, len(schedule) - 1)
        group_start = rd.randint(0, len(schedule) - group_length)
        group_end = group_start + group_length
        group = schedule[group_start:group_end]
        del schedule[group_start:group_end]

        insertion_indices = [
            index for index in range(len(schedule) + 1)
            if index != group_start
        ]
        insertion_index = rd.choice(insertion_indices)
        schedule[insertion_index:insertion_index] = group

    def update_candidate_solution_list(
            self,
            population_with_makespans: list[tuple[list[Battery], float]]):
        if not population_with_makespans:
            return

        list_size = self.candidate_list_size
        if list_size is None:
            list_size = self.calculate_f_size(self.population_size)

        candidates = self.candidate_solution_list + population_with_makespans
        candidates.sort(key=lambda pair: pair[1])

        unique_candidates = []
        sequence_keys = set()
        for schedule, makespan in candidates:
            sequence_key = tuple(getattr(battery, "id", id(battery)) for battery in schedule)
            if sequence_key in sequence_keys:
                continue

            unique_candidates.append((list(schedule), makespan))
            sequence_keys.add(sequence_key)
            if len(unique_candidates) == list_size:
                break

        self.candidate_solution_list = unique_candidates

    def population_deteriorated(
            self,
            population_with_makespans: list[tuple[list[Battery], float]]) -> bool:
        if not population_with_makespans or not self.candidate_solution_list:
            return False
        return population_with_makespans[0][1] > self.candidate_solution_list[0][1] + 1e-12

    def calculate_f_size(self, population_size: int) -> int:
        if population_size < 2:
            return 1
        return max(1, min(population_size - 1, int(population_size * self.pop_f_ratio)))

    def build_parent_pool(
            self,
            population_with_makespans: list[tuple[list[Battery], float]],
            parent_count: int,
            phase: int) -> list[list[Battery]]:

        if phase not in {1, 2}:
            raise ValueError("phase musi mieć wartość 1 albo 2.")
        if parent_count < 1:
            return []
        if len(population_with_makespans) == 1:
            return [population_with_makespans[0][0]] * parent_count

        f_size = self.calculate_f_size(len(population_with_makespans))
        pop_f = population_with_makespans[:f_size]
        pop_minus_f = population_with_makespans[f_size:]
        parent_pool = []
        if phase == 1:
            parent_pool.extend(individual for individual, _ in pop_f)
            if self.population_deteriorated(population_with_makespans):
                parent_keys = {
                    tuple(getattr(battery, "id", id(battery)) for battery in individual)
                    for individual in parent_pool
                }
                for candidate, _ in self.candidate_solution_list:
                    candidate_key = tuple(getattr(battery, "id", id(battery)) for battery in candidate)
                    if candidate_key not in parent_keys and len(parent_pool) < parent_count:
                        parent_pool.append(list(candidate))
                        parent_keys.add(candidate_key)

        while len(parent_pool) < parent_count:
            parent_pool.append(self.tournament_selection(pop_minus_f))

        return parent_pool[:parent_count]
