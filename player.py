import os

import pygame
import yaml


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
        self.sprites, self.ch_data = load_character_sprites(name, scale)
        self.rect: pygame.Rect = pygame.rect.Rect(pos, (
            self.ch_data['RECT_WIDTH'] * scale, self.ch_data['RECT_HEIGHT'] * scale))

        temp = pygame.Surface((self.ch_data['RECT_WIDTH'] * scale, self.ch_data['RECT_HEIGHT'] * scale),
                              pygame.SRCALPHA, 32)
        self.sprite_offset_x = (self.ch_data['RECT_WIDTH'] - self.ch_data['CHARACTER_WIDTH']) // 2
        self.sprite_offset_y = self.ch_data['RECT_HEIGHT'] - self.ch_data['CHARACTER_HEIGHT']
        pygame.draw.rect(temp, (255, 255, 255), (
            self.sprite_offset_x, self.sprite_offset_y, self.ch_data['CHARACTER_WIDTH'],
            self.ch_data['CHARACTER_HEIGHT']))
        self.mask = pygame.mask.from_surface(temp)

        self.sprite: pygame.Surface = None

        self.hp = 100

        self.v = 192  # В пикселях в секунду
        self.vx = 0
        self.vy = 0
        self.x, self.y = pos

        self.off_ground_counter = 0
        self.jump_counter = 0
        self.animations_counter = 0
        self.sprites_change_rate = self.ch_data['SPRITES_CHANGE_RATE']

        self.status = 'idle'
        self.direction = 'right'

        self.sprite_animation_counter = 0

        self.inventory = []
        self.current_weapons = []
        self.is_holding_weapon = False

    def draw_weapon_and_hands(self, screen, offset_x, offset_y):
        if self.is_holding_weapon:
            # Рисуем оружие в левой и правой руке
            pass
        else:
            # рисуем просто руки
            screen.blit(self.sprite, (self.rect.x + offset_x, self.rect.y + offset_y))

    def get_position(self):
        x = self.x + self.ch_data['RECT_WIDTH'] // 2
        y = self.y + self.ch_data['RECT_HEIGHT'] - self.ch_data['CHARACTER_HEIGHT']
        return x, y

    def get_center_position(self):
        x, y = self.get_position()
        y += self.ch_data['CHARACTER_HEIGHT'] // 2
        return x, y

    def update_sprite(self, time_delta):

        if self.hp <= 0 and self.status != 'deathNoMovement':
            self.sprite_animation_counter = 0

        self.status = 'idle'

        if self.hp <= 0:
            self.status = 'deathNoMovement'
        elif self.vy < 0:
            self.status = 'jump'
        elif self.vy * time_delta > 2:
            self.status = 'fall'
        elif self.vx != 0:
            self.status = 'run'

        sprite_name = self.status + '_' + self.direction
        sprite_index = (self.sprite_animation_counter // self.sprites_change_rate) % len(self.sprites[sprite_name])
        self.sprite = self.sprites[sprite_name][sprite_index]

        if self.status == 'deathNoMovement' and sprite_index == len(self.sprites[sprite_name]) - 1:
            return

        self.sprite_animation_counter += 1

    def move_left(self):
        if self.hp <= 0:
            return
        self.direction = 'left'
        self.vx = -self.v

    def move_right(self):
        if self.hp <= 0:
            return
        self.direction = 'right'
        self.vx = self.v

    def move(self, dx, dy):
        self.x += dx
        self.rect.x = self.x
        self.y += dy
        self.rect.y = self.y

    def jump(self):
        if self.hp <= 0:
            return
        if self.jump_counter == 0:
            self.off_ground_counter = 0
            self.vy = -600
            self.jump_counter += 1

    def touch_down(self):
        self.off_ground_counter = 0
        self.jump_counter = 0
        self.vy = 0

    def touch_ceil(self):
        self.vy *= -1

    def get_left(self):
        return self.rect.left + (self.ch_data['RECT_WIDTH'] - self.ch_data['CHARACTER_WIDTH']) // 2

    def get_right(self):
        return self.rect.right - (self.ch_data['RECT_WIDTH'] - self.ch_data['CHARACTER_WIDTH'] - 1) // 2

    def get_top(self):
        return self.rect.top + (self.ch_data['RECT_HEIGHT'] - self.ch_data['CHARACTER_HEIGHT'])

    def get_bottom(self):
        return self.rect.top + self.rect.height

    def set_left(self, x):
        self.rect.left = x - (self.ch_data['RECT_WIDTH'] - self.ch_data['CHARACTER_WIDTH']) // 2
        self.x = self.rect.x

    def set_right(self, x):
        self.rect.right = x + (self.ch_data['RECT_WIDTH'] - self.ch_data['CHARACTER_WIDTH'] - 1) // 2
        self.x = self.rect.x

    def set_top(self, y):
        self.rect.top = y - (self.ch_data['RECT_HEIGHT'] - self.ch_data['CHARACTER_HEIGHT'])
        self.y = self.rect.y

    def set_bottom(self, y):
        self.rect.bottom = y
        self.y = self.rect.top

    def loop(self, time_delta):
        time_delta = min(1 / 20, time_delta)

        self.update_sprite(time_delta)
        self.vy += min(1, self.off_ground_counter) * time_delta * 2000
        self.off_ground_counter += 1
        self.move(self.vx * time_delta, self.vy * time_delta)

    def draw(self, screen, offset_x, offset_y):
        screen.blit(self.sprite, (self.rect.x + offset_x, self.rect.y + offset_y))

    #  self.draw_weapon_and_hands(self.sprite, (self.rect.x + offset_x, self.rect.y + offset_y))

    def encode(self):
        return [self.rect.x, self.rect.y, self.status, self.direction, self.sprite_animation_counter,
                self.hp]

    def initial_info(self):
        return [self.rect.x, self.rect.y, self.status, self.direction, self.sprite_animation_counter,
                self.hp, self.ch_data]

    def apply(self, data):
        self.rect.x = data[0]
        self.rect.y = data[1]
        self.status = data[2]
        self.direction = data[3]
        self.sprite_animation_counter = data[4] - 1
        self.hp = data[5]
        sprite_name = self.status + '_' + self.direction
        sprite_index = (self.sprite_animation_counter // self.sprites_change_rate) % len(self.sprites[sprite_name])
        self.sprite = self.sprites[sprite_name][sprite_index]


class Bullet:
    def __init__(self, position, speed):
        self.x, self.y = position
        self.vx, self.vy = speed
        self.image = pygame.surface.Surface((10, 10))
        self.image.fill((255, 255, 255))

    def encode(self):
        return [self.x, self.y, self.vx, self.vy]

    def apply(self, data):
        self.x, self.y, self.vx, self.vy = data

    def update(self, time_delta):
        dx, dy = self.vx * time_delta, self.vy * time_delta
        self.x += dx
        self.y += dy

    def draw(self, screen: pygame.Surface, offset_x, offset_y):
        pygame.draw.circle(screen, (255, 255, 255), (self.x + offset_x, self.y + offset_y), 5)
