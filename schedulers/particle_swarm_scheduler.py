import time
import random as rd
import math
import numpy as np
from schedulers.base_scheduler import BaseBatteryScheduler, ScheduleResult, IterationLog
from helpers.spv_helper import *
from models.battery import Battery
from models.terminal import Terminal
from helpers.general_helper import get_eta

class Particle:
    def __init__(self, num_dimensions: int):
        self.position = [rd.uniform(-10.0, 10.0) for _ in range(num_dimensions)]
        self.velocity = [rd.uniform(-1.0, 1.0) for _ in range(num_dimensions)]
        self.personal_best_position = list(self.position)
        self.personal_best_makespan = float('inf')


class ParticleSwarmScheduler(BaseBatteryScheduler):
    def __init__(self,
                 num_particles: int = 40,
                 iterations: int = 200,
                 stubbornness_coefficient: float = 0.9,
                 personal_impact_coefficient: float = 2.0,
                 environmental_impact_coefficient: float = 2.0,
                 final_temperature: float = 0.5,
                 cooling_rate: float = 0.98,
                 apply_vns: bool = True,
                 apply_sa: bool = True,
                 max_time_s: float = 5.00 * 60
                 ):
        self.num_particles = num_particles
        self.iterations = iterations
        self.stubbornness_coefficient = stubbornness_coefficient
        self.personal_impact_coefficient = personal_impact_coefficient
        self.environmental_impact_coefficient = environmental_impact_coefficient
        self.final_temperature = final_temperature
        self.cooling_rate = cooling_rate
        self.apply_vns = apply_vns
        self.apply_sa = apply_sa
        self.max_time_s = max_time_s

        self.initial_temperature = 100.0
        self.vns_max_iterations = 0
        self.max_velocity = 5.0
        self.terminal = None
        self.max_iters_without_improvement = 50

    def fit(self, terminal: Terminal, batteries: list[Battery]) -> ScheduleResult:
        self.terminal = terminal
        self.vns_max_iterations = min(len(batteries) * 5, 1000)
        start_time = time.time_ns()
        num_dimensions = len(batteries)

        swarm = [Particle(num_dimensions) for _ in range(self.num_particles)]

        sorted_indices_by_eta = sorted(range(num_dimensions), key=lambda i: get_eta(batteries[i]), reverse=True)
        for rank, original_index in enumerate(sorted_indices_by_eta):
            swarm[0].position[original_index] = -10.0 + (rank * (20.0 / num_dimensions))
        swarm[0].personal_best_position = list(swarm[0].position)

        global_best_position = []
        global_best_makespan = float('inf')
        global_best_schedule = []
        best_permutation_global_iteration = 0

        makespans_history = []
        for particle in swarm:
            current_schedule = smallest_position_value_sort(particle.position, batteries)
            current_makespan = self.evaluate_makespan(current_schedule)

            particle.personal_best_makespan = current_makespan
            particle.personal_best_position = list(particle.position)

            if current_makespan < global_best_makespan:
                global_best_makespan = current_makespan
                global_best_position = list(particle.position)
                global_best_schedule = current_schedule

        for iteration in range(self.iterations):
            if time.time() - start_time > self.max_time_s:
                break

            for particle in swarm:
                for d in range(num_dimensions):
                    # Equation explained more thoroughly in https://en.wikipedia.org/wiki/Particle_swarm_optimization
                    r1 = rd.random()
                    r2 = rd.random()

                    personal_impact_velocity = self.personal_impact_coefficient * r1 * (particle.personal_best_position[d] - particle.position[d])
                    environmental_impact_velocity = self.environmental_impact_coefficient * r2 * (global_best_position[d] - particle.position[d])

                    particle.velocity[d] = (self.stubbornness_coefficient * particle.velocity[d]) + personal_impact_velocity + environmental_impact_velocity
                    particle.velocity[d] = np.clip(particle.velocity[d], -self.max_velocity, self.max_velocity)

                    particle.position[d] += particle.velocity[d]

                current_schedule = smallest_position_value_sort(particle.position, batteries)
                current_makespan = self.evaluate_makespan(current_schedule)

                if current_makespan < particle.personal_best_makespan:
                    particle.personal_best_makespan = current_makespan
                    particle.personal_best_position = list(particle.position)

                if current_makespan < global_best_makespan:
                    global_best_makespan = current_makespan
                    global_best_position = list(particle.position)
                    global_best_schedule = current_schedule
                    best_permutation_global_iteration = iteration


            if self.apply_vns:
                for _ in range(self.vns_max_iterations):
                    current_schedule = self.generate_swapped_neighbourhood(global_best_schedule)
                    current_makespan = self.evaluate_makespan(current_schedule)
                    if global_best_makespan > current_makespan:
                        global_best_schedule = current_schedule
                        global_best_makespan = current_makespan
                        global_best_position = align_continuous_position(global_best_schedule, global_best_position, batteries)

            if self.apply_sa:
                current_temperature = self.initial_temperature
                sa_current_schedule = list(global_best_schedule)
                sa_current_makespan = global_best_makespan

                while current_temperature >= self.final_temperature:
                    neighbor_schedule = self.generate_swapped_neighbourhood(sa_current_schedule)
                    neighbor_makespan = self.evaluate_makespan(neighbor_schedule)

                    makespan_diff = neighbor_makespan - sa_current_makespan

                    if makespan_diff < 0 or math.exp(-makespan_diff / current_temperature) > rd.random():
                        sa_current_schedule = neighbor_schedule
                        sa_current_makespan = neighbor_makespan

                        if sa_current_makespan < global_best_makespan:
                            global_best_makespan = sa_current_makespan
                            global_best_schedule = list(sa_current_schedule)
                            global_best_position = align_continuous_position(global_best_schedule, global_best_position, batteries)

                    current_temperature *= self.cooling_rate

            makespans_history.append(IterationLog(makespan=global_best_makespan, iteration=iteration, time_elapsed=time.time() - start_time))

            if iteration - best_permutation_global_iteration > self.max_iters_without_improvement:
                break

        end_time = time.time_ns()

        return ScheduleResult(
            makespan=makespans_history[-1].makespan,
            batteries=global_best_schedule,
            execution_time=end_time - start_time,
            history=makespans_history,
        )

    def generate_swapped_neighbourhood(self, current_schedule: list[Battery]) -> list[Battery]:
        neighbor_sequence = list(current_schedule)
        idx1, idx2 = rd.sample(range(len(neighbor_sequence)), 2)
        neighbor_sequence[idx1], neighbor_sequence[idx2] = neighbor_sequence[idx2], neighbor_sequence[idx1]

        return neighbor_sequence

    def evaluate_makespan(self, sequence: list[Battery]) -> float:
        self.terminal.load_batteries(sequence)
        return self.terminal.process()

    def generate_bias(self, batteries: list[Battery]) -> list[float]:
        etas = [get_eta(battery) for battery in batteries]
        etas_normalized = (np.array(etas) - min(etas)) / (max(etas) - min(etas)) * 3

        return etas_normalized.tolist()