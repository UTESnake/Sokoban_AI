from functools import lru_cache


MOVE_DELTAS = {
    "U": (-1, 0),
    "D": (1, 0),
    "L": (0, -1),
    "R": (0, 1),
}

# Ô có thể đi vào. '?' được dùng cho màn quan sát hạn chế,
# khi thuật toán đã quyết định đi qua thì xem như sàn trống.
WALKABLE = {" ", ".", "?"}
BOXES = {"$", "*"}
BLOCKING = {"#", "E"}


def _matrix_value(matrix, y, x):
    """Đọc ma trận an toàn; ngoài biên được xem như tường."""
    if y < 0 or y >= len(matrix):
        return "#"
    if x < 0 or x >= len(matrix[y]):
        return "#"
    return matrix[y][x]


def _is_original_dock(state, y, x):
    return (y, x) in getattr(state, "dockListPosition", [])


def _restore_docks(state):
    for y, x in getattr(state, "dockListPosition", []):
        if state.matrix[y][x] not in {"*", "@"}:
            state.matrix[y][x] = "."


def validMove(state):
    """ACTIONS(s): trả về các bước hợp lệ theo thứ tự cố định U, D, L, R."""
    worker = state.workerPosition()
    if worker is None:
        return []

    wy, wx = worker
    moves = []

    for step, (dy, dx) in MOVE_DELTAS.items():
        next_cell = _matrix_value(state.matrix, wy + dy, wx + dx)
        after_box = _matrix_value(state.matrix, wy + 2 * dy, wx + 2 * dx)

        if next_cell in WALKABLE:
            moves.append(step)
        elif next_cell in BOXES and after_box in WALKABLE:
            moves.append(step)

    return moves


def apply_step(state, step):
    """RESULT(s, a): áp dụng một bước đi lên đối tượng Solve.

    Hàm này không dùng Solve.move() để xử lý thống nhất cho cả '?',
    ô dock và đối thủ 'E'. Sau mỗi bước, pathSolution được cộng thêm action.
    """
    if step not in MOVE_DELTAS:
        raise ValueError(f"Invalid step: {step}")

    worker = state.workerPosition()
    if worker is None:
        return False

    dy, dx = MOVE_DELTAS[step]
    wy, wx = worker
    ny, nx = wy + dy, wx + dx
    next_cell = _matrix_value(state.matrix, ny, nx)

    if next_cell in WALKABLE:
        state.matrix[wy][wx] = "." if _is_original_dock(state, wy, wx) else " "
        state.matrix[ny][nx] = "@"

    elif next_cell in BOXES:
        by, bx = ny + dy, nx + dx
        after_box = _matrix_value(state.matrix, by, bx)

        if after_box not in WALKABLE:
            return False

        state.matrix[wy][wx] = "." if _is_original_dock(state, wy, wx) else " "
        state.matrix[ny][nx] = "@"
        state.matrix[by][bx] = "*" if _is_original_dock(state, by, bx) else "$"

    else:
        return False

    _restore_docks(state)
    state.pathSolution += step
    return True


def box_positions(state, include_docked=False):
    """Lấy vị trí các thùng.

    include_docked = False:
        chỉ lấy box chưa nằm trên dock, tức ký hiệu '$'.

    include_docked = True:
        lấy cả '$' và '*'.
    """
    symbols = {"$", "*"} if include_docked else {"$"}

    return [
        (y, x)
        for y, row in enumerate(state.matrix)
        for x, value in enumerate(row)
        if value in symbols
    ]


def dock_positions(state):
    return list(getattr(state, "dockListPosition", None) or state.dockPosition())


def manhattan(pos1, pos2):
    """Khoảng cách Manhattan giữa hai ô."""
    return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])


def box_toDock(state):
    """Heuristic tối ưu hơn cho phần box → dock.

    Công thức:
        box_toDock(state)
        = min tổng Manhattan khi ghép mỗi box chưa xếp với một dock còn trống.

    Chỉ xét:
        - box chưa xếp: ký hiệu '$'
        - dock chưa bị box '*' chiếm
    """
    boxes = tuple(box_positions(state, include_docked=False))
    all_docks = tuple(dock_positions(state))
    docked_boxes = set(box_positions(state, include_docked=True)) - set(boxes)

    docks = tuple(dock for dock in all_docks if dock not in docked_boxes)

    if not boxes:
        return 0

    if not docks:
        return float("inf")

    if len(docks) < len(boxes):
        return float("inf")

    @lru_cache(maxsize=None)
    def dp(i, mask):
        if i == len(boxes):
            return 0

        best = float("inf")
        box = boxes[i]

        for dock_index, dock in enumerate(docks):
            if mask & (1 << dock_index):
                continue

            cost = manhattan(box, dock) + dp(i + 1, mask | (1 << dock_index))
            best = min(best, cost)

        return best

    return dp(0, 0)

def worker_toBox(state):
    """Khoảng cách Manhattan từ worker tới box chưa xếp gần nhất."""
    boxes = box_positions(state)
    worker = state.workerPosition()

    if not boxes or worker is None:
        return 0

    return min(manhattan(worker, box) for box in boxes)


def heuristic(state):
    """h(n) dùng chung cho A*, Greedy, IDA*, Beam.

    Công thức mới:

        h(n) = box_toDock_matching(n) + worker_toBox(n)

    Trong đó:
        - box_toDock dùng ghép tối ưu một-một giữa box và dock.
        - worker_toBox là khoảng cách Manhattan từ worker tới box gần nhất.

    h càng nhỏ càng tốt.
    """
    return box_toDock(state) + worker_toBox(state)


def _is_static_block(matrix, y, x):
    return _matrix_value(matrix, y, x) in {"#", "E"}


def isDeadlock(state):
    """Deadlock góc cơ bản cho box chưa nằm trên dock.

    Nếu một box '$' kẹt giữa một vật cản dọc và một vật cản ngang,
    và ô đó không phải dock gốc, box đó không thể được đưa tới goal.
    """
    matrix = state.matrix

    for y, x in box_positions(state):
        if _is_original_dock(state, y, x):
            continue

        vertical_block = (
            _is_static_block(matrix, y - 1, x)
            or _is_static_block(matrix, y + 1, x)
        )

        horizontal_block = (
            _is_static_block(matrix, y, x - 1)
            or _is_static_block(matrix, y, x + 1)
        )

        if vertical_block and horizontal_block:
            return True

    return False


def state_key(state):
    return tuple(tuple(row) for row in state.getMatrix())
