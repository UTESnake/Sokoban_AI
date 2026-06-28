import copy
import math
import random
import time

from algorithm.common import apply_step, box_toDock, isDeadlock, state_key, validMove, worker_toBox


def get_heuristic(state):
    # Hàm đánh giá (Heuristic) = Khoảng cách từ người đến hộp + từ hộp đến đích.
    # Càng nhỏ càng tốt.
    return worker_toBox(state) + box_toDock(state)


def simple_hill_climbing(game):
    """
    Thuật toán Leo đồi (Hill Climbing) cơ bản.
    Tại mỗi bước, chỉ chọn trạng thái kề (neighbor) có giá trị Heuristic tốt nhất.
    Nếu không có trạng thái kề nào tốt hơn trạng thái hiện tại thì dừng lại (mắc kẹt ở đỉnh địa phương).
    """
    start = time.time()
    node_generated = 0
    current_state = copy.deepcopy(game)
    node_generated += 1

    print("Processing HILL CLIMBING......")

    if isDeadlock(current_state):
        print("No Solution!")
        return "NoSol"

    while True:
        if current_state.isComplete():
            end = time.time()
            print("Time to find solution:", round(end - start, 2), "seconds")
            print("Number of visited nodes:", node_generated)
            print("Solution:", current_state.pathSolution, "Number steps:", len(current_state.pathSolution))
            return current_state.pathSolution

        neighbors = []
        for step in validMove(current_state):
            new_state = copy.deepcopy(current_state)
            node_generated += 1
            apply_step(new_state, step)
            if not isDeadlock(new_state):
                neighbors.append(new_state)

        if not neighbors:
            break

        # Tìm neighbor có Heuristic nhỏ nhất (tốt nhất)
        best_neighbor = min(neighbors, key=lambda s: get_heuristic(s))
        
        # LƯU Ý CHO SINH VIÊN: Nếu neighbor tốt nhất vẫn tệ hơn hoặc bằng current_state
        # thì thuật toán bị kẹt ở "Local Optimum" (Đỉnh địa phương) và sẽ bỏ cuộc.
        if get_heuristic(best_neighbor) >= get_heuristic(current_state):
            print("Stuck at local optimum!")
            break
            
        current_state = best_neighbor

    print(node_generated)
    print("No Solution!")
    return "NoSol"


def beam_search(game, beam_width=3):
    """
    Tìm kiếm chùm (Local Beam Search).
    Khắc phục điểm yếu của Hill Climbing bằng cách giữ lại 'k' (beam_width) trạng thái tốt nhất
    ở mỗi bước thay vì chỉ giữ 1 trạng thái.
    """
    start = time.time()
    node_generated = 0
    start_state = copy.deepcopy(game)
    node_generated += 1

    print(f"Processing BEAM SEARCH (width={beam_width})......")

    if isDeadlock(start_state):
        print("No Solution!")
        return "NoSol"

    # Tập hợp các trạng thái hiện tại (chùm/tia)
    beam = [start_state]
    visited = {state_key(start_state)}

    # Giới hạn số vòng lặp để tránh lặp vô hạn
    max_steps = 1000 
    
    for _ in range(max_steps):
        next_states = []
        
        for current_state in beam:
            if current_state.isComplete():
                end = time.time()
                print("Time to find solution:", round(end - start, 2), "seconds")
                print("Number of visited nodes:", node_generated)
                print("Solution:", current_state.pathSolution, "Number steps:", len(current_state.pathSolution))
                return current_state.pathSolution
                
            for step in validMove(current_state):
                new_state = copy.deepcopy(current_state)
                node_generated += 1
                apply_step(new_state, step)
                
                key = state_key(new_state)
                if key not in visited and not isDeadlock(new_state):
                    visited.add(key)
                    next_states.append(new_state)

        if not next_states:
            break

        # Sắp xếp các trạng thái con sinh ra theo Heuristic (từ nhỏ đến lớn)
        next_states.sort(key=lambda s: get_heuristic(s))
        
        # Chỉ lấy cắt lại đúng 'k' trạng thái tốt nhất cho vòng lặp tiếp theo
        beam = next_states[:beam_width]

    print(node_generated)
    print("No Solution!")
    return "NoSol"


def simulated_annealing_search(game, initial_temperature=100, cooling_rate=0.99, max_iterations=5000):
    """
    Thuật toán Luyện kim (Simulated Annealing).
    Đôi khi chấp nhận đi những bước "tệ hơn" với một xác suất giảm dần theo nhiệt độ (Temperature).
    Nhờ vậy tác nhân có cơ hội leo xuống khỏi "Đỉnh địa phương" để tìm "Đỉnh toàn cục".
    """
    start = time.time()
    node_generated = 0
    current_state = copy.deepcopy(game)
    node_generated += 1

    print("Processing SIMULATED ANNEALING......")

    if isDeadlock(current_state):
        print("No Solution!")
        return "NoSol"

    temperature = initial_temperature
    
    for _ in range(max_iterations):
        if current_state.isComplete():
            end = time.time()
            print("Time to find solution:", round(end - start, 2), "seconds")
            print("Number of visited nodes:", node_generated)
            print("Solution:", current_state.pathSolution, "Number steps:", len(current_state.pathSolution))
            return current_state.pathSolution

        if temperature <= 0.01: # Nhiệt độ quá thấp thì nguội hẳn, dừng lại
            break

        moves = validMove(current_state)
        if not moves:
            break

        # Chọn NGẪU NHIÊN 1 nước đi kề
        step = random.choice(moves)
        next_state = copy.deepcopy(current_state)
        node_generated += 1
        apply_step(next_state, step)

        if isDeadlock(next_state):
            continue

        current_h = get_heuristic(current_state)
        next_h = get_heuristic(next_state)
        
        # Tính độ chênh lệch. (Heuristic nhỏ là tốt, nên delta > 0 nghĩa là next_state tốt hơn)
        delta_e = current_h - next_h 

        if delta_e > 0:
            # Trạng thái mới TỐT HƠN -> Luôn luôn đi sang đó
            current_state = next_state
        else:
            # Trạng thái mới TỆ HƠN -> Chấp nhận với một xác suất P = e^(delta / T)
            probability = math.exp(delta_e / temperature)
            if random.random() < probability:
                current_state = next_state

        # Giảm nhiệt độ từ từ
        temperature *= cooling_rate

    print(node_generated)
    print("No Solution!")
    return "NoSol"