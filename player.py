import pygame
import os
import yaml
from math import ceil


def load_character_sprites(name: str, scale: int) -> (dict[str, list[pygame.surface.Surface]], dict[str, int]):
    path = os.path.join("data", "PlayerSprites", name)
    ch_data = {}
    with open(os.path.join(path, '_config.yaml'), "r") as stream:
        try:
            data = yaml.safe_load(stream)
            ch_data['RECT_WIDTH'] = data['RECT_WIDTH']
            ch_data['RECT_HEIGHT'] = data['RECT_HEIGHT']
            ch_data['CHARACTER_WIDTH'] = data['CHARACTER_WIDTH']
            ch_data['CHARACTER_HEIGHT'] = data['CHARACTER_HEIGHT']
            ch_data['SPRITES_CHANGE_RATE'] = data['SPRITES_CHANGE_RATE']
        except yaml.YAMLError as exc:
            print(exc)

    sprites_dict: dict[str, list[pygame.surface.Surface]] = dict()
    for filename in os.listdir(path):
        if '.png' not in filename:
            continue
        state = filename.replace('.png', '')
        sprites_dict[state + "_right"] = []
        sprites_dict[state + "_left"] = []
        sprite_sheet = pygame.image.load(os.path.join(path, filename))
        sprites_count = sprite_sheet.get_width() // ch_data['RECT_WIDTH']
        for i in range(sprites_count):
            sprite = sprite_sheet.subsurface((ch_data['RECT_WIDTH'] * i, 0),
                                             (ch_data['RECT_WIDTH'], ch_data['RECT_HEIGHT']))
            sprite = pygame.transform.scale(sprite, (ch_data['RECT_WIDTH'] * scale, ch_data['RECT_HEIGHT'] * scale))
            sprites_dict[state + "_right"].append(sprite)
            sprites_dict[state + "_left"].append(pygame.transform.flip(sprite, True, False))
    return sprites_dict, ch_data


class Player(pygame.sprite.Sprite):
    def __init__(self, pos, scale, name):
        super().__init__()
        self.sprites, ch_data = load_character_sprites(name, scale)
        self.rect: pygame.Rect = pygame.rect.Rect(pos, (ch_data['RECT_WIDTH'] * scale, ch_data['RECT_HEIGHT'] * scale))

        temp = pygame.Surface((ch_data['RECT_WIDTH'] * scale, ch_data['RECT_HEIGHT'] * scale), pygame.SRCALPHA, 32)
        self.sprite_offset_x = (ch_data['RECT_WIDTH'] - ch_data['CHARACTER_WIDTH']) // 2
        self.sprite_offset_y = ch_data['RECT_HEIGHT'] - ch_data['CHARACTER_HEIGHT']
        pygame.draw.rect(temp, (255, 255, 255), (
            self.sprite_offset_x, self.sprite_offset_y, ch_data['CHARACTER_WIDTH'], ch_data['CHARACTER_HEIGHT']))
        self.mask = pygame.mask.from_surface(temp)

        self.sprite: pygame.Surface = None

        self.v = 256  # В пикселях в секунду
        self.vx = 0
        self.vy = 0
        self.x, self.y = pos

        self.off_ground_counter = 0
        self.jump_counter = 0

        self.animations_counter = 0
        self.sprites_change_rate = ch_data['SPRITES_CHANGE_RATE']

        self.status = 'idle'
        self.direction = 'right'

        self.sprite_animation_counter = 0
        self.update_sprite()

    def update_sprite(self):
        status = 'idle'

        if self.vy < 0:
            status = 'jump'
        elif self.vy > 2:
            status = 'fall'
        elif self.vx != 0:
            status = 'run'

        sprite_name = status + '_' + self.direction
        sprite_index = (self.sprite_animation_counter // self.sprites_change_rate) % len(self.sprites[sprite_name])
        self.sprite = self.sprites[sprite_name][sprite_index]
        self.sprite_animation_counter += 1

    def move_left(self):
        self.direction = 'left'
        self.vx = -self.v

    def move_right(self):
        self.direction = 'right'
        self.vx = self.v

    def move(self, dx, dy):
        self.x += dx
        self.rect.x = self.x

        # Надо пофиксить
        self.y += dy
        self.rect.y += dy

    def jump(self):
        if self.jump_counter == 0:
            self.vy = -4
            self.jump_counter += 1

    def touch_down(self):
        self.off_ground_counter = 0
        self.jump_counter = 0
        self.vy = 0

    def touch_ceil(self):
        self.vy *= -1

    def loop(self, fps):
        delta_time = 1 / fps
        self.update_sprite()
        self.move(self.vx * delta_time, self.vy)
        self.vy += min(1, self.off_ground_counter / fps)
        self.off_ground_counter += 1

    def draw(self, screen, offset_x, offset_y):
        screen.blit(self.sprite, (self.rect.x + offset_x, self.rect.y + offset_y))
