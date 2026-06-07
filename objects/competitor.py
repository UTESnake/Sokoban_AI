import assets
import pygame.sprite
from layer import Layer


class Competitor(pygame.sprite.Sprite):
    def __init__(self, x, y, *groups):
        self._layer = Layer.WORKER
        self.image = assets.get_sprite("competitor")
        if self.image is None:
            raise ValueError("Không tìm thấy sprite cho 'competitor'")
        self.rect = self.image.get_rect(topleft=(x, y))
        super().__init__(*groups)
