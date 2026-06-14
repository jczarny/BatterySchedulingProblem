import itertools
import time
import copy
import os
import csv
from instance_generator import InstanceGenerator
from models.battery import Battery
from models.terminal import Terminal
from schedulers.ant_colony_scheduler import AntColonyScheduler
from schedulers.base_scheduler import BaseBatteryScheduler
from schedulers.brkga_r_ls_scheduler import BRKGA_R_LS_Scheduler
from schedulers.genetic_algorithm_base_sheduler import GeneticAlgorithmScheduler
from schedulers.particle_swarm_scheduler import ParticleSwarmScheduler
from schedulers.tabu_search_scheduler import TabuSearchScheduler
from schedulers.two_phase_ga_scheduler import TwoPhaseGAScheduler

HEURISTIC_PARAM_GRIDS = {
    "ACO": {
        "num_ants": [50, 100, 150],
        "alpha": [1.0, 2.0, 5.0],
        "beta": [1.0, 2.0, 5.0],
        "decay": [0.05, 0.1, 0.25],
        "p_best": [0.1, 0.2],
    },
    "HPSO": {
        "num_particles": [50, 100, 150],
        "stubbornness_coefficient": [0.5, 1, 2.0],
        "personal_impact_coefficient": [0.5, 1, 2.0],
        "environmental_impact_coefficient": [0.5, 1, 2.0],
        "cooling_rate": [0.9, 0.95, 0.98],
    },
    "TS": {
        "neighbourhood_size": [50, 100, 150],
        "dynamic_tenure": [True, False],
        "base_tabu_tenure": [10, 15, 25],
        "no_improve_diversify": [25, 50, 100],
        "diversification_factor": [0.1, 0.15, 0.25],
    },
    "GA": {
        "population_size": [50, 100, 150],
        "crossover_rate": [0.75, 0.85, 0.95],
        "mutation_rate": [0.05, 0.1, 0.15],
        "survival_rate": [0.05, 0.1, 0.15],
        "tournament_size": [2, 3, 5],
        "mutation_iters": [1, 3],
    },
    "2PGA": {
        "phase1_duration": [5, 15, 25],
        "phase2_duration": [5, 15, 25],
        "pop_f_ratio": [0.05, 0.1, 0.2],
    },
    "BRKGA-R-LS": {
        "elite_percentage": [10, 15, 20],
        "mutant_percentage": [10, 15, 20],
        "elite_inheritance_prob": [0.65, 0.75, 0.85],
        "restarts_patience": [50, 100],
        "ls_range": [3, 7],
        "ls_periodic_run_period": [50, 100],
    }
}

class RunRecord:
    def __init__(self, scheduler_name, config, config_id, instance_id, size, makespan, execution_time_s):
        self.scheduler_name = scheduler_name
        self.config = config
        self.config_id = config_id
        self.instance_id = instance_id
        self.size = size
        self.makespan = makespan
        self.execution_time_s = execution_time_s
        self.best_known_makespan = None
        self.rpd = None


class SummaryRecord:
    def __init__(self, scheduler_name, config, config_id, average_rpd, average_makespan, average_execution_time_s):
        self.scheduler_name = scheduler_name
        self.config = config
        self.config_id = config_id
        self.average_rpd = average_rpd
        self.average_makespan = average_makespan
        self.average_execution_time_s = average_execution_time_s


class GridSearchResult:
    def __init__(self, runs, summaries):
        self.runs = runs
        self.summaries = summaries

    def best(self, top_n=5):
        return sorted(self.summaries, key=lambda row: row.average_rpd)[:top_n]

    def save_to_csv(self, filename):
        os.makedirs("optimizer_results", exist_ok=True)

        runs_path = os.path.join("optimizer_results", f"{filename}_runs.csv")
        with open(runs_path, mode='w', newline='', encoding='utf-8') as f:
            if self.runs:
                writer = csv.DictWriter(f, fieldnames=vars(self.runs[0]).keys())
                writer.writeheader()
                for run in self.runs:
                    writer.writerow(vars(run))

        summaries_path = os.path.join("optimizer_results", f"{filename}_summaries.csv")
        with open(summaries_path, mode='w', newline='', encoding='utf-8') as f:
            self.summaries = sorted(self.summaries, key=lambda row: row.average_rpd)
            if self.summaries:
                writer = csv.DictWriter(f, fieldnames=vars(self.summaries[0]).keys())
                writer.writeheader()
                for summary in self.summaries:
                    writer.writerow(vars(summary))


def expand_param_grid(param_grid):
    keys = list(param_grid.keys())
    values = [list(param_grid[key]) for key in keys]
    return [dict(zip(keys, combination)) for combination in itertools.product(*values)]


class GridSearchOptimizer:
    def __init__(
            self,
            terminal_max_power,
            energy_missing_range,
            initial_power_consumption_range,
            instance_sizes=(20, 50, 100),
            instances_per_size=3,
    ):
        self.terminal_max_power = terminal_max_power
        self.energy_missing_range = energy_missing_range
        self.initial_power_consumption_range = initial_power_consumption_range
        self.instance_sizes = tuple(instance_sizes)
        self.instances_per_size = instances_per_size
        self.seed = 123

    def tune(self, scheduler_name):
        instances_to_use = self.generate_instances()
        params_grid = HEURISTIC_PARAM_GRIDS[scheduler_name]
        configs = expand_param_grid(params_grid)
        scheduler_class = get_scheduler_class_by_name(scheduler_name)

        runs = []
        total_cases = len(configs) * len(instances_to_use)

        for config_id, config in enumerate(configs, start=1):
            for id, instance in enumerate(instances_to_use, start=1):
                print(
                    f"[{len(runs) + 1}/{total_cases}] {scheduler_name} | config={config_id} | instance={id} | instance_size={len(instance)} | config={config}")

                terminal = Terminal(max_power_capacity=self.terminal_max_power)
                scheduler = scheduler_class(**config)

                start_time = time.time()
                instance_copy = copy.deepcopy(instance)
                result = scheduler.fit(terminal, instance_copy)
                time_elapsed = time.time() - start_time

                runs.append(
                    RunRecord(
                        scheduler_name=scheduler_name,
                        config=config,
                        config_id=config_id,
                        instance_id=id,
                        size=len(instance),
                        makespan=float(result.makespan),
                        execution_time_s=time_elapsed
                    )
                )

        best_by_instance = {}
        for run in runs:
            current_best = best_by_instance.get(run.instance_id, float('inf'))
            best_by_instance[run.instance_id] = min(current_best, run.makespan)

        for run in runs:
            run.best_known_makespan = best_by_instance[run.instance_id]
            if run.best_known_makespan > 0:
                run.rpd = ((run.makespan - run.best_known_makespan) / run.best_known_makespan) * 100.0
            else:
                run.rpd = 0.0

        summaries = []
        for config_id, config in enumerate(configs, start=1):
            config_runs = [run for run in runs if run.config_id == config_id]

            avg_rpd = sum(r.rpd for r in config_runs) / len(config_runs)
            avg_makespan = sum(r.makespan for r in config_runs) / len(config_runs)
            avg_time = sum(r.execution_time_s for r in config_runs) / len(config_runs)

            summaries.append(
                SummaryRecord(
                    scheduler_name=scheduler_name,
                    config=config,
                    config_id=config_id,
                    average_rpd=avg_rpd,
                    average_makespan=avg_makespan,
                    average_execution_time_s=avg_time
                )
            )

        return GridSearchResult(runs=runs, summaries=summaries)

    def generate_instances(self):
        instances = []
        instance_id = 0
        for size in self.instance_sizes:
            for i in range(self.instances_per_size):
                seed = self.seed + (size * 100) + i
                generator = InstanceGenerator(seed=seed)
                generator.set_size(size)
                generator.set_energy_missing_range(*self.energy_missing_range)
                generator.set_initial_power_consumption_range(*self.initial_power_consumption_range)

                batteries = generator.generate(self.terminal_max_power)

                instances.append(batteries)
                instance_id += 1
        return instances


def print_top(result, top_n=5):
    for i, row in enumerate(result.best(top_n), start=1):
        print(
            f"#{i} | {row.scheduler_name} | Avg RPD: {row.average_rpd:.4f}% | Avg Time: {row.average_execution_time_s:.2f}s | Config: {row.config}")

def get_scheduler_class_by_name(scheduler_class):
    match scheduler_class:
        case "HPSO":
            return ParticleSwarmScheduler
        case "ACO":
            return AntColonyScheduler
        case "GA":
            return GeneticAlgorithmScheduler
        case "2PGA":
            return TwoPhaseGAScheduler
        case "BRKGA-R-LS":
            return BRKGA_R_LS_Scheduler
        case "TS":
            return TabuSearchScheduler
        case _:
            return BaseBatteryScheduler

def clear_batteries(batteries: list[Battery]):
    for battery in batteries:
        battery.start_time = 0
        battery.completion_time = 0

    return batteries



if __name__ == '__main__':
    for algorithm_name in ['HPSO', 'ACO', '2PGA', 'BRKGA-R-LS']:
        optimizer = GridSearchOptimizer(
            terminal_max_power=100.0,
            energy_missing_range=(100.0, 1000.0),
            initial_power_consumption_range=(20.0, 70.0),
        )

        start = time.time()
        alg_name = algorithm_name
        result = optimizer.tune(scheduler_name=algorithm_name)
        print_top(result, top_n=5)
        result.save_to_csv(f"grid_search_{algorithm_name}")