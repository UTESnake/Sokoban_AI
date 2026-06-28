import copy
import heapq
import time

from algorithm.common import (
    MOVE_DELTAS,
    apply_step,
    heuristic,
    isDeadlock,
    state_key,
    validMove,
)


# ============================================================
# FAST ADVERSARIAL CONFIG
# ============================================================

# Giảm mạnh giới hạn để không làm treo giao diện Tkinter/PyQt.
MAX_PLAYER_BRANCH = 4
MAX_OPPONENT_BRANCH = 4
# Expectimax vẫn tính kỳ vọng trên mọi nước E; frontier chỉ giữ vài outcome
# đại diện để không nổ trạng thái khi tìm path replay.
MAX_EXPECTIMAX_OUTCOME_BRANCH = 2
MAX_EXPANDED_STATES = 1800
FALLBACK_MAX_NODES = 12000

# Mỗi lượt thật: MAX đi, sau đó MIN/CHANCE phản ứng và state sau E
# được đưa tiếp vào frontier cho lượt MAX kế tiếp.
LOOKAHEAD_DEPTH = 1
EXPECTIMINIMAX_DEPTH = 2

# Chặn thời gian cho mỗi thuật toán. Nếu gần quá giới hạn, chuyển sang fallback A* nhanh.
TIME_LIMIT_SECONDS = 4.5

# Minimax / Alpha-Beta thận trọng hơn vì xem E là đối thủ.
MINIMAX_RISK_WEIGHT = 1.15

# Expectimax bớt thận trọng hơn vì xem E là biến ngẫu nhiên.
EXPECTIMAX_RISK_WEIGHT = 0.28


_STATS = {
    "game_nodes": 0,
    "pruned_nodes": 0,
    "chance_nodes": 0,
}


def _reset_stats():
    _STATS["game_nodes"] = 0
    _STATS["pruned_nodes"] = 0
    _STATS["chance_nodes"] = 0


# ============================================================
# PUBLIC API
# ============================================================

def minimax(game):
    """
    MINIMAX adversarial search.

    MAX: người chơi.
    MIN: đối thủ E.
    MIN luôn chọn hành động làm utility của MAX nhỏ nhất.

    Frontier lưu trạng thái sau lượt MIN, nên cây đi luân phiên MAX -> MIN -> MAX.
    """
    print("Processing MINIMAX adversarial game tree......")
    return _adversarial_path_search(game, label="Minimax", mode="minimax")


def alpha_beta(game):
    """
    ALPHA-BETA adversarial search.

    Cùng giá trị quyết định với Minimax nhưng dùng alpha cutoff khi chấm action.
    Do đó path có thể giống Minimax; khác biệt chính là số node và số nhánh bị cắt.
    """
    print("Processing ALPHA-BETA adversarial game tree......")
    return _adversarial_path_search(game, label="Alpha-Beta", mode="alpha_beta")


def expectimax(game):
    """
    EXPECTIMINIMAX / EXPECTIMAX search.

    MAX: người chơi, chọn giá trị lớn nhất.
    MIN: đối thủ E, chọn giá trị nhỏ nhất.
    CHANCE: outcome ngẫu nhiên của hành động E, lấy trung bình có trọng số.
    """
    print("Processing EXPECTIMINIMAX chance game tree......")
    return _adversarial_path_search(game, label="Expectimax", mode="expectimax")


# ============================================================
# OUTER PATH SEARCH
# ============================================================

def _adversarial_path_search(game, label, mode):
    """
    Tìm path thật để GUI replay được.

    Mỗi successor trong frontier là trạng thái sau một lượt đầy đủ:
    MAX đi một bước, rồi MIN/CHANCE phản ứng bằng cách di chuyển E.
    pathSolution vẫn chỉ lưu bước của MAX để GUI replay được.

    Guard giữ UI không bị treo:
    - Cây minimax/expectimax chỉ lookahead hữu hạn.
    - Có giới hạn thời gian, nếu quá lâu thì fallback sang A* an toàn.
    """

    _reset_stats()

    start_time = time.time()
    start_state = copy.deepcopy(game)

    node_generated = 1
    expanded_states = 0
    counter = 0

    if isDeadlock(start_state):
        reason = "Trạng thái ban đầu đã rơi vào deadlock."
        print(f"{label} failed:", reason)
        return _failure_result(label, reason, start_state, node_generated, start_time)

    open_list = []
    best_g = {state_key(start_state): 0}

    first_priority = _frontier_priority(start_state, g_cost=0, mode=mode, value=0)
    heapq.heappush(open_list, (first_priority, 0, counter, start_state))

    while open_list and expanded_states < MAX_EXPANDED_STATES:
        if time.time() - start_time > TIME_LIMIT_SECONDS:
            print(f"{label}: gần quá giới hạn thời gian, chuyển sang fallback A* nhanh.")
            return _fallback_result(
                label=label,
                start_state=start_state,
                node_generated=node_generated,
                expanded_states=expanded_states,
                start_time=start_time,
                reason="Đã chuyển sang fallback để tránh treo giao diện.",
            )

        _, g_cost, _, current = heapq.heappop(open_list)

        current_key = state_key(current)
        if g_cost != best_g.get(current_key):
            continue

        expanded_states += 1

        if current.isComplete():
            _print_solution(label, start_time, node_generated, current.pathSolution)
            return _success_result(
                label=label,
                path=current.pathSolution,
                node_generated=node_generated,
                expanded_states=expanded_states,
                start_time=start_time,
            )

        action_scores = []
        alpha_hint = float("-inf")

        for action in _ordered_player_actions(current, mode=mode):
            turn_result = _adversarial_turn_successors(
                current,
                action,
                mode=mode,
                depth=LOOKAHEAD_DEPTH,
                alpha_hint=alpha_hint,
            )

            if turn_result is None:
                continue

            value, successors, player_child, generated = turn_result
            node_generated += generated

            if player_child.isComplete():
                _print_solution(label, start_time, node_generated, player_child.pathSolution)
                return _success_result(
                    label=label,
                    path=player_child.pathSolution,
                    node_generated=node_generated,
                    expanded_states=expanded_states,
                    start_time=start_time,
                )

            if mode == "alpha_beta":
                alpha_hint = max(alpha_hint, value)

            action_scores.append((value, action, successors))

        action_scores.sort(key=lambda item: item[0], reverse=True)

        for value, _action, successors in action_scores[:MAX_PLAYER_BRANCH]:
            for successor in successors:
                key = state_key(successor)
                new_g = len(successor.pathSolution)

                if new_g >= best_g.get(key, float("inf")):
                    continue

                best_g[key] = new_g
                counter += 1
                priority = _frontier_priority(
                    successor, g_cost=new_g, mode=mode, value=value)
                heapq.heappush(open_list, (priority, new_g, counter, successor))

    if open_list:
        return _fallback_result(
            label=label,
            start_state=start_state,
            node_generated=node_generated,
            expanded_states=expanded_states,
            start_time=start_time,
            reason="Vượt giới hạn trạng thái của tìm kiếm đối kháng.",
        )

    reason = "Frontier rỗng, thuật toán chưa tìm được lời giải."
    print(f"{label} could not find a solution.")
    return _failure_result(label, reason, None, node_generated, start_time)


def _frontier_priority(state, g_cost, mode, value):
    """
    heapq lấy priority nhỏ trước.

    Minimax/Alpha-Beta:
    - phạt threat lớn hơn để né E.

    Expectimax:
    - phạt threat nhẹ hơn để có thể chọn đường ngắn hơn.
    """

    if mode == "expectimax":
        risk = EXPECTIMAX_RISK_WEIGHT
        return g_cost + heuristic(state) + risk * _opponent_threat_score(state) - 0.04 * value

    risk = MINIMAX_RISK_WEIGHT
    return g_cost + heuristic(state) + risk * _opponent_threat_score(state) - 0.03 * value


def _adversarial_turn_successors(state, action, mode, depth, alpha_hint=float("-inf")):
    """
    RESULT của một lượt thật trong game đối kháng.

    1. MAX chọn action và tạo player_child.
    2. MIN/CHANCE phản ứng bằng cách di chuyển E.
    3. Trả các state sau lượt E để frontier tiếp tục từ lượt MAX kế tiếp.
    """
    player_child = _player_result(state, action)

    if player_child is None:
        return None

    if player_child.isComplete():
        return (
            _utility(player_child, risk_weight=_risk_weight_for_mode(mode)),
            [player_child],
            player_child,
            1,
        )

    if mode == "minimax":
        value, opponent_action = _min_value_minimax(player_child, depth)
        successors = [_commit_opponent_action(player_child, opponent_action)]

    elif mode == "alpha_beta":
        value, opponent_action = _min_value_alpha_beta(
            player_child, depth, alpha_hint, float("inf"))
        successors = [_commit_opponent_action(player_child, opponent_action)]

    else:
        value, opponent_action = _expectiminimax_value(
            player_child,
            max(depth, EXPECTIMINIMAX_DEPTH),
            node_type="min",
        )
        value += 0.35 * _progress_bonus(state, player_child)
        successors = _opponent_chance_successors(player_child, opponent_action)

    successors = _unique_successors(successors)
    return value, successors, player_child, 1 + len(successors)


def _commit_opponent_action(state, action):
    if action is None:
        return state

    child = _opponent_result(state, action)
    if child is None:
        return state

    return child


def _chance_opponent_successors(state):
    successors = []

    for action in _chance_opponent_actions(state):
        child = _opponent_result(state, action)
        if child is not None:
            successors.append(child)

    if not successors:
        successors.append(state)

    successors = _unique_successors(successors)
    successors.sort(
        key=lambda child: (
            heuristic(child)
            + EXPECTIMAX_RISK_WEIGHT * _opponent_threat_score(child)
        )
    )
    return successors[:MAX_EXPECTIMAX_OUTCOME_BRANCH]


def _opponent_chance_outcomes(state, action):
    """Các outcome ngẫu nhiên của một action E đã được MIN chọn.

    Mô hình:
    - action thành công: 0.8
    - E đứng yên/trượt action: 0.2

    Nếu action là stay hoặc không hợp lệ thì state hiện tại có xác suất 1.0.
    """
    if action is None or action == "S":
        return [(1.0, copy.deepcopy(state))]

    intended = _opponent_result(state, action)
    if intended is None:
        return [(1.0, copy.deepcopy(state))]

    raw = [
        (0.8, intended),
        (0.2, copy.deepcopy(state)),
    ]
    return _merge_probability_outcomes(raw)


def _opponent_chance_successors(state, action):
    outcomes = _opponent_chance_outcomes(state, action)
    outcomes.sort(key=lambda item: item[0], reverse=True)
    return [child for _probability, child in outcomes[:MAX_EXPECTIMAX_OUTCOME_BRANCH]]


def _merge_probability_outcomes(outcomes):
    merged = {}
    states = {}

    for probability, child in outcomes:
        key = state_key(child)
        merged[key] = merged.get(key, 0.0) + probability
        states[key] = child

    total = sum(merged.values())
    if total <= 0:
        return []

    return [
        (probability / total, states[key])
        for key, probability in merged.items()
    ]


def _unique_successors(states):
    unique = []
    seen = set()

    for state in states:
        key = state_key(state)
        if key in seen:
            continue
        seen.add(key)
        unique.append(state)

    return unique


def _risk_weight_for_mode(mode):
    if mode == "expectimax":
        return EXPECTIMAX_RISK_WEIGHT
    return MINIMAX_RISK_WEIGHT


# ============================================================
# ACTION EVALUATION
# ============================================================

def _evaluate_action_minimax(state, action, depth):
    result = _adversarial_turn_successors(
        state, action, mode="minimax", depth=depth)
    if result is None:
        return float("-inf")

    value, _successors, _player_child, _generated = result
    return value


def _evaluate_action_alpha_beta(state, action, depth, alpha_hint):
    result = _adversarial_turn_successors(
        state, action, mode="alpha_beta", depth=depth, alpha_hint=alpha_hint)
    if result is None:
        return float("-inf")

    value, _successors, _player_child, _generated = result
    return value


def _evaluate_action_expectimax(state, action, depth):
    result = _adversarial_turn_successors(
        state, action, mode="expectimax", depth=depth)
    if result is None:
        return float("-inf")

    value, _successors, _player_child, _generated = result
    return value


def _progress_bonus(parent, child):
    delta = heuristic(parent) - heuristic(child)

    if delta > 3:
        return 3

    if delta < -3:
        return -3

    return delta


# ============================================================
# MINIMAX / ALPHA-BETA / EXPECTIMAX VALUES
# ============================================================

def _max_value_minimax(state, depth):
    """MAX player's turn.

    Pseudocode (isMaximizingPlayer = true):
        if depth == 0 or terminal: return evaluate(node)
        bestValue = -∞
        for each child in generateMoves(node):
            value = minimax(child, depth - 1, false)
            bestValue = max(bestValue, value)
        return bestValue
    """
    _STATS["game_nodes"] += 1

    if _is_terminal(state, depth):
        return _utility(state, risk_weight=MINIMAX_RISK_WEIGHT), None

    actions = _ordered_player_actions(state, mode="minimax")
    if not actions:
        return _utility(state, risk_weight=MINIMAX_RISK_WEIGHT), None

    value = float("-inf")
    best_move = None

    for action in actions:
        child = _player_result(state, action)
        if child is None:
            continue

        child_value, _ = _min_value_minimax(child, depth - 1)

        if child_value > value:
            value = child_value
            best_move = action

    if best_move is None:
        return _utility(state, risk_weight=MINIMAX_RISK_WEIGHT), None

    return value, best_move


def _min_value_minimax(state, depth):
    """MIN player's turn.

    Pseudocode (isMaximizingPlayer = false):
        if depth == 0 or terminal: return evaluate(node)
        bestValue = +∞
        for each child in generateMoves(node):
            value = minimax(child, depth - 1, true)
            bestValue = min(bestValue, value)
        return bestValue
    """
    _STATS["game_nodes"] += 1

    if _is_terminal(state, depth):
        return _utility(state, risk_weight=MINIMAX_RISK_WEIGHT), None

    actions = _ordered_opponent_actions(state)

    if not actions:
        return _utility(state, risk_weight=MINIMAX_RISK_WEIGHT), None

    value = float("inf")
    best_move = None

    for action in actions:
        child = _opponent_result(state, action)
        if child is None:
            continue

        child_value, _ = _max_value_minimax(child, depth - 1)

        if child_value < value:
            value = child_value
            best_move = action

    if best_move is None:
        return _utility(state, risk_weight=MINIMAX_RISK_WEIGHT), None

    return value, best_move


def _max_value_alpha_beta(state, depth, alpha, beta):
    """MAX player's turn.

    Pseudocode (maximizingPlayer = true):
        if depth == 0 or terminal: return evaluate(node)
        value := -∞
        for each child in generateMoves(node):
            value := max(value, alphaBeta(child, depth-1, alpha, beta, false))
            alpha := max(alpha, value)
            if alpha >= beta: break   // Beta cut-off
        return value
    """
    _STATS["game_nodes"] += 1

    if _is_terminal(state, depth):
        return _utility(state, risk_weight=MINIMAX_RISK_WEIGHT), None

    actions = _ordered_player_actions(state, mode="minimax")
    if not actions:
        return _utility(state, risk_weight=MINIMAX_RISK_WEIGHT), None

    value = float("-inf")
    best_move = None

    for index, action in enumerate(actions):
        child = _player_result(state, action)
        if child is None:
            continue

        child_value, _ = _min_value_alpha_beta(child, depth - 1, alpha, beta)

        if child_value > value:
            value = child_value
            best_move = action

        alpha = max(alpha, value)
        if alpha >= beta:
            _STATS["pruned_nodes"] += max(0, len(actions) - index - 1)
            break

    if best_move is None:
        return _utility(state, risk_weight=MINIMAX_RISK_WEIGHT), None

    return value, best_move


def _min_value_alpha_beta(state, depth, alpha, beta):
    """MIN player's turn.

    Pseudocode (maximizingPlayer = false):
        if depth == 0 or terminal: return evaluate(node)
        value := +∞
        for each child in generateMoves(node):
            value := min(value, alphaBeta(child, depth-1, alpha, beta, true))
            beta := min(beta, value)
            if beta <= alpha: break   // Alpha cut-off
        return value
    """
    _STATS["game_nodes"] += 1

    if _is_terminal(state, depth):
        return _utility(state, risk_weight=MINIMAX_RISK_WEIGHT), None

    actions = _ordered_opponent_actions(state)

    if not actions:
        return _utility(state, risk_weight=MINIMAX_RISK_WEIGHT), None

    value = float("inf")
    best_move = None

    for index, action in enumerate(actions):
        child = _opponent_result(state, action)
        if child is None:
            continue

        child_value, _ = _max_value_alpha_beta(child, depth - 1, alpha, beta)

        if child_value < value:
            value = child_value
            best_move = action

        beta = min(beta, value)
        if beta <= alpha:
            _STATS["pruned_nodes"] += max(0, len(actions) - index - 1)
            break

    if best_move is None:
        return _utility(state, risk_weight=MINIMAX_RISK_WEIGHT), None

    return value, best_move


def _expectiminimax_value(state, depth, node_type, pending_action=None):
    """EXPECTIMINIMAX(node, depth, node_type).

    - terminal/depth=0: trả utility heuristic của node.
    - MIN/opponent node: chọn child có giá trị nhỏ nhất.
    - MAX/player node: chọn child có giá trị lớn nhất.
    - CHANCE node: trả trung bình có trọng số của các outcome.
    """
    if _is_terminal(state, depth):
        return _utility(state, risk_weight=EXPECTIMAX_RISK_WEIGHT), None

    if node_type == "min":
        _STATS["game_nodes"] += 1
        actions = _ordered_opponent_actions(state)
        if not actions:
            return _utility(state, risk_weight=EXPECTIMAX_RISK_WEIGHT), None

        value = float("inf")
        best_move = None
        for action in actions:
            child_value, _ = _expectiminimax_value(
                state,
                depth - 1,
                node_type="chance",
                pending_action=action,
            )
            if child_value < value:
                value = child_value
                best_move = action

        if best_move is None:
            return _utility(state, risk_weight=EXPECTIMAX_RISK_WEIGHT), None
        return value, best_move

    if node_type == "max":
        _STATS["game_nodes"] += 1
        actions = _ordered_player_actions(state, mode="expectimax")
        if not actions:
            return _utility(state, risk_weight=EXPECTIMAX_RISK_WEIGHT), None

        value = float("-inf")
        best_move = None
        for action in actions:
            child = _player_result(state, action)
            if child is None:
                continue

            child_value, _ = _expectiminimax_value(
                child,
                depth - 1,
                node_type="min",
            )
            if child_value > value:
                value = child_value
                best_move = action

        if best_move is None:
            return _utility(state, risk_weight=EXPECTIMAX_RISK_WEIGHT), None
        return value, best_move

    if node_type == "chance":
        _STATS["chance_nodes"] += 1
        outcomes = _opponent_chance_outcomes(state, pending_action)
        if not outcomes:
            return _utility(state, risk_weight=EXPECTIMAX_RISK_WEIGHT), None

        expected_value = 0.0
        for probability, child in outcomes:
            child_value, _ = _expectiminimax_value(
                child,
                depth - 1,
                node_type="max",
            )
            expected_value += probability * child_value

        return expected_value, None

    return _utility(state, risk_weight=EXPECTIMAX_RISK_WEIGHT), None


def _max_value_expectimax(state, depth):
    return _expectiminimax_value(state, depth, node_type="max")


def _chance_value_expectimax(state, depth):
    return _expectiminimax_value(state, depth, node_type="chance")


# ============================================================
# TERMINAL / UTILITY
# ============================================================

def _is_terminal(state, depth):
    if depth <= 0:
        return True

    if state.isComplete():
        return True

    return not _has_player_action(state)


def _has_player_action(state):
    for action in validMove(state):
        if _player_result(state, action) is not None:
            return True

    return False


def _utility(state, risk_weight=1.0):
    """
    Utility cho MAX.

    MAX muốn:
    - hoàn thành map;
    - heuristic nhỏ;
    - ít bước;
    - tránh E.
    """

    if state.isComplete():
        return 10000 - len(state.pathSolution)

    return (
        -heuristic(state)
        - risk_weight * _opponent_threat_score(state)
        - 0.05 * len(state.pathSolution)
    )


def _opponent_threat_score(state):
    matrix = state.getMatrix()
    competitor = _competitor_position(matrix)
    worker = state.workerPosition()

    if competitor is None or worker is None:
        return 0

    score = 0

    # E gần người chơi.
    score += max(0, 7 - _manhattan(competitor, worker)) * 3

    # E gần box, dock, vị trí đứng đẩy box.
    for box in state.boxPosition():
        score += max(0, 6 - _manhattan(competitor, box)) * 3

        for stance in _push_stances(state, box):
            score += max(0, 5 - _manhattan(competitor, stance)) * 5

    for dock in state.dockPosition():
        score += max(0, 5 - _manhattan(competitor, dock)) * 2

    # E ở hành lang/cổ chai thì nguy hiểm hơn.
    if _walkable_neighbor_count(state, competitor) <= 2:
        score += 5

    return score


# ============================================================
# ACTIONS / RESULTS
# ============================================================

def _ordered_player_actions(state, mode="minimax"):
    actions = []

    for action in validMove(state):
        child = _player_result(state, action)

        if child is None:
            continue

        if mode == "expectimax":
            score = heuristic(child) + EXPECTIMAX_RISK_WEIGHT * _opponent_threat_score(child)
        else:
            score = heuristic(child) + MINIMAX_RISK_WEIGHT * _opponent_threat_score(child)

        actions.append((score, action))

    actions.sort(key=lambda item: item[0])
    return [action for _score, action in actions[:MAX_PLAYER_BRANCH]]


def _ordered_opponent_actions(state):
    """
    MIN actions.

    Với Minimax/Alpha-Beta, E ưu tiên các nước gây bất lợi cao cho MAX.
    """
    position = _competitor_position(state.getMatrix())

    if position is None:
        return []

    actions = [(0, "S")]

    for action, (dy, dx) in MOVE_DELTAS.items():
        next_position = position[0] + dy, position[1] + dx

        if _opponent_can_move_to(state, next_position):
            score = _opponent_action_score(state, next_position)
            actions.append((score, action))

    actions.sort(key=lambda item: item[0], reverse=True)
    return [action for _score, action in actions[:MAX_OPPONENT_BRANCH]]


def _chance_opponent_actions(state):
    """
    Chance actions cho Expectimax.

    Không sắp xếp theo hướng gây hại.
    Không giới hạn top nhánh nguy hiểm.
    """
    position = _competitor_position(state.getMatrix())

    if position is None:
        return []

    actions = ["S"]

    for action, (dy, dx) in MOVE_DELTAS.items():
        next_position = position[0] + dy, position[1] + dx

        if _opponent_can_move_to(state, next_position):
            actions.append(action)

    return actions


def _player_result(state, action):
    if action not in MOVE_DELTAS:
        return None

    if _player_action_hits_competitor(state, action):
        return None

    child = copy.deepcopy(state)
    apply_step(child, action)

    if isDeadlock(child):
        return None

    return child


def _opponent_result(state, action):
    child = copy.deepcopy(state)

    if action == "S":
        return child

    position = _competitor_position(child.getMatrix())

    if position is None:
        return child

    dy, dx = MOVE_DELTAS[action]
    next_position = (position[0] + dy, position[1] + dx)

    if not _opponent_can_move_to(child, next_position):
        return child

    _move_competitor(child, position, next_position)
    return child


def _player_action_hits_competitor(state, action):
    """
    Không cho người chơi:
    - đi vào E;
    - đẩy box vào E.
    """
    matrix = state.getMatrix()
    worker = state.workerPosition()

    if worker is None:
        return False

    dy, dx = MOVE_DELTAS[action]
    next_position = (worker[0] + dy, worker[1] + dx)
    next_cell = _matrix_value(matrix, next_position)

    if next_cell == "E":
        return True

    if next_cell in {"$", "*"}:
        box_destination = (next_position[0] + dy, next_position[1] + dx)

        if _matrix_value(matrix, box_destination) == "E":
            return True

    return False


def _opponent_can_move_to(state, position):
    """
    E chỉ đi vào ô trống thường.

    Không cho E đi vào '.', '$', '*', '@' để tránh phải xử lý ký hiệu E-on-goal.
    """
    return _matrix_value(state.getMatrix(), position) == " "


def _move_competitor(state, old_position, new_position):
    if old_position == new_position:
        return

    matrix = state.getMatrix()

    old_row, old_col = old_position
    new_row, new_col = new_position

    matrix[old_row][old_col] = " "
    matrix[new_row][new_col] = "E"


# ============================================================
# FALLBACK FAST A*
# ============================================================

def _fallback_result(label, start_state, node_generated, expanded_states, start_time, reason):
    path, fallback_nodes = _fast_astar(start_state)

    node_generated += fallback_nodes
    expanded_states += fallback_nodes

    if path != "NoSol":
        print(f"{label}: fallback thành công. {reason}")
        _print_solution(label, start_time, node_generated, path)
        return _success_result(
            label=label,
            path=path,
            node_generated=node_generated,
            expanded_states=expanded_states,
            start_time=start_time,
        )

    return _failure_result(label, reason, start_state, node_generated, start_time)


def _fast_astar(start_state):
    start = copy.deepcopy(start_state)

    open_list = []
    counter = 0
    node_generated = 1
    best_g = {state_key(start): 0}

    heapq.heappush(open_list, (heuristic(start), 0, counter, start))

    while open_list and node_generated < FALLBACK_MAX_NODES:
        _, g_cost, _, state = heapq.heappop(open_list)

        if g_cost != best_g.get(state_key(state)):
            continue

        if state.isComplete():
            return state.pathSolution, node_generated

        for action in validMove(state):
            child = _player_result(state, action)

            if child is None:
                continue

            node_generated += 1
            key = state_key(child)
            new_g = len(child.pathSolution)

            if new_g >= best_g.get(key, float("inf")):
                continue

            best_g[key] = new_g
            counter += 1
            priority = new_g + heuristic(child)
            heapq.heappush(open_list, (priority, new_g, counter, child))

    return "NoSol", node_generated


# ============================================================
# POSITION HELPERS
# ============================================================

def _competitor_position(matrix):
    for row, cells in enumerate(matrix):
        for col, value in enumerate(cells):
            if value == "E":
                return row, col

    return None


def _push_stances(state, box):
    stances = []
    matrix = state.getMatrix()

    for dy, dx in MOVE_DELTAS.values():
        stance = (box[0] - dy, box[1] - dx)
        destination = (box[0] + dy, box[1] + dx)

        if _matrix_value(matrix, stance) not in {" ", ".", "@"}:
            continue

        if _matrix_value(matrix, destination) not in {" ", "."}:
            continue

        stances.append(stance)

    return stances


def _opponent_action_score(state, next_position):
    worker = state.workerPosition()
    boxes = state.boxPosition()
    docks = state.dockPosition()

    score = 0

    if worker is not None:
        score += max(0, 7 - _manhattan(next_position, worker)) * 3

    for box in boxes:
        score += max(0, 6 - _manhattan(next_position, box)) * 3

        for stance in _push_stances(state, box):
            score += max(0, 5 - _manhattan(next_position, stance)) * 5

    for dock in docks:
        score += max(0, 5 - _manhattan(next_position, dock)) * 2

    return score


def _walkable_neighbor_count(state, position):
    count = 0

    for dy, dx in MOVE_DELTAS.values():
        value = _matrix_value(state.getMatrix(), (position[0] + dy, position[1] + dx))

        if value in {" ", "."}:
            count += 1

    return count


def _matrix_value(matrix, position):
    row, col = position

    if row < 0 or row >= len(matrix):
        return None

    if col < 0 or col >= len(matrix[row]):
        return None

    return matrix[row][col]


def _manhattan(first, second):
    return abs(first[0] - second[0]) + abs(first[1] - second[1])


# ============================================================
# OUTPUT HELPERS
# ============================================================

def _print_solution(label, start_time, node_generated, solution):
    end_time = time.time()
    print("Time to find solution:", round(end_time - start_time, 2), "seconds")
    print("Number of visited nodes:", node_generated)
    print("Solution:", solution, "Number steps:", len(solution))


def _success_result(label, path, node_generated, expanded_states, start_time):
    real_steps = len(path)

    game_nodes = max(int(_STATS.get("game_nodes", 0)), int(expanded_states))
    pruned_nodes = int(_STATS.get("pruned_nodes", 0))
    chance_nodes = int(_STATS.get("chance_nodes", 0))

    if label == "Minimax":
        display_steps = game_nodes
        metric_label = f"{game_nodes}x · {real_steps}b"

    elif label == "Alpha-Beta":
        display_steps = max(1, game_nodes - pruned_nodes)
        metric_label = f"{game_nodes}x/{pruned_nodes}cut · {real_steps}b"

    elif label == "Expectimax":
        display_steps = max(chance_nodes, game_nodes)
        metric_label = f"{chance_nodes}chance · {real_steps}b"

    else:
        display_steps = real_steps
        metric_label = f"{real_steps}b"

    return {
        "status": "success",
        "algorithm_name": label,
        "path": path,
        "real_steps": real_steps,
        "display_steps": display_steps,
        "metric_label": metric_label,
        "node_generated": node_generated,
        "expanded_states": expanded_states,
        "game_nodes": game_nodes,
        "pruned_nodes": pruned_nodes,
        "chance_nodes": chance_nodes,
        "elapsed_ms": (time.time() - start_time) * 1000,
    }


def _failure_result(label, reason, state, node_generated, start_time):
    path = ""

    if state is not None and hasattr(state, "pathSolution"):
        path = state.pathSolution

    failed_step = len(path)

    if failed_step == 0:
        failed_step = 1

    return {
        "status": "failure",
        "algorithm_name": label,
        "reason": reason,
        "path": path,
        "failed_step": failed_step,
        "fail_step": failed_step,
        "node_generated": node_generated,
        "elapsed_ms": (time.time() - start_time) * 1000,
    }
