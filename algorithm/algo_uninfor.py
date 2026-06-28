import copy
import time
from collections import deque

from algorithm.common import apply_step, isDeadlock, state_key, validMove


def _print_solution(label, start_time, node_generated, solution):
    end_time = time.time()
    print("Time to find solution:", round(end_time - start_time, 2), "seconds")
    print("Number of visited nodes:", node_generated)
    print("Solution:", solution, "Number steps:", len(solution))


def bfs_search(game):
    """Breadth-First Search đúng FIFO queue theo giả mã."""
    start_time = time.time()
    node_generated = 1
    start_state = copy.deepcopy(game)

    print("Processing BFS......")
    if start_state.isComplete():
        _print_solution("BFS", start_time, node_generated, start_state.pathSolution)
        return start_state.pathSolution
    if isDeadlock(start_state):
        print("No Solution!")
        return "NoSol"

    frontier = deque([start_state])
    reached = {state_key(start_state)}

    while frontier:
        node = frontier.popleft()
        for step in validMove(node):
            child = copy.deepcopy(node)
            apply_step(child, step)
            node_generated += 1
            child_key = state_key(child)

            if child.isComplete():
                _print_solution("BFS", start_time, node_generated, child.pathSolution)
                return child.pathSolution

            if child_key not in reached and not isDeadlock(child):
                reached.add(child_key)
                frontier.append(child)

    print("Number of visited nodes:", node_generated)
    print("No Solution!")
    return "NoSol"


def dfs_search(game):
    """Depth-First Search đúng LIFO stack theo giả mã."""
    start_time = time.time()
    node_generated = 1
    start_state = copy.deepcopy(game)

    print("Processing DFS......")
    if start_state.isComplete():
        _print_solution("DFS", start_time, node_generated, start_state.pathSolution)
        return start_state.pathSolution
    if isDeadlock(start_state):
        print("No Solution!")
        return "NoSol"

    frontier = [start_state]
    reached = {state_key(start_state)}

    while frontier:
        node = frontier.pop()
        for step in validMove(node):
            child = copy.deepcopy(node)
            apply_step(child, step)
            node_generated += 1
            child_key = state_key(child)

            if child.isComplete():
                _print_solution("DFS", start_time, node_generated, child.pathSolution)
                return child.pathSolution

            if child_key not in reached and not isDeadlock(child):
                reached.add(child_key)
                frontier.append(child)

    print("Number of visited nodes:", node_generated)
    print("No Solution!")
    return "NoSol"


def ids_search(game, max_depth=200):
    """Iterative Deepening Search: lặp depth và gọi DLS.

    DLS dùng IS-CYCLE theo đường đi hiện tại, không dùng visited toàn cục.
    """
    start_time = time.time()
    total_generated = 0
    print("Processing IDS......")

    for depth_limit in range(max_depth + 1):
        result, generated = _depth_limited_search(game, depth_limit)
        total_generated += generated
        if result is not None:
            _print_solution("IDS", start_time, total_generated, result)
            print("Depth limit:", depth_limit)
            return result

    print("IDS exceeded max depth:", max_depth)
    print("Number of visited nodes:", total_generated)
    print("No Solution!")
    return "NoSol"


def _depth_limited_search(game, limit):
    start_state = copy.deepcopy(game)
    node_generated = 1

    def recursive_dls(state, depth, path_keys):
        nonlocal node_generated
        if state.isComplete():
            return state.pathSolution
        if depth >= limit:
            return None

        for step in validMove(state):
            child = copy.deepcopy(state)
            apply_step(child, step)
            node_generated += 1
            child_key = state_key(child)
            if child_key in path_keys or isDeadlock(child):
                continue
            path_keys.add(child_key)
            result = recursive_dls(child, depth + 1, path_keys)
            path_keys.remove(child_key)
            if result is not None:
                return result
        return None

    return recursive_dls(start_state, 0, {state_key(start_state)}), node_generated
