import asyncio
import queue
import time

import pygame

from level import Level, GameObjectPoint
from network import DataPacket

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


async def read(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> bytes:
    return await reader.readline()


async def accept_connection(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    global current_id, client_socket_to_id

    client_socket_to_id[(reader, writer)] = current_id
    current_id += 1

    auth_data = {'id': client_socket_to_id[(reader, writer)]}
    response = DataPacket(DataPacket.AUTH, auth_data)
    await send(writer, response)

    game_data = {'level_name': 'lobby', 'position': game_state.get_spawn()}
    response = DataPacket(DataPacket.GAME_INFO, game_data)
    await send(writer, response)

    print(f"New connection. Id={client_socket_to_id[(reader, writer)]}")

    while True:

        data = await read(reader, writer)
        data_packet = DataPacket.from_bytes(data)
        await handle_packet(data_packet, writer)
        if data == b'':
            break

    await disconnect(reader, writer)


async def disconnect(reader, writer):
    client_id = client_socket_to_id[(reader, writer)]

    if client_id in game_state.players.keys():
        game_state.players.pop(client_id)

    client_socket_to_id.pop((reader, writer))
    writer.close()
    await writer.wait_closed()
    print(f'client with id {client_id} disconnected')


async def send_players_data(writer: asyncio.StreamWriter):
    players_data = dict()
    for player_id in game_state.players.keys():
        if GameState.STATUS_PLAYING not in game_state.players[player_id].flags:
            continue
        players_data[player_id] = game_state.players[player_id].encode()
    response = DataPacket(DataPacket.PLAYERS_INFO, players_data)

    await send(writer, response)


async def send(writer: asyncio.StreamWriter, data_packet: DataPacket):
    writer.write(data_packet.encode() + b'\n')
    await writer.drain()


def change_level(level_name):
    game_state.game_ended = False
    game_state.change_level(level_name)

    for client_socket, player_id in client_socket_to_id.items():
        game_state.players[player_id].hp = 100
        spawn_pos = game_state.get_spawn()
        game_data = {'level_name': game_state.level_name, 'position': spawn_pos}
        game_state.players[player_id].x, game_state.players[player_id].y = spawn_pos

        response = DataPacket(DataPacket.GAME_INFO, game_data)
        if GameState.STATUS_PLAYING in game_state.players[player_id].flags:
            game_state.players[player_id].flags.remove(GameState.STATUS_PLAYING)
        send(client_socket, response)


async def handle_packet(data_packet: DataPacket, writer: asyncio.StreamWriter):
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
        for (reader, writer), player_id in client_socket_to_id.items():
            await send(writer, response)

    await send_players_data(writer)


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


async def loop():
    tick_rate = 1
    last_tick = time.time()

    while True:
        for _ in range(event_queue.qsize()):
            event = event_queue.get()
            if time.time() > event.time_created + event.delay_seconds:
                event.callback(*event.args)
            else:
                event_queue.put(event)

        time_delta = time.time() - last_tick
        update(time_delta)

        await asyncio.sleep(tick_rate)


async def main():
    # tcp_socket = get_tcp_socket()
    tcp_server = await asyncio.start_server(accept_connection, server, tcp_port)

    print("Server is up waiting...")

    loop_task = asyncio.create_task(loop())

    await loop_task
    async with tcp_server:
        await tcp_server.serve_forever()

    return


if __name__ == '__main__':
    asyncio.run(main(), debug=True)
