import copy
import assets as _assets

class Game:
    def __init__(self, matrix, stack_matrix):
        self.matrix = matrix
        self.stack_matrix = stack_matrix

    _sprite_for_char = {
        '#': "wall",
        '@': "worker",
        '.': "dock",
        '$': "box",
        '*': "box_docked",
        'E': "competitor",
        '?': "blind_box",
    }

    @classmethod
    def _blit_tile(cls, screen, sprite_name, x, y):
        surf = _assets.sprites.get(sprite_name)
        if surf is not None:
            screen.blit(surf, (x, y))

    def print_game(self, screen):
        x, y = 0, 0
        for row in self.matrix:
            for char in row:
                sprite_name = self._sprite_for_char.get(char)
                if sprite_name is not None:
                    self._blit_tile(screen, sprite_name, x, y)
                x += 64
            x = 0
            y += 64

    @staticmethod
    def fill_screen_with_floor(size, screen):
        screen_width, screen_height = size
        floor_surf = _assets.sprites.get("floor")
        if floor_surf is None:
            return
        for x in range(0, screen_width, 64):
            for y in range(0, screen_height, 64):
                screen.blit(floor_surf, (x, y))

    def is_completed(self, dock):
        for i, j in dock:
            if self.matrix[i][j] != "*":
                return False
        return True

    def getPosition(self):
        for i, row in enumerate(self.matrix):
            for j, char in enumerate(row):
                if char == "@":
                    return i, j

    def listDock(self):
        dockList = []
        for i, row in enumerate(self.matrix):
            for j, char in enumerate(row):
                if char == ".":
                    dockList.append((i, j))
        return dockList

    def _cell(self, x, y):
        if x < 0 or x >= len(self.matrix):
            return "#"
        if y < 0 or y >= len(self.matrix[x]):
            return "#"
        return self.matrix[x][y]

    def canMove(self, x, y):
        return self._cell(x, y) not in ["#", "$", "*", "E"]

    def canPushBox(self, x, y):
        return self._cell(x, y) not in ["#", "$", "*", "E"]

    def update_position(self, old_x, old_y, new_x, new_y, symbol):
        self.matrix[old_x][old_y] = " "
        self.matrix[new_x][new_y] = symbol

    def next_move(self, x, y):
        cur_x, cur_y = self.getPosition()
        new_x, new_y = cur_x + x, cur_y + y
        self.update_position(cur_x, cur_y, new_x, new_y, "@")

    def move_box(self, x, y):
        cur_x, cur_y = self.getPosition()
        cur_box_x, cur_box_y = cur_x + x, cur_y + y
        new_box_x, new_box_y = cur_box_x + x, cur_box_y + y

        if self.canPushBox(new_box_x, new_box_y):
            self.update_position(cur_x, cur_y, cur_box_x, cur_box_y, "@")
            if self.matrix[new_box_x][new_box_y] in [" ", "?"]:
                self.matrix[new_box_x][new_box_y] = "$"
            elif self.matrix[new_box_x][new_box_y] == ".":
                self.matrix[new_box_x][new_box_y] = "*"
            return True
        return False

    def move(self, y, x, dock):
        cur_x, cur_y = self.getPosition()
        next_x, next_y = cur_x + y, cur_y + x
        before = copy.deepcopy(self.matrix)
        moved = False

        if self.canMove(next_x, next_y):
            self.next_move(y, x)
            moved = True
        elif self._cell(next_x, next_y) in ["*", "$"]:
            moved = self.move_box(y, x)

        for i, j in dock:
            if self.matrix[i][j] not in ["*", "@"]:
                self.matrix[i][j] = "."

        if moved:
            self.stack_matrix.append(before)
        return moved
