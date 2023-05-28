import os
import pygame
import yaml
from sound import load_weapon_sound

pygame.mixer.init()


def load_weapon_sprites(scale: int) -> (dict[str, list[pygame.surface.Surface]], dict[str, int]):
    path = os.path.join("data", 'WeaponSprites')
    weapon_data = {}
    sprites_dict: dict[str, list[pygame.surface.Surface]] = dict()
    directories = os.listdir(path)
    for directory in directories:
        if 'Weapon' not in directory:
            continue
        weapon_data[directory] = dict()
        with open(os.path.join(path, directory, '_config.yaml'), "r") as stream:
            try:
                data = yaml.safe_load(stream)
                weapon_data[directory]['WEAPON_RECT_WIDTH'] = data['WEAPON_RECT_WIDTH']
                weapon_data[directory]['WEAPON_RECT_HEIGHT'] = data['WEAPON_RECT_HEIGHT']
                weapon_data[directory]['ARMS_RECT_WIDTH'] = data['ARMS_RECT_WIDTH']
                weapon_data[directory]['ARMS_RECT_HEIGHT'] = data['ARMS_RECT_HEIGHT']
                weapon_data[directory]['IMAGE_OFFSET_X'] = data['IMAGE_OFFSET_X']
                weapon_data[directory]['IMAGE_OFFSET_Y'] = data['IMAGE_OFFSET_Y']
                weapon_data[directory]['IMAGE_WIDTH'] = data['IMAGE_WIDTH']
                weapon_data[directory]['IMAGE_HEIGHT'] = data['IMAGE_HEIGHT']
                weapon_data[directory]['OFFSET_X_LEFT'] = data['OFFSET_X_LEFT']
                weapon_data[directory]['OFFSET_X_RIGHT'] = data['OFFSET_X_RIGHT']
                weapon_data[directory]['OFFSET_Y'] = data['OFFSET_Y']
                weapon_data[directory]['BULLET_SPEED'] = data['BUlLET_SPEED']
                weapon_data[directory]['BULLET_DAMAGE'] = data['BULLET_DAMAGE']
                weapon_data[directory]['PATRONS'] = data['PATRONS']
                weapon_data[directory]['RELOAD_T'] = data['RELOAD_T']
                weapon_data[directory]['BARREL_OFFSET_X'] = data['BARREL_OFFSET_X']
                weapon_data[directory]['BARREL_OFFSET_Y'] = data['BARREL_OFFSET_Y']
                weapon_data[directory]['FRAME_RATE'] = data['FRAME_RATE']
            except yaml.YAMLError as exc:
                print(exc)
        for filename in os.listdir(os.path.join(path, directory)):
            if '.png' not in filename:
                continue
            state = filename.replace('.png', '')
            if 'arms' in state:
                sprite_width = weapon_data[directory]['ARMS_RECT_WIDTH']
                sprite_height = weapon_data[directory]['ARMS_RECT_HEIGHT']
            else:
                sprite_width = weapon_data[directory]['WEAPON_RECT_WIDTH']
                sprite_height = weapon_data[directory]['WEAPON_RECT_HEIGHT']
            sprites_dict[f'{directory}_{state}_right'] = []
            sprites_dict[f'{directory}_{state}_left'] = []
            sprite_sheet = pygame.image.load(os.path.join(path, directory, filename))
            sprites_count = sprite_sheet.get_width() // sprite_width
            for i in range(sprites_count):
                sprite = sprite_sheet.subsurface((sprite_width * i, 0), (sprite_width, sprite_height))
                sprite = pygame.transform.scale(sprite, (sprite_width * scale, sprite_height * scale))
                sprites_dict[f'{directory}_{state}_right'].append(sprite)
                sprites_dict[f'{directory}_{state}_left'].append(pygame.transform.flip(sprite, True, False))
    return sprites_dict, weapon_data


class Weapon:
    all_weapons_sprites, all_weapons_info = load_weapon_sprites(1)

    def __init__(self, name, ammo=0, pos=None, owner=None):
        self.attached = False
        self.owner = None  # Reference to player

        self.status = 'idle'
        self.name = name
        self.weapon_sprite: pygame.Surface = None
        self.arms_sprite: pygame.Surface = None
        self.ammo = ammo
        self.damage = Weapon.all_weapons_info[self.name]['BULLET_DAMAGE']
        self.sounds = load_weapon_sound(name)

        if pos:
            self.direction = 'right'
            self.x = pos[0]
            self.y = pos[1]
        if owner:
            self.direction = owner.direction
            self.owner = owner
            self.x, self.y = owner.rect.x, owner.rect.y

        # Everything is measured in seconds
        self.animation_switch_timer: float = 0
        self.animation_switch_time: float = Weapon.all_weapons_info[self.name]['FRAME_RATE']

        self.sprite_number = 0

        self.update_sprite(0)

    def attach(self, player):
        self.owner = player
        self.attached = True

    def detach(self):
        self.owner = None
        self.attached = False

    def shoot(self):
        if self.name == 'WeaponNone':
            return None
        if self.status == 'shoot':
            return None
        if self.ammo <= 0:
            self.sounds['is_empty'].sound_play()
            return None
        self.sounds['shot'].sound_play()
        self.ammo -= 1
        self.status = 'shoot'
        self.sprite_number = 0

        speed_x = (1 if self.direction == 'right' else -1) * Weapon.all_weapons_info[self.name]['BULLET_SPEED']

        return Bullet(self.get_barrel_position(), (speed_x, 0), self.damage)

    def update_sprite(self, time_delta):
        if self.attached:
            self.direction = self.owner.direction
            self.x = self.owner.rect.x + Weapon.all_weapons_info[self.name][f'OFFSET_X_{self.direction.upper()}']
            self.y = self.owner.rect.y + Weapon.all_weapons_info[self.name]['OFFSET_Y']

        self.animation_switch_timer += time_delta
        if self.animation_switch_timer >= self.animation_switch_time:
            self.sprite_number += 1

            if self.sprite_number >= len(
                    Weapon.all_weapons_sprites[f'{self.name}_{self.status}_{self.direction}']):
                if self.status == 'shoot':
                    self.status = 'idle'

                self.sprite_number = 0

            self.animation_switch_timer = 0

        if self.attached:
            self.arms_sprite = \
                Weapon.all_weapons_sprites[f'{self.name}_arms_{self.status}_{self.direction}'][self.sprite_number]
            self.weapon_sprite = \
                Weapon.all_weapons_sprites[f'{self.name}_{self.status}_{self.direction}'][self.sprite_number]
        else:
            self.weapon_sprite = \
                Weapon.all_weapons_sprites[f'{self.name}_{self.status}_{self.direction}'][self.sprite_number]

    def get_position(self):
        return self.x, self.y

    def get_barrel_position(self):
        if self.direction == 'right':
            x = self.x + Weapon.all_weapons_info[self.name]['IMAGE_OFFSET_X'] + \
                Weapon.all_weapons_info[self.name]['BARREL_OFFSET_X']
            y = self.y + Weapon.all_weapons_info[self.name]['IMAGE_OFFSET_Y'] + \
                Weapon.all_weapons_info[self.name]['BARREL_OFFSET_Y']
        else:
            x = self.x + Weapon.all_weapons_info[self.name]['WEAPON_RECT_WIDTH'] - Weapon.all_weapons_info[self.name][
                'IMAGE_OFFSET_X'] - \
                Weapon.all_weapons_info[self.name]['BARREL_OFFSET_X']
            y = self.y + Weapon.all_weapons_info[self.name]['IMAGE_OFFSET_Y'] + \
                Weapon.all_weapons_info[self.name]['BARREL_OFFSET_Y']
        return x, y

    def draw(self, screen: pygame.Surface, offset_x, offset_y):
        if self.attached:
            weapon_position = self.get_position()
            weapon_coords = (weapon_position[0] + offset_x, weapon_position[1] + offset_y)
            screen.blit(self.weapon_sprite, weapon_coords)
            arms_position = self.owner.rect.x + offset_x, self.owner.rect.y + offset_y
            screen.blit(self.arms_sprite, arms_position)
        else:
            weapon_position = (self.x + offset_x, self.y + offset_y)
            screen.blit(self.weapon_sprite, weapon_position)


class Bullet:
    def __init__(self, position, speed, damage):
        self.damage = damage
        self.x, self.y = position
        self.vx, self.vy = speed
        self.image = pygame.surface.Surface((10, 10))
        self.image.fill((255, 255, 255))

    def encode(self):
        return [self.x, self.y, self.vx, self.vy, self.damage]

    def apply(self, data):
        self.x, self.y, self.vx, self.vy = data

    def update(self, time_delta):
        dx, dy = self.vx * time_delta, self.vy * time_delta
        self.x += dx
        self.y += dy

    def draw(self, screen: pygame.Surface, offset_x, offset_y):
        pygame.draw.circle(screen, (255, 255, 255), (self.x + offset_x, self.y + offset_y), 2)
