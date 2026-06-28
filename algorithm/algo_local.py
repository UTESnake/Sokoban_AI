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

    Ý tưởng:
    - Thuật toán luôn giữ một trạng thái hiện tại và nhìn các trạng thái lân
      cận sinh ra từ một bước di chuyển hợp lệ.
    - Nếu gặp lân cận có giá trị tốt hơn trạng thái hiện tại, nó chuyển ngay
      sang lân cận đó và tiếp tục leo.
    - Cách này đơn giản và nhanh, nhưng dễ kẹt ở cực trị cục bộ: một trạng
      thái không có hàng xóm tốt hơn dù chưa phải lời giải.
    - Trong Sokoban, điều đó thường xảy ra khi box đã bị đẩy vào vị trí khó
      cải thiện hoặc heuristic tạm thời không nhìn thấy đường vòng cần thiết.
    """
    print("Processing SIMPLE HILL CLIMBING......")
    start_time = time.time()
    node_generated = 1

    # Bắt đầu từ trạng thái ban đầu và xem nó là điểm đang đứng trên "đồi".
    current = copy.deepcopy(game)
    current_value = _value(current)

    # Lặp cho tới khi không còn hàng xóm nào cải thiện được giá trị hiện tại.
    while True:
        # Xét từng nước đi hợp lệ như một hàng xóm của trạng thái hiện tại.
        moved = False

        for step in validMove(current):
            neighbor = copy.deepcopy(current)
            apply_step(neighbor, step)
            node_generated += 1

            if isDeadlock(neighbor):
                continue

            # Gặp hàng xóm tốt hơn thì đi ngay theo hướng đó.
            if _value(neighbor) > current_value:
                current = neighbor
                current_value = _value(current)
                moved = True
                break

        # Không có hàng xóm tốt hơn nghĩa là đã kẹt ở cực trị cục bộ.
        if not moved:
            break

    # Nếu trạng thái đang đứng là goal thì trả lời giải; nếu không báo kẹt.
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

    Ý tưởng:
    - Thay vì chỉ leo từ một trạng thái như Hill Climbing, Beam Search giữ một
      "chùm" gồm nhiều trạng thái tốt nhất tại mỗi vòng.
    - Mỗi vòng, thuật toán mở rộng toàn bộ trạng thái trong chùm, lọc deadlock
      và trạng thái đã thấy, rồi chọn lại beam_width trạng thái có heuristic
      thấp nhất.
    - Cách này giảm rủi ro kẹt ở một nhánh xấu vì nhiều hướng được giữ song
      song, nhưng vẫn không đảm bảo tối ưu do các nhánh ngoài chùm bị loại.
    - Trong Sokoban, beam_width càng lớn thì khả năng giữ được đường vòng tốt
      càng cao, đổi lại số node sinh ra cũng tăng.
    """
    start_time = time.time()
    rng = random.Random(seed)
    node_generated = 0

    print("Processing LOCAL BEAM SEARCH......")

    # Tạo chùm ban đầu bằng các trạng thái ngẫu nhiên đi ra từ Start.
    current_state_set = _random_state_set(game, beam_width, rng)
    node_generated += len(current_state_set)
    seen = {state_key(state) for state in current_state_set}

    best_state = min(current_state_set, key=heuristic)
    best_heuristic = heuristic(best_state)
    if best_state.isComplete():
        _print_solution("Local Beam Search", start_time, node_generated, best_state.pathSolution)
        return best_state.pathSolution

    # Lặp có giới hạn để tránh kẹt vòng lặp vô hạn.
    for iteration in range(1, max_iterations + 1):
        current_best_state = min(current_state_set, key=heuristic)
        current_best_heuristic = heuristic(current_best_state)

        # Mở rộng tất cả trạng thái trong chùm hiện tại.
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

        # Nếu không còn hàng xóm mới, chùm hiện tại đã hết hướng đi.
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

        # Goal có thể xuất hiện ngay trong lớp hàng xóm vừa sinh.
        for neighbor in neighbor_states:
            if neighbor.isComplete():
                _print_solution("Local Beam Search", start_time, node_generated, neighbor.pathSolution)
                return neighbor.pathSolution

        # Giữ lại beam_width trạng thái có heuristic tốt nhất để đi tiếp.
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

    Ý tưởng:
    - Thuật toán mô phỏng quá trình làm nguội: lúc nhiệt độ cao, nó có thể
      chấp nhận cả bước đi xấu để thoát khỏi cực trị cục bộ.
    - Khi nhiệt độ giảm dần, xác suất nhận bước xấu nhỏ lại, thuật toán trở
      nên "tham lam" hơn và tập trung quanh vùng trạng thái tốt.
    - best_state luôn lưu trạng thái tốt nhất từng gặp để nếu quá trình thử
      nghiệm kết thúc mà chưa tới goal, ta vẫn biết thuật toán đã tiến xa tới đâu.
    - Trong Sokoban, cơ chế nhận bước xấu có ích khi cần tạm thời đi xa box
      hoặc tăng heuristic trước khi có thể đẩy box vào hướng đúng.
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

    # Vòng lặp dừng khi hết lượt thử hoặc nhiệt độ đã giảm quá thấp.
    for iteration in range(1, max_iterations + 1):
        if T <= min_temperature:
            stop_reason = "Simulated Annealing đã nguội về Tmin nhưng chưa đạt Goal."
            break

        # Gặp goal ở bất kỳ thời điểm nào thì trả lời giải ngay.
        if current.isComplete():
            _print_solution("Simulated Annealing", start_time, node_generated, current.pathSolution)
            return current.pathSolution

        # Lấy một hàng xóm ngẫu nhiên để tránh đi theo một hướng cố định.
        next_state = _random_neighbor(current, rng)
        if next_state is None:
            stop_reason = "Không còn trạng thái lân cận hợp lệ."
            break
        node_generated += 1
        next_heuristic = heuristic(next_state)

        if next_state.isComplete():
            _print_solution("Simulated Annealing", start_time, node_generated, next_state.pathSolution)
            return next_state.pathSolution

        # delta < 0 nghĩa là hàng xóm tốt hơn; delta > 0 là bước đi xấu hơn.
        delta = next_heuristic - current_heuristic

        accepted = False
        if delta < 0:
            current = next_state
            current_heuristic = next_heuristic
            accepted = True
        else:
            # Nhiệt độ càng cao thì xác suất chấp nhận bước xấu càng lớn.
            p = math.exp(-delta / T)
            if rng.random() < p:
                current = next_state
                current_heuristic = next_heuristic
                accepted = True

        # best_state chỉ lấy từ quỹ đạo đã được accept.
        if accepted and current_heuristic < best_heuristic:
            best_state = copy.deepcopy(current)
            best_heuristic = current_heuristic

        # Làm nguội: càng về sau thuật toán càng ít chấp nhận bước xấu.
        T *= cooling_rate
    else:
        stop_reason = f"Đạt giới hạn {max_iterations} vòng lặp nhưng chưa đạt Goal."

    # Hết nhiệt hoặc hết vòng lặp: chỉ thành công nếu best_state thật sự là goal.
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
