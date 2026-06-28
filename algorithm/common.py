import copy
import queue


MOVE_DELTAS = {
    "U": (-1, 0),
    "D": (1, 0),
    "L": (0, -1),
    "R": (0, 1),
}


def validMove(state):
    valid_moves = []
    for step, (y, x) in MOVE_DELTAS.items():
        if state.workerCanMove(y, x) or state.workerCanPushBox(y, x):
            valid_moves.append(step)
    return valid_moves


def box_toDock(state):
    total = 0
    box_list = state.boxPosition()
    dock_list = state.dockPosition()
    for box in box_list:
        min_distance = float("inf")
        for dock in dock_list:
            distance = abs(dock[0] - box[0]) + abs(dock[1] - box[1])
            if distance < min_distance:
                min_distance = distance
        total += min_distance
    return total


def worker_toBox(state):
    total = 0
    box_list = state.boxPosition()
    worker_pos = state.workerPosition()
    for box in box_list:
        total += abs(box[0] - worker_pos[0]) + abs(box[1] - worker_pos[1])
    return total


def isDeadlock(state):
    boxListPosition = state.boxPosition()

    deadlock_conditions = [
        lambda box_y, box_x: (
            state.getMatrixElement(box_y, box_x - 1) in ["#", "$", "*"]
            and state.getMatrixElement(box_y - 1, box_x) in ["#", "$", "*"]
            and state.getMatrixElement(box_y - 1, box_x - 1) in ["#", "$", "*"]
        ),
        lambda box_y, box_x: (
            state.getMatrixElement(box_y, box_x + 1) in ["#", "$", "*"]
            and state.getMatrixElement(box_y - 1, box_x) in ["#", "$", "*"]
            and state.getMatrixElement(box_y - 1, box_x + 1) in ["#", "$", "*"]
        ),
        lambda box_y, box_x: (
            state.getMatrixElement(box_y, box_x - 1) in ["#", "$", "*"]
            and state.getMatrixElement(box_y + 1, box_x) in ["#", "$", "*"]
            and state.getMatrixElement(box_y + 1, box_x - 1) in ["#", "$", "*"]
        ),
        lambda box_y, box_x: (
            state.getMatrixElement(box_y, box_x + 1) in ["#", "$", "*"]
            and state.getMatrixElement(box_y + 1, box_x) in ["#", "$", "*"]
            and state.getMatrixElement(box_y + 1, box_x + 1) in ["#", "$", "*"]
        ),
    ]

    for box in boxListPosition:
        y, x = box
        if any(condition(y, x) for condition in deadlock_conditions):
            return True

    return False


def apply_step(state, step):
    y, x = MOVE_DELTAS[step]
    state.move(y, x)
    state.pathSolution += step


def state_key(state):
    return tuple(map(tuple, state.getMatrix()))


def heuristic(state):
    return worker_toBox(state) + box_toDock(state)


def depth_limited_search(game, limit):
    start_state = copy.deepcopy(game)
    visited = set()

    def solve(state, depth):
        if state.isComplete():
            return state.pathSolution
        if depth == limit:
            return None

        visited.add(state_key(state))
        for step in validMove(state):
            new_state = copy.deepcopy(state)
            apply_step(new_state, step)
            key = state_key(new_state)
            if key in visited or isDeadlock(new_state):
                continue
            result = solve(new_state, depth + 1)
            if result:
                return result
        return None

    return solve(start_state, 0)


def greedy_best_first(game):
    start_state = copy.deepcopy(game)
    if isDeadlock(start_state):
        return "NoSol"

    open_list = queue.PriorityQueue()
    counter = 0
    open_list.put((heuristic(start_state), counter, start_state))
    visited = set()

    while not open_list.empty():
        _, _, current = open_list.get()
        if current.isComplete():
            return current.pathSolution

        visited.add(state_key(current))
        for step in validMove(current):
            new_state = copy.deepcopy(current)
            apply_step(new_state, step)
            key = state_key(new_state)
            if key in visited or isDeadlock(new_state):
                continue
            counter += 1
            open_list.put((heuristic(new_state), counter, new_state))

    return "NoSol"


def beam_best_first(game, beam_width=3, max_depth=300):
    frontier = [copy.deepcopy(game)]
    visited = {state_key(frontier[0])}

    for _ in range(max_depth):
        candidates = []
        for state in frontier:
            if state.isComplete():
                return state.pathSolution
            for step in validMove(state):
                new_state = copy.deepcopy(state)
                apply_step(new_state, step)
                key = state_key(new_state)
                if key in visited or isDeadlock(new_state):
                    continue
                visited.add(key)
                candidates.append(new_state)

        if not candidates:
            return "NoSol"
        candidates.sort(key=heuristic)
        frontier = candidates[:beam_width]

    return "NoSol"
