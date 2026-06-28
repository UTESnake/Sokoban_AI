import copy
import math
import time
from algorithm.common import apply_step, validMove, worker_toBox, box_toDock, isDeadlock

def evaluate_state(state):
    # Hàm đánh giá: Trừ đi heuristic. Heuristic càng nhỏ (càng gần đích) thì giá trị eval càng cao (Tốt cho MAX)
    return -(worker_toBox(state) + box_toDock(state))

def minimax(game, max_depth=3):
    start = time.time()
    print("Processing MINIMAX......")

    def max_value(state, depth):
        if state.isComplete(): return 10000, state.pathSolution
        if depth == 0 or isDeadlock(state): return evaluate_state(state), state.pathSolution

        v = -math.inf
        best_path = state.pathSolution
        for step in validMove(state):
            new_state = copy.deepcopy(state)
            apply_step(new_state, step)
            min_val, _ = min_value(new_state, depth - 1)
            if min_val > v:
                v = min_val
                best_path = new_state.pathSolution
        return v, best_path

    def min_value(state, depth):
        if state.isComplete(): return -10000, state.pathSolution
        if depth == 0 or isDeadlock(state): return evaluate_state(state), state.pathSolution

        v = math.inf
        best_path = state.pathSolution
        # Giả lập đối thủ (MIN): Chọn nước đi làm cho điểm của MAX thấp nhất có thể
        for step in validMove(state):
            new_state = copy.deepcopy(state)
            apply_step(new_state, step)
            max_val, _ = max_value(new_state, depth - 1)
            if max_val < v:
                v = max_val
                best_path = new_state.pathSolution
        return v, best_path

    _, solution = max_value(game, max_depth)
    print("Time to find solution:", round(time.time() - start, 2), "seconds")
    return solution if solution != game.pathSolution else "NoSol"


def alpha_beta(game, max_depth=4):
    start = time.time()
    print("Processing ALPHA-BETA PRUNING......")

    def max_value(state, depth, alpha, beta):
        if state.isComplete(): return 10000, state.pathSolution
        if depth == 0 or isDeadlock(state): return evaluate_state(state), state.pathSolution

        v = -math.inf
        best_path = state.pathSolution
        for step in validMove(state):
            new_state = copy.deepcopy(state)
            apply_step(new_state, step)
            min_val, _ = min_value(new_state, depth - 1, alpha, beta)
            if min_val > v:
                v = min_val
                best_path = new_state.pathSolution
            if v >= beta: # Cắt tỉa Beta
                return v, best_path
            alpha = max(alpha, v)
        return v, best_path

    def min_value(state, depth, alpha, beta):
        if state.isComplete(): return -10000, state.pathSolution
        if depth == 0 or isDeadlock(state): return evaluate_state(state), state.pathSolution

        v = math.inf
        best_path = state.pathSolution
        for step in validMove(state):
            new_state = copy.deepcopy(state)
            apply_step(new_state, step)
            max_val, _ = max_value(new_state, depth - 1, alpha, beta)
            if max_val < v:
                v = max_val
                best_path = new_state.pathSolution
            if v <= alpha: # Cắt tỉa Alpha
                return v, best_path
            beta = min(beta, v)
        return v, best_path

    _, solution = max_value(game, max_depth, -math.inf, math.inf)
    print("Time to find solution:", round(time.time() - start, 2), "seconds")
    return solution if solution != game.pathSolution else "NoSol"


def expectimax(game, max_depth=3):
    start = time.time()
    print("Processing EXPECTIMAX......")

    def max_value(state, depth):
        if state.isComplete(): return 10000, state.pathSolution
        if depth == 0 or isDeadlock(state): return evaluate_state(state), state.pathSolution

        v = -math.inf
        best_path = state.pathSolution
        for step in validMove(state):
            new_state = copy.deepcopy(state)
            apply_step(new_state, step)
            exp_val, _ = exp_value(new_state, depth - 1)
            if exp_val > v:
                v = exp_val
                best_path = new_state.pathSolution
        return v, best_path

    def exp_value(state, depth):
        # Khác với Minimax, Expectimax tính trung bình (Average/Chance) thay vì Min
        if state.isComplete(): return 0, state.pathSolution
        if depth == 0 or isDeadlock(state): return evaluate_state(state), state.pathSolution

        v = 0
        moves = validMove(state)
        if not moves: return evaluate_state(state), state.pathSolution
        
        probability = 1.0 / len(moves) # Giả sử các nhánh có xác suất xảy ra như nhau
        best_path = state.pathSolution
        
        for step in moves:
            new_state = copy.deepcopy(state)
            apply_step(new_state, step)
            max_val, path = max_value(new_state, depth - 1)
            v += probability * max_val
            best_path = path # Lấy path ngẫu nhiên đại diện
            
        return v, best_path

    _, solution = max_value(game, max_depth)
    print("Time to find solution:", round(time.time() - start, 2), "seconds")
    return solution if solution != game.pathSolution else "NoSol"