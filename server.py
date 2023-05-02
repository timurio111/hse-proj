import queue
import selectors
import socket
import time

import pygame

from level import Level, GameObjectPoint
from network import DataPacket

sel = selectors.DefaultSelector()
event_queue = queue.Queue()
server = "127.0.0.1"
tcp_port = 5555

current_id = 0
client_socket_to_id = {}
MAX_CONNECTIONS = 10
c = 0


class ServerEvent:
    EVENT = 0
    NEW_GAME = 1

    def __init__(self, event_type, delay_seconds=0, callback=None, *args):
        self.callback = callback
        self.event_type = event_type
        self.delay_seconds = delay_seconds
        self.time_created = time.time()
        self.args = args


class SeverPlayer:
    def __init__(self, player_id, x, y, status, direction, sprite_animation_counter, hp, ch_data, weapon_name):
        self.id = player_id
        self.x = x
        self.y = y
        self.status = status
        self.direction = direction
        self.sprite_animation_counter = sprite_animation_counter
        self.hp = hp
        self.ch_data = ch_data
        self.weapon_name = weapon_name
        self.sprite_offset_x = (self.ch_data['RECT_WIDTH'] - self.ch_data['CHARACTER_WIDTH']) // 2
        self.sprite_offset_y = self.ch_data['RECT_HEIGHT'] - self.ch_data['CHARACTER_HEIGHT']

        self.sprite_rect = pygame.Rect((self.x + self.sprite_offset_x, self.y + self.sprite_offset_y),
                                       (ch_data['CHARACTER_WIDTH'], ch_data['CHARACTER_HEIGHT']))

        self.flags: set[int] = set()

    @staticmethod
    def from_player_data(player_id, data):
        return SeverPlayer(player_id, *data)

    def apply(self, data):
        self.x, self.y, self.status, self.direction, self.sprite_animation_counter, self.hp, self.weapon_name = data
        self.sprite_rect.x = self.x + self.sprite_offset_x
        self.sprite_rect.y = self.y + self.sprite_offset_y

    def encode(self):

        return [self.x, self.y, self.status, self.direction, self.sprite_animation_counter, self.hp, self.weapon_name]

    def __repr__(self):
        return str((self.x, self.y, self.hp))


class ServerBullet:
    bullet_id = 0

    def __init__(self, x, y, vx, vy):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.lifetime = 0
        self.damage = 300

    def update(self, timedelta):
        self.lifetime += timedelta
        self.x += self.vx * timedelta
        self.y += self.vy * timedelta

    def get_position(self):
        return self.x, self.y


class GameState:
    STATUS_WAIT = 1
    STATUS_CONNECTED = 2
    STATUS_PLAYING = 3

    def __init__(self):
        self.players: dict[int, SeverPlayer] = dict()
        self.bullets: dict[int, ServerBullet] = dict()

        self.level_name = 'lobby'
        self.level: Level = None
        self.spawn_points: list[GameObjectPoint] = []
        self.current_spawn_point = 0
        self.change_level(self.level_name)

        self.game_ended = False

    def change_level(self, level_name):
        self.level_name = level_name
        for player_id, player in self.players.items():
            if DataPacket.FLAG_READY in player.flags:
                player.flags.remove(DataPacket.FLAG_READY)
        self.current_spawn_point = 0

        self.bullets.clear()
        self.level = Level(level_name)
        self.spawn_points: GameObjectPoint = self.level.objects['points']

    def get_spawn(self):
        spawn_point = self.spawn_points[self.current_spawn_point % len(self.spawn_points)]
        self.current_spawn_point += 1
        return spawn_point.x, spawn_point.y


game_state = GameState()


def accept_connection(server_socket: socket.socket, mask):
    global current_id, client_socket_to_id

    server_socket.listen(MAX_CONNECTIONS)
    client_socket, address = server_socket.accept()
    client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

    client_socket.setblocking(False)
    client_socket_to_id[client_socket] = current_id
    current_id += 1

    auth_data = {'id': client_socket_to_id[client_socket]}
    response = DataPacket(DataPacket.AUTH, auth_data).encode()
    client_socket.send(response + b'\n')

    game_data = {'level_name': 'lobby', 'position': game_state.get_spawn()}
    response = DataPacket(DataPacket.GAME_INFO, game_data).encode()
    client_socket.send(response + b'\n')

    sel.register(fileobj=client_socket, events=selectors.EVENT_READ, data=handle_tcp)

    print(f"New connection from {address}. Id={client_socket_to_id[client_socket]}")


def disconnect(client_socket):
    sel.unregister(client_socket)
    client_socket.close()
    client_id = client_socket_to_id[client_socket]

    if client_id in game_state.players.keys():
        game_state.players.pop(client_id)

    client_socket_to_id.pop(client_socket)
    print(f'client with id {client_id} disconnected')


def send_players_data(client_socket: socket.socket):
    players_data = dict()
    for player_id in game_state.players.keys():
        if GameState.STATUS_PLAYING not in game_state.players[player_id].flags:
            continue
        players_data[player_id] = game_state.players[player_id].encode()
    response = DataPacket(DataPacket.PLAYERS_INFO, players_data).encode()

    client_socket.send(response + b'\n')


def send(client_socket: socket.socket, data_packet: DataPacket):
    client_socket.send(data_packet.encode() + b'\n')


def change_level(level_name):
    game_state.game_ended = False
    game_state.change_level(level_name)

    for client_socket, player_id in client_socket_to_id.items():
        game_state.players[player_id].hp = 100
        spawn_pos = game_state.get_spawn()
        game_data = {'level_name': game_state.level_name, 'position': spawn_pos}
        game_state.players[player_id].x, game_state.players[player_id].y = spawn_pos

        response = DataPacket(DataPacket.GAME_INFO, game_data).encode()
        if GameState.STATUS_PLAYING in game_state.players[player_id].flags:
            game_state.players[player_id].flags.remove(GameState.STATUS_PLAYING)
        client_socket.send(response + b'\n')


def handle_tcp(client_socket: socket.socket, mask):
    try:
        data_bytes = b''
        while True:
            byte = client_socket.recv(1)
            if byte == b'\n':
                break
            data_bytes += byte
    except Exception as e:
        print(e)
        disconnect(client_socket)
        return

    if not data_bytes:
        disconnect(client_socket)
        return

    data_packet = DataPacket.from_bytes(data_bytes)
    client_id = data_packet['id']

    if data_packet.data_type == DataPacket.INITIAL_INFO:
        data = data_packet['data']
        game_state.players[client_id] = SeverPlayer.from_player_data(client_id, data)
        game_state.players[client_id].flags.add(GameState.STATUS_PLAYING)

    if data_packet.data_type == DataPacket.CLIENT_PLAYER_INFO:
        if GameState.STATUS_PLAYING in game_state.players[client_id].flags:
            data = data_packet['data']
            game_state.players[client_id].apply(data)

    if data_packet.data_type == DataPacket.ADD_PLAYER_FLAG:
        game_state.players[client_id].flags.add(data_packet['data'])

    if data_packet.data_type == DataPacket.REMOVE_PLAYER_FLAG:
        flag = data_packet['data']
        if flag in game_state.players[client_id].flags:
            game_state.players[client_id].flags.remove(flag)

    if data_packet.data_type == DataPacket.NEW_BULLET_FROM_CLIENT:
        bullet_data = data_packet['data']
        bullet = ServerBullet(*bullet_data)
        bullet_id = ServerBullet.bullet_id
        ServerBullet.bullet_id += 1

        game_state.bullets[bullet_id] = bullet

        response = DataPacket(DataPacket.NEW_BULLET_FROM_SERVER, [bullet_id, bullet_data])
        for client_socket, player_id in client_socket_to_id.items():
            send(client_socket, response)

    send_players_data(client_socket)


def get_tcp_socket():
    tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    tcp_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    tcp_socket.setblocking(False)
    tcp_socket.bind((server, tcp_port))
    tcp_socket.listen(MAX_CONNECTIONS)
    return tcp_socket


def update(time_delta):
    if not game_state.players:
        if game_state.level_name != 'lobby':
            change_level('lobby')
        return

    if game_state.game_ended:
        return

    if all([DataPacket.FLAG_READY in player.flags for player in game_state.players.values()]) \
            and not game_state.game_ended:
        game_state.game_ended = True
        event_queue.put(ServerEvent(ServerEvent.EVENT, 1, change_level, 'firstmap'))
        return

    if len(game_state.players) > 1 and sum([player.hp > 0 for player in game_state.players.values()]) == 1 \
            and not game_state.game_ended:
        game_state.game_ended = True
        event_queue.put(ServerEvent(ServerEvent.EVENT, 1, change_level, 'firstmap'))
        return

    for client_socket, client_id in client_socket_to_id.items():
        if client_id in game_state.players.keys() and game_state.players[client_id].y > 3000:
            if game_state.players[client_id].hp == 0:
                continue
            game_state.players[client_id].hp = 0
            data_packet = DataPacket(DataPacket.HEALTH_POINTS, game_state.players[client_id].hp)
            send(client_socket, data_packet)

    def delete_bullet(bullet_id):
        for client_socket, client_id in client_socket_to_id.items():
            data_packet = DataPacket(DataPacket.DELETE_BULLET_FROM_SERVER, bullet_id)
            send(client_socket, data_packet)
        game_state.bullets.pop(bullet_id)

    for bullet_id in list(game_state.bullets.keys()):
        bullet = game_state.bullets[bullet_id]
        bullet.update(time_delta)
        if bullet.lifetime > 1 or game_state.level.collide_point(*bullet.get_position()):
            delete_bullet(bullet_id)

    for bullet_id in list(game_state.bullets):
        bullet = game_state.bullets[bullet_id]

        for client_socket, client_id in client_socket_to_id.items():
            if game_state.players[client_id].hp <= 0:
                continue
            if GameState.STATUS_PLAYING not in game_state.players[client_id].flags:
                continue

            if game_state.players[client_id].sprite_rect.collidepoint(bullet.get_position()):
                game_state.players[client_id].hp -= bullet.damage
                data_packet = DataPacket(DataPacket.HEALTH_POINTS, game_state.players[client_id].hp)
                send(client_socket, data_packet)
                delete_bullet(bullet_id)


def main():
    tcp_socket = get_tcp_socket()

    print("Server is up waiting...")

    sel.register(tcp_socket, selectors.EVENT_READ, data=accept_connection)

    tick = 1 / 60
    last_tick = time.time()

    while True:
        if time.time() - last_tick >= tick:
            for _ in range(event_queue.qsize()):
                event = event_queue.get()
                if time.time() > event.time_created + event.delay_seconds:
                    event.callback(*event.args)
                else:
                    event_queue.put(event)

            time_delta = time.time() - last_tick
            last_tick = time.time()
            update(time_delta)

        events = sel.select(timeout=0)
        for key, mask in events:
            callback = key.data
            callback(key.fileobj, mask)


if __name__ == '__main__':
    main()
