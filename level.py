import os
import xml.etree.ElementTree as ET
from fnmatch import fnmatch
from typing import Protocol

import pygame

from config import WIDTH, HEIGHT


def load_map(name: str):
    path = os.path.join("data", "levels", name)

    map_xml = None
    for filename in os.listdir(path):
        if fnmatch(filename, '*.tmx'):
            map_xml = ET.parse(os.path.join(path, filename))

    if map_xml is None:
        raise Exception

    map_xml_root = map_xml.getroot()

    tileset_source = os.path.join(path, map_xml_root.find('tileset').get('source'))
    tileset_xml = ET.parse(tileset_source)
    tileset_xml_root = tileset_xml.getroot()

    tilewidth = int(tileset_xml_root.get('tilewidth'))
    tileheight = int(tileset_xml_root.get('tileheight'))
    image_source = os.path.join(path, tileset_xml_root.find('image').get('source'))
    image = pygame.image.load(image_source)
    tiles_images: list[pygame.Surface] = []

    animations: dict[int, int] = dict()  # Какая картинка следует за текущей

    for tile in tileset_xml_root.findall('tile'):
        tile_id = int(tile.get('id'))
        next_tile_id = int(tile.find('properties').find('property').get('value'))
        animations[tile_id] = next_tile_id

    for i in range(image.get_height() // tileheight):
        for j in range(image.get_width() // tilewidth):
            tiles_images.append(image.subsurface(j * tilewidth, i * tileheight, tilewidth, tileheight))
    tiles_images.append(pygame.Surface((tilewidth, tileheight)))  # Последний тайл (с id = -1) прозрачный
    tiles_images[-1].set_colorkey((0, 0, 0))

    Tile.tile_images = tiles_images
    Tile.animations = animations

    map_width = int(map_xml_root.get('width'))
    map_height = int(map_xml_root.get('height'))
    scale = int(map_xml_root.find('properties').find('property').get('value'))
    layers: list[Layer] = []
    animated_tiles: list[Tile] = []

    for layer in map_xml_root.findall('layer'):
        tiles: list[Tile] = []
        data = layer.find('data').text
        tile_ids = list(map(int, data.split(',')))
        has_collision = True if (layer.find('properties').find('property').get('value') == 'true') else False
        for i, tile_id in enumerate(tile_ids):
            tile_x = i % map_width
            tile_y = i // map_width
            tile = Tile(tilewidth * tile_x, tileheight * tile_y, tilewidth, tileheight,
                        tile_id, tile_id - 1, has_collision)
            tile.animated = (tile.image_id in animations.keys())
            animated_tiles.append(tile)
            tiles.append(tile)
        layers.append(Layer(has_collision, tiles))

    objects = dict()
    objects['rectangles'], objects['points'] = [], []
    for objectgroup in map_xml_root.findall('objectgroup'):
        for game_object in objectgroup.findall('object'):
            object_name = game_object.get('name')
            if game_object.find('point') is not None:
                x, y = game_object.get('x'), game_object.get('y')
                objects['points'].append(GameObjectPoint(int(float(x)), int(float(y)), object_name))
            elif game_object.find('ellipse') is not None:
                pass
            elif game_object.find('polygon') is not None:
                pass
            else:
                x, y = game_object.get('x'), game_object.get('y')
                width, height = game_object.get('width'), game_object.get('height')
                objects['rectangles'].append(
                    GameObjectRect(int(float(x)), int(float(y)), int(float(width)), int(float(height)), object_name))

    info = dict()
    info['scale'] = scale
    info['width'] = map_width
    info['height'] = map_height
    info['tile_width'] = tilewidth
    info['tile_height'] = tileheight
    return layers, objects, info, animated_tiles


class Collidable(Protocol):
    rect: pygame.Rect
    mask: pygame.mask.Mask


class Level:
    def __init__(self, name: str):
        self.layers, self.objects, self.info, self.animated_tiles = load_map(name)
        self.scale = self.info['scale']
        self.radius = 500

    def draw(self, screen: pygame.Surface, offset_x, offset_y, pos_x, pos_y):
        visible_tiles = self.get_visible_tiles(offset_x, offset_y)
        for layer in self.layers:
            for tile_number in visible_tiles:
                tile = layer.tiles[tile_number]
                tile.draw(screen, offset_x, offset_y, self.scale)

    def update(self, time_delta):
        for tile in self.animated_tiles:
            tile.update(time_delta)

    def get_visible_tiles(self, offset_x, offset_y):
        tile_numbers = []
        i_start = int(max(0, -offset_y // (self.info['tile_height'])))
        j_start = int(max(0, -offset_x // (self.info['tile_width'])))
        i_end = int(min(self.info['height'], i_start + HEIGHT // (self.info['tile_height'] * self.scale) + 2))
        j_end = int(min(self.info['width'], j_start + WIDTH // (self.info['tile_width'] * self.scale) + 2))
        for i in range(i_start, i_end):
            for j in range(j_start, j_end):
                tile_number = int(i * self.info['width'] + j)
                tile_numbers.append(tile_number)
        return tile_numbers

    def collide_sprite(self, sprite: Collidable):
        collided = []
        rect = sprite.rect
        for layer in self.layers:
            if not layer.has_collision:
                continue
            for i in range(self.info['height']):
                for j in range(self.info['width']):
                    tile = layer.tiles[i * self.info['width'] + j]
                    if tile.rect.bottom <= rect.top:
                        break
                    if tile.rect.top >= rect.bottom:
                        return collided

                    if tile.rect.right <= rect.left:
                        continue
                    if tile.rect.left >= rect.right:
                        break

                    if tile.tile_id == 0:
                        continue
                    if pygame.sprite.collide_mask(tile, sprite):
                        collided.append(tile)
        return collided

    def collide_point(self, x, y):
        collided = []
        for layer in self.layers:
            if not layer.has_collision:
                continue
            tile_number = int(y // self.info['tile_height'] * self.info['width'] + x // self.info['tile_width'])
            if tile_number < 0 or tile_number >= len(layer.tiles):
                break
            tile = layer.tiles[tile_number]
            if tile.mask.get_at((x % self.info['tile_width'], y % self.info['tile_height'])):
                collided.append(tile)

        return collided


class GameObjectRect:
    def __init__(self, x, y, width, height, name):
        self.name = name
        self.rect = pygame.Rect((x, y), (width, height))


class GameObjectPoint:
    def __init__(self, x, y, name):
        self.name = name
        self.x, self.y = x, y


class Layer:
    def __init__(self, has_collision, tiles):
        self.has_collision = has_collision
        self.tiles: list[Tile] = tiles


class Tile(pygame.sprite.Sprite):
    tile_images: list[pygame.Surface]
    animations: dict[int, int]

    def __init__(self, x, y, width, height, tile_id, image_id: int, has_collision):
        super().__init__()

        self.has_collision = has_collision
        self.animated = False

        self.tile_id = tile_id
        self.image_id = image_id

        self.rect = pygame.Rect((x, y), (width, height))
        self.mask = pygame.mask.from_surface(Tile.tile_images[self.image_id])

        self.timer = 0
        self.delay = 0.15

    def visible(self, offset_x, offset_y, scale):
        return not (self.rect.bottom + offset_y <= 0 or self.rect.top + offset_y >= HEIGHT // scale or
                    self.rect.right + offset_x <= 0 or self.rect.left + offset_x >= WIDTH // scale)

    def update(self, time_delta):
        if not self.animated:
            return

        self.timer += time_delta
        if self.timer < self.delay:
            return

        self.image_id = Tile.animations[self.image_id]
        self.mask = pygame.mask.from_surface(Tile.tile_images[self.image_id])  # TODO надо ли?
        self.timer = 0

    def distance(self, pos_x, pos_y):
        return ((pos_x - self.rect.x) ** 2 + (pos_y - self.rect.y) ** 2) ** 0.5

    def draw(self, screen: pygame.Surface, offset_x, offset_y, scale):
        screen.blit(Tile.tile_images[self.image_id], (self.rect.x + offset_x, self.rect.y + offset_y))
