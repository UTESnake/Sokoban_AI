import copy
import time

from algorithm.common import apply_step, beam_best_first, greedy_best_first, isDeadlock, state_key, validMove


def no_observation_search(game):
    return greedy_best_first(game)


def partial_observation_search(game):
    return greedy_best_first(game)


def backtracking_search(game):
    start = time.time()
    node_generated = 0
    start_state = copy.deepcopy(game)
    visited = set()

    if isDeadlock(start_state):
        print("No Solution!")
        return "NoSol"

    print("Processing BACKTRACKING......")

    def solve(state):
        nonlocal node_generated

        if state.isComplete():
            return state.pathSolution

        visited.add(state_key(state))

        for step in validMove(state):
            new_state = copy.deepcopy(state)
            node_generated += 1
            apply_step(new_state, step)

            if state_key(new_state) in visited or isDeadlock(new_state):
                continue

            solution_path = solve(new_state)
            if solution_path:
                return solution_path

        return None

    solution = solve(start_state)
    end = time.time()

    if solution:
        print("Time to find solution:", round(end - start, 2), "seconds")
        print("Number of visited nodes:", node_generated)
        print("Solution:", solution, "Number steps:", len(solution))
        return solution

    print("No Solution!")
    return "NoSol"


def path_finding(game):
    return beam_best_first(game, beam_width=8)


def global_search(game):
    return greedy_best_first(game)


def min_conflict(game):
    return beam_best_first(game, beam_width=10)
