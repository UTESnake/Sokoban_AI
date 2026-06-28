import copy
import heapq
import time

from algorithm.common import (
    apply_step,
    heuristic,
    isDeadlock,
    state_key,
    validMove,
)


def _print_solution(label, start_time, node_generated, solution):
    end = time.time()
    print("Algorithm:", label)
    print("Time to find solution:", round(end - start_time, 2), "seconds")
    print("Number of visited nodes:", node_generated)
    print("Solution:", solution, "Number steps:", len(solution))


def astar_search(game):
    """A* Search.

    Công thức:
        f(n) = g(n) + h(n)

    Trong đó:
        g(n) = số bước đi từ trạng thái đầu đến trạng thái hiện tại
        h(n) = heuristic(state)

    Theo common.py đã sửa:
        h(n) = box_toDock_matching(n) + worker_toBox(n)

    A* luôn chọn node có f(n) nhỏ nhất trong open_list.
    Nếu f bằng nhau thì xét g, sau đó xét counter để ổn định thứ tự.
    """
    start_time = time.time()
    node_generated = 1
    start_state = copy.deepcopy(game)

    print("Processing A*......")

    if start_state.isComplete():
        _print_solution("A*", start_time, node_generated, start_state.pathSolution)
        return start_state.pathSolution

    if isDeadlock(start_state):
        print("No Solution!")
        return "NoSol"

    open_list = []
    counter = 0

    start_key = state_key(start_state)
    start_g = 0
    start_h = heuristic(start_state)
    start_f = start_g + start_h
    start_state.heuristic = start_f

    best_g = {start_key: start_g}
    closed_list = set()

    heapq.heappush(
        open_list,
        (start_f, start_g, counter, start_state),
    )

    while open_list:
        f_cost, g_cost, _counter, node = heapq.heappop(open_list)
        node_key = state_key(node)

        # Nếu node này không còn là đường tốt nhất tới state đó thì bỏ qua.
        if g_cost != best_g.get(node_key):
            continue

        if node_key in closed_list:
            continue
        closed_list.add(node_key)

        if node.isComplete():
            _print_solution("A*", start_time, node_generated, node.pathSolution)
            return node.pathSolution

        for step in validMove(node):
            child = copy.deepcopy(node)

            if not apply_step(child, step):
                continue

            node_generated += 1

            if isDeadlock(child):
                continue

            child_key = state_key(child)
            new_g = g_cost + 1

            # Nếu đã có đường tới child tốt hơn hoặc bằng thì bỏ qua.
            if new_g >= best_g.get(child_key, float("inf")):
                continue

            if child_key in closed_list:
                continue

            child_h = heuristic(child)
            child_f = new_g + child_h
            child.heuristic = child_f

            best_g[child_key] = new_g
            counter += 1

            heapq.heappush(
                open_list,
                (child_f, new_g, counter, child),
            )

    print("Number of visited nodes:", node_generated)
    print("No Solution!")
    return "NoSol"


def greedy_search(game):
    """Greedy Best-First Search.

    Công thức:
        priority(n) = h(n)

    Greedy chỉ chọn node có h(n) nhỏ nhất.
    Nó không cộng g(n), nên không đảm bảo đường đi tối ưu như A*.
    """
    start_time = time.time()
    node_generated = 1
    start_state = copy.deepcopy(game)

    print("Processing GREEDY SEARCH......")

    if start_state.isComplete():
        _print_solution("Greedy", start_time, node_generated, start_state.pathSolution)
        return start_state.pathSolution

    if isDeadlock(start_state):
        print("No Solution!")
        return "NoSol"

    open_list = []
    counter = 0

    reached = set()
    frontier_keys = {state_key(start_state)}

    start_h = heuristic(start_state)

    heapq.heappush(
        open_list,
        (start_h, counter, start_state),
    )

    while open_list:
        h_cost, _counter, node = heapq.heappop(open_list)
        node_key = state_key(node)
        frontier_keys.discard(node_key)

        if node_key in reached:
            continue

        if node.isComplete():
            _print_solution("Greedy", start_time, node_generated, node.pathSolution)
            return node.pathSolution

        reached.add(node_key)

        for step in validMove(node):
            child = copy.deepcopy(node)

            if not apply_step(child, step):
                continue

            node_generated += 1

            if isDeadlock(child):
                continue

            child_key = state_key(child)

            if child_key in reached or child_key in frontier_keys:
                continue

            child_h = heuristic(child)

            counter += 1
            frontier_keys.add(child_key)

            heapq.heappush(
                open_list,
                (child_h, counter, child),
            )

    print("Number of visited nodes:", node_generated)
    print("No Solution!")
    return "NoSol"


def ida_star_search(game, max_bound_iterations=120, max_generated=3_000_000):
    """IDA*: Iterative Deepening A*.

    Lý thuyết:
        IDA* giống IDS nhưng cutoff không phải depth.
        Cutoff của IDA* là f(n).

    Công thức:
        f(n) = g(n) + h(n)

    Trong đó:
        g(n) = số bước đã đi
        h(n) = heuristic(state)

    Cách chạy:
        - bound đầu tiên = h(start)
        - DFS chỉ đi tiếp nếu f(n) <= bound
        - nếu f(n) > bound thì cắt nhánh
        - bound vòng sau = f nhỏ nhất đã vượt bound ở vòng trước

    Hàm này không dùng Greedy shortcut.
    """
    start_time = time.time()
    node_generated = 1
    start_state = copy.deepcopy(game)

    print("Processing IDA*......")

    if start_state.isComplete():
        _print_solution("IDA*", start_time, node_generated, start_state.pathSolution)
        return start_state.pathSolution

    if isDeadlock(start_state):
        print("No Solution!")
        return "NoSol"

    bound = heuristic(start_state)
    start_key = state_key(start_state)

    def search(state, g_cost, current_bound, path_keys, best_seen):
        """DFS có giới hạn theo f-cost.

        Trả về:
            ("FOUND", solution) nếu tìm thấy goal
            (next_bound, None) nếu chưa thấy goal

        next_bound là f nhỏ nhất vượt current_bound.
        """
        nonlocal node_generated

        h_cost = heuristic(state)
        f_cost = g_cost + h_cost

        if f_cost > current_bound:
            return f_cost, None

        if state.isComplete():
            return "FOUND", state.pathSolution

        if node_generated >= max_generated:
            return float("inf"), None

        key = state_key(state)

        # Trong cùng một vòng bound, nếu đã tới state này với g nhỏ hơn hoặc bằng,
        # thì không cần xét lại state này với đường dài hơn.
        if best_seen.get(key, float("inf")) <= g_cost:
            return float("inf"), None

        best_seen[key] = g_cost

        minimum_next_bound = float("inf")
        children = []

        for step in validMove(state):
            child = copy.deepcopy(state)

            if not apply_step(child, step):
                continue

            node_generated += 1

            child_key = state_key(child)

            if child_key in path_keys:
                continue

            if isDeadlock(child):
                continue

            child_g = g_cost + 1
            child_h = heuristic(child)
            child_f = child_g + child_h

            children.append(
                (child_f, child_h, step, child, child_key)
            )

        # Sắp xếp con theo đúng tinh thần IDA*:
        # ưu tiên f nhỏ hơn, nếu f bằng thì h nhỏ hơn, nếu vẫn bằng thì theo step.
        children.sort(key=lambda item: (item[0], item[1], item[2]))

        for _child_f, _child_h, _step, child, child_key in children:
            path_keys.add(child_key)

            next_bound, solution = search(
                child,
                g_cost + 1,
                current_bound,
                path_keys,
                best_seen,
            )

            path_keys.remove(child_key)

            if next_bound == "FOUND":
                return "FOUND", solution

            if next_bound < minimum_next_bound:
                minimum_next_bound = next_bound

        return minimum_next_bound, None

    for iteration in range(max_bound_iterations):
        print("IDA* iteration:", iteration, "bound:", bound)

        next_bound, solution = search(
            start_state,
            0,
            bound,
            {start_key},
            {},
        )

        if next_bound == "FOUND":
            _print_solution("IDA*", start_time, node_generated, solution)
            print("Final bound:", bound)
            print("Bound iterations:", iteration + 1)
            return solution

        if next_bound == float("inf"):
            break

        # Đây chính là phần quan trọng của IDA*:
        # bound mới = f nhỏ nhất vượt bound cũ.
        bound = next_bound

    print("IDA* could not find a solution within the configured limit.")
    print("Number of visited nodes:", node_generated)
    return "NoSol"
