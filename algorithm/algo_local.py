import copy
import math
import random
import time

from algorithm.common import (
    apply_step,
    heuristic,
    isDeadlock,
    state_key,
    validMove,
)


def _print_solution(label, start_time, node_generated, solution):
    end_time = time.time()
    print("Processing", label, "DONE")
    print("Time to find solution:", round(end_time - start_time, 2), "seconds")
    print("Number of visited nodes:", node_generated)
    print("Solution:", solution, "Number steps:", len(solution))


def _print_partial_solution(label, start_time, node_generated, path, reason, show_path=True):
    end_time = time.time()
    print("Processing", label, "STOPPED")
    print("Time before stop:", round(end_time - start_time, 2), "seconds")
    print("Number of visited nodes:", node_generated)
    print("Reason:", reason)
    if show_path:
        print("Partial solution before local optimum:", path, "Number steps:", len(path))
    else:
        print("Stopped at step:", len(path))


def _value(state):
    # Hill Climbing tối đa hóa Value, trong khi Sokoban tối thiểu hóa h.
    return -heuristic(state)


def _make_failure_result(
        algorithm_name, reason, state, node_generated, start_time,
        failed_step=None, extra=None, show_path=True):
    path = ""
    if state is not None and hasattr(state, "pathSolution"):
        path = state.pathSolution
    if failed_step is None:
        failed_step = len(path)
    _print_partial_solution(
        algorithm_name, start_time, node_generated, path, reason,
        show_path=show_path)
    result = {
        "status": "failure",
        "algorithm_name": algorithm_name,
        "reason": reason,
        "path": path,
        "path_steps": len(path),
        "hide_failed_path": not show_path,
        "failed_step": max(int(failed_step), 1),
        "fail_step": max(int(failed_step), 1),
        "node_generated": node_generated,
        "elapsed_ms": (time.time() - start_time) * 1000,
    }
    if state is not None:
        result["heuristic"] = heuristic(state)
    if extra:
        result.update(extra)
    return result


def simple_hill_climbing(game):
    """Simple Hill Climbing.

    Pseudocode:
        function Simple_Hill_Climbing(Start):
        1. Current_State = Start
           Tính giá trị đánh giá của Current_State
        2. TRONG KHI (đúng):
           a. Sinh lần lượt các trạng thái lân cận của Current_State
           b. Với mỗi Next_State:
              i. Tính Value(Next_State)
              ii. NẾU Value(Next_State) > Value(Current_State):
                  Current_State = Next_State
                  Chuyển sang lần lặp tiếp theo
           c. NẾU không có lân cận nào tốt hơn: Dừng (cực đại cục bộ)
        3. TRẢ VỀ Current_State
    """
    print("Processing SIMPLE HILL CLIMBING......")
    start_time = time.time()
    node_generated = 1

    # 1. Khởi tạo Current_State = Start; tính Value(Current_State)
    current = copy.deepcopy(game)
    current_value = _value(current)

    # 2. TRONG KHI (đúng)
    while True:
        # a. Sinh lần lượt các trạng thái lân cận của Current_State
        moved = False

        for step in validMove(current):
            # b.i. Tính Value(Next_State)
            neighbor = copy.deepcopy(current)
            apply_step(neighbor, step)
            node_generated += 1

            if isDeadlock(neighbor):
                continue

            # b.ii. NẾU Value(Next_State) > Value(Current_State)
            if _value(neighbor) > current_value:
                current = neighbor          # Current_State = Next_State
                current_value = _value(current)
                moved = True
                break                       # Chuyển sang lần lặp tiếp theo

        # c. NẾU không có lân cận nào tốt hơn: Dừng (cực đại cục bộ)
        if not moved:
            break

    # 3. TRẢ VỀ Current_State
    if current.isComplete():
        _print_solution("Simple Hill Climbing", start_time, node_generated, current.pathSolution)
        return current.pathSolution

    reason = "Không còn trạng thái lân cận nào tốt hơn; thuật toán dừng ở cực đại cục bộ."
    print("Simple Hill Climbing failed:", reason)
    return _make_failure_result(
        "Simple Hill Climbing",
        reason,
        current,
        node_generated,
        start_time,
        failed_step=max(len(current.pathSolution), 1),
    )


def beam_search(game, beam_width=50, seed=7, max_iterations=500):
    """Local Beam Search.

    Pseudocode:
        function Local_Beam_Search(k):
        1. Current_State_set = {Sinh ngẫu nhiên k trạng thái từ Start}
        2. Lặp tối đa max_iterations lần:
           Neighbor_States = rỗng
           2.1 SINH TRẠNG THÁI LÂN CẬN:
               VỚI MỖI State trong Current_State_set:
                   Sinh tất cả neighbor chưa có trong seen, thêm vào Neighbor_States
           2.2 KIỂM TRA BẾ TẮC:
               NẾU Neighbor_States = rỗng:
                   TRẢ VỀ trạng thái tốt nhất trong Current_State_set
           2.3 KIỂM TRA ĐÍCH:
               VỚI MỖI Neighbor trong Neighbor_States:
                   NẾU Neighbor == Goal: TRẢ VỀ Neighbor
           2.4 LỰA CHỌN CHÙM:
               Sắp xếp Neighbor_States theo h tốt dần
               New_State_set = k trạng thái tốt nhất
               NẾU New_State_set không cải thiện h tốt nhất: Dừng
               Current_State_set = New_State_set
    """
    start_time = time.time()
    rng = random.Random(seed)
    node_generated = 0

    print("Processing LOCAL BEAM SEARCH......")

    # 1. Khởi tạo: Current_State_set = {k trạng thái ngẫu nhiên từ Start}
    current_state_set = _random_state_set(game, beam_width, rng)
    node_generated += len(current_state_set)
    seen = {state_key(state) for state in current_state_set}

    best_state = min(current_state_set, key=heuristic)
    best_heuristic = heuristic(best_state)
    if best_state.isComplete():
        _print_solution("Local Beam Search", start_time, node_generated, best_state.pathSolution)
        return best_state.pathSolution

    # 2. Lặp có giới hạn để tránh kẹt vòng lặp vô hạn
    for iteration in range(1, max_iterations + 1):
        current_best_state = min(current_state_set, key=heuristic)
        current_best_heuristic = heuristic(current_best_state)

        # 2.1 SINH TRẠNG THÁI LÂN CẬN
        neighbor_states = []
        for state in current_state_set:
            for step in validMove(state):
                neighbor = copy.deepcopy(state)
                apply_step(neighbor, step)
                node_generated += 1
                key = state_key(neighbor)
                if key in seen:
                    continue
                seen.add(key)
                if isDeadlock(neighbor):
                    continue
                neighbor_states.append(neighbor)

        # 2.2 KIỂM TRA BẾ TẮC
        if not neighbor_states:
            best_state = min(current_state_set, key=heuristic)
            if best_state.isComplete():
                _print_solution("Local Beam Search", start_time, node_generated, best_state.pathSolution)
                return best_state.pathSolution
            reason = "Không sinh được trạng thái lân cận mới từ chùm hiện tại."
            return _make_failure_result(
                "Local Beam Search", reason, best_state,
                node_generated, start_time,
                failed_step=len(best_state.pathSolution),
                extra={
                    "beam_width": beam_width,
                    "iteration": iteration,
                    "seen_count": len(seen),
                },
            )

        # 2.3 KIỂM TRA ĐÍCH
        for neighbor in neighbor_states:
            if neighbor.isComplete():
                _print_solution("Local Beam Search", start_time, node_generated, neighbor.pathSolution)
                return neighbor.pathSolution

        # 2.4 LỰA CHỌN CHÙM
        neighbor_states.sort(key=heuristic)
        next_state_set = neighbor_states[:beam_width]
        next_best_state = next_state_set[0]
        next_best_heuristic = heuristic(next_best_state)

        if next_best_heuristic < best_heuristic:
            best_state = next_best_state
            best_heuristic = next_best_heuristic

        if next_best_heuristic >= current_best_heuristic:
            reason = "Chùm mới không cải thiện heuristic tốt nhất nên dừng."
            return _make_failure_result(
                "Local Beam Search", reason, current_best_state,
                node_generated, start_time,
                failed_step=len(current_best_state.pathSolution),
                extra={
                    "beam_width": beam_width,
                    "iteration": iteration,
                    "best_heuristic": current_best_heuristic,
                    "next_best_heuristic": next_best_heuristic,
                    "seen_count": len(seen),
                },
            )

        current_state_set = next_state_set

    reason = f"Đạt giới hạn {max_iterations} vòng lặp nhưng chưa tìm được Goal."
    return _make_failure_result(
        "Local Beam Search", reason, best_state,
        node_generated, start_time,
        failed_step=len(best_state.pathSolution),
        extra={
            "beam_width": beam_width,
            "iteration": max_iterations,
            "best_heuristic": best_heuristic,
            "seen_count": len(seen),
        },
    )


def simulated_annealing_search(
    game,
    initial_temperature=1000.0,
    cooling_rate=0.95,
    min_temperature=0.001,
    seed=19,
    max_iterations=1000,
):
    """Simulated Annealing.

    Pseudocode:
        SimulatedAnnealing(start, goal):
            current_state = start
            best_state = start
            T = T0
            for i = 1 to max_iterations while T > Tmin:
                if current_state == goal: return current_state
                next_state = RandomNeighbor(current_state)
                if h(next_state) < h(best_state): best_state = next_state
                Δ = h(next_state) - h(current_state)
                if Δ < 0: current_state = next_state
                else:
                    p = exp(-Δ/T)
                    if Random(0,1) < p: current_state = next_state
                T = α * T
            return best_state
    """
    start_time = time.time()
    rng = random.Random(seed)
    node_generated = 1

    print("Processing SIMULATED ANNEALING......")

    # current_state = start
    current = copy.deepcopy(game)
    current_heuristic = heuristic(current)
    best_state = copy.deepcopy(current)
    best_heuristic = current_heuristic

    # T = T0
    T = float(initial_temperature)
    stop_reason = "Simulated Annealing đã nguội về Tmin nhưng chưa đạt Goal."
    iteration = 0

    # for i = 1 to max_iterations while T > Tmin
    for iteration in range(1, max_iterations + 1):
        if T <= min_temperature:
            stop_reason = "Simulated Annealing đã nguội về Tmin nhưng chưa đạt Goal."
            break

        # if current_state == goal: return current_state
        if current.isComplete():
            _print_solution("Simulated Annealing", start_time, node_generated, current.pathSolution)
            return current.pathSolution

        # next_state = RandomNeighbor(current_state)
        next_state = _random_neighbor(current, rng)
        if next_state is None:
            stop_reason = "Không còn trạng thái lân cận hợp lệ."
            break
        node_generated += 1
        next_heuristic = heuristic(next_state)

        if next_state.isComplete():
            _print_solution("Simulated Annealing", start_time, node_generated, next_state.pathSolution)
            return next_state.pathSolution

        # Δ = h(next_state) - h(current_state)
        delta = next_heuristic - current_heuristic

        # if Δ < 0: current_state = next_state
        accepted = False
        if delta < 0:
            current = next_state
            current_heuristic = next_heuristic
            accepted = True
        else:
            # p = exp(-Δ/T)
            # if Random(0,1) < p: current_state = next_state
            p = math.exp(-delta / T)
            if rng.random() < p:
                current = next_state
                current_heuristic = next_heuristic
                accepted = True

        # best_state chỉ lấy từ quỹ đạo đã được accept.
        if accepted and current_heuristic < best_heuristic:
            best_state = copy.deepcopy(current)
            best_heuristic = current_heuristic

        # T = α * T
        T *= cooling_rate
    else:
        stop_reason = f"Đạt giới hạn {max_iterations} vòng lặp nhưng chưa đạt Goal."

    # return best_state
    if best_state.isComplete():
        _print_solution("Simulated Annealing", start_time, node_generated, best_state.pathSolution)
        return best_state.pathSolution

    reason = stop_reason
    print("Simulated Annealing failed:", reason)
    return _make_failure_result(
        "Simulated Annealing",
        reason,
        best_state,
        node_generated,
        start_time,
        failed_step=max(len(best_state.pathSolution), 1),
        extra={
            "best_heuristic": best_heuristic,
            "final_temperature": T,
            "iteration": iteration,
            "max_iterations": max_iterations,
        },
        show_path=False,
    )


def _random_neighbor(state, rng):
    """RandomNeighbor — chọn ngẫu nhiên một trạng thái lân cận hợp lệ."""
    candidates = []
    for step in validMove(state):
        neighbor = copy.deepcopy(state)
        apply_step(neighbor, step)
        if not isDeadlock(neighbor):
            candidates.append(neighbor)
    if not candidates:
        return None
    return rng.choice(candidates)


def _random_state_set(game, count, rng, walk_length=12):
    states = []
    seen = set()
    attempts = 0

    while len(states) < count and attempts < max(1, count * 100):
        attempts += 1
        state = _random_walk_from_start(game, rng, rng.randint(0, walk_length))
        key = state_key(state)
        if key in seen:
            continue
        seen.add(key)
        states.append(state)

    while len(states) < count:
        states.append(copy.deepcopy(game))

    return states


def _random_walk_from_start(game, rng, walk_length):
    state = copy.deepcopy(game)

    for _ in range(walk_length):
        neighbors = []
        for step in validMove(state):
            neighbor = copy.deepcopy(state)
            apply_step(neighbor, step)
            if not isDeadlock(neighbor):
                neighbors.append(neighbor)
        if not neighbors:
            break
        state = rng.choice(neighbors)

    return state
