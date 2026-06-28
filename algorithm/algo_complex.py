import copy
import heapq
import random
import time
from collections import deque

from solver import Solve
from algorithm.common import (
    MOVE_DELTAS,
    apply_step,
    heuristic,
    isDeadlock,
    state_key,
    validMove,
)


# ============================================================
# CONFIG
# ============================================================


MAX_BELIEF_EXPANSIONS = 12000
MAX_PATH_NODES = 25000
MAX_UNKNOWN_CELLS = 6
MAX_SENSORLESS_WORLDS = 12
MAX_SENSORLESS_SAFE_UNKNOWNS = 3
SENSORLESS_OBJECT_RADIUS = 0
MAX_AND_OR_DEPTH = 80
MAX_AND_OR_NODES = 60000
AND_OR_TIMEOUT_SECONDS = 5.0
MAX_PARTIAL_REPLANS = 500
MAX_PARTIAL_PLAN_EXPANSIONS = 1500


# ============================================================
# OUTPUT HELPERS
# ============================================================

def _print_solution(
        label, start_time, node_generated, solution,
        algorithm_steps=None, plan_text=None, plan_kind="path"):
    end = time.time()
    print("Time to find solution:", round(end - start_time, 2), "seconds")
    print("Number of visited nodes:", node_generated)
    if algorithm_steps is not None:
        print("Algorithm processing steps:", algorithm_steps)
    print("Replay path:", solution, "Number path steps:", len(solution))
    if plan_text:
        print(f"{plan_kind}:", plan_text)


def _success_result(
        label, start_time, node_generated, solution, algorithm_steps=None,
        note=None, plan_text=None, plan_kind="path", extra=None):
    """
    Trả result dạng dict để main.py so sánh được:
    - display_steps: lượng công việc của thuật toán;
    - real_steps: số bước thật dùng để animation Sokoban.
    """
    if algorithm_steps is None:
        algorithm_steps = len(solution)

    elapsed_ms = (time.time() - start_time) * 1000
    _print_solution(
        label,
        start_time,
        node_generated,
        solution,
        algorithm_steps,
        plan_text=plan_text,
        plan_kind=plan_kind,
    )

    metric_label = f"{int(algorithm_steps)}x · {len(solution)}b"
    result = {
        "status": "success",
        "algorithm_name": label,
        "path": solution,
        "plan_text": plan_text or solution,
        "plan_kind": plan_kind,
        "display_steps": int(algorithm_steps),
        "metric_label": metric_label,
        "node_generated": int(node_generated),
        "real_steps": len(solution),
        "elapsed_ms": elapsed_ms,
        "note": note or "",
    }

    if extra:
        result.update(extra)

    return result


def _format_actions(actions, max_actions=80):
    if not actions:
        return "STOP"

    shown = " ".join(actions[:max_actions])
    if len(actions) > max_actions:
        shown += f" ... (+{len(actions) - max_actions} bước)"
    return shown


def _and_or_plan_branches(plan, prefix=""):
    if plan == "failure":
        return []
    if plan == []:
        return [prefix]
    if not isinstance(plan, list) or len(plan) == 0:
        return [prefix]

    action, and_plan = plan
    if not and_plan:
        return [prefix + action]

    branches = []
    for subplan in and_plan.values():
        branches.extend(_and_or_plan_branches(subplan, prefix + action))
    return branches


def _format_and_or_policy(plan):
    branches = _and_or_plan_branches(plan)
    if not branches:
        return "AND-OR policy: failure"

    lines = [f"AND-OR policy với {len(branches)} nhánh outcome:"]
    for index, branch in enumerate(branches[:6], start=1):
        lines.append(f"nhánh {index}: {_format_actions(branch)}")
    if len(branches) > 6:
        lines.append(f"... còn {len(branches) - 6} nhánh")
    return " | ".join(lines)


def _format_conformant_plan(plan, belief_count):
    return (
        f"Conformant plan Π(B0) cho {belief_count} world belief: "
        f"{_format_actions(plan)}"
    )


def _format_partial_plan_set(records, executed_path, final_plan=""):
    lines = [f"Contingency/replanning plan set ({len(records)} lần lập kế hoạch):"]

    for index, record in enumerate(records[:8], start=1):
        plan = record.get("plan") or record.get("action") or ""
        lines.append(
            f"{index}. sau {record.get('step', 0)} bước, "
            f"|B|={record.get('beliefs', 0)}, "
            f"{record.get('source', 'replan')} -> {_format_actions(plan, 30)}"
        )

    if len(records) > 8:
        lines.append(f"... còn {len(records) - 8} replan")

    branch = executed_path + final_plan
    lines.append(f"Nhánh replay hiện tại: {_format_actions(branch)}")
    return " | ".join(lines)


def _failure_result(label, reason, state, node_generated, start_time, failed_step=None, extra=None):
    path = ""
    if state is not None and hasattr(state, "pathSolution"):
        path = state.pathSolution

    if failed_step is None:
        failed_step = max(len(path), node_generated - 1, 1)

    result = {
        "status": "failure",
        "algorithm_name": label,
        "reason": reason,
        "path": path,
        "failed_step": int(failed_step),
        "fail_step": int(failed_step),
        "node_generated": int(node_generated),
        "elapsed_ms": (time.time() - start_time) * 1000,
    }

    if extra:
        result.update(extra)

    return result


# ============================================================
# STATE / MATRIX HELPERS
# ============================================================

def _matrix_copy_from_game(game):
    return copy.deepcopy(game.getMatrix())


def _replace_unknowns(matrix, value=" "):
    """
    Ký hiệu '?' dùng cho môi trường quan sát hạn chế.

    Với animation thật:
    - coi '?' là ô sàn trống.

    Với belief-state:
    - '?' sẽ được tách thành nhiều thế giới có thể là wall hoặc floor.
    """
    result = copy.deepcopy(matrix)
    for r, row in enumerate(result):
        for c, cell in enumerate(row):
            if cell == "?":
                result[r][c] = value
    return result


def _actual_state_from_game(game):
    """
    Trạng thái thật dùng để replay GUI.
    Nếu map có '?', GUI vẫn cần một path thật hợp lệ, nên quy ước '?' = sàn.
    """
    return Solve(_replace_unknowns(_matrix_copy_from_game(game), " "))


def _actual_state_from_matrix(matrix):
    return Solve(_replace_unknowns(matrix, " "))


def _safe_child(state, action):
    if action not in MOVE_DELTAS:
        return None

    if action not in validMove(state):
        return None

    child = copy.deepcopy(state)
    apply_step(child, action)

    if isDeadlock(child):
        return None

    return child


def _is_goal(state):
    return state is not None and state.isComplete()


# ============================================================
# AND-OR GRAPH SEARCH
# ============================================================

def and_or_search(
        game,
        max_depth=MAX_AND_OR_DEPTH,
        max_nodes=MAX_AND_OR_NODES,
        timeout_seconds=AND_OR_TIMEOUT_SECONDS):
    """
    AND-OR Graph Search cho môi trường phức tạp.

    Pseudocode:
        function AND_OR_GRAPH_SEARCH(problem):
            return OR_SEARCH(problem.initial_state, problem, [])

        function OR_SEARCH(state, problem, path):
            if state in problem.goal_test: return []
            if depth > max_depth: return failure
            if node limit or timeout reached: return failure
            if state in path: return failure
            for each action in problem.actions(state):
                result_states = problem.results(state, action)
                plan = AND_SEARCH(result_states, problem, path + [state])
                if plan != failure: return [action, plan]
            return failure

        function AND_SEARCH(states, problem, path):
            plans = empty mapping
            for each s in states:
                plan_s = OR_SEARCH(s, problem, path)
                if plan_s == failure: return failure
                plans[s] = plan_s
            return plans
    """
    print("Processing AND-OR GRAPH SEARCH......")

    start_time = time.time()
    deadline = time.perf_counter() + timeout_seconds
    start_state = _actual_state_from_game(game)
    seed_path, _seed_nodes = _constraint_guided_search(
        start_state,
        assignment=None,
        strategy="astar",
        max_nodes=MAX_PATH_NODES,
    )
    if seed_path == "NoSol":
        seed_path = ""

    # problem định nghĩa không gian trạng thái cho AND-OR
    problem = {
        "actions": lambda s: _ordered_and_or_actions(s, seed_path),
        "results": lambda s, a: _and_or_outcomes(s, a),
    }

    node_generated = 1
    or_calls = 0
    and_calls = 0
    stop_reason = None
    solved_cache = {}
    failed_cache = {}

    def guard_exceeded(depth):
        nonlocal stop_reason

        if depth > max_depth:
            stop_reason = f"AND-OR đạt giới hạn độ sâu {max_depth}."
            return True

        if node_generated >= max_nodes:
            stop_reason = f"AND-OR đạt giới hạn {max_nodes} node."
            return True

        if time.perf_counter() >= deadline:
            stop_reason = f"AND-OR vượt timeout nội bộ {timeout_seconds:g}s."
            return True

        return False

    def or_search(state, problem, path, depth):
        """OR_SEARCH(state, problem, path) — returns a plan or failure."""
        nonlocal node_generated, or_calls
        or_calls += 1

        if guard_exceeded(depth):
            return "failure"

        # if state ∈ problem.goal_test: return []
        if state.isComplete():
            return []

        key = state_key(state)

        # if state ∈ path: return failure (tránh lặp)
        if key in path:
            return "failure"

        if key in solved_cache:
            return solved_cache[key]

        remaining_depth = max_depth - depth
        if failed_cache.get(key, -1) >= remaining_depth:
            return "failure"

        # for each action in problem.actions(state)
        for action in problem["actions"](state):
            # result_states = problem.results(state, action)
            result_states = problem["results"](state, action)
            if not result_states:
                continue

            node_generated += len(result_states)
            if guard_exceeded(depth):
                return "failure"

            # plan = AND_SEARCH(result_states, problem, path + [state])
            plan = and_search(
                result_states,
                problem,
                path + [state_key(state)],
                depth + 1,
            )
            if plan != "failure":
                result_plan = [action, plan]
                solved_cache[key] = result_plan
                return result_plan

        failed_cache[key] = remaining_depth
        return "failure"

    def and_search(states, problem, path, depth):
        """AND_SEARCH(states, problem, path) — returns plans mapping or failure."""
        nonlocal and_calls
        and_calls += 1

        if guard_exceeded(depth):
            return "failure"

        # plans = empty mapping
        plans = {}

        # for each s in states
        for s in states:
            # plan_s = OR_SEARCH(s, problem, path)
            plan_s = or_search(s, problem, path, depth)
            if plan_s == "failure":
                return "failure"
            plans[state_key(s)] = plan_s

        return plans

    # AND_OR_GRAPH_SEARCH: OR_SEARCH(initial_state, problem, [])
    result = or_search(start_state, problem, [], 0)

    if result == "failure":
        reason = stop_reason or "AND-OR không tìm thấy policy hợp lệ trong giới hạn."
        print("AND-OR Graph Search failed.")
        return _failure_result(
            "AND-OR",
            reason,
            start_state,
            node_generated,
            start_time,
            failed_step=max(or_calls + and_calls, 1),
            extra={
                "or_calls": or_calls,
                "and_calls": and_calls,
                "max_depth": max_depth,
                "max_nodes": max_nodes,
                "timeout_seconds": timeout_seconds,
                "plan_kind": "policy",
                "plan": "failure",
            },
        )

    # Chuyển kế hoạch lồng [action, {state: plan}] → chuỗi hành động phẳng
    solution = _flatten_and_or_plan(result)

    algorithm_steps = or_calls + and_calls
    return _success_result(
        "AND-OR",
        start_time,
        node_generated,
        solution,
        algorithm_steps=algorithm_steps,
        plan_text=_format_and_or_policy(result),
        plan_kind="policy",
        extra={"plan": result, "policy": result},
        note="x = số lượt OR/AND; b = số bước animation.",
    )


def _flatten_and_or_plan(plan):
    """Chuyển kế hoạch lồng AND-OR [action, {state: plan}] → chuỗi hành động phẳng."""
    if plan == "failure" or not isinstance(plan, list) or len(plan) == 0:
        return ""
    action, and_plan = plan
    if not and_plan:
        return action
    # Đi theo outcome đầu tiên trong AND plan (outcome dự định)
    first_subplan = next(iter(and_plan.values()))
    return action + _flatten_and_or_plan(first_subplan)


def _ordered_and_or_actions(state, seed_path=""):
    choices = []
    fallback = []
    preferred_action = None

    if seed_path:
        prefix_len = len(getattr(state, "pathSolution", ""))
        if prefix_len < len(seed_path):
            preferred_action = seed_path[prefix_len]

    for action in validMove(state):
        child = _safe_child(state, action)
        if child is None:
            continue

        preferred_bonus = -1000 if action == preferred_action else 0
        item = (preferred_bonus + heuristic(child), action)
        if isDeadlock(child):
            fallback.append(item)
        else:
            choices.append(item)

    if not choices:
        choices = fallback

    choices.sort(key=lambda item: item[0])
    return [action for _score, action in choices]


def _and_or_outcomes(state, action):
    """
    Tạo outcome cho AND-OR.

    Chỉ dùng outcome của action dự định. Không tự bẻ sang hướng vuông góc,
    vì hướng đó không phải kết quả trực tiếp của hành động đang xét.
    """
    intended = _safe_child(state, action)
    if intended is None:
        return []

    return [intended]


# ============================================================
# NO OBSERVATION / PARTIAL OBSERVATION
# ============================================================

def search_with_no_observation(game):
    """
    Sensorless / conformant planning.

    Agent không nhận percept nào, nên plan phải là một chuỗi action duy nhất
    hợp lệ và đạt goal trong mọi state thuộc belief-state ban đầu.
    """
    print("Processing NO OBSERVATION BELIEF-STATE SEARCH......")
    start_time = time.time()
    initial_matrix = _matrix_copy_from_game(game)
    start_states = _sensorless_initial_belief_variants(initial_matrix)
    belief_model = "hidden_object"

    solution, node_generated, belief_expansions = _conformant_plan_from_belief(
        start_states,
        max_expansions=MAX_BELIEF_EXPANSIONS,
    )

    if solution is None:
        fallback_states = _sensorless_safe_layout_belief_variants(initial_matrix)
        fallback_key = _belief_key(fallback_states)

        if fallback_key != _belief_key(start_states):
            (
                fallback_solution,
                fallback_nodes,
                fallback_expansions,
            ) = _conformant_plan_from_belief(
                fallback_states,
                max_expansions=MAX_BELIEF_EXPANSIONS,
            )
            node_generated += fallback_nodes
            belief_expansions += fallback_expansions

            if fallback_solution is not None:
                solution = fallback_solution
                start_states = fallback_states
                belief_model = "safe_layout_uncertainty"

    if solution is not None:
        plan_text = _format_conformant_plan(solution, len(start_states))
        note = (
            "Sensorless/conformant: không có percept, action phải hợp lệ "
            "và đạt goal trong mọi world thuộc belief-state."
        )
        if belief_model == "safe_layout_uncertainty":
            note += (
                " Belief object bị che hoàn toàn của level này không có plan chung, "
                "nên NoObs dùng belief layout an toàn để vẫn sinh kế hoạch conformant."
            )
        return _success_result(
            "No Observation",
            start_time,
            node_generated,
            solution,
            algorithm_steps=belief_expansions,
            plan_text=plan_text,
            plan_kind="conformant_plan",
            extra={
                "plan": {
                    "type": "conformant",
                    "belief_worlds": len(start_states),
                    "belief_model": belief_model,
                    "actions": solution,
                },
                "belief_worlds": len(start_states),
                "belief_model": belief_model,
            },
            note=note,
        )

    reason = (
        "No Observation không tìm được conformant plan an toàn cho "
        f"{len(start_states)} trạng thái ban đầu khả dĩ."
    )
    print("No Observation failed.")
    return _failure_result(
        "No Observation",
        reason,
        None,
        node_generated,
        start_time,
        failed_step=max(belief_expansions, 1),
        extra={
            "belief_expansions": belief_expansions,
            "belief_worlds": len(start_states),
            "plan_kind": "conformant_plan",
            "suppress_failure_popup": True,
            "plan": {
                "type": "conformant",
                "belief_worlds": len(start_states),
                "belief_model": belief_model,
                "actions": None,
            },
        },
    )


def partially_observable_search(game, observe_radius=1):
    """
    Online planning/replanning trong môi trường quan sát một phần.

    Ở mỗi lượt:
    1. Nhận percept cục bộ quanh worker.
    2. Lọc belief-state.
    3. Replan trên belief hiện tại.
    4. Execute một action, rồi quan sát lại.
    """
    print("Processing PARTIAL OBSERVATION BELIEF-STATE SEARCH......")
    start_time = time.time()
    initial_matrix = _matrix_copy_from_game(game)
    has_unknown = any("?" in row for row in initial_matrix)

    real_start = _actual_state_from_matrix(initial_matrix)
    real_state = real_start
    belief_states = _belief_variants(initial_matrix)

    node_generated = len(belief_states)
    replans = 0
    plan_expansions = 0
    observation_filters = 0
    path = ""
    seen_runtime = set()
    plan_records = []

    for _turn in range(MAX_PARTIAL_REPLANS):
        observation_filters += 1
        belief_states = _filter_by_real_observation(
            belief_states,
            real_state,
            observe_radius,
        )

        # Nếu model bị rỗng vì cắt bớt unknown quá mạnh, phục hồi bằng state thật
        # đã quan sát được để online replanning vẫn tiếp tục.
        if not belief_states:
            belief_states = [copy.deepcopy(real_state)]

        if real_state.isComplete():
            note = (
                "Partial Observation/online replanning: sau mỗi percept, "
                "agent lọc belief-state rồi lập lại kế hoạch."
            )
            if not has_unknown:
                note += " Map không có '?' nên quan sát cục bộ ít tạo phân nhánh."
            return _success_result(
                "Partial Observation",
                start_time,
                node_generated,
                path,
                algorithm_steps=replans + plan_expansions + observation_filters,
                plan_text=_format_partial_plan_set(
                    plan_records,
                    executed_path=path,
                    final_plan="",
                ),
                plan_kind="contingency_plan_set",
                extra={
                    "plan": {
                        "type": "contingency_replanning",
                        "records": plan_records,
                        "executed_branch": path,
                    },
                    "plan_records": plan_records,
                },
                note=note,
            )

        if (
                len(belief_states) == 1
                and state_key(belief_states[0]) == state_key(real_state)):
            plan, plan_nodes, expansions = _conformant_plan_from_belief(
                [real_state],
                max_expansions=MAX_BELIEF_EXPANSIONS,
            )
            replans += 1
            plan_expansions += expansions
            node_generated += plan_nodes

            if plan is not None:
                plan_records.append({
                    "step": len(path),
                    "beliefs": len(belief_states),
                    "plan": plan,
                    "action": plan[0] if plan else "STOP",
                    "source": "belief collapsed",
                })
                solution = path + plan
                note = (
                    "Partial Observation: belief-state đã collapse còn một world, "
                    "nên phần còn lại được giải như fully observable planning."
                )
                if not has_unknown:
                    note += " Map không có '?' nên collapse xảy ra ngay từ đầu."
                return _success_result(
                    "Partial Observation",
                    start_time,
                    node_generated,
                    solution,
                    algorithm_steps=replans + plan_expansions + observation_filters,
                    plan_text=_format_partial_plan_set(
                        plan_records,
                        executed_path=path,
                        final_plan=plan,
                    ),
                    plan_kind="contingency_plan_set",
                    extra={
                        "plan": {
                            "type": "contingency_replanning",
                            "records": plan_records,
                            "executed_branch": solution,
                        },
                        "plan_records": plan_records,
                    },
                    note=note,
                )

        runtime_key = (state_key(real_state), _belief_key(belief_states))
        if runtime_key in seen_runtime:
            action = _choose_partial_exploration_action(
                belief_states,
                real_state,
                observe_radius,
            )
            if action is not None:
                plan_records.append({
                    "step": len(path),
                    "beliefs": len(belief_states),
                    "plan": action,
                    "action": action,
                    "source": "cycle-break exploration",
                })
        else:
            seen_runtime.add(runtime_key)
            plan, plan_nodes, expansions = _conformant_plan_from_belief(
                belief_states,
                max_expansions=MAX_PARTIAL_PLAN_EXPANSIONS,
            )
            replans += 1
            plan_expansions += expansions
            node_generated += plan_nodes
            action = plan[0] if plan else None

            if action is None:
                action = _choose_partial_exploration_action(
                    belief_states,
                    real_state,
                    observe_radius,
                )
                if action is not None:
                    plan_records.append({
                        "step": len(path),
                        "beliefs": len(belief_states),
                        "plan": action,
                        "action": action,
                        "source": "exploration action",
                    })
            else:
                plan_records.append({
                    "step": len(path),
                    "beliefs": len(belief_states),
                    "plan": plan,
                    "action": action,
                    "source": "conditional replan",
                })

        if action is None:
            break

        real_child = _safe_child(real_state, action)
        if real_child is None:
            break

        next_belief = _belief_successors(
            belief_states,
            action,
            require_all=False,
        )
        node_generated += len(next_belief)

        real_state = real_child
        path += action

        observation_filters += 1
        belief_states = _filter_by_real_observation(
            next_belief,
            real_state,
            observe_radius,
        )
        if not belief_states:
            belief_states = [copy.deepcopy(real_state)]

    reason = "Partial Observation hết giới hạn online replanning hoặc không còn action hợp lệ."
    print("Partial Observation failed.")
    return _failure_result(
        "Partial Observation",
        reason,
        real_state,
        node_generated,
        start_time,
        failed_step=max(len(path), replans, 1),
        extra={
            "replans": replans,
            "plan_expansions": plan_expansions,
            "observation_filters": observation_filters,
        },
    )


def _conformant_plan_from_belief(start_states, max_expansions):
    node_generated = len(start_states)
    belief_expansions = 0
    start_key = _belief_key(start_states)
    open_list = []
    counter = 0
    best_g = {start_key: 0}

    heapq.heappush(
        open_list,
        (
            _belief_heuristic(start_states),
            0,
            counter,
            start_states,
            "",
        ),
    )

    while open_list and belief_expansions < max_expansions:
        _, g_cost, _, belief_states, path = heapq.heappop(open_list)
        belief_expansions += 1

        key = _belief_key(belief_states)
        if g_cost != best_g.get(key):
            continue

        if all(state.isComplete() for state in belief_states):
            return path, node_generated, belief_expansions

        for action in _ordered_belief_actions(belief_states):
            next_states = _belief_successors(
                belief_states,
                action,
                require_all=True,
            )
            if not next_states:
                continue

            next_key = _belief_key(next_states)
            new_g = g_cost + 1

            if new_g >= best_g.get(next_key, float("inf")):
                continue

            best_g[next_key] = new_g
            counter += 1
            node_generated += len(next_states)

            priority = new_g + _belief_heuristic(next_states)

            heapq.heappush(
                open_list,
                (
                    priority,
                    new_g,
                    counter,
                    next_states,
                    path + action,
                ),
            )

    return None, node_generated, belief_expansions


def _belief_variants(matrix):
    unknowns = [
        (r, c)
        for r, row in enumerate(matrix)
        for c, value in enumerate(row)
        if value == "?"
    ]

    if not unknowns:
        return [_actual_state_from_matrix(matrix)]

    variants = [copy.deepcopy(matrix)]

    # Giới hạn để không nổ 2^n quá lớn.
    for r, c in unknowns[:MAX_UNKNOWN_CELLS]:
        new_variants = []

        for variant in variants:
            as_wall = copy.deepcopy(variant)
            as_wall[r][c] = "#"
            new_variants.append(as_wall)

            as_floor = copy.deepcopy(variant)
            as_floor[r][c] = " "
            new_variants.append(as_floor)

        variants = new_variants

    return [Solve(_replace_unknowns(variant, " ")) for variant in variants]


def _sensorless_initial_belief_variants(matrix):
    """Belief-state cho No Observation.

    Agent biết layout và goal, nhưng không biết chính xác trạng thái ban đầu
    của các object bị che trên giao diện. Với radius 0, belief chỉ dùng đúng
    các ô đang được blind_box che để không lệch khỏi phần UI đang minh họa.
    """
    clean = _replace_unknowns(matrix, " ")
    worker = None
    boxes = []
    docks = set()

    for row, cells in enumerate(clean):
        for col, value in enumerate(cells):
            if value in {".", "*"}:
                docks.add((row, col))
            if value == "@":
                worker = (row, col)
            elif value in {"$", "*"}:
                boxes.append((row, col))

    if worker is None or not boxes:
        return [_actual_state_from_matrix(matrix)]

    base = copy.deepcopy(clean)
    hidden_positions = [worker] + boxes
    for row, col in hidden_positions:
        base[row][col] = "." if (row, col) in docks else " "

    candidates = _sensorless_candidate_cells(base, hidden_positions)
    worlds = []
    seen = set()

    def add_world(worker_pos, box_positions):
        if worker_pos in box_positions:
            return

        world = copy.deepcopy(base)
        world[worker_pos[0]][worker_pos[1]] = "@"
        for box_pos in box_positions:
            symbol = "*" if box_pos in docks else "$"
            world[box_pos[0]][box_pos[1]] = symbol

        state = Solve(world)
        key = state_key(state)
        if key in seen:
            return
        seen.add(key)
        worlds.append(state)

    add_world(worker, tuple(boxes))

    for worker_pos in candidates:
        if len(worlds) >= MAX_SENSORLESS_WORLDS:
            break

        for box_positions in _limited_box_position_sets(candidates, len(boxes), worker_pos):
            add_world(worker_pos, box_positions)
            if len(worlds) >= MAX_SENSORLESS_WORLDS:
                break

    return worlds or [_actual_state_from_matrix(matrix)]


def _sensorless_safe_layout_belief_variants(matrix):
    """
    Fallback cho No Observation khi belief object bị che làm bài vô nghiệm.

    Vẫn tạo nhiều world belief-state, nhưng chỉ đặt '?' vào các ô layout
    không thể đi tới từ worker trong map thật. Các world này khác nhau về
    wall/floor ở vùng không ảnh hưởng tới plan, nên có thể tồn tại một
    conformant plan chung để minh họa đúng đầu ra của sensorless planning.
    """
    base = _replace_unknowns(matrix, " ")
    reachable = _layout_reachable_cells(base)
    candidate_cells = []

    for row, cells in enumerate(base):
        for col, value in enumerate(cells):
            if value != " ":
                continue
            if (row, col) in reachable:
                continue
            candidate_cells.append((row, col))

    if not candidate_cells:
        return [_actual_state_from_matrix(matrix)]

    candidate_cells.sort(key=lambda pos: (
        pos[0] not in {0, len(base) - 1},
        pos[0],
        pos[1],
    ))

    world_map = copy.deepcopy(base)
    for row, col in candidate_cells[:MAX_SENSORLESS_SAFE_UNKNOWNS]:
        world_map[row][col] = "?"

    return _belief_variants(world_map)


def _layout_reachable_cells(matrix):
    worker = None

    for row, cells in enumerate(matrix):
        for col, value in enumerate(cells):
            if value in {"@", "+"}:
                worker = (row, col)
                break
        if worker is not None:
            break

    if worker is None:
        return set()

    reachable = {worker}
    queue = deque([worker])

    while queue:
        row, col = queue.popleft()

        for dr, dc in MOVE_DELTAS.values():
            nr, nc = row + dr, col + dc
            if nr < 0 or nr >= len(matrix) or nc < 0 or nc >= len(matrix[nr]):
                continue
            if (nr, nc) in reachable:
                continue
            if matrix[nr][nc] == "#":
                continue
            reachable.add((nr, nc))
            queue.append((nr, nc))

    return reachable


def _sensorless_candidate_cells(base, hidden_positions):
    candidates = set(hidden_positions)

    for center_row, center_col in hidden_positions:
        for row in range(center_row - SENSORLESS_OBJECT_RADIUS,
                         center_row + SENSORLESS_OBJECT_RADIUS + 1):
            for col in range(center_col - SENSORLESS_OBJECT_RADIUS,
                             center_col + SENSORLESS_OBJECT_RADIUS + 1):
                if row < 0 or row >= len(base) or col < 0 or col >= len(base[row]):
                    continue
                if abs(row - center_row) + abs(col - center_col) > SENSORLESS_OBJECT_RADIUS:
                    continue
                if base[row][col] in {" ", "."}:
                    candidates.add((row, col))

    def score(position):
        return min(
            abs(position[0] - row) + abs(position[1] - col)
            for row, col in hidden_positions
        )

    return sorted(candidates, key=lambda pos: (score(pos), pos[0], pos[1]))


def _limited_box_position_sets(candidates, box_count, worker_pos):
    available = [pos for pos in candidates if pos != worker_pos]

    if box_count <= 0:
        return [tuple()]

    result = []

    def backtrack(start, chosen):
        if len(result) >= MAX_SENSORLESS_WORLDS:
            return
        if len(chosen) == box_count:
            result.append(tuple(chosen))
            return

        for index in range(start, len(available)):
            chosen.append(available[index])
            backtrack(index + 1, chosen)
            chosen.pop()

    backtrack(0, [])
    return result


def _belief_key(states):
    return tuple(sorted(state_key(state) for state in states))


def _dedupe_belief_states(states):
    result = []
    seen = set()

    for state in states:
        key = state_key(state)
        if key in seen:
            continue
        seen.add(key)
        result.append(state)

    return result


def _belief_successors(states, action, require_all):
    next_states = []

    for state in states:
        child = _safe_child(state, action)
        if child is None:
            if require_all:
                return []
            continue
        next_states.append(child)

    return _dedupe_belief_states(next_states)


def _belief_heuristic(states):
    if not states:
        return 0
    # No Observation phải an toàn với tình huống xấu nhất nên dùng max.
    return max(heuristic(state) for state in states)


def _ordered_belief_actions(states, require_all=True):
    """
    Sắp action theo trung bình heuristic trên các belief-state.

    require_all=True:
        dùng cho conformant/no-observation, action phải hợp lệ ở mọi world.

    require_all=False:
        dùng cho partial-observation online, action có thể là hành động khám phá;
        những world mà action không khớp sẽ bị loại sau khi quan sát action outcome.
    """
    scores = []

    for action, _delta in MOVE_DELTAS.items():
        total = 0
        count = 0
        failed = 0
        observations = set()

        for state in states:
            child = _safe_child(state, action)
            if child is None:
                failed += 1
                if require_all:
                    break
                continue
            total += heuristic(child)
            count += 1
            observations.add(_local_observation(child, radius=1))

        if count == 0:
            continue

        if require_all and failed:
            continue

        avg_h = total / count
        # Partial observation thích action vừa tiến tới goal vừa có khả năng
        # tạo percept khác nhau để giảm uncertainty.
        info_bonus = 0 if require_all else len(observations)
        failure_penalty = failed / max(len(states), 1)
        scores.append((avg_h + failure_penalty - 0.25 * info_bonus, action))

    scores.sort(key=lambda item: item[0])
    return [action for _score, action in scores]


def _choose_partial_exploration_action(belief_states, real_state, observe_radius):
    candidates = []

    for action in _ordered_belief_actions(belief_states, require_all=False):
        real_child = _safe_child(real_state, action)
        if real_child is None:
            continue

        possible_children = _belief_successors(
            belief_states,
            action,
            require_all=False,
        )
        if not possible_children:
            continue

        observation_classes = {
            _local_observation(child, observe_radius)
            for child in possible_children
        }
        avg_h = sum(heuristic(child) for child in possible_children) / len(possible_children)
        score = (
            avg_h
            + 0.10 * len(possible_children)
            - 0.40 * len(observation_classes)
        )
        candidates.append((score, action))

    if not candidates:
        return None

    candidates.sort(key=lambda item: item[0])
    return candidates[0][1]


def _filter_by_real_observation(states, real_state, radius):
    observed = _local_observation(real_state, radius)
    return [state for state in states if _local_observation(state, radius) == observed]


def _local_observation(state, radius):
    worker = state.workerPosition()
    if worker is None:
        return ()

    wr, wc = worker
    matrix = state.getMatrix()
    obs = []

    for r in range(wr - radius, wr + radius + 1):
        for c in range(wc - radius, wc + radius + 1):
            if r < 0 or r >= len(matrix) or c < 0 or c >= len(matrix[r]):
                value = "#"
            else:
                value = matrix[r][c]
            obs.append((r - wr, c - wc, value))

    return tuple(obs)


# ============================================================
# BACKTRACKING SEARCH
# ============================================================

def backtracking_search(game, max_nodes=MAX_PATH_NODES, max_depth=350):
    """
    Backtracking trên không gian trạng thái Sokoban.

    Pseudocode:
        function BACKTRACK(state):
            if state is goal then return path
            mark state as visited
            for each action in ACTIONS(state) do
                child ← RESULT(state, action)
                if child not visited and not deadlock then
                    result ← BACKTRACK(child)
                    if result != failure then return result
            return failure
    """
    print("Processing BACKTRACKING SEARCH......")

    start_time = time.time()
    start_state = _actual_state_from_game(game)
    node_generated = 1
    visited = set()
    stop_reason = None

    if start_state.isComplete():
        return _success_result(
            "Backtracking",
            start_time,
            node_generated,
            start_state.pathSolution,
            algorithm_steps=node_generated,
            note="x = số node backtracking; b = số bước animation.",
        )

    if isDeadlock(start_state):
        reason = "Trạng thái ban đầu đã rơi vào deadlock."
        print("Backtracking failed:", reason)
        return _failure_result(
            "Backtracking", reason, start_state, node_generated, start_time)

    def solve(state, depth):
        """BACKTRACK(state) — returns a path string or failure."""
        nonlocal node_generated, stop_reason

        if state.isComplete():
            return state.pathSolution

        if node_generated >= max_nodes:
            stop_reason = f"Backtracking đạt giới hạn {max_nodes} node."
            return "failure"

        if depth >= max_depth:
            stop_reason = f"Backtracking đạt giới hạn độ sâu {max_depth}."
            return "failure"

        visited.add(state_key(state))

        for step in validMove(state):
            node_generated += 1
            if node_generated >= max_nodes:
                stop_reason = f"Backtracking đạt giới hạn {max_nodes} node."
                return "failure"

            child = _safe_child(state, step)
            if child is None:
                continue

            child_key = state_key(child)

            if child_key in visited:
                continue

            result = solve(child, depth + 1)
            if result != "failure":
                return result

        return "failure"

    solution = solve(start_state, 0)

    if solution != "failure":
        return _success_result(
            "Backtracking",
            start_time,
            node_generated,
            solution,
            algorithm_steps=node_generated,
            note="x = số node backtracking; b = số bước animation.",
        )

    reason = stop_reason or "Backtracking đã thử hết nhánh hợp lệ nhưng không tìm được lời giải."

    print("Backtracking failed:", reason)
    return _failure_result(
        "Backtracking",
        reason,
        start_state,
        node_generated,
        start_time,
        failed_step=max(node_generated, 1),
    )


# ============================================================
# MIN-CONFLICTS
# ============================================================

def min_conflict_search(game, max_steps=1000):
    """
    Min-Conflicts CSP.

    Pseudocode:
        function MIN-CONFLICTS(csp, max_steps) returns a solution or failure
        inputs: csp, a constraint satisfaction problem
        max_steps, the number of steps allowed before giving up

        current ← an initial complete assignment for csp
        for i = 1 to max_steps do
            if current is a solution for csp then return current
            var ← a randomly chosen conflicted variable from csp.VARIABLES
            value ← the value v for var that minimizes CONFLICTS(var, v, current, csp)
            set var = value in current
        return failure
    """
    print("Processing MIN-CONFLICTS CSP SEARCH......")

    start_time = time.time()
    real_game = _actual_state_from_game(game)
    csp = _build_box_dock_csp(real_game)

    if csp is None:
        reason = "Số box và số dock không khớp nên không tạo được CSP."
        return _failure_result("Min-Conflicts", reason, real_game, 0, start_time)

    rng = random.Random(7)
    variables = csp["variables"]

    if not variables:
        return _success_result("Min-Conflicts", start_time, 0, "", algorithm_steps=0)

    if any(not csp["domains"].get(var) for var in variables):
        reason = "Có ít nhất một biến CSP có miền giá trị rỗng."
        return _failure_result("Min-Conflicts", reason, real_game, 0, start_time)

    # current ← an initial complete assignment for csp
    current = {var: rng.choice(csp["domains"][var]) for var in variables}
    conflict_steps = 0

    # for i = 1 to max_steps do
    for i in range(1, max_steps + 1):
        conflict_steps = i

        # if current is a solution for csp then return current
        if _is_csp_solution(csp, current):
            solution, path_nodes = _constraint_guided_search(
                real_game,
                assignment=current,
                strategy="min_conflict",
                max_nodes=MAX_PATH_NODES,
                rng_seed=i + 17,
            )

            if solution == "NoSol":
                solution, extra_nodes = _constraint_guided_search(
                    real_game,
                    assignment=current,
                    strategy="astar",
                    max_nodes=MAX_PATH_NODES,
                    rng_seed=i + 17,
                )
                path_nodes += extra_nodes

            total_work = conflict_steps + path_nodes

            if solution != "NoSol":
                return _success_result(
                    "Min-Conflicts",
                    start_time,
                    total_work,
                    solution,
                    algorithm_steps=total_work,
                    note="x = số bước sửa conflict + số node randomized search; b = số bước animation.",
                )

            reason = "Min-Conflicts có assignment hợp lệ nhưng path search không tìm được lời giải Sokoban."
            return _failure_result("Min-Conflicts", reason, real_game, total_work, start_time)

        # var ← a randomly chosen conflicted variable from csp.VARIABLES
        conflicted = _conflicted_variables(csp, current)
        var = rng.choice(conflicted)

        # value ← the value v for var that minimizes CONFLICTS(var, v, current, csp)
        value = min(
            csp["domains"][var],
            key=lambda v: _count_conflicts(csp, var, v, current),
        )

        # set var = value in current
        current[var] = value

    # return failure
    reason = "Min-Conflicts đạt max_steps nhưng chưa có assignment CSP nhất quán."
    print("Min-Conflicts reached max_steps without a consistent assignment.")
    return _failure_result(
        "Min-Conflicts",
        reason,
        real_game,
        conflict_steps,
        start_time,
        failed_step=max(conflict_steps, 1),
    )


# ============================================================
# AC-3
# ============================================================

def ac3_search(game):
    """
    AC-3 CSP.

    Khác Backtracking / Min-Conflicts:
    - Lan truyền ràng buộc arc consistency trước.
    - Sau đó dùng A* với miền đã rút gọn.
    """
    print("Processing AC-3 CSP SEARCH......")

    start_time = time.time()
    real_game = _actual_state_from_game(game)
    csp = _build_box_dock_csp(real_game)

    if csp is None:
        reason = "Số box và số dock không khớp nên không tạo được CSP."
        return _failure_result("AC-3", reason, real_game, 0, start_time)

    ac3_ok, arc_checks = _ac3(csp)

    if not ac3_ok:
        reason = "AC-3 phát hiện miền giá trị bị rỗng sau khi revise."
        print("AC-3 detected inconsistent domains.")
        return _failure_result(
            "AC-3",
            reason,
            real_game,
            arc_checks,
            start_time,
            failed_step=max(arc_checks, 1),
        )

    assignment = _domains_to_assignment(csp)

    solution, path_nodes = _constraint_guided_search(
        real_game,
        assignment=assignment,
        strategy="astar",
        max_nodes=MAX_PATH_NODES,
    )

    total_work = arc_checks + path_nodes

    if solution != "NoSol":
        return _success_result(
            "AC-3",
            start_time,
            total_work,
            solution,
            algorithm_steps=total_work,
            note="x = số cung AC-3 kiểm tra + số node A* sau khi rút gọn miền; b = số bước animation.",
        )

    reason = "AC-3 rút gọn miền thành công nhưng path search không tìm được lời giải Sokoban."
    return _failure_result("AC-3", reason, real_game, total_work, start_time)


# ============================================================
# CSP HELPERS
# ============================================================

def _build_box_dock_csp(game):
    boxes = list(game.boxPosition())
    docks = list(game.dockPosition())

    if len(boxes) != len(docks):
        return None

    matrix = game.getMatrix()

    domains = {}
    for box in boxes:
        domain = []
        for dock in docks:
            if _static_path_exists(matrix, box, dock):
                domain.append(dock)

        # Nếu static path quá chặt làm rỗng miền, cho phép toàn bộ dock để thuật toán CSP còn chạy.
        if not domain:
            domain = list(docks)

        domains[box] = domain

    return {
        "variables": boxes,
        "domains": domains,
        "docks": docks,
        "matrix": matrix,
    }


def _select_unassigned_variable(assignment, csp):
    """SELECT-UNASSIGNED-VARIABLE(assignment, csp) — MRV heuristic."""
    unassigned = [var for var in csp["variables"] if var not in assignment]
    return min(unassigned, key=lambda var: len(csp["domains"].get(var, [])))


def _order_domain_values(var, assignment, csp):
    """ORDER-DOMAIN-VALUES(var, assignment, csp) — LCV: ưu tiên dock chưa dùng và gần."""
    values = list(csp["domains"].get(var, []))
    return sorted(
        values,
        key=lambda dock: (
            dock in assignment.values(),
            _distance(var, dock),
        ),
    )


def _consistent(var, value, assignment, csp):
    """CONSISTENT(var, value, assignment, csp) — value chưa được gán và nằm trong domain."""
    if value in assignment.values():
        return False
    return value in csp["domains"].get(var, [])


def _is_csp_solution(csp, assignment):
    if len(assignment) != len(csp["variables"]):
        return False

    used = set()

    for var, value in assignment.items():
        if value not in csp["domains"].get(var, []):
            return False

        if value in used:
            return False

        used.add(value)

    return True


def _conflicted_variables(csp, assignment):
    result = []

    for var, value in assignment.items():
        if _count_conflicts(csp, var, value, assignment) > 0:
            result.append(var)

    return result


def _count_conflicts(csp, var, value, assignment):
    conflicts = 0

    if value not in csp["domains"].get(var, []):
        conflicts += 1

    for other, other_value in assignment.items():
        if other == var:
            continue

        if other_value == value:
            conflicts += 1

    return conflicts


def _ac3(csp):
    """
    AC-3 algorithm — returns the CSP, possibly with reduced domains.

    Pseudocode:
        function AC-3(csp) returns the CSP, possibly with reduced domains
        inputs: csp, a binary CSP with variables {X1, X2, ..., Xn}
        local variables: queue, a queue of arcs, initially all the arcs in csp

        while queue is not empty do
            (Xi, Xj) ← REMOVE-FIRST(queue)
            if RM-INCONSISTENT-VALUES(Xi, Xj) then
                for each Xk in NEIGHBORS[Xi] do
                    add (Xk, Xi) to queue
    """
    variables = csp["variables"]

    # NEIGHBORS[Xi] — every variable that shares a constraint with Xi
    neighbors = {xi: [xj for xj in variables if xj != xi] for xi in variables}

    # Queue ← all arcs in csp
    queue = deque()
    for xi in variables:
        for xj in neighbors[xi]:
            queue.append((xi, xj))

    arc_checks = 0

    while queue:
        xi, xj = queue.popleft()               # REMOVE-FIRST(queue)
        arc_checks += 1

        if _revise(csp, xi, xj):                # RM-INCONSISTENT-VALUES
            if not csp["domains"][xi]:
                return False, arc_checks

            for xk in neighbors[xi]:            # for each Xk in NEIGHBORS[Xi]
                queue.append((xk, xi))           # add (Xk, Xi) to queue

    return True, arc_checks


def _revise(csp, xi, xj):
    """
    RM-INCONSISTENT-VALUES(Xi, Xj) — returns true iff we remove a value.

    Pseudocode:
        removed ← false
        for each x in DOMAIN[Xi] do
            if no value y in DOMAIN[Xj] allows (x,y) to satisfy constraint(Xi, Xj)
            then delete x from DOMAIN[Xi]; removed ← true
        return removed
    """
    removed = False

    for x in list(csp["domains"][xi]):
        # Kiểm tra: có tồn tại y trong DOMAIN[Xj] để (x,y) thoả constraint?
        # Constraint: hai box không được chọn cùng một dock → x != y
        if not any(x != y for y in csp["domains"][xj]):
            csp["domains"][xi].remove(x)
            removed = True

    return removed


def _domains_to_assignment(csp):
    assignment = {}
    used = set()

    for var in sorted(csp["variables"], key=lambda item: len(csp["domains"][item])):
        values = sorted(
            csp["domains"][var],
            key=lambda dock: (
                dock in used,
                _distance(var, dock),
            ),
        )

        for value in values:
            if value not in used:
                assignment[var] = value
                used.add(value)
                break

        if var not in assignment and values:
            assignment[var] = values[0]

    return assignment


# ============================================================
# PATH SEARCH AFTER CSP / SHARED PATH ENGINE
# ============================================================

def _constraint_guided_search(game_or_state, assignment=None, strategy="astar", max_nodes=MAX_PATH_NODES, rng_seed=0):
    """
    Tìm path Sokoban sau khi có assignment CSP.

    strategy:
    - astar: dùng cho AC-3, thường tối ưu hơn;
    - greedy: dùng fallback;
    - dfs: dùng cho Backtracking để thể hiện bản chất quay lui;
    - min_conflict: dùng randomized greedy để khác Backtracking/AC-3.
    """
    start = copy.deepcopy(game_or_state)

    if strategy == "dfs":
        return _dfs_path_search(start, assignment, max_nodes)

    return _priority_path_search(start, assignment, strategy, max_nodes, rng_seed)


def _priority_path_search(start, assignment, strategy, max_nodes, rng_seed):
    rng = random.Random(rng_seed)
    open_list = []
    counter = 0
    node_generated = 1
    best_g = {state_key(start): 0}

    first_priority = _path_priority(start, assignment, strategy, 0, rng)
    heapq.heappush(open_list, (first_priority, 0, counter, start))

    while open_list and node_generated < max_nodes:
        _, g_cost, _, state = heapq.heappop(open_list)

        if g_cost != best_g.get(state_key(state)):
            continue

        if state.isComplete():
            return state.pathSolution, node_generated

        for step in _ordered_steps(state, assignment, strategy, rng):
            child = _safe_child(state, step)
            if child is None:
                continue

            node_generated += 1
            key = state_key(child)
            new_g = g_cost + 1

            if new_g >= best_g.get(key, float("inf")):
                continue

            best_g[key] = new_g
            counter += 1
            priority = _path_priority(child, assignment, strategy, new_g, rng)

            heapq.heappush(open_list, (priority, new_g, counter, child))

    return "NoSol", node_generated


def _dfs_path_search(start, assignment, max_nodes):
    stack = [(start, 0)]
    best_depth = {state_key(start): 0}
    node_generated = 1

    while stack and node_generated < max_nodes:
        state, depth = stack.pop()

        if state.isComplete():
            return state.pathSolution, node_generated

        # DFS cố ý đảo thứ tự khác A* để biểu đồ/path không bị đồng nhất.
        steps = _ordered_steps(state, assignment, strategy="dfs")
        steps = list(reversed(steps))

        for step in steps:
            child = _safe_child(state, step)
            if child is None:
                continue

            node_generated += 1
            key = state_key(child)
            new_depth = depth + 1

            if new_depth >= best_depth.get(key, float("inf")):
                continue

            best_depth[key] = new_depth
            stack.append((child, new_depth))

    return "NoSol", node_generated


def _ordered_steps(state, assignment=None, strategy="astar", rng=None):
    candidates = []

    for step in validMove(state):
        child = _safe_child(state, step)
        if child is None:
            continue

        score = _assignment_heuristic(child, assignment)

        if strategy == "and_or":
            score = heuristic(child)

        elif strategy == "dfs":
            # DFS/backtracking: ưu tiên theo thứ tự khác greedy.
            score = -score

        elif strategy == "greedy":
            score = score

        elif strategy == "min_conflict":
            # Randomized greedy: vẫn hướng goal nhưng có nhiễu nhỏ.
            noise = rng.random() if rng is not None else random.random()
            score = score + 0.35 * noise

        elif strategy == "astar":
            score = score

        candidates.append((score, step))

    candidates.sort(key=lambda item: item[0])
    return [step for _score, step in candidates]


def _path_priority(state, assignment, strategy, g_cost, rng):
    h = _assignment_heuristic(state, assignment)

    if strategy == "greedy":
        return h

    if strategy == "min_conflict":
        return h + 0.50 * rng.random() + 0.20 * g_cost

    # AC-3 dùng A* rõ ràng hơn.
    return g_cost + h


def _assignment_heuristic(state, assignment):
    base = heuristic(state)

    if not assignment:
        return base

    boxes = list(state.boxPosition())
    if not boxes:
        return 0

    assigned_docks = list(assignment.values())
    if not assigned_docks:
        return base

    total = 0

    for box in boxes:
        total += min(_distance(box, dock) for dock in assigned_docks)

    return base + total


# ============================================================
# STATIC REACHABILITY HELPERS
# ============================================================

def _static_path_exists(matrix, start, target):
    """
    Kiểm tra đường tĩnh giữa box và dock, bỏ qua worker.
    Đây là kiểm tra nhẹ để tạo domain CSP, không thay thế path search thật.
    """
    clean_matrix = _replace_unknowns(matrix, " ")

    queue = deque([start])
    visited = {start}

    while queue:
        r, c = queue.popleft()

        if (r, c) == target:
            return True

        for dr, dc in MOVE_DELTAS.values():
            nr, nc = r + dr, c + dc

            if nr < 0 or nr >= len(clean_matrix):
                continue

            if nc < 0 or nc >= len(clean_matrix[nr]):
                continue

            if (nr, nc) in visited:
                continue

            if clean_matrix[nr][nc] in {"#", "E"}:
                continue

            visited.add((nr, nc))
            queue.append((nr, nc))

    return False


def _distance(first, second):
    return abs(first[0] - second[0]) + abs(first[1] - second[1])


# ============================================================
# COMPATIBILITY ALIASES FOR OLDER IMPORTS
# ============================================================

no_observation_search = search_with_no_observation
partial_observation_search = partially_observable_search
min_conflict = min_conflict_search
