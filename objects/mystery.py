import assets
import pygame.sprite
from layer import Layer


class Mystery(pygame.sprite.Sprite):
    def __init__(self, x, y, *groups):
        self._layer = Layer.BOX
        self.image = assets.get_sprite("blind_box")
        if self.image is None:
            raise ValueError("Không tìm thấy sprite cho 'mystery'")
        self.rect = self.image.get_rect(topleft=(x, y))
        super().__init__(*groups)
