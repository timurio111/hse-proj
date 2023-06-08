from __future__ import annotations

import pygame

import config
from config import WIDTH, HEIGHT, MAX_FPS, FULLSCREEN
from network import Network

pygame.init()
pygame.mixer.init()

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
from player import Player
from weapon import Weapon, Bullet
from screens import Menu, ConnectToServerMenu, LoadingScreen, MessageScreen, StartServerMenu, SettingsMenu, EndScreen
from sound import SoundCore


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
    def __init__(self, clock: pygame.time.Clock, game_manager: GameManager, level_name="", player_position=(0, 0)):
        self.clock = clock
        self.game_manager = game_manager
        self.offset_x, self.offset_y = 0, 0

        self.level = Level(level_name)
        self.player = Player((0, 0), 1, "Knight")
        self.player.set_right(player_position[0] + self.player.width // 2)
        self.player.set_top(player_position[1])
        self.players: dict[int, Player] = {}
        self.bullets: dict[int, Bullet] = {}
        self.weapons: dict[int, Weapon] = {}

        self.camera = Camera(self.player)

    def update(self):
        fps = self.clock.get_fps()
        time_delta = 1 / max(1, fps)
        for bullet_id, bullet in self.bullets.items():
            bullet.update(time_delta)

        if not self.game_manager.packet_received:
            for player_id, player in self.players.items():
                if player_id == self.game_manager.network.id:
                    continue
                player.loop(time_delta)
                self.collision_y(player)

        self.player.loop(time_delta)
        self.input_handle(time_delta)
        self.camera.update(time_delta)
        self.level.update(time_delta)

        for weapon_id, weapon in self.weapons.items():
            weapon.update(time_delta, self.level)
            weapon.update_sprite(time_delta)

        for player_id, player in self.players.items():
            if player_id == self.game_manager.network.id:
                continue
            if player.weapon.name == 'WeaponNone':
                player.weapon.update_sprite(time_delta)

    def draw(self, screen):
        image = pygame.Surface((WIDTH // self.level.scale, HEIGHT // self.level.scale))

        self.update()
        self.offset_x = -self.camera.x + WIDTH // self.level.scale // 2
        self.offset_y = -self.camera.y + HEIGHT // self.level.scale // 2

        self.level.draw(image, self.offset_x, self.offset_y, *self.player.get_position())
        for player_id, player in self.players.items():
            player.draw(image, self.offset_x, self.offset_y)
        self.player.draw(image, self.offset_x, self.offset_y)

        for weapon_id, weapon in self.weapons.items():
            if not weapon.attached:
                weapon.draw(image, self.offset_x, self.offset_y)

        for bullet_id, bullet in self.bullets.items():
            bullet.draw(image, self.offset_x, self.offset_y)

        image = pygame.transform.scale_by(image, self.level.scale)
        screen.blit(image, (0, 0))

    def input_handle(self, time_delta):
        keys = pygame.key.get_pressed()
        collide_vertical = self.collision_y(self.player)
        collide_left: list[Tile] = self.collision_x(self.player, min(-1, -int(self.player.v * time_delta)) - 1)
        collide_right: list[Tile] = self.collision_x(self.player, max(1, int(self.player.v * time_delta)) + 1)

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

        if keys[pygame.K_RETURN]:
            self.game_manager.shoot_bullet()

    def collision_x(self, player, dx):
        player.move(dx, 0)
        collided = self.level.collide_sprite(player)
        player.move(-dx, 0)
        return collided

    def collision_y(self, player):
        collided = self.level.collide_sprite(player)
        if not collided:
            return collided

        lowest_point = collided[0].rect.bottom
        highest_point = collided[0].rect.top
        for tile in collided:
            lowest_point = max(lowest_point, tile.rect.bottom)
            highest_point = min(highest_point, tile.rect.top)
        if player.vy > 0:
            player.set_bottom(highest_point)
            player.touch_down()
        elif player.vy < 0:
            player.set_top(lowest_point)
            player.touch_ceil()

        return collided

    def apply(self, data):
        pass


class GameManager:
    from network import DataPacket

    game_id = 0

    def __init__(self):
        self.packet_received = True
        self.player_flags = set()
        self.network: Network = None
        self.game: Game = None
        self.game_started = False
        self.webcam_ready = False

    def connect(self, server, port):
        self.network = Network(server, port, self.callback)
        self.network.authorize()

    def callback(self, data_packet: DataPacket, mask):
        game_id = data_packet.headers['game_id']

        if data_packet.data_type == self.DataPacket.WEBCAM_READY:
            self.webcam_ready = True

        if data_packet.data_type == self.DataPacket.WEBCAM_RESPONSE:
            data = data_packet['data']
            if data == 'hands up':
                self.game.player.jump()

        if data_packet.data_type == self.DataPacket.WEBCAM_EXCEPTION:
            raise Exception(data_packet['data'])

        if data_packet.data_type == self.DataPacket.AUTH:
            self.network.id = data_packet.data['id']

        if data_packet.data_type == self.DataPacket.GAME_ALREADY_STARTED:
            raise Exception('Game is already started')

        if data_packet.data_type == self.DataPacket.DISCONNECT:
            event = pygame.event.Event(SHOW_GAME_STATISTICS)
            event.dict['statistics'] = data_packet['statistics']
            pygame.event.post(event)

        if data_packet.data_type == self.DataPacket.GAME_INFO:
            GameManager.game_id = game_id
            self.game = Game(clock, self, data_packet['level_name'], data_packet['position'])
            self.game.player.set_color(data_packet['color'])
            self.send_initial_info()
            self.game_started = True

        if data_packet.data_type == self.DataPacket.PLAYERS_INFO:
            for player_id, data in data_packet.data.items():
                player_id = int(player_id)
                if player_id == self.network.id:
                    continue

                if player_id not in self.game.players.keys():
                    color = data[9]
                    self.game.players[player_id] = Player((0, 0), 1, "Knight", color)

                self.game.players[player_id].apply(data)

            for player_id in list(self.game.players.keys()):
                if str(player_id) not in data_packet.data.keys():
                    self.game.players.pop(player_id)

        if data_packet.data_type == self.DataPacket.NEW_SHOT_FROM_SERVER:
            client_id, bullet_id, bullet_data = data_packet.data

            bullet_id = int(bullet_id)
            self.game.bullets[bullet_id] = Bullet.from_data(bullet_data)
            if client_id == self.network.id:
                self.game.player.weapon.shoot()
            else:
                self.game.players[client_id].weapon.shoot()

        if data_packet.data_type == self.DataPacket.DELETE_BULLET_FROM_SERVER:
            bullet_id = data_packet.data
            bullet_id = int(bullet_id)
            if bullet_id in self.game.bullets.keys():
                self.game.bullets.pop(bullet_id)

        if data_packet.data_type == self.DataPacket.HEALTH_POINTS:
            self.game.player.hp = data_packet.data

        if data_packet.data_type == self.DataPacket.NEW_WEAPON_FROM_SERVER:
            weapon_id = data_packet['weapon_id']
            weapon_name, weapon_x, weapon_y, weapon_ammo = data_packet['weapon_data']
            self.game.weapons[weapon_id] = Weapon(name=weapon_name, ammo=weapon_ammo, pos=(weapon_x, weapon_y))

        if data_packet.data_type == self.DataPacket.CLIENT_PICKED_WEAPON:
            client_id = data_packet['owner_id']
            weapon_id = data_packet['weapon_id']

            if client_id == self.network.id:
                self.game.player.attach_weapon(self.game.weapons[weapon_id])
            else:
                self.game.players[client_id].attach_weapon(self.game.weapons[weapon_id])

        if data_packet.data_type == self.DataPacket.CLIENT_DROPPED_WEAPON:
            client_id = data_packet['owner_id']
            weapon_id = data_packet['weapon_id']
            weapon_position = data_packet['weapon_position']
            weapon_direction = data_packet['weapon_direction']
            weapon_ammo = data_packet['weapon_ammo']

            if client_id == self.network.id:
                self.game.player.attach_weapon(Weapon('WeaponNone', owner=self.game.player))
            else:
                self.game.players[client_id].attach_weapon(Weapon('WeaponNone', owner=self.game.players[client_id]))
            self.game.weapons[weapon_id].x, self.game.weapons[weapon_id].y = weapon_position
            self.game.weapons[weapon_id].direction = weapon_direction
            self.game.weapons[weapon_id].ammo = weapon_ammo

    def handle_game_objects_collision(self):
        for object in self.game.level.objects['rectangles']:
            if pygame.rect.Rect.colliderect(object.rect, self.game.player.rect):
                if self.DataPacket.FLAG_READY not in self.player_flags:
                    self.player_flags.add(self.DataPacket.FLAG_READY)
                    response_data = {'data': self.DataPacket.FLAG_READY}
                    response = self.DataPacket(self.DataPacket.ADD_PLAYER_FLAG, response_data, )
                    self.send(response)
            else:
                if self.DataPacket.FLAG_READY in self.player_flags:
                    self.player_flags.remove(self.DataPacket.FLAG_READY)
                    response_data = {'data': self.DataPacket.FLAG_READY}
                    response = self.DataPacket(self.DataPacket.REMOVE_PLAYER_FLAG, response_data)
                    self.send(response)

    def shoot_bullet(self):
        if self.game.player.hp <= 0:
            return
        if self.game.player.weapon.name == "WeaponNone":
            return
        bullets = self.game.player.weapon.shoot()
        if bullets is None:
            return

        for bullet in bullets:
            bullet_data = {'data': bullet.encode()}
            response = self.DataPacket(self.DataPacket.NEW_SHOT_FROM_CLIENT, bullet_data)
            self.send(response)

    def pick_up_weapon(self):
        response = self.DataPacket(self.DataPacket.CLIENT_PICK_WEAPON_REQUEST)
        self.send(response)

    def drop_weapon(self):
        if self.game.player.weapon.name == 'WeaponNone':
            return

        dropped_weapon_id = 0
        for weapon_id, weapon in self.game.weapons.items():
            if weapon == self.game.player.weapon:
                dropped_weapon_id = weapon_id
                break
        response = self.DataPacket(self.DataPacket.CLIENT_DROPPED_WEAPON,
                                   {'weapon_id': dropped_weapon_id,
                                    'weapon_direction': self.game.player.weapon.direction,
                                    'weapon_position': (self.game.player.weapon.get_position()),
                                    'weapon_ammo': self.game.player.weapon.ammo})
        self.send(response)

    def send_initial_info(self):
        player_data = {'data': self.game.player.initial_info()}
        response = self.DataPacket(self.DataPacket.INITIAL_INFO, player_data)
        self.send(response)

    def send_player_data(self):
        player_data = {'data': self.game.player.encode()}
        response = self.DataPacket(self.DataPacket.CLIENT_PLAYER_INFO, player_data)
        self.send(response)

    def send(self, data_packet):
        data_packet.headers['id'] = self.network.id
        data_packet.headers['game_id'] = self.game_id
        if data_packet.data_type == self.DataPacket.CLIENT_PLAYER_INFO:
            self.network.send_udp(data_packet)
        else:
            self.network.send_tcp(data_packet)

    def receive(self):
        return self.network.receive()

    def draw(self, screen: pygame.Surface):
        self.packet_received = self.receive()
        if self.game is None:
            LoadingScreen().draw(screen)
        elif not self.webcam_ready:
            LoadingScreen(text='Waiting for webcam').draw(screen)
        else:
            self.handle_game_objects_collision()
            self.send_player_data()
            self.game.draw(screen)


def validate_address(user_input):
    if ':' not in user_input:
        raise ValueError('Not a valid server address')
    server, port = user_input.split(':')
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
    SoundCore.main_menu_music.music_play()
    while run:
        clock.tick(MAX_FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
                break

            if event.type == pygame.KEYDOWN:
                if game_manager.game_started and game_manager.game.player.hp > 0:
                    if event.key == pygame.K_j:
                        if game_manager.game.player.weapon.name == 'WeaponNone':
                            game_manager.pick_up_weapon()
                        else:
                            game_manager.drop_weapon()

            if type(current_screen) == ConnectToServerMenu:
                current_screen.event_handle(event)
            if type(current_screen) == StartServerMenu:
                current_screen.event_handle(event)
            if type(current_screen) == SettingsMenu:
                current_screen.event_handle(event)

            if event.type == SHOW_GAME_STATISTICS:
                current_screen = EndScreen(event.dict['statistics'])
            if event.type == LOADING_SCREEN_EVENT:
                current_screen = LoadingScreen()
            if event.type == START_GAME_EVENT:
                pass
            if event.type == OPEN_CONNECTION_MENU_EVENT:
                if SoundCore.current_music != SoundCore.SERVER_CONNECTION_MUSIC:
                    SoundCore.server_connection_music.music_play()
                current_screen = ConnectToServerMenu()
            if event.type == OPEN_MAIN_MENU_EVENT:
                current_screen = Menu()
                if SoundCore.current_music != SoundCore.MAIN_MENU_MUSIC:
                    SoundCore.main_menu_music.music_play()

            if event.type == CONNECT_TO_SERVER_EVENT:
                try:
                    SoundCore.in_game_music.music_play()
                    server, port = validate_address(event.dict['input'])
                    current_screen = game_manager
                    game_manager.connect(server, port)
                except Exception as e:
                    current_screen = MessageScreen(str(e), pygame.event.Event(OPEN_CONNECTION_MENU_EVENT))
                    print(e)
            if event.type == START_SERVER_MENU_EVENT:
                SoundCore.server_connection_music.music_play()
                current_screen = StartServerMenu()

            if event.type == OPEN_SETTINGS_MENU_EVENT:
                current_screen = SettingsMenu()

            if event.type == CHANGE_SOUND_MODE:
                SoundCore.is_sound_on = not SoundCore.is_sound_on
                current_screen.buttons_update()
                if SoundCore.is_sound_on:
                    SoundCore.sound_on()
                else:
                    SoundCore.sound_off()

            if event.type == CHANGE_MUSIC_MODE:
                SoundCore.is_music_on = not SoundCore.is_music_on
                current_screen.buttons_update()
                if SoundCore.is_music_on:
                    SoundCore.music_on()
                    SoundCore.main_menu_music.music_play()
                else:
                    SoundCore.music_off()

            if event.type == CHANGE_SOUNDS_SLIDER:
                SoundCore.change_sounds_loud(event.dict['value'])
            if event.type == CHANGE_MUSIC_SLIDER:
                SoundCore.change_music_loud(event.dict['value'])
        try:
            current_screen.draw(screen)
        except Exception as e:
            current_screen = MessageScreen(str(e), pygame.event.Event(OPEN_MAIN_MENU_EVENT))
        pygame.display.set_caption(f"{int(clock.get_fps())} FPS")
        pygame.display.flip()

    pygame.mixer.quit()
    pygame.quit()


if __name__ == "__main__":
    main(screen)
