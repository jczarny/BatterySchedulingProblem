from models.battery import Battery

class Terminal:
    def __init__(
            self,
            max_power_capacity: float):
        self.max_power_capacity = max_power_capacity
        self.batteries_to_load = []

    def load_batteries(self, batteries: list[Battery]):
        self.batteries_to_load = batteries[:]
        for battery in batteries:
            battery.start_time = 0.0
            battery.completion_time = 0.0

    def process(self) -> float:
        if len(self.batteries_to_load) == 0:
            return 0.0

        max_power_consumption = max(battery.initial_power_consumption for battery in self.batteries_to_load)
        if max_power_consumption > self.max_power_capacity:
            raise ValueError("Error: Initial power consumption of each battery must be lower or equal of max power of terminal.")

        batteries_loaded = []
        batteries_loading = []
        current_power_used = 0.0

        jobs_at_zero = []
        for battery in self.batteries_to_load:
            if current_power_used + battery.initial_power_consumption < self.max_power_capacity:
                battery.start_time = 0.0
                battery.completion_time = battery.processing_time
                batteries_loading.append(battery)
                jobs_at_zero.append(battery)
                current_power_used += battery.initial_power_consumption
            else:
                break

        for battery in batteries_loading:
            self.batteries_to_load.remove(battery)

        while self.batteries_to_load or batteries_loading:
            if self.batteries_to_load and not batteries_loading:
                next_battery = self.batteries_to_load.pop(0)
                next_start = batteries_loaded[-1].completion_time if batteries_loaded else 0.0
                next_battery.start_time = next_start
                next_battery.completion_time = next_start + next_battery.processing_time
                batteries_loaded.append(next_battery)
                continue

            next_loaded_battery = min(batteries_loading, key=lambda b: b.completion_time)
            next_loaded_battery_time = next_loaded_battery.completion_time

            if self.batteries_to_load:
                next_battery = self.batteries_to_load[0]
                next_battery_required_power = next_battery.initial_power_consumption

                # Equation (17)
                t_k_numerator = next_battery_required_power - self.max_power_capacity
                t_k_denominator = 0

                for battery in batteries_loading:
                    p0i = battery.initial_power_consumption
                    di = battery.processing_time
                    si = battery.start_time

                    t_k_numerator += p0i + ((p0i / di) * si)
                    t_k_denominator += (p0i / di)

                t_k = t_k_numerator / t_k_denominator
            else:
                t_k = float('inf')

            if t_k > next_loaded_battery_time:
                batteries_loading.remove(next_loaded_battery)
                batteries_loaded.append(next_loaded_battery)
            else:
                next_battery_to_load = self.batteries_to_load.pop(0)
                next_battery_to_load.start_time = t_k
                next_battery_to_load.completion_time = next_battery_to_load.start_time + next_battery_to_load.processing_time
                batteries_loading.append(next_battery_to_load)

        timespan = max(battery.completion_time for battery in batteries_loaded)
        return timespan