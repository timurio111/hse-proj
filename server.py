from __future__ import annotations

import asyncio
import time
from random import shuffle, choice

import pygame

from colors import color_generator
from level import Level, GameObjectPoint
from network import DataPacket
from weapon import Weapon

DEBUG = True
TICK_RATE = 240
POSITIONS_SEND_RATE = 120

ADDRESS = ('127.0.0.1', 5555)

start_time = int(time.time())

level_names = ['pirate_ship_map', 'firstmap', 'pirate_island_map', 'frozen_map']


class GameStatistics:
    def __init__(self):
        self.players_data = {}
        self.data = {'colors': {}}

    def new_player(self, player_id: int):
        self.players_data[player_id] = {'kill': 0, 'death': 0, 'win': 0, 'damage': 0}

    def sort_by_rating(self):
        rating = list(self.players_data.keys())
        rating.sort(key=lambda player: (self[player]['win'], self[player]['kill'], -self[player]['death']), reverse=True)
        return rating

    def get_data(self):
        self.data['statistics'] = self.players_data
        self.data['winner'] = self.sort_by_rating()[0]
        return self.data

    def __getitem__(self, item):
        return self.players_data[item]

    def __setitem__(self, key, value):
        self.players_data[key] = value


class ServerPlayer:
    def __init__(self, player_id: int, x: int, y: int, status: str, direction: str, sprite_animation_counter: int,
                 hp: int, ch_data: dict, color: list):
        self.id: int = player_id
        self.x = x
        self.y = y
        self.status = status
        self.direction: str = direction
        self.sprite_animation_counter = sprite_animation_counter
        self.hp = hp
        self.ch_data = ch_data
        self.vx = 0
        self.vy = 0
        self.off_ground_counter = 0
        self.sprite_offset_x: int = (self.ch_data['RECT_WIDTH'] - self.ch_data['CHARACTER_WIDTH']) // 2
        self.sprite_offset_y: int = self.ch_data['RECT_HEIGHT'] - self.ch_data['CHARACTER_HEIGHT']
        self.sprite_rect = pygame.Rect((self.x + self.sprite_offset_x, self.y + self.sprite_offset_y),
                                       (ch_data['CHARACTER_WIDTH'], ch_data['CHARACTER_HEIGHT']))
        self.weapon_id = -1
        self.color = color
        self.flags: set[int] = set()

    @staticmethod
    def from_player_data(player_id, data) -> ServerPlayer:
        return ServerPlayer(player_id, *data)

    def apply(self, data) -> None:
        self.x, self.y, self.status, self.direction, self.sprite_animation_counter, self.hp, \
            self.vx, self.vy, self.off_ground_counter = data
        self.sprite_rect.x = self.x + self.sprite_offset_x
        self.sprite_rect.y = self.y + self.sprite_offset_y

    def get_center(self) -> tuple[int, int]:
        return self.sprite_rect.x + self.ch_data['CHARACTER_WIDTH'] // 2, self.sprite_rect.bottom

    def encode(self) -> list:
        return [self.x, self.y, self.status, self.direction, self.sprite_animation_counter, self.hp,
                self.vx, self.vy, self.off_ground_counter, self.color]

    def __repr__(self):
        return str((self.x, self.y, self.hp))


class ServerBullet:
    bullet_id = 0

    def __init__(self, owner: int, pos: tuple[int, int], v: tuple[int, int], damage: int, ay: int):
        self.owner = owner
        self.ay = ay
        self.x, self.y = pos
        self.vx, self.vy = v
        self.damage = damage
        self.current_lifetime_seconds = 0
        self.max_lifetime_seconds = 1

    @staticmethod
    def from_data(owner: int, data: list):
        return ServerBullet(owner, *data)

    def update(self, timedelta: int) -> None:
        self.vy += self.ay
        self.current_lifetime_seconds += timedelta
        self.x += self.vx * timedelta
        self.y += self.vy * timedelta

    def get_position(self) -> tuple[int, int]:
        return self.x, self.y


class ServerWeapon:
    weapon_id = 0

    def __init__(self, name, x, y):
        self.owner = None
        self.name = name
        self.vy = 0

        self.ammo = Weapon.all_weapons_info[self.name]['PATRONS']

        weapon_rect_height = Weapon.all_weapons_info[name]['WEAPON_RECT_HEIGHT']
        weapon_rect_width = Weapon.all_weapons_info[name]['WEAPON_RECT_WIDTH']
        image_offset_x = Weapon.all_weapons_info[name]['IMAGE_OFFSET_X']
        image_offset_y = Weapon.all_weapons_info[name]['IMAGE_OFFSET_Y']
        image_width = Weapon.all_weapons_info[name]['IMAGE_WIDTH']
        image_height = Weapon.all_weapons_info[name]['IMAGE_HEIGHT']

        self.center_offset_x = image_offset_x + image_width // 2
        self.center_offset_y = image_offset_x + image_height // 2
        self.bottom_offset_y = image_offset_y + image_height
        self.rect = pygame.Rect(x - self.center_offset_x, y - self.bottom_offset_y,
                                weapon_rect_width, weapon_rect_height)
        self.direction = 'right'

    def update(self, time_delta, level):
        time_delta = min(1 / 20, time_delta)
        if self.owner:
            self.direction = self.owner.direction
            self.rect.x = self.owner.x + Weapon.all_weapons_info[self.name][f'OFFSET_X_{self.direction.upper()}']
            self.rect.y = self.owner.y + Weapon.all_weapons_info[self.name]['OFFSET_Y']
        else:
            dvy = 128
            dy = int(time_delta * self.vy)
            self.rect.y += dy
            if level.collide_point(*self.get_center()):
                self.rect.y -= dy
                self.vy = 0
            else:
                self.vy += dvy
                self.vy = min(self.vy, 512)

    def reload(self):
        self.ammo = Weapon.all_weapons_info[self.name]['PATRONS']

    def get_center(self) -> tuple[int, int]:
        if self.direction == 'right':
            return self.rect.x + self.center_offset_x, self.rect.y + self.bottom_offset_y
        elif self.direction == 'left':
            return self.rect.right - self.center_offset_x, self.rect.y + self.bottom_offset_y

    def encode(self):
        return [self.name, self.rect.x, self.rect.y, self.ammo]


class GameState:
    STATUS_WAIT = 1
    STATUS_CONNECTED = 2
    STATUS_PLAYING = 3
    MAX_LEVELS = 10

    def __init__(self):
        self.level_id = 0

        self.players: dict[int, ServerPlayer] = dict()
        self.players_alive: set[int] = set()
        self.bullets: dict[int, ServerBullet] = dict()
        self.weapons: dict[int, ServerWeapon] = dict()

        self.level_name: str = 'lobby'
        self.lastlevel: bool = False
        self.level: Level = Level(self.level_name)
        self.spawn_points: list[GameObjectPoint] = []
        self.current_spawn_point: int = 0
        self.change_level(self.level_name)

        self.game_ended = False
        self.game_started = False

    def change_level(self, level_name) -> None:
        self.level_id += 1
        self.players_alive = set(self.players.keys())
        self.level_name = level_name
        for player_id, player in self.players.items():
            if DataPacket.FLAG_READY in player.flags:
                player.flags.remove(DataPacket.FLAG_READY)
        self.current_spawn_point = 0
        self.spawn_points.clear()

        self.bullets.clear()
        self.weapons.clear()
        ServerBullet.bullet_id = 0
        ServerWeapon.weapon_id = 0

        self.level = Level(level_name)
        for point in self.level.objects['points']:
            if point.name == 'spawnpoint':
                self.spawn_points.append(point)
            if 'Weapon' in point.name:
                self.weapons[ServerWeapon.weapon_id] = ServerWeapon(point.name, point.x, point.y)
                ServerWeapon.weapon_id += 1

    def get_spawn_point(self) -> tuple[int, int]:
        spawn_point = self.spawn_points[self.current_spawn_point]
        self.current_spawn_point = (self.current_spawn_point + 1) % len(self.spawn_points)
        return spawn_point.x, spawn_point.y


class ServerEvent:
    ACCEPT_CONNECTION = 0
    SEND_TCP = 1
    SEND_UDP = 2
    SEND_INITIAL_GAME_INFO = 3
    HANDLE_PACKET = 4
    DISCONNECT_PLAYER = 5
    SEND_PLAYERS_DATA = 6
    UPDATE_GAME_STATE = 7
    CHANGE_LEVEL = 8
    KILL_SERVER = 9

    def __init__(self, event_type, data=None, delay=0):
        self.event_type = event_type
        self.data = data if data is not None else {}
        self.time = time.time() + delay

    def __getitem__(self, item):
        return self.data[item]

    def __setitem__(self, key, value):
        self.data[key] = value


class UdpServerProtocol(asyncio.DatagramProtocol):

    def __init__(self, events_queue: asyncio.Queue):
        self.events_queue = events_queue

    # noinspection PyAttributeOutsideInit
    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        data_packet = DataPacket.from_bytes(data)
        handle_packet_event = ServerEvent(event_type=ServerEvent.HANDLE_PACKET,
                                          data={'type': 'datagram',
                                                'address': addr,
                                                'packet': data_packet})
        self.events_queue.put_nowait(handle_packet_event)


class ServerNetwork:
    __next_client_id = 0

    @staticmethod
    def get_next_client_id():
        client_id = ServerNetwork.__next_client_id
        ServerNetwork.__next_client_id += 1
        return client_id

    def __init__(self, events_queue: asyncio.Queue):
        self.lock = asyncio.Lock()

        self.events_queue = events_queue
        self.id_to_stream: dict[int, tuple[asyncio.StreamReader, asyncio.StreamWriter]] = {}
        self.stream_to_id: dict[tuple[asyncio.StreamReader, asyncio.StreamWriter], int] = {}

        self.id_to_udp_address: dict[int, tuple[str, int]] = {}
        self.id_to_last_udp_packet_time: dict[int, float] = {}

    @classmethod
    async def create(cls, events_queue: asyncio.Queue, address: tuple[str, int]):
        self = ServerNetwork(events_queue)
        await self.start(address)

        return self

    # noinspection PyAttributeOutsideInit
    async def start(self, address: tuple[str, int]):
        server, port = address
        tcp_port = port
        udp_port = port + 1

        self.transport, self.protocol = await asyncio.get_running_loop().create_datagram_endpoint(
            protocol_factory=lambda: UdpServerProtocol(self.events_queue),
            local_addr=(server, udp_port)
        )

        self.tcp_server = await asyncio.start_server(
            client_connected_cb=self.acceptor,
            host=server,
            port=tcp_port)

    async def acceptor(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        flag = asyncio.Event()

        client_id = ServerNetwork.get_next_client_id()

        self.id_to_stream[client_id] = (reader, writer)
        self.stream_to_id[(reader, writer)] = client_id
        self.id_to_last_udp_packet_time[client_id] = 0

        print(f'client with id {client_id} connected')

        server_event = ServerEvent(event_type=ServerEvent.ACCEPT_CONNECTION,
                                   data={'client_id': client_id,
                                         'reader': reader,
                                         'writer': writer,
                                         'flag': flag})

        self.events_queue.put_nowait(server_event)

        try:
            await asyncio.wait_for(flag.wait(), timeout=2)  # TODO? костыль
        except asyncio.TimeoutError:
            server_event = ServerEvent(event_type=ServerEvent.DISCONNECT_PLAYER,
                                       data={'client_id': client_id})
            self.events_queue.put_nowait(server_event)
            return

        response_data = {'id': client_id}
        response = DataPacket(data_type=DataPacket.AUTH, data=response_data)
        response.headers['game_id'] = 0
        server_event = ServerEvent(event_type=ServerEvent.SEND_TCP,
                                   data={'client_id': client_id, 'packet': response})
        self.events_queue.put_nowait(server_event)

        server_event = ServerEvent(event_type=ServerEvent.SEND_INITIAL_GAME_INFO,
                                   data={'client_id': client_id})
        self.events_queue.put_nowait(server_event)

        while True:
            try:
                data = await reader.readline()
            except Exception as e:
                print(e)
                break
            if data == b'':
                break
            data_packet = DataPacket.from_bytes(data)
            handle_packet_event = ServerEvent(event_type=ServerEvent.HANDLE_PACKET,
                                              data={'type': 'tcp',
                                                    'packet': data_packet})
            self.events_queue.put_nowait(handle_packet_event)

        server_event = ServerEvent(event_type=ServerEvent.DISCONNECT_PLAYER,
                                   data={'client_id': client_id})
        self.events_queue.put_nowait(server_event)

    async def send_tcp(self, client_id: int, data_packet: DataPacket):
        _, writer = self.id_to_stream[client_id]
        writer.write(data_packet.encode())
        try:
            await asyncio.wait_for(writer.drain(), timeout=5)
            print(f'sent {data_packet.encode()}')
        except (ConnectionResetError, asyncio.TimeoutError):
            server_event = ServerEvent(event_type=ServerEvent.DISCONNECT_PLAYER,
                                       data={'client_id': client_id})
            self.events_queue.put_nowait(server_event)

    def send_udp(self, client_id: int, data_packet: DataPacket):
        data_packet.headers['time'] = round(time.time() - start_time, 3)
        if client_id not in self.id_to_udp_address.keys():
            return
        self.protocol.transport.sendto(data=data_packet.encode(),
                                       addr=self.id_to_udp_address[client_id])


class GameSession:
    next_session_id = 0

    def __init__(self):
        self.events_queue: asyncio.Queue[ServerEvent] = asyncio.Queue()
        self.game_statistics = GameStatistics()
        self.game_state = GameState()
        self.client_last_ping = dict()
        self.session_ended = False

    @classmethod
    async def create(cls, address: tuple[str, int]):
        self = GameSession()
        await self.start(address)

        return self

    # noinspection PyAttributeOutsideInit
    async def start(self, address: tuple[str, int]):
        self.server_network = await ServerNetwork.create(self.events_queue, address)

        events_handler = asyncio.create_task(self.events_listener())
        players_data_sender = asyncio.create_task(self.players_data_sender())
        game_state_updater = asyncio.create_task(self.game_state_updater())
        ping_players = asyncio.create_task(self.ping_players())

        await events_handler
        await players_data_sender
        await game_state_updater
        await ping_players

    def send_packet_tcp(self, client_id: int, data_packet: DataPacket, delay_seconds=0):
        data_packet.headers['game_id'] = self.game_state.level_id
        server_event = ServerEvent(event_type=ServerEvent.SEND_TCP,
                                   data={'client_id': client_id, 'packet': data_packet},
                                   delay=delay_seconds)
        self.events_queue.put_nowait(server_event)

    def send_packet_udp(self, client_id: int, data_packet: DataPacket, delay_seconds=0):
        data_packet.headers['game_id'] = self.game_state.level_id
        server_event = ServerEvent(event_type=ServerEvent.SEND_UDP,
                                   data={'client_id': client_id, 'packet': data_packet},
                                   delay=delay_seconds)
        self.events_queue.put_nowait(server_event)

    async def ping_players(self):
        while not self.session_ended:
            for client_id in self.game_state.players.keys():
                self.send_packet_tcp(client_id, DataPacket(DataPacket.PING))
            await asyncio.sleep(1)

    async def players_data_sender(self):
        while not self.session_ended:
            server_event = ServerEvent(event_type=ServerEvent.SEND_PLAYERS_DATA)
            self.events_queue.put_nowait(server_event)
            await asyncio.sleep(1 / POSITIONS_SEND_RATE)

    async def game_state_updater(self):
        last_tick = time.time()
        while not self.session_ended:
            time_delta = time.time() - last_tick
            last_tick = time.time()

            server_event = ServerEvent(event_type=ServerEvent.UPDATE_GAME_STATE,
                                       data={'time_delta': time_delta})
            self.events_queue.put_nowait(server_event)
            await asyncio.sleep(1 / TICK_RATE)

    async def events_listener(self):
        while not self.session_ended:
            server_event = await self.events_queue.get()

            if server_event.time > time.time():
                self.events_queue.put_nowait(server_event)
                await asyncio.sleep(0)
                continue

            if server_event.event_type == ServerEvent.KILL_SERVER:
                self.session_ended = True

            if server_event.event_type == ServerEvent.ACCEPT_CONNECTION:
                client_id: int = server_event['client_id']
                reader: asyncio.StreamReader = server_event['reader']
                writer: asyncio.StreamWriter = server_event['writer']
                flag: asyncio.Event = server_event['flag']

                self.server_network.id_to_stream[client_id] = (reader, writer)
                self.server_network.stream_to_id[(reader, writer)] = client_id
                self.client_last_ping[client_id] = time.time()

                if self.game_state.game_started or len(self.game_state.players) >= 4:
                    response = DataPacket(data_type=DataPacket.GAME_ALREADY_STARTED)
                    self.send_packet_tcp(client_id, response)
                else:
                    self.game_statistics.new_player(client_id)
                    flag.set()

            if server_event.event_type == ServerEvent.DISCONNECT_PLAYER:
                client_id: int = server_event['client_id']
                if client_id not in self.server_network.id_to_udp_address.keys():
                    continue

                reader, writer = self.server_network.id_to_stream[client_id]

                self.server_network.id_to_stream.pop(client_id)
                self.server_network.stream_to_id.pop((reader, writer))
                self.server_network.id_to_last_udp_packet_time.pop(client_id)
                if client_id in self.game_state.players.keys():
                    self.game_state.players.pop(client_id)
                if client_id in self.game_state.players_alive:
                    self.game_state.players_alive.remove(client_id)
                if client_id in self.server_network.id_to_udp_address.keys():
                    self.server_network.id_to_udp_address.pop(client_id)
                if client_id in self.client_last_ping.keys():
                    self.client_last_ping.pop(client_id)

                print(f'client with id {client_id} disconnected')
                writer.close()
                try:
                    await asyncio.wait_for(writer.wait_closed(), timeout=5)
                except Exception as e:
                    print(e)

            if server_event.event_type == ServerEvent.UPDATE_GAME_STATE:
                time_delta = server_event['time_delta']
                self.update_game_state(time_delta)

            if server_event.event_type == ServerEvent.SEND_PLAYERS_DATA:
                players_data = dict()
                for player_id in self.game_state.players.keys():
                    if GameState.STATUS_PLAYING not in self.game_state.players[player_id].flags:
                        continue
                    players_data[player_id] = self.game_state.players[player_id].encode()
                response = DataPacket(data_type=DataPacket.PLAYERS_INFO, data=players_data)

                for client_id in self.server_network.id_to_udp_address.keys():
                    self.send_packet_udp(client_id, response)

            if server_event.event_type == ServerEvent.CHANGE_LEVEL:
                level_name = server_event['level_name']
                self.change_level(level_name)

            if server_event.event_type == ServerEvent.SEND_TCP:
                client_id: int = server_event['client_id']
                data_packet: DataPacket = server_event['packet']
                await self.server_network.send_tcp(client_id, data_packet)

            if server_event.event_type == ServerEvent.SEND_UDP:
                client_id: int = server_event['client_id']
                data_packet: DataPacket = server_event['packet']
                self.server_network.send_udp(client_id, data_packet)

            if server_event.event_type == ServerEvent.SEND_INITIAL_GAME_INFO:
                client_id: int = server_event['client_id']

                response_data = {'level_name': 'lobby',
                                 'position': self.game_state.get_spawn_point(),
                                 'color': color_generator.__next__()}
                response = DataPacket(data_type=DataPacket.GAME_INFO, data=response_data)
                self.send_packet_tcp(client_id, response)

            if server_event.event_type == ServerEvent.HANDLE_PACKET:
                packet_type = server_event['type']
                data_packet = server_event['packet']

                client_id: int = data_packet.headers['id']
                if client_id == -1:
                    continue
                if client_id not in self.server_network.id_to_stream.keys():
                    continue

                if packet_type == 'datagram':
                    if client_id not in self.game_state.players.keys():
                        continue
                    if data_packet.headers['game_id'] != self.game_state.level_id:
                        continue

                    addr = server_event['address']
                    if data_packet.headers['time'] < self.server_network.id_to_last_udp_packet_time[client_id]:
                        continue
                    self.server_network.id_to_last_udp_packet_time[client_id] = data_packet.headers['time']
                    if client_id not in self.server_network.id_to_udp_address.keys():
                        self.server_network.id_to_udp_address[client_id] = addr

                self.packet_handler(data_packet)

    def packet_handler(self, data_packet: DataPacket):
        client_id = data_packet.headers['id']

        if client_id == -1:
            return

        if data_packet.data_type == DataPacket.PING:
            self.client_last_ping[client_id] = time.time()

        if data_packet.data_type == DataPacket.INITIAL_INFO:
            data = data_packet['data']
            self.game_state.players[client_id] = ServerPlayer.from_player_data(client_id, data)
            self.game_state.players[client_id].flags.add(GameState.STATUS_PLAYING)
            self.game_statistics.data['colors'][client_id] = self.game_state.players[client_id].color

        if data_packet.data_type == DataPacket.CLIENT_PLAYER_INFO:
            if GameState.STATUS_PLAYING in self.game_state.players[client_id].flags:
                data = data_packet['data']
                self.game_state.players[client_id].apply(data)

        if data_packet.data_type == DataPacket.RELOAD_WEAPON:
            weapon_id = self.game_state.players[client_id].weapon_id
            self.game_state.weapons[weapon_id].reload()

            response = DataPacket(DataPacket.RELOAD_WEAPON, {'weapon_id': weapon_id})
            for client_id in self.game_state.players.keys():
                self.send_packet_tcp(client_id, response)

        if data_packet.data_type == DataPacket.ADD_PLAYER_FLAG:
            self.game_state.players[client_id].flags.add(data_packet['data'])

        if data_packet.data_type == DataPacket.REMOVE_PLAYER_FLAG:
            flag = data_packet['data']
            if flag in self.game_state.players[client_id].flags:
                self.game_state.players[client_id].flags.remove(flag)

        if data_packet.data_type == DataPacket.NEW_SHOT_FROM_CLIENT:
            bullet_data = data_packet['data']
            bullet = ServerBullet.from_data(client_id, bullet_data)
            bullet_id = ServerBullet.bullet_id
            ServerBullet.bullet_id += 1

            self.game_state.bullets[bullet_id] = bullet

            response = DataPacket(DataPacket.NEW_SHOT_FROM_SERVER, [client_id, bullet_id, bullet_data])
            for client_id in self.game_state.players.keys():
                self.send_packet_tcp(client_id, response)

        if data_packet.data_type == DataPacket.CLIENT_PICK_WEAPON_REQUEST:
            closest_weapon_id = None
            min_dist = 1e9
            for weapon_id, weapon in self.game_state.weapons.items():

                if weapon.owner is not None:
                    continue
                distance = pygame.math.Vector2(weapon.get_center()).distance_to(self.game_state.players[client_id].get_center())
                if distance > 32:
                    continue
                if distance < min_dist:
                    min_dist = distance
                    closest_weapon_id = weapon_id

            if closest_weapon_id is not None:
                self.game_state.weapons[closest_weapon_id].owner = self.game_state.players[client_id]
                self.game_state.players[client_id].weapon_id = closest_weapon_id
                response = DataPacket(data_type=DataPacket.CLIENT_PICKED_WEAPON,
                                      data={'owner_id': client_id, 'weapon_id': closest_weapon_id})
                for client_id in self.game_state.players.keys():
                    self.send_packet_tcp(client_id, response)

        if data_packet.data_type == DataPacket.CLIENT_DROPPED_WEAPON:
            weapon_id = data_packet['weapon_id']
            weapon_direction = data_packet['weapon_direction']
            weapon_position = data_packet['weapon_position']
            weapon_ammo = data_packet['weapon_ammo']
            self.game_state.weapons[weapon_id].owner = None
            self.game_state.weapons[weapon_id].rect.x, self.game_state.weapons[weapon_id].rect.y = weapon_position
            self.game_state.weapons[weapon_id].direction = weapon_direction
            response = DataPacket(DataPacket.CLIENT_DROPPED_WEAPON,
                                  {'owner_id': client_id,
                                   'weapon_id': weapon_id,
                                   'weapon_position': weapon_position,
                                   'weapon_direction': weapon_direction,
                                   'weapon_ammo': weapon_ammo})
            for client_id in self.game_state.players.keys():
                self.send_packet_tcp(client_id, response)

    def change_level(self, level_name):
        self.game_state.game_ended = False
        self.game_state.change_level(level_name)

        players_by_rating = [player for player in self.game_statistics.sort_by_rating() if player in self.game_state.players.keys()]
        spawn_points = [self.game_state.get_spawn_point() for _ in range(len(players_by_rating))]

        if not self.game_state.lastlevel:
            shuffle(spawn_points)

        for player_id, spawn_point in zip(players_by_rating, spawn_points):
            if GameState.STATUS_PLAYING in self.game_state.players[player_id].flags:
                self.game_state.players[player_id].flags.remove(GameState.STATUS_PLAYING)

            player_color = self.game_state.players[player_id].color
            response_data = {'level_name': level_name,
                             'position': spawn_point,
                             'color': player_color}

            response = DataPacket(data_type=DataPacket.GAME_INFO, data=response_data)
            self.send_packet_tcp(player_id, response)

            for weapon_id, weapon in self.game_state.weapons.items():
                weapon_data = {'weapon_id': weapon_id, 'weapon_data': weapon.encode()}
                response = DataPacket(data_type=DataPacket.NEW_WEAPON_FROM_SERVER, data=weapon_data)
                self.send_packet_tcp(player_id, response)

        if self.game_state.lastlevel:
            for player_id in self.game_state.players.keys():
                response = DataPacket(data_type=DataPacket.DISCONNECT,
                                      data={'statistics': self.game_statistics.get_data()})
                self.send_packet_tcp(player_id, response, delay_seconds=5)

                self.events_queue.put_nowait(ServerEvent(event_type=ServerEvent.KILL_SERVER, delay=6))

    def update_game_state(self, time_delta):
        for client_id in self.game_state.players.keys():
            if time.time() - self.client_last_ping[client_id] > 10:
                server_event = ServerEvent(event_type=ServerEvent.DISCONNECT_PLAYER,
                                           data={'client_id': client_id})
                self.events_queue.put_nowait(server_event)

        if not self.game_state.players:
            if self.game_state.level_name != 'lobby':
                self.game_state.game_ended = False
                self.game_state.game_started = False
                server_event = ServerEvent(event_type=ServerEvent.CHANGE_LEVEL,
                                           data={'level_name': 'lobby'})
                self.events_queue.put_nowait(server_event)
            return

        if all([DataPacket.FLAG_READY in player.flags for player in self.game_state.players.values()]) \
                and not self.game_state.game_ended and len(self.game_state.players) > 1:
            self.game_state.game_ended = True
            self.game_state.game_started = True
            level_name = choice(level_names)
            server_event = ServerEvent(event_type=ServerEvent.CHANGE_LEVEL,
                                       data={'level_name': level_name},
                                       delay=2)
            self.events_queue.put_nowait(server_event)
            return

        if len(self.game_state.players) > 1 and len(self.game_state.players_alive) == 1 and not self.game_state.game_ended:
            self.game_state.game_ended = True
            self.game_statistics[self.game_state.players_alive.pop()]['win'] += 1
            if self.game_state.level_id == GameState.MAX_LEVELS:
                self.game_state.lastlevel = True
                final_level_name = 'lastmap' + str(len(self.game_state.players.keys()))
                server_event = ServerEvent(event_type=ServerEvent.CHANGE_LEVEL,
                                           data={'level_name': final_level_name},
                                           delay=1)
                self.events_queue.put_nowait(server_event)
            else:
                level_name = choice(level_names)
                server_event = ServerEvent(event_type=ServerEvent.CHANGE_LEVEL,
                                           data={'level_name': level_name},
                                           delay=1)
                self.events_queue.put_nowait(server_event)
            return

        for weapon_id in self.game_state.weapons.keys():
            self.game_state.weapons[weapon_id].update(time_delta, self.game_state.level)

        for client_id in self.game_state.players.keys():

            if client_id in self.game_state.players.keys() and self.game_state.players[client_id].y > 3000:
                if client_id not in self.game_state.players_alive:
                    continue
                if GameState.STATUS_PLAYING not in self.game_state.players[client_id].flags:
                    continue
                self.kill_player(client_id)

        for bullet_id in list(self.game_state.bullets.keys()):
            bullet = self.game_state.bullets[bullet_id]
            bullet.update(time_delta)

            if bullet.current_lifetime_seconds > bullet.max_lifetime_seconds or \
                    self.game_state.level.collide_point(*bullet.get_position()):
                self.delete_bullet(bullet_id)
                continue

            for client_id in self.game_state.players.keys():
                if client_id not in self.game_state.players_alive:
                    continue
                if GameState.STATUS_PLAYING not in self.game_state.players[client_id].flags:
                    continue

                if self.game_state.players[client_id].sprite_rect.collidepoint(bullet.get_position()):
                    self.damage_player(client_id, bullet)

                    self.delete_bullet(bullet_id)

    def delete_bullet(self, bullet_id):
        self.game_state.bullets.pop(bullet_id)
        for client_id in self.game_state.players.keys():
            data_packet = DataPacket(DataPacket.DELETE_BULLET_FROM_SERVER, bullet_id)
            self.send_packet_tcp(client_id, data_packet)

    def damage_player(self, player_id, bullet: ServerBullet):
        player = self.game_state.players[player_id]
        damage = min(bullet.damage, player.hp)
        self.game_statistics[bullet.owner]['damage'] += damage
        player.hp -= damage

        response = DataPacket(DataPacket.HEALTH_POINTS, self.game_state.players[player_id].hp)
        self.send_packet_tcp(player_id, response)

        if player.hp == 0:
            self.game_statistics[bullet.owner]['kill'] += 1
            self.kill_player(player_id)

    def kill_player(self, player_id):
        self.game_statistics[player_id]['death'] += 1
        self.game_state.players_alive.remove(player_id)
        self.game_state.players[player_id].hp = 0

        data_packet = DataPacket(DataPacket.HEALTH_POINTS, 0)
        self.send_packet_tcp(player_id, data_packet)

        weapon_id = self.game_state.players[player_id].weapon_id
        if weapon_id != -1:
            weapon = self.game_state.weapons[weapon_id]
            weapon.owner = None
            response_data = {'owner_id': player_id,
                             'weapon_id': weapon_id,
                             'weapon_direction': weapon.direction,
                             'weapon_position': (weapon.rect.x, weapon.rect.y),
                             'weapon_ammo': weapon.ammo}
            response = DataPacket(DataPacket.CLIENT_DROPPED_WEAPON, response_data)
            for client_id in self.game_state.players.keys():
                self.send_packet_tcp(client_id, response)


async def start_session(address: tuple[str, int]):
    # noinspection PyUnusedLocal
    game_session = await GameSession.create(address)


from multiprocessing import Process


class ServerManager:
    server_process: Process = Process()

    @staticmethod
    def run_server(address: tuple[str, int]):
        asyncio.run(start_session(address), debug=DEBUG)

    @staticmethod
    def run_subprocess(address: tuple[str, int]):
        ServerManager.kill_subprocess()
        ServerManager.server_process = Process(target=ServerManager.run_server, args=(address,))
        ServerManager.server_process.start()

    @staticmethod
    def kill_subprocess():
        if ServerManager.server_process.is_alive():
            ServerManager.server_process.kill()

    @staticmethod
    def check_server():
        if ServerManager.server_process.exitcode:
            ServerManager.server_process = Process()
            raise Exception("Server upal")


if __name__ == '__main__':
    ServerManager.run_server(ADDRESS)
