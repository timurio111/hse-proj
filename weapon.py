import os

import pygame
import yaml

def load_weapon_sprites(name: str, scale: int) -> (dict[str, list[pygame.surface.Surface]], dict[str, int]):
    path = os.path.join("data", name)
    weapon_data = {}
    sprites_dict: dict[str, list[pygame.surface.Surface]] = dict()
    dirs =  os.listdir(path)
    for dir in dirs:
        weapon_data[dir] = dict()

        with open(os.path.join(path, dir,'_config.yaml'), "r") as stream:
            try:
                data = yaml.safe_load(stream)
                weapon_data[dir]['RECT_WIDTH'] = data['RECT_WIDTH']
                weapon_data[dir]['RECT_HEIGHT'] = data['RECT_HEIGHT']
                weapon_data[dir]['OFFSET_X'] = data['OFFSET_X']
                weapon_data[dir]['OFFSET_Y'] = data['OFFSET_Y']
                weapon_data[dir]['PATRONS'] = data['PATRONS']
                weapon_data[dir]['RELOAD_T'] = data['RELOAD_T']
            except yaml.YAMLError as exc:
                print(exc)
        for filename in os.listdir(os.path.join(path, dir)):
            if not '.png' in filename:
                continue
            state = filename.replace('.png', '')
            sprites_dict[state + "_right"] = []
            sprites_dict[state + "_left"] = []
            sprite_sheet = pygame.image.load(os.path.join(path, dir,filename))
            sprites_count = sprite_sheet.get_width() // weapon_data[dir]['RECT_WIDTH']
            for i in range(sprites_count):
                sprite = sprite_sheet.subsurface((weapon_data[dir]['RECT_WIDTH'] * i, 0),
                                                 (weapon_data[dir]['RECT_WIDTH'], weapon_data[dir]['RECT_HEIGHT']))
                sprite = pygame.transform.scale(sprite, (weapon_data[dir]['RECT_WIDTH'] * scale, weapon_data[dir]['RECT_HEIGHT'] * scale))
                sprites_dict[state + "_right"].append(sprite)
                sprites_dict[state + "_left"].append(pygame.transform.flip(sprite, True, False))
    return sprites_dict, weapon_data

print(load_weapon_sprites('WeaponSprites', 1))

class Weapon():
    def __init__(self, name, pos):
        self.sprite: pygame.Surface = None
        self.name = name
        self.rectangle = None
        self.x = pos[0]
        self.y = pos[1]

        self.rectangle = pygame.rect.Rect(pos, )
        all_wepons_sprites = load_weapon_sprites('WeaponSprites', 1)

    def update_sprite(self, direction):
        self.sprite = self.name + direction



    def draw(self, screen, coords):
        screen.blit(self.sprite, coords)