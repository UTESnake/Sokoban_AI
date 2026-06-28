from functools import lru_cache


# Quy ước chung của toàn bộ solver:
# - Tọa độ luôn là (row, col), tương đương (y, x) trong ma trận.
# - Action là một ký tự U/D/L/R.
# - Mỗi thuật toán tạo trạng thái con bằng validMove(...) + apply_step(...).
#   Nhờ vậy BFS, A*, belief-state, adversarial... đều dùng cùng một luật Sokoban.
MOVE_DELTAS = {
    "U": (-1, 0),
    "D": (1, 0),
    "L": (0, -1),
    "R": (0, 1),
}

# Các nhóm ký hiệu trên map:
#   " " : sàn trống
#   "." : dock/goal
#   "?" : ô chưa quan sát trong NoObs/PartialObs
#   "$" : box thường
#   "*" : box đang nằm trên dock
#   "#" : tường
#   "E" : đối thủ trong adversarial level
#
# '?' được xem như ô có thể đi qua khi thuật toán đã quyết định execute action.
# Lý do: trong giao diện '?' chỉ là thông tin bị che; khi replay thật, ô này
# được quy ước là sàn nếu action đi qua nó.
WALKABLE = {" ", ".", "?"}
BOXES = {"$", "*"}
BLOCKING = {"#", "E"}


def _matrix_value(matrix, y, x):
    """Đọc ma trận an toàn.

    Nếu tọa độ nằm ngoài map thì trả về "#".
    Cách này giúp các hàm validMove/apply_step không bị IndexError và vẫn
    hiểu ngoài biên như một bức tường không thể đi xuyên qua.
    """
    if y < 0 or y >= len(matrix):
        return "#"
    if x < 0 or x >= len(matrix[y]):
        return "#"
    return matrix[y][x]


def _is_original_dock(state, y, x):
    """Kiểm tra ô (y, x) có phải dock gốc của level hay không.

    Solve.dockListPosition được lưu ngay khi tạo state. Dù trong quá trình di
    chuyển worker/box có ghi đè ký hiệu '.', ta vẫn cần danh sách dock gốc để
    khôi phục lại đúng ký hiệu sau mỗi bước.
    """
    return (y, x) in getattr(state, "dockListPosition", [])


def _restore_docks(state):
    """Khôi phục các dock bị worker/box rời khỏi.

    Khi worker đi qua dock, ký hiệu trên ô có thể tạm bị đổi thành " ".
    Sau mỗi apply_step, hàm này đặt lại "." cho mọi dock không còn chứa
    worker "@" hoặc box-docked "*".
    """
    for y, x in getattr(state, "dockListPosition", []):
        if state.matrix[y][x] not in {"*", "@"}:
            state.matrix[y][x] = "."


def validMove(state):
    """ACTIONS(s): trả về các bước hợp lệ theo thứ tự cố định U, D, L, R.

    Một action hợp lệ khi:
    - ô kế tiếp là WALKABLE: worker có thể bước vào;
    - hoặc ô kế tiếp là BOXES và ô sau box là WALKABLE: worker có thể đẩy box.

    Hàm này chỉ kiểm tra luật di chuyển một bước, chưa xét deadlock. Deadlock
    được lọc riêng bằng isDeadlock(...) trong các thuật toán tìm kiếm.
    """
    worker = state.workerPosition()
    if worker is None:
        return []

    wy, wx = worker
    moves = []

    for step, (dy, dx) in MOVE_DELTAS.items():
        next_cell = _matrix_value(state.matrix, wy + dy, wx + dx)
        after_box = _matrix_value(state.matrix, wy + 2 * dy, wx + 2 * dx)

        # Đi thường: worker bước vào sàn/dock/ô chưa quan sát.
        if next_cell in WALKABLE:
            moves.append(step)
        # Đẩy box: ô trước mặt là box và ô phía sau box còn trống/dock/?.
        elif next_cell in BOXES and after_box in WALKABLE:
            moves.append(step)

    return moves


def apply_step(state, step):
    """RESULT(s, a): áp dụng một bước đi lên đối tượng Solve.

    Hàm này không dùng Solve.move() để xử lý thống nhất cho cả '?',
    ô dock và đối thủ 'E'. Sau mỗi bước, pathSolution được cộng thêm action.

    Trả về:
    - True nếu action làm thay đổi state hợp lệ;
    - False nếu action không thể áp dụng.
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

    # Case 1: worker đi vào ô trống/dock/unknown.
    if next_cell in WALKABLE:
        # Nếu worker rời khỏi dock gốc, ô cũ phải trở lại "."; ngược lại là sàn.
        state.matrix[wy][wx] = "." if _is_original_dock(state, wy, wx) else " "
        state.matrix[ny][nx] = "@"

    # Case 2: worker đẩy box.
    elif next_cell in BOXES:
        by, bx = ny + dy, nx + dx
        after_box = _matrix_value(state.matrix, by, bx)

        if after_box not in WALKABLE:
            return False

        # Worker chiếm vị trí cũ của box, box bị đẩy sang ô kế tiếp.
        state.matrix[wy][wx] = "." if _is_original_dock(state, wy, wx) else " "
        state.matrix[ny][nx] = "@"
        # Nếu box đáp xuống dock gốc thì dùng "*", nếu không thì "$".
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
    """Lấy danh sách dock gốc.

    Ưu tiên dockListPosition vì danh sách này không bị mất khi worker/box
    tạm thời đứng lên dock. Nếu state cũ chưa có thuộc tính này thì fallback
    sang state.dockPosition().
    """
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
        # Ghép box thứ i với một dock chưa dùng. mask đánh dấu dock đã được ghép.
        # Đây là bài toán assignment nhỏ; dùng DP bitmask để tránh ghép tham lam
        # sai khi có nhiều box/dock.
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
    """Vật cản tĩnh dùng để phát hiện deadlock góc.

    Chỉ tường và đối thủ E được xem là block tĩnh. Box khác không đưa vào đây
    để tránh đánh deadlock quá mạnh trong các tình huống box có thể còn được đẩy.
    """
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
    """Khóa hashable cho visited/reached/belief-state.

    Matrix là list lồng nhau nên không thể đưa trực tiếp vào set/dict.
    Chuyển thành tuple(tuple(...)) để các thuật toán so sánh trạng thái đã
    thăm và loại trùng lặp.
    """
    return tuple(tuple(row) for row in state.getMatrix())
