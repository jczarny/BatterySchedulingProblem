from models.battery import Battery

def smallest_position_value_sort(position: list[float], batteries: list[Battery]) -> list[Battery]:
    position_battery_pairs = list(zip(position, batteries))
    position_battery_pairs.sort(key=lambda pair: pair[0])
    return [battery for _, battery in position_battery_pairs]


def align_continuous_position(target_sequence: list[Battery], reference_position: list[float], base_batteries: list[Battery]) -> list[float]:
    sorted_continuous_values = sorted(reference_position)
    aligned_position = [0.0] * len(reference_position)

    for rank, battery in enumerate(target_sequence):
        dimension_index = base_batteries.index(battery)
        aligned_position[dimension_index] = sorted_continuous_values[rank]

    return aligned_position