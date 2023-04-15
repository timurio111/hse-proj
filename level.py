import xml.etree.ElementTree as ET
import pygame
from fnmatch import fnmatch
from config import WIDTH, HEIGHT

import os


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

    for i in range(image.get_height() // tileheight):
        for j in range(image.get_width() // tilewidth):
            tiles_images.append(image.subsurface(j * tilewidth, i * tileheight, tilewidth, tileheight))

    map_width = int(map_xml_root.get('width'))
    map_height = int(map_xml_root.get('height'))
    scale = int(map_xml_root.find('properties').find('property').get('value'))
    tiles: list[Tile] = []
    for layer in map_xml_root.findall('layer'):
        data = layer.find('data').text
        tile_ids = list(map(int, data.split(',')))
        has_collision = True if (layer.find('properties').find('property').get('value') == 'true') else False
        for i, tile_id in enumerate(tile_ids):
            tile_x = (i) % (map_width)
            tile_y = (i) // (map_width)
            tile = Tile(tilewidth * tile_x, tileheight * tile_y,
                        tilewidth, tileheight, tiles_images[tile_id - 1], has_collision)
            tiles.append(tile)

    objects: list[GameObject] = []
    for objectgroup in map_xml_root.findall('objectgroup'):
        for object in objectgroup.findall('object'):
            x, y = object.get('x'), object.get('y')
            width, height = object.get('width'), object.get('height')
            objects.append(GameObject(int(x), int(y), int(width), int(height)))

    return tiles, scale, objects


class Level:
    def __init__(self, name: str):
        self.tiles, self.scale, self.objects = load_map(name)
        self.obstacles = [tile for tile in self.tiles if tile.has_collision]
        self.visible_tiles = []
        self.fuck = 200

    def update(self, offset_x, offset_y):
        self.visible_tiles.clear()
        for tile in self.tiles:
            if tile.visible(offset_x, offset_y, self.scale):
                self.visible_tiles.append(tile)

    def get_near_tiles(self, offset_x, offset_y, radius):
        near_tiles = []
        for tile in self.tiles:
            if tile.distance(offset_x, offset_y, self.scale) < radius:
                near_tiles.append(tile)
        return near_tiles

    def draw(self, screen: pygame.Surface, offset_x, offset_y):
        self.update(offset_x, offset_y)
        for tile in self.tiles:
            if tile.distance(offset_x, offset_y, self.scale) < self.fuck:
                tile.draw(screen, offset_x, offset_y, self.scale)
        return
        for tile in self.visible_tiles:
            tile.draw(screen, offset_x, offset_y, self.scale)


class GameObject(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height):
        super().__init__()
        self.rect = pygame.Rect((x, y), (width, height))


class Tile(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height, image: pygame.Surface, has_collision, name=None):
        super().__init__()
        self.has_collision = has_collision
        self.rect = pygame.Rect((x, y), (width, height))
        self.image = image
        self.name = name
        self.mask = pygame.mask.from_surface(self.image)

    def visible(self, offset_x, offset_y, scale):
        return not (self.rect.bottom + offset_y <= 0 or self.rect.top + offset_y >= HEIGHT // scale or
                    self.rect.right + offset_x <= 0 or self.rect.left + offset_x >= WIDTH // scale)

    def distance(self, offset_x, offset_y, scale):
        x = -offset_x + WIDTH // scale // 2
        y = -offset_y + HEIGHT // scale // 2
        return ((x - self.rect.x) ** 2 + (y - self.rect.y) ** 2) ** 0.5

    def draw(self, screen: pygame.Surface, offset_x, offset_y, scale):
        screen.blit(self.image, (self.rect.x + offset_x, self.rect.y + offset_y))
