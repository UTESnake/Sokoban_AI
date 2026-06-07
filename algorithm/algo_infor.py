import copy
import queue
import time

from algorithm.common import (
    apply_step,
    box_toDock,
    greedy_best_first,
    isDeadlock,
    state_key,
    validMove,
    worker_toBox,
)


def astar_search(game):
    start = time.time()
    node_generated = 0
    start_state = copy.deepcopy(game)
    node_generated += 1
    start_state.heuristic = worker_toBox(start_state) + box_toDock(start_state)

    if isDeadlock(start_state):
        print("No Solution!")
        return "NoSol"

    open_list = queue.PriorityQueue()
    open_list.put(start_state)
    close_list = set()

    print("Processing A*......")

    while not open_list.empty():
        cur_state = open_list.get()
        close_list.add(state_key(cur_state))

        for step in validMove(cur_state):
            new_state = copy.deepcopy(cur_state)
            node_generated += 1
            apply_step(new_state, step)
            new_state.heuristic = worker_toBox(new_state) + box_toDock(new_state)

            if new_state.isComplete():
                end = time.time()
                print("Time to find solution:", round(end - start, 2), "seconds")
                print("Number of visited nodes:", node_generated)
                print("Solution:", new_state.pathSolution, "Number steps:", len(new_state.pathSolution))
                return new_state.pathSolution

            if state_key(new_state) not in close_list and not isDeadlock(new_state):
                open_list.put(new_state)

    print(node_generated)
    print("No Solution!")
    return "NoSol"


def ida_star_search(game):
    # IDA* fallback: the project currently uses A* as the reliable informed solver.
    return astar_search(game)


def greedy_search(game):
    return greedy_best_first(game)
