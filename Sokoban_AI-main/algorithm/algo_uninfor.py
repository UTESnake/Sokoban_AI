import copy
import time
from collections import deque

from algorithm.common import apply_step, depth_limited_search, isDeadlock, state_key, validMove


def bfs_search(game):
    start = time.time()
    node_generated = 0
    start_state = copy.deepcopy(game)
    node_generated += 1

    if isDeadlock(start_state):
        print("No Solution!")
        return "NoSol"

    search_queue = deque([start_state])
    visited = {state_key(start_state)}

    print("Processing BFS......")

    while search_queue:
        curr_state = search_queue.popleft()
        for step in validMove(curr_state):
            new_state = copy.deepcopy(curr_state)
            node_generated += 1
            apply_step(new_state, step)

            if new_state.isComplete():
                end = time.time()
                print("Time to find solution:", round(end - start, 2), "seconds")
                print("Number of visited nodes:", node_generated)
                print("Solution:", new_state.pathSolution, "Number steps:", len(new_state.pathSolution))
                return new_state.pathSolution

            key = state_key(new_state)
            if key not in visited and not isDeadlock(new_state):
                search_queue.append(new_state)
                visited.add(key)

    print(node_generated)
    print("No Solution!")
    return "NoSol"


def dfs_search(game):
    start = time.time()
    node_generated = 0
    start_state = copy.deepcopy(game)
    node_generated += 1

    if isDeadlock(start_state):
        print("No Solution!")
        return "NoSol"

    stack = [start_state]
    visited = {state_key(start_state)}

    print("Processing DFS......")

    while stack:
        curr_state = stack.pop()
        for step in validMove(curr_state):
            new_state = copy.deepcopy(curr_state)
            node_generated += 1
            apply_step(new_state, step)

            if new_state.isComplete():
                end = time.time()
                print("Time to find solution:", round(end - start, 2), "seconds")
                print("Number of visited nodes:", node_generated)
                print("Solution:", new_state.pathSolution, "Number steps:", len(new_state.pathSolution))
                return new_state.pathSolution

            key = state_key(new_state)
            if key not in visited and not isDeadlock(new_state):
                stack.append(new_state)
                visited.add(key)

    print(node_generated)
    print("No Solution!")
    return "NoSol"


def ids_search(game, max_depth=80):
    for limit in range(max_depth + 1):
        result = depth_limited_search(game, limit)
        if result:
            return result
    return "NoSol"
