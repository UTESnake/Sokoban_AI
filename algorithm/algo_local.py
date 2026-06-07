import copy
import math
import random
import time

from algorithm.common import (
    apply_step,
    beam_best_first,
    box_toDock,
    greedy_best_first,
    validMove,
    worker_toBox,
)


def simple_hill_climbing(game):
    return greedy_best_first(game)


def beam_search(game):
    return beam_best_first(game)


def simulated_annealing_search(game, initial_temperature=1000, cooling_rate=0.95, max_iterations=1000):
    start = time.time()
    node_generated = 0

    current_state = copy.deepcopy(game)
    node_generated += 1

    temperature = initial_temperature
    best_path = ""
    best_heuristic = worker_toBox(current_state) + box_toDock(current_state)

    print("Processing SIMULATED ANNEALING......")

    for _ in range(max_iterations):
        if current_state.isComplete():
            end = time.time()
            print("Time to find solution:", round(end - start, 2), "seconds")
            print("Number of visited nodes:", node_generated)
            print("Solution:", best_path, "Number steps:", len(best_path))
            return best_path

        moves = validMove(current_state)
        if not moves:
            break

        step = random.choice(moves)
        next_state = copy.deepcopy(current_state)
        node_generated += 1
        apply_step(next_state, step)

        next_heuristic = worker_toBox(next_state) + box_toDock(next_state)
        delta = next_heuristic - best_heuristic
        if delta < 0 or random.uniform(0, 1) < math.exp(-delta / temperature):
            current_state = next_state
            best_path += step
            best_heuristic = next_heuristic

        temperature *= cooling_rate

    print("No Solution Found!")
    return "NoSol"
