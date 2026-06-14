import random
from models.battery import Battery

class InstanceGenerator:
    def __init__(self, seed: int = -1):
        self.seed = seed
        if seed != -1:
            self.rng = random.Random(self.seed)
        else:
            self.rng = random.Random()

        self.size = 0
        self.energy_missing_min = 0.0
        self.energy_missing_max = 0.0
        self.initial_power_consumption_min = 0.0
        self.initial_power_consumption_max = 0.0

    def set_size(self, size: int):
        self.size = size

    def set_energy_missing_range(self, e_min: float, e_max: float):
        self.energy_missing_min = e_min
        self.energy_missing_max = e_max

    def set_initial_power_consumption_range(self, p_min: float, p_max: float):
        self.initial_power_consumption_min = p_min
        self.initial_power_consumption_max = p_max

    def generate(self, terminal_max_power: float) -> list[Battery]:
        if self.initial_power_consumption_max > terminal_max_power:
            raise ValueError("Error: Initial power consumption of each battery must be lower or equal of max power of terminal.")

        batteries = []
        for _ in range(self.size):
            e_missing = self.rng.uniform(self.energy_missing_min, self.energy_missing_max)
            p_initial = self.rng.uniform(self.initial_power_consumption_min, self.initial_power_consumption_max)
            batteries.append(Battery(e_missing, p_initial))

        return batteries