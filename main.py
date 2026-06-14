from instance_generator import InstanceGenerator
from schedulers.longest_time_processing_scheduler import LongestTimeProcessingScheduler
from schedulers.smallest_initial_power_scheduler import SmallestInitialPowerScheduler
from schedulers.ant_colony_scheduler import AntColonyScheduler
from schedulers.tabu_search_scheduler import TabuSearchScheduler
from schedulers.particle_swarm_scheduler import ParticleSwarmScheduler
from schedulers.genetic_algorithm_base_sheduler import GeneticAlgorithmScheduler
from schedulers.two_phase_ga_scheduler import TwoPhaseGAScheduler
from schedulers.brkga_r_ls_scheduler import BRKGA_R_LS_Scheduler
from schedulers.base_scheduler import ScheduleResult
from models.terminal import Terminal

if __name__ == '__main__':
    terminal = Terminal(max_power_capacity=100.0)

    generator = InstanceGenerator(1)
    generator.set_size(50)
    generator.set_energy_missing_range(50.0, 150.0)
    generator.set_initial_power_consumption_range(20.0, 60.0)

    tasks = generator.generate(terminal_max_power=100.0)

    terminal.load_batteries(tasks)
    makespan = terminal.process()
    print(f"\nDEFAULT: CAŁKOWITY CZAS ŁADOWANIA (Makespan): {makespan:.2f} godzin.")

    scheduler = SmallestInitialPowerScheduler()
    result: ScheduleResult = scheduler.fit(terminal, tasks)
    print(f"\nSIP: CAŁKOWITY CZAS ŁADOWANIA (Makespan): {result.makespan:.2f} godzin.")

    scheduler = LongestTimeProcessingScheduler()
    result: ScheduleResult = scheduler.fit(terminal, tasks)
    print(f"\nLTP: CAŁKOWITY CZAS ŁADOWANIA (Makespan): {result.makespan:.2f} godzin.")

    scheduler = AntColonyScheduler(num_ants=50, iterations=100, beta=0.5)
    result: ScheduleResult = scheduler.fit(terminal, tasks)
    print(f"\nACO: CAŁKOWITY CZAS ŁADOWANIA (Makespan): {result.makespan:.2f} godzin.")

    scheduler = TabuSearchScheduler(iterations=1000, neighbourhood_size=40, apply_neh_ss2=True)
    result: ScheduleResult = scheduler.fit(terminal, tasks)
    print(f"\nTABU: CAŁKOWITY CZAS ŁADOWANIA (Makespan): {result.makespan:.2f} godzin.")

    scheduler = ParticleSwarmScheduler(iterations=50)
    result: ScheduleResult = scheduler.fit(terminal, tasks)
    print(f"\nPSO: CAŁKOWITY CZAS ŁADOWANIA (Makespan): {result.makespan:.2f} godzin.")

    scheduler = GeneticAlgorithmScheduler()
    result: ScheduleResult = scheduler.fit(terminal, tasks)
    print(f"\nGA: CAŁKOWITY CZAS ŁADOWANIA (Makespan): {result.makespan:.2f} godzin.")

    scheduler = TwoPhaseGAScheduler()
    result: ScheduleResult = scheduler.fit(terminal, tasks)
    print(f"\n2PGA: CAŁKOWITY CZAS ŁADOWANIA (Makespan): {result.makespan:.2f} godzin.")

    scheduler = BRKGA_R_LS_Scheduler()
    result: ScheduleResult = scheduler.fit(terminal, tasks)
    print(f"\nBRKGA-R-LS: CAŁKOWITY CZAS ŁADOWANIA (Makespan): {result.makespan:.2f} godzin.")
