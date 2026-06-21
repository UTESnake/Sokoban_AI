import os
import pygame

sprites = {}
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TILE_SIZE = (64, 64)

def load_sprites():
    path = os.path.join(BASE_DIR, "assets", "sprites")

    if not os.path.exists(path):
        print(f"Thư mục {path} không tồn tại.")
        return

    for file in os.listdir(path):
        try:
            sprite_name = os.path.splitext(file)[0]
            sprite = pygame.image.load(os.path.join(path, file))
            if sprite.get_size() != TILE_SIZE:
                sprite = pygame.transform.smoothscale(sprite, TILE_SIZE)

            sprites[sprite_name] = sprite

        except pygame.error as e:
            print(f"Không thể tải hình ảnh {file}: {e}")

def get_sprite(name):
    sprite = sprites.get(name)

    if sprite is None:
        print(f"Không tìm thấy sprite: {name}")
    return sprite
