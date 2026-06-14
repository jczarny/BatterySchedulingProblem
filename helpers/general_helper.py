from models.battery import Battery
from models.terminal import Terminal

import random as rd


def generate_neh_ss2_initial_solution(terminal: Terminal, batteries: list[Battery], size_lps1: int = 5) -> list[Battery]:
    n = len(batteries)
    if n <= 1:
        return list(batteries)

    initial_order = generate_greedy_initial_solution(batteries)
    lps1 = [[initial_order[0]]]

    for i in range(1, n):
        job_to_insert = initial_order[i]

        lps2 = []
        best_makespan = float('inf')

        for partial_seq in lps1:
            for pos in range(len(partial_seq) + 1):
                candidate_sequence = list(partial_seq)
                candidate_sequence.insert(pos, job_to_insert)

                terminal.load_batteries(candidate_sequence)
                candidate_makespan = terminal.process()

                if candidate_makespan < best_makespan:
                    best_makespan = candidate_makespan
                    lps2 = [candidate_sequence]

                elif candidate_makespan == best_makespan:
                    lps2.append(candidate_sequence)


        if len(lps2) <= size_lps1:
            lps1 = lps2
        else:
            lps1 = rd.sample(lps2, size_lps1)

    return lps1[0]

def generate_greedy_initial_solution(batteries: list[Battery]) -> list[Battery]:
    return sorted(batteries, key=lambda x: get_eta(x), reverse=True)

def get_eta(battery: Battery) -> float:
    return battery.processing_time / battery.initial_power_consumption