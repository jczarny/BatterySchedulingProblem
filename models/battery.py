import uuid

class Battery:
    def __init__(
            self,
            energy_missing: float,
            initial_power_consumption: float):
        self.id = str(uuid.uuid4())
        self.energy_missing = energy_missing
        self.initial_power_consumption = initial_power_consumption
        self.processing_time = (2.0 * self.energy_missing) / self.initial_power_consumption # Equation (7)

        self.start_time = None
        self.completion_time = None