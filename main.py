import socket
import pygame
import os
import config
from time import time
from button import Button, TextInput
from level import Level
from player import Player
from collections import deque
from network import Network
from config import WIDTH, HEIGHT, MAX_FPS, FULLSCREEN
import json

pygame.init()
pygame.scrap.init()
pygame.scrap.set_mode(pygame.SCRAP_CLIPBOARD)

if FULLSCREEN:
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
    config.HEIGHT = screen.get_height()
    config.WIDTH = screen.get_width()
else:
    screen = pygame.display.set_mode((WIDTH, HEIGHT))

EXIT_GAME_EVENT = pygame.QUIT
START_GAME_EVENT = pygame.USEREVENT + 1
OPEN_MAIN_MENU_EVENT = pygame.USEREVENT + 2
LOADING_SCREEN_EVENT = pygame.USEREVENT + 3
OPEN_CONNECTION_MENU_EVENT = pygame.USEREVENT + 4
CONNECT_TO_SERVER_EVENT = pygame.USEREVENT + 5

clock = pygame.time.Clock()


def load_background(image_name: str) -> pygame.Surface:
    path = os.path.join("data", "Background", image_name)
    image = pygame.transform.scale(pygame.image.load(path), (WIDTH, HEIGHT))
    return image.convert()


class Menu:
    def __init__(self):
        self.visible = True
        self.background = load_background("gradient2.png")
        self.button_start_server = Button(size=(WIDTH // 2, HEIGHT // 12),
                                          pos=(WIDTH // 2 - WIDTH // 4, HEIGHT // 2),
                                          event=pygame.event.Event(START_GAME_EVENT),
                                          text="Start server",
                                          font='data/fonts/menu_font.ttf')
        self.button_connect = Button(size=(WIDTH // 2, HEIGHT // 12),
                                     pos=(WIDTH // 2 - WIDTH // 4, HEIGHT // 2 + HEIGHT // 8),
                                     event=pygame.event.Event(OPEN_CONNECTION_MENU_EVENT),
                                     text="Connect to server",
                                     font='data/fonts/menu_font.ttf')
        self.button_exit = Button(size=(WIDTH // 2, HEIGHT // 12),
                                  pos=(WIDTH // 2 - WIDTH // 4, HEIGHT // 2 + 2 * HEIGHT // 8),
                                  event=pygame.event.Event(EXIT_GAME_EVENT),
                                  text="Quit", font='data/fonts/menu_font.ttf')

    def draw(self, screen: pygame.Surface):
        screen.blit(self.background, (0, 0))
        self.button_connect.draw(screen, 1)
        self.button_start_server.draw(screen, 1)
        self.button_exit.draw(screen, 1)


class ConnectToServerMenu:
    def __init__(self):
        self.background = load_background('gradient1.png')
        self.button_back = Button(size=(WIDTH // 5, 40),
                                  pos=(10, 10),
                                  text="Back",
                                  event=pygame.event.Event(OPEN_MAIN_MENU_EVENT))
        self.text_input_address = TextInput(size=(WIDTH // 1.1, 40),
                                            pos=((WIDTH - WIDTH // 1.1) // 2, HEIGHT // 2),
                                            hint="server address",
                                            text="",
                                            font='data/fonts/menu_font.ttf')

        self.button_start_game = Button(size=(WIDTH // 5, 40),
                                        pos=(WIDTH - WIDTH // 5 - 10, HEIGHT - 40 - 10),
                                        text="Connect",
                                        event=pygame.event.Event(CONNECT_TO_SERVER_EVENT, ))

    def event_handle(self, event):
        self.text_input_address.event_handle(event)
        self.button_start_game.event.dict['input'] = self.text_input_address.text

    def draw(self, screen: pygame.Surface):
        screen.blit(self.background, (0, 0))
        self.text_input_address.draw(screen, 1)
        self.button_back.draw(screen, 1)
        self.button_start_game.draw(screen, 1)


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
    def __init__(self, clock, level_name="", player_position=(0, 0)):
        self.clock: pygame.time.Clock = clock
        self.offset_x, self.offset_y = 0, 0
        self.visible = True
        self.level = Level(level_name)
        self.player = Player(player_position, 1, "Character")
        self.players: dict[int, Player] = {}
        self.camera = Camera(self.player)

    def update(self):
        fps = self.clock.get_fps()
        time_delta = 1 / max(1, fps)

        self.player.loop(time_delta)
        self.input_handle(time_delta)
        self.camera.update(time_delta)

    def draw(self, screen):
        image = pygame.Surface((WIDTH // self.level.scale, HEIGHT // self.level.scale))

        self.update()
        self.offset_x = -self.camera.x + WIDTH // self.level.scale // 2
        self.offset_y = -self.camera.y + HEIGHT // self.level.scale // 2
        self.level.draw(image, self.offset_x, self.offset_y)
        for id_, player in self.players.items():
            player.draw(image, self.offset_x, self.offset_y)
        self.player.draw(image, self.offset_x, self.offset_y)

        image = pygame.transform.scale_by(image, self.level.scale)
        screen.blit(image, (0, 0))

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

    def apply(self, data):
        pass


class LoadingScreen:
    def __init__(self, text='Waiting...'):
        self.set_text(text)
        self.visible = False

    def set_text(self, text):
        self.text = text
        font = pygame.font.Font(None, 100)
        self.image = pygame.Surface((WIDTH, HEIGHT))
        self.image.fill((0, 0, 0))
        text_image = font.render(self.text, True, (255, 255, 255))
        self.image.blit(text_image, (WIDTH // 2 - text_image.get_width() // 2,
                                     HEIGHT // 2 - text_image.get_height() // 2))

    def draw(self, screen):
        screen.blit(self.image, (0, 0))


class GameManager:
    from network import DataPacket

    def __init__(self):
        self.player_flags = set()
        self.network: Network = None
        self.game = None

    def connect(self, server, port):
        self.network = Network(server, port, self.callback)
        self.network.authorize()

    def callback(self, client_socket: socket.socket, mask):

        data_bytes = b''
        while True:
            byte = client_socket.recv(1)
            if byte == b'\n':
                break
            data_bytes += byte
        data_packet = self.DataPacket.from_bytes(data_bytes)

        if data_packet.data_type == self.DataPacket.AUTH:
            self.network.id = data_packet.data['id']

        if data_packet.data_type == self.DataPacket.GAME_INFO:
            self.game = Game(clock, data_packet['level_name'], data_packet['position'])

        if data_packet.data_type == self.DataPacket.PLAYERS_INFO:
            for player_id, data in data_packet.data.items():
                player_id = int(player_id)
                # if player_id == self.network.id:
                #    continue

                if player_id not in self.game.players.keys():
                    self.game.players[player_id] = Player((0, 0), 1, "Character")

                self.game.players[player_id].apply(data)

            for player_id in list(self.game.players.keys()):
                if str(player_id) not in data_packet.data.keys():
                    self.game.players.pop(player_id)

    def handle_game_objects_collision(self):
        for object in self.game.level.objects:
            if pygame.rect.Rect.colliderect(object.rect, self.game.player.rect):
                if self.DataPacket.FLAG_READY not in self.player_flags:
                    print('ready')
                    self.player_flags.add(self.DataPacket.FLAG_READY)
                    response_data = {'id': self.network.id, 'data': self.DataPacket.FLAG_READY}
                    response = self.DataPacket(self.DataPacket.ADD_PLAYER_FLAG, response_data)
                    self.network.send(response)
            else:
                if self.DataPacket.FLAG_READY in self.player_flags:
                    print('not ready')
                    self.player_flags.remove(self.DataPacket.FLAG_READY)
                    response_data = {'id': self.network.id, 'data': self.DataPacket.FLAG_READY}
                    response = self.DataPacket(self.DataPacket.REMOVE_PLAYER_FLAG, response_data)
                    self.network.send(response)

    def send_player_data(self):
        player_data = {'id': self.network.id, 'data': self.game.player.encode()}
        response = self.DataPacket(self.DataPacket.CLIENT_PLAYER_INFO, player_data)
        self.network.send(response)

    def receive(self):
        self.network.receive()

    def draw(self, screen: pygame.Surface):
        self.receive()
        if self.game is None:
            LoadingScreen().draw(screen)
        else:
            self.handle_game_objects_collision()
            self.send_player_data()
            self.game.draw(screen)


def main(screen):
    current_screen = Menu()
    game_manager = GameManager()
    run = True
    while run:
        clock.tick(MAX_FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
                break

            if type(current_screen) == ConnectToServerMenu:
                current_screen.event_handle(event)

            if event.type == LOADING_SCREEN_EVENT:
                current_screen = LoadingScreen()
            if event.type == START_GAME_EVENT:
                pass
            if event.type == OPEN_CONNECTION_MENU_EVENT:
                current_screen = ConnectToServerMenu()
            if event.type == OPEN_MAIN_MENU_EVENT:
                current_screen = Menu()
            if event.type == CONNECT_TO_SERVER_EVENT:

                try:
                    user_input = event.dict['input']

                    if ':' not in user_input:
                        raise ValueError('Not a valid server address')
                    server, port = user_input.split(':')
                    socket.inet_aton(server)
                    port = int(port)
                    if port < 1 or port > 65535:
                        raise ValueError('Not a valid port number')

                    current_screen = game_manager
                    game_manager.connect(server, port)
                except Exception as e:
                    print(e)

        current_screen.draw(screen)
        pygame.display.set_caption(f"{int(clock.get_fps())} FPS")
        pygame.display.flip()

    pygame.quit()
    quit(0)


if __name__ == "__main__":
    main(screen)
