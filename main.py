import socket

import pygame

import config
from config import WIDTH, HEIGHT, MAX_FPS, FULLSCREEN
from network import Network

pygame.init()

if FULLSCREEN:
    config.HEIGHT = pygame.display.Info().current_h
    config.WIDTH = pygame.display.Info().current_w
    WIDTH = config.WIDTH
    HEIGHT = config.HEIGHT
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)

else:
    screen = pygame.display.set_mode((WIDTH, HEIGHT))

clock = pygame.time.Clock()

from event_codes import *
from level import Level, Tile
from player import Player, Bullet
from screens import Menu, ConnectToServerMenu, LoadingScreen, MessageScreen, StartServerMenu


class Camera:

    def __init__(self, focus: Player):
        self.focus = focus
        self.x, self.y = focus.get_position()
        self.rect = [int(self.x), int(self.y), 45, 45]

    def update(self, time_delta):
        new_x, new_y = self.focus.get_position()

        if self.is_in_rect() == 'x_left':
            self.x += (new_x - self.rect[0])
            self.rect[0] = new_x

        if self.is_in_rect() == 'x_right':
            self.x += new_x - (self.rect[0] + self.rect[2])
            self.rect[0] = new_x - self.rect[2]

        if self.is_in_rect() == 'y_up':
            self.y += new_y - self.rect[1]
            self.rect[1] = new_y

        if self.is_in_rect() == 'y_down':
            self.y += new_y - (self.rect[1] + self.rect[3])
            self.rect[1] = new_y - self.rect[3]

    def get_coords(self):
        return self.x, self.y

    def is_in_rect(self):
        player_x, player_y = self.focus.get_position()
        if not (self.rect[0] <= player_x):
            return 'x_left'
        if not (player_x <= self.rect[0] + self.rect[2]):
            return 'x_right'
        if not (self.rect[1] <= player_y):
            return 'y_up'
        if not (player_y <= self.rect[1] + self.rect[3]):
            return 'y_down'
        else:
            return 'ok'


class Game:
    def __init__(self, clock, level_name="", player_position=(0, 0)):
        self.clock: pygame.time.Clock = clock
        self.offset_x, self.offset_y = 0, 0

        self.level = Level(level_name)
        self.player = Player(player_position, 1, "New_Knight")
        self.players: dict[int, Player] = {}
        self.bullets = {}

        self.camera = Camera(self.player)

    def update(self):
        fps = self.clock.get_fps()
        time_delta = 1 / max(1, fps)

        for bullet_id, bullet in self.bullets.items():
            bullet.update(time_delta)

        self.player.loop(time_delta)
        self.input_handle(time_delta)
        self.camera.update(time_delta)

    def draw(self, screen):
        image = pygame.Surface((WIDTH // self.level.scale, HEIGHT // self.level.scale))

        self.update()
        self.offset_x = -self.camera.x + WIDTH // self.level.scale // 2
        self.offset_y = -self.camera.y + HEIGHT // self.level.scale // 2

        self.level.draw(image, self.offset_x, self.offset_y, *self.player.get_position())
        for player_id, player in self.players.items():
            player.draw(image, self.offset_x, self.offset_y)
        self.player.draw(image, self.offset_x, self.offset_y)

        for bullet_id, bullet in self.bullets.items():
            bullet.draw(image, self.offset_x, self.offset_y)

        image = pygame.transform.scale_by(image, self.level.scale)
        screen.blit(image, (0, 0))

    def input_handle(self, time_delta):
        keys = pygame.key.get_pressed()
        collide_vertical = self.collision_y()
        collide_left: list[Tile] = self.collision_x(min(-1, -int(self.player.v * time_delta)) - 1)
        collide_right: list[Tile] = self.collision_x(max(1, int(self.player.v * time_delta)) + 1)

        self.player.vx = 0
        if keys[pygame.K_a] and not collide_left:
            self.player.move_left()
        elif keys[pygame.K_a] and collide_left:
            left = min(self.player.get_left(), max([tile.rect.right for tile in collide_left]))
            self.player.set_left(left)

        if keys[pygame.K_d] and not collide_right:
            self.player.move_right()
        elif keys[pygame.K_d] and collide_right:
            right = max(self.player.get_right(), min([tile.rect.left for tile in collide_right]))
            self.player.set_right(right)

        if keys[pygame.K_SPACE] and not collide_vertical:
            self.player.jump()
        if keys[pygame.K_UP]:
            self.level.scale += 0.05
            self.level.scale = min(self.level.scale, 8)
        if keys[pygame.K_DOWN]:
            self.level.scale -= 0.05
            self.level.scale = max(self.level.scale, 0.5)
        if keys[pygame.K_LEFT]:
            self.level.radius += 4
            pass
        if keys[pygame.K_RIGHT]:
            self.level.radius -= 4
            pass

    def collision_x(self, dx):
        self.player.move(dx, 0)
        collided = self.level.collide_sprite(self.player)
        self.player.move(-dx, 0)
        return collided

    def collision_y(self):
        collided = self.level.collide_sprite(self.player)
        if not collided:
            return collided

        lowest_point = collided[0].rect.bottom
        highest_point = collided[0].rect.top
        for tile in collided:
            lowest_point = max(lowest_point, tile.rect.bottom)
            highest_point = min(highest_point, tile.rect.top)

        if self.player.vy > 0:
            self.player.set_bottom(highest_point)
            self.player.touch_down()
        elif self.player.vy < 0:
            self.player.set_top(lowest_point)
            self.player.touch_ceil()

        return collided

    def apply(self, data):
        pass


class GameManager:
    from network import DataPacket

    def __init__(self):
        self.player_flags = set()
        self.network: Network = None
        self.game: Game = None
        self.game_started = False

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
            self.send_initial_info()
            self.game_started = True

        if data_packet.data_type == self.DataPacket.PLAYERS_INFO:
            for player_id, data in data_packet.data.items():
                player_id = int(player_id)
                if player_id == self.network.id:
                    continue

                if player_id not in self.game.players.keys():
                    self.game.players[player_id] = Player((0, 0), 1, "New_Knight")

                self.game.players[player_id].apply(data)

            for player_id in list(self.game.players.keys()):
                if str(player_id) not in data_packet.data.keys():
                    self.game.players.pop(player_id)

        if data_packet.data_type == self.DataPacket.NEW_BULLET_FROM_SERVER:
            bullet_id, bullet = data_packet.data
            bullet_id = int(bullet_id)
            self.game.bullets[bullet_id] = Bullet((bullet[0], bullet[1]), (bullet[2], bullet[3]))

        if data_packet.data_type == self.DataPacket.DELETE_BULLET_FROM_SERVER:
            bullet_id = data_packet.data
            bullet_id = int(bullet_id)
            if bullet_id in self.game.bullets.keys():
                self.game.bullets.pop(bullet_id)

        if data_packet.data_type == self.DataPacket.HEALTH_POINTS:
            self.game.player.hp = data_packet.data

    def handle_game_objects_collision(self):
        for object in self.game.level.objects['rectangles']:
            if pygame.rect.Rect.colliderect(object.rect, self.game.player.rect):
                if self.DataPacket.FLAG_READY not in self.player_flags:
                    self.player_flags.add(self.DataPacket.FLAG_READY)
                    response_data = {'id': self.network.id, 'data': self.DataPacket.FLAG_READY}
                    response = self.DataPacket(self.DataPacket.ADD_PLAYER_FLAG, response_data)
                    self.network.send(response)
            else:
                if self.DataPacket.FLAG_READY in self.player_flags:
                    self.player_flags.remove(self.DataPacket.FLAG_READY)
                    response_data = {'id': self.network.id, 'data': self.DataPacket.FLAG_READY}
                    response = self.DataPacket(self.DataPacket.REMOVE_PLAYER_FLAG, response_data)
                    self.network.send(response)

    def shoot_bullet(self):
        if self.game.player.hp <= 0:
            return
        speed = 1200
        bullet = Bullet(self.game.player.get_center_position(),
                        (speed if (self.game.player.direction == 'right') else -speed, 0))
        bullet_data = {'id': self.network.id, 'data': bullet.encode()}
        response = self.DataPacket(self.DataPacket.NEW_BULLET_FROM_CLIENT, bullet_data)
        self.network.send(response)

    def send_initial_info(self):
        player_data = {'id': self.network.id, 'data': self.game.player.initial_info()}
        response = self.DataPacket(self.DataPacket.INITIAL_INFO, player_data)
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


def validate_address(user_input):
    if ':' not in user_input:
        raise ValueError('Not a valid server address')
    server, port = user_input.split(':')
    socket.inet_aton(server)
    try:
        port = int(port)
    except Exception:
        raise ValueError('Not a valid port number')
    if port < 1 or port > 65535:
        raise ValueError('Not a valid port number')
    return server, port


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

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    if game_manager.game_started:
                        game_manager.shoot_bullet()

            if type(current_screen) == ConnectToServerMenu:
                current_screen.event_handle(event)
            if type(current_screen) == StartServerMenu:
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
                    server, port = validate_address(event.dict['input'])
                    current_screen = game_manager
                    game_manager.connect(server, port)
                except Exception as e:
                    current_screen = MessageScreen(str(e), pygame.event.Event(OPEN_CONNECTION_MENU_EVENT))
                    print(e)
            if event.type == START_SERVER_MENU_EVENT:
                current_screen = StartServerMenu()

        current_screen.draw(screen)
        pygame.display.set_caption(f"{int(clock.get_fps())} FPS")
        pygame.display.flip()

    pygame.quit()
    quit(0)


if __name__ == "__main__":
    main(screen)
