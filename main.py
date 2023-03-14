import pygame
import os
import config
from button import Button
from level import Level
from player import Player
from network import Network
from config import WIDTH, HEIGHT, MAX_FPS, FULLSCREEN
import json

pygame.init()

if FULLSCREEN:
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
    config.HEIGHT = screen.get_height()
    config.WIDTH = screen.get_width()
else:
    screen = pygame.display.set_mode((WIDTH, HEIGHT))

EXIT_GAME_EVENT = pygame.event.Event(pygame.QUIT)
START_GAME_EVENT = pygame.event.Event(pygame.USEREVENT + 1)
GO_TO_MENU_EVENT = pygame.event.Event(pygame.USEREVENT + 2)


def load_background(image_name: str) -> pygame.Surface:
    path = os.path.join("data", "Background", image_name)
    image = pygame.transform.scale(pygame.image.load(path), (WIDTH, HEIGHT))
    return image.convert()


class Menu:
    def __init__(self):
        self.visible = True
        self.background = load_background("gradient2.png")
        self.button_start = Button(size=(WIDTH // 4, HEIGHT // 12), pos=(WIDTH // 2 - WIDTH // 8, HEIGHT // 2),
                                   event=START_GAME_EVENT, text="Play", font='data/fonts/menu_font.ttf')
        self.button_exit = Button(size=(WIDTH // 4, HEIGHT // 12),
                                  pos=(WIDTH // 2 - WIDTH // 8, HEIGHT // 2 + HEIGHT // 6), event=EXIT_GAME_EVENT,
                                  text="Quit", font='data/fonts/menu_font.ttf')

    def draw(self, screen):
        screen.blit(self.background, (0, 0))
        self.button_start.draw(screen, 1)
        self.button_exit.draw(screen, 1)


class Camera:

    def __init__(self, focus: Player):
        self.focus = focus
        self.x, self.y = focus.get_position()

    def update(self, time_delta):
        new_x, new_y = self.focus.get_position()
        dx = new_x - self.x
        dy = new_y - self.y

        self.x += dx // 1
        self.y += dy // 1

    def get_coords(self):
        return self.x, self.y


class Game:
    def __init__(self, clock):
        self.clock: pygame.time.Clock = clock
        self.offset_x, self.offset_y = 0, 0
        self.visible = True
        self.btn_back = Button((20, 10), (10, 10), "To menu", event=GO_TO_MENU_EVENT, font='data/fonts/menu_font.ttf')
        self.level = Level('verylongmap')
        self.player = Player((100, 0), 1, "Character")
        self.players: dict[int, Player] = {}
        self.network = Network()
        self.camera = Camera(self.player)

    def update(self):
        fps = self.clock.get_fps()
        if fps == 0:
            return
        time_delta = 1 / max(1, fps)

        self.player.loop(time_delta)
        self.input_handle(time_delta)
        self.camera.update(time_delta)
        data = self.player.encode()
        reply = self.network.send(data)
        t = json.loads(reply)


        for k, v in t.items():
            k = int(k)
            v = json.loads(v)
            if k == self.network.id:
                continue
            if k not in self.players.keys():
                self.players[k] = Player((0, 0), 1, "Character")
            self.players[k].apply(v)

        for k in list(self.players.keys()):
            if str(k) not in t.keys():
                self.players.pop(k)


    def draw(self, screen):
        self.update()
        self.offset_x = -self.camera.x + WIDTH // self.level.scale // 2
        self.offset_y = -self.camera.y + HEIGHT // self.level.scale // 2
        self.level.draw(screen, self.offset_x, self.offset_y)
        for player in self.players.values():
            player.draw(screen, self.offset_x, self.offset_y)

    def input_handle(self, time_delta):
        keys = pygame.key.get_pressed()
        collide_vertical = self.collision_y()
        collide_left = self.collision_x(min(-1, -int(self.player.v * time_delta)) * 2)
        collide_right = self.collision_x(max(1, int(self.player.v * time_delta)) * 2)

        self.player.vx = 0
        if keys[pygame.K_a] and not collide_left:
            self.player.move_left()
        elif keys[pygame.K_a] and collide_left:
            l, r = 1, int(self.player.v * time_delta) * 2
            while r - l > 1:
                m = (l + r) // 2
                if self.collision_x(-m):
                    r = m
                else:
                    l = m
            if l > 1:
                self.player.move(-l / 4, 0)

        if keys[pygame.K_d] and not collide_right:
            self.player.move_right()
        elif keys[pygame.K_d] and collide_right:
            l, r = 1, int(self.player.v * time_delta) * 2
            while r - l > 1:
                m = (l + r) // 2
                if self.collision_x(m):
                    r = m
                else:
                    l = m
            if l > 1:
                self.player.move(l / 4, 0)

        if keys[pygame.K_SPACE] and not collide_vertical:
            self.player.jump()
        if keys[pygame.K_UP]:
            self.level.scale += 0.05
            self.level.scale = min(self.level.scale, 8)
        if keys[pygame.K_DOWN]:
            self.level.scale -= 0.05
            self.level.scale = max(self.level.scale, 0.5)
        if keys[pygame.K_LEFT]:
            self.level.fuck += 4
            pass
        if keys[pygame.K_RIGHT]:
            self.level.fuck -= 4
            pass

    def collision_x(self, dx):
        self.player.move(dx, 0)
        collided = False
        for tile in self.level.visible_tiles:
            if not tile.has_collision:
                continue
            if pygame.sprite.collide_mask(self.player, tile):
                collided = True
                break
        self.player.move(-dx, 0)
        return collided

    def collision_y(self):
        collided = False
        for tile in self.level.visible_tiles:
            if not tile.has_collision:
                continue
            if pygame.sprite.collide_mask(self.player, tile):
                collided = True
                if self.player.vy > 0:
                    self.player.rect.bottom = tile.rect.top
                    self.player.y = self.player.rect.top
                    self.player.touch_down()
                elif self.player.vy < 0:
                    self.player.touch_ceil()
                    self.player.rect.top = tile.rect.bottom - self.player.sprite_offset_y
        return collided


def main(screen):
    clock = pygame.time.Clock()

    menu = Menu()
    game = Game(clock)

    run = True

    while run:
        clock.tick(MAX_FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
                break
            if event == START_GAME_EVENT:
                menu.visible = False
                game.visible = True
            if event == GO_TO_MENU_EVENT:
                menu.visible = True
                game.visible = False

        if menu.visible:
            menu.draw(screen)
        elif game.visible:
            image = pygame.Surface((WIDTH // game.level.scale, HEIGHT // game.level.scale))
            game.draw(image)
            image = pygame.transform.scale_by(image, game.level.scale)
            screen.blit(image, (0, 0))

        pygame.display.set_caption(f"{int(clock.get_fps())} FPS")
        pygame.display.flip()

    pygame.quit()
    quit(0)


if __name__ == "__main__":
    main(screen)
