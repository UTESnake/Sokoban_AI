import copy
import queue
import time

from algorithm.common import apply_step, box_toDock, isDeadlock, state_key, validMove, worker_toBox


def no_observation_search(game):
    """
    Tìm kiếm không quan sát (Sensorless Search / Conformant Planning)
    Giả định tác nhân không nhìn thấy trạng thái hiện tại, thuật toán duyệt qua các chuỗi 
    hành động bằng BFS để tìm ra đường đi chắc chắn dẫn đến đích từ trạng thái ban đầu.
    """
    start = time.time()
    node_generated = 0
    start_state = copy.deepcopy(game)
    node_generated += 1

    if isDeadlock(start_state):
        print("No Solution!")
        return "NoSol"

    print("Processing NO OBSERVATION SEARCH......")

    search_queue = queue.Queue()
    search_queue.put(start_state)
    visited = {state_key(start_state)}

    while not search_queue.empty():
        curr_state = search_queue.get()
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
                search_queue.put(new_state)
                visited.add(key)

    print(node_generated)
    print("No Solution!")
    return "NoSol"


def partial_observation_search(game):
    """
    Tìm kiếm quan sát một phần (Partial Observation Search)
    Mô phỏng bằng thuật toán tìm kiếm dựa trên Heuristic kết hợp phạt điểm (Penalty) 
    khi di chuyển vào các vùng chưa rõ thông tin (ô ký hiệu '?' Mystery) hoặc có đối thủ ('E').
    """
    start = time.time()
    node_generated = 0
    start_state = copy.deepcopy(game)
    node_generated += 1

    if isDeadlock(start_state):
        print("No Solution!")
        return "NoSol"

    print("Processing PARTIAL OBSERVATION SEARCH......")

    open_list = queue.PriorityQueue()
    counter = 0
    h_start = worker_toBox(start_state) + box_toDock(start_state)
    open_list.put((h_start, counter, start_state))
    visited = set()

    while not open_list.empty():
        _, _, cur_state = open_list.get()
        visited.add(state_key(cur_state))

        for step in validMove(cur_state):
            new_state = copy.deepcopy(cur_state)
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
                # Tính khoảng cách Heuristic thông thường
                h_val = worker_toBox(new_state) + box_toDock(new_state)
                
                # Tính toán Penalty từ môi trường quan sát một phần (Ví dụ đếm ô chưa biết '?')
                mystery_count = sum(row.count('?') for row in new_state.matrix)
                penalty = mystery_count * 15  # Phạt điểm để tác nhân ưu tiên đi vùng an toàn trước
                
                counter += 1
                open_list.put((h_val + penalty, counter, new_state))

    print(node_generated)
    print("No Solution!")
    return "NoSol"

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
