import os
import pygame

sprites = {}
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TILE_SIZE = (64, 64)
REQUIRED_SPRITES = (
    "floor",
    "wall",
    "dock",
    "box",
    "box_docked",
    "worker",
    "competitor",
    "mystery",
)


def _new_tile(fill):
    surface = pygame.Surface(TILE_SIZE, pygame.SRCALPHA)
    surface.fill(fill)
    return surface


def _draw_floor(surface):
    surface.fill("#D8E0D2")
    pygame.draw.rect(surface, "#C7D2C2", surface.get_rect(), 2)
    pygame.draw.line(surface, "#EAF0E5", (0, 0), (63, 0), 2)
    pygame.draw.line(surface, "#EAF0E5", (0, 0), (0, 63), 2)


def _fallback_floor():
    surface = _new_tile("#D8E0D2")
    _draw_floor(surface)
    return surface


def _fallback_wall():
    surface = _fallback_floor()
    pygame.draw.rect(surface, "#5D6A7B", (5, 5, 54, 54), border_radius=7)
    pygame.draw.rect(surface, "#445163", (5, 5, 54, 54), 3, border_radius=7)
    pygame.draw.line(surface, "#758196", (10, 22), (54, 22), 3)
    pygame.draw.line(surface, "#758196", (10, 42), (54, 42), 3)
    pygame.draw.line(surface, "#758196", (24, 9), (24, 21), 3)
    pygame.draw.line(surface, "#758196", (42, 24), (42, 41), 3)
    return surface


def _fallback_dock():
    surface = _fallback_floor()
    pygame.draw.circle(surface, "#F7C948", (32, 32), 18)
    pygame.draw.circle(surface, "#B7791F", (32, 32), 18, 3)
    pygame.draw.circle(surface, "#FFF7D6", (32, 32), 8)
    return surface


def _fallback_box():
    surface = _fallback_floor()
    pygame.draw.rect(surface, "#C9853C", (10, 10, 44, 44), border_radius=6)
    pygame.draw.rect(surface, "#8F5A28", (10, 10, 44, 44), 3, border_radius=6)
    pygame.draw.line(surface, "#E3A861", (16, 18), (48, 18), 3)
    pygame.draw.line(surface, "#A66B31", (16, 44), (48, 44), 3)
    pygame.draw.line(surface, "#A66B31", (32, 12), (32, 52), 3)
    return surface


def _fallback_box_docked():
    surface = _fallback_dock()
    pygame.draw.rect(surface, "#47B881", (11, 11, 42, 42), border_radius=6)
    pygame.draw.rect(surface, "#2F855A", (11, 11, 42, 42), 3, border_radius=6)
    pygame.draw.line(surface, "#D9F99D", (22, 32), (29, 39), 4)
    pygame.draw.line(surface, "#D9F99D", (29, 39), (44, 23), 4)
    return surface


def _fallback_worker():
    surface = _fallback_floor()
    pygame.draw.circle(surface, "#F6C177", (32, 22), 11)
    pygame.draw.rect(surface, "#4C78A8", (20, 32, 24, 21), border_radius=8)
    pygame.draw.circle(surface, "#263A5F", (28, 20), 2)
    pygame.draw.circle(surface, "#263A5F", (36, 20), 2)
    pygame.draw.arc(surface, "#263A5F", (27, 20, 10, 9), 0.2, 2.9, 2)
    return surface


def _fallback_competitor():
    surface = _fallback_floor()
    pygame.draw.circle(surface, "#F4A261", (32, 22), 11)
    pygame.draw.rect(surface, "#7C3AED", (20, 32, 24, 21), border_radius=8)
    pygame.draw.polygon(surface, "#FDE68A", [(32, 8), (38, 18), (26, 18)])
    pygame.draw.circle(surface, "#2D244D", (28, 20), 2)
    pygame.draw.circle(surface, "#2D244D", (36, 20), 2)
    return surface


def _fallback_mystery():
    surface = _fallback_floor()
    pygame.draw.rect(surface, "#9F7AEA", (10, 10, 44, 44), border_radius=8)
    pygame.draw.rect(surface, "#5B3AA4", (10, 10, 44, 44), 3, border_radius=8)
    pygame.draw.circle(surface, "#FFFFFF", (32, 46), 3)
    pygame.draw.arc(surface, "#FFFFFF", (21, 14, 22, 22), 5.0, 2.0, 4)
    return surface


FALLBACK_BUILDERS = {
    "floor": _fallback_floor,
    "wall": _fallback_wall,
    "dock": _fallback_dock,
    "box": _fallback_box,
    "box_docked": _fallback_box_docked,
    "worker": _fallback_worker,
    "competitor": _fallback_competitor,
    "mystery": _fallback_mystery,
}


def _ensure_required_sprites():
    missing = [name for name in REQUIRED_SPRITES if name not in sprites]
    for name in missing:
        sprites[name] = FALLBACK_BUILDERS[name]()
    if missing:
        print("Đã tạo sprite mặc định cho:", ", ".join(missing))

def load_sprites():
    path = os.path.join(BASE_DIR, "assets", "sprites")

    if not os.path.exists(path):
        print(f"Thư mục {path} không tồn tại.")
        _ensure_required_sprites()
        return

    for file in os.listdir(path):
        if not file.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif")):
            continue
        try:
            sprite_name = os.path.splitext(file)[0]
            sprite = pygame.image.load(os.path.join(path, file))
            if sprite.get_size() != TILE_SIZE:
                sprite = pygame.transform.smoothscale(sprite, TILE_SIZE)

            sprites[sprite_name] = sprite

        except pygame.error as e:
            print(f"Không thể tải hình ảnh {file}: {e}")

    _ensure_required_sprites()

def get_sprite(name):
    sprite = sprites.get(name)

    if sprite is None:
        print(f"Không tìm thấy sprite: {name}")
    return sprite
