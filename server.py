from __future__ import annotations

import asyncio
import time

import pygame

from level import Level, GameObjectPoint
from network import DataPacket
from weapon import Weapon

DEBUG = True
TICK_RATE = 60

server = "127.0.0.1"
tcp_port = 5555

current_id = 0
client_socket_to_id: dict[tuple[asyncio.StreamReader, asyncio.StreamWriter], int] = {}

lock = asyncio.Lock()


class ServerPlayer:
    def __init__(self, player_id: int, x: int, y: int, status: str, direction: str, sprite_animation_counter: int,
                 hp: int, ch_data: dict):
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
                self.vx, self.vy, self.off_ground_counter]

    def __repr__(self):
        return str((self.x, self.y, self.hp))


class ServerBullet:
    bullet_id = 0

    def __init__(self, x: int, y: int, vx: int, vy: int):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.current_lifetime_seconds = 0
        self.max_lifetime_seconds = 1
        self.damage = 300

    def update(self, timedelta: int) -> None:
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

        weapon_rect_height = Weapon.all_weapons_info[name]['WEAPON_RECT_HEIGHT']
        weapon_rect_width = Weapon.all_weapons_info[name]['WEAPON_RECT_WIDTH']
        image_offset_x = Weapon.all_weapons_info[name]['IMAGE_OFFSET_X']
        image_offset_y = Weapon.all_weapons_info[name]['IMAGE_OFFSET_Y']
        image_width = Weapon.all_weapons_info[name]['IMAGE_WIDTH']
        image_height = Weapon.all_weapons_info[name]['IMAGE_HEIGHT']

        self.center_offset_x = image_offset_x + image_width // 2
        self.center_offset_y = image_offset_y + image_height
        self.rect = pygame.Rect(x - self.center_offset_x, y - self.center_offset_y,
                                weapon_rect_height, weapon_rect_width)

    def update(self):
        pass

    def get_center(self) -> tuple[int, int]:
        return self.rect.x + self.center_offset_x, self.rect.y + self.center_offset_y

    def pick_up(self, player_id):
        pass

    def encode(self):
        return [self.name, self.rect.x, self.rect.y]


class GameState:
    STATUS_WAIT = 1
    STATUS_CONNECTED = 2
    STATUS_PLAYING = 3

    def __init__(self):
        self.players: dict[int, ServerPlayer] = dict()
        self.bullets: dict[int, ServerBullet] = dict()
        self.weapons: dict[int, ServerWeapon] = dict()

        self.level_name: str = 'lobby'
        self.level: Level = Level(self.level_name)
        self.spawn_points: list[GameObjectPoint] = []
        self.current_spawn_point: int = 0
        self.change_level(self.level_name)

        self.game_ended = False

    def change_level(self, level_name) -> None:
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

    def get_spawn_point(self) -> tuple[int, int]:
        spawn_point = self.spawn_points[self.current_spawn_point]
        self.current_spawn_point = (self.current_spawn_point + 1) % len(self.spawn_points)
        return spawn_point.x, spawn_point.y


game_state = GameState()


async def accept_connection(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    global current_id, client_socket_to_id

    client_socket_to_id[(reader, writer)] = current_id
    current_id += 1

    auth_data = {'id': client_socket_to_id[(reader, writer)]}
    response = DataPacket(DataPacket.AUTH, auth_data)
    await send(writer, response)

    game_data = {'level_name': 'lobby', 'position': game_state.get_spawn_point()}
    response = DataPacket(DataPacket.GAME_INFO, game_data)
    await send(writer, response)

    print(f"New connection. Id={client_socket_to_id[(reader, writer)]}")

    while True:
        try:
            data = await read(reader)
        except Exception as e:
            print(e)
            break
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


async def read(reader: asyncio.StreamReader) -> bytes:
    return await reader.readline()


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


async def change_level(level_name):
    game_state.game_ended = False
    game_state.change_level(level_name)

    for (reader, writer), player_id in client_socket_to_id.items():
        game_state.players[player_id].hp = 100
        spawn_pos = game_state.get_spawn_point()

        game_data = {'level_name': game_state.level_name, 'position': spawn_pos}
        game_state.players[player_id].x, game_state.players[player_id].y = spawn_pos

        response = DataPacket(DataPacket.GAME_INFO, game_data)
        if GameState.STATUS_PLAYING in game_state.players[player_id].flags:
            game_state.players[player_id].flags.remove(GameState.STATUS_PLAYING)
        await send(writer, response)

        for weapon_id, weapon in game_state.weapons.items():
            weapon_data = {'weapon_id': weapon_id, 'weapon_data': weapon.encode()}
            response = DataPacket(DataPacket.NEW_WEAPON_FROM_SERVER, weapon_data)
            await send(writer, response)


async def handle_packet(data_packet: DataPacket, writer: asyncio.StreamWriter):
    client_id: int = data_packet['id']

    if data_packet.data_type == DataPacket.INITIAL_INFO:
        data = data_packet['data']
        game_state.players[client_id] = ServerPlayer.from_player_data(client_id, data)
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

    if data_packet.data_type == DataPacket.NEW_SHOT_FROM_CLIENT:

        bullet_data = data_packet['data']
        bullet = ServerBullet(*bullet_data)
        bullet_id = ServerBullet.bullet_id
        ServerBullet.bullet_id += 1

        game_state.bullets[bullet_id] = bullet

        response = DataPacket(DataPacket.NEW_SHOT_FROM_SERVER, [client_id, bullet_id, bullet_data])
        for (reader, writer), player_id in client_socket_to_id.items():
            await send(writer, response)

    if data_packet.data_type == DataPacket.CLIENT_PICK_WEAPON_REQUEST:
        closest_weapon_id = None
        min_dist = 1e9
        for weapon_id, weapon in game_state.weapons.items():

            if weapon.owner is not None:
                continue
            distance = pygame.math.Vector2(weapon.get_center()).distance_to(game_state.players[client_id].get_center())
            if distance > 16:
                continue
            if distance < min_dist:
                min_dist = distance
                closest_weapon_id = weapon_id

        if closest_weapon_id is not None:
            game_state.weapons[closest_weapon_id].owner = client_id
            response = DataPacket(DataPacket.CLIENT_PICKED_WEAPON,
                                  {'owner_id': client_id, 'weapon_id': closest_weapon_id})
            for (reader, writer), player_id in client_socket_to_id.items():
                await send(writer, response)

    if data_packet.data_type == DataPacket.CLIENT_DROPPED_WEAPON:
        weapon_id = data_packet['weapon_id']
        weapon_position = data_packet['weapon_position']
        game_state.weapons[weapon_id].owner = None
        game_state.weapons[weapon_id].rect.x, game_state.weapons[weapon_id].rect.y = weapon_position
        response = DataPacket(DataPacket.CLIENT_DROPPED_WEAPON,
                              {'owner_id': client_id, 'weapon_id': weapon_id, 'weapon_position': weapon_position})
        for (reader, writer), player_id in client_socket_to_id.items():
            await send(writer, response)

    await send_players_data(writer)


async def update(time_delta):
    # Игроков не осталось
    if not game_state.players:
        if game_state.level_name != 'lobby':
            await change_level('lobby')
        return

    if game_state.game_ended:
        return

    # Все игроки готовы начать игру (флаг устанавливается в лобби)
    if all([DataPacket.FLAG_READY in player.flags for player in game_state.players.values()]) \
            and not game_state.game_ended:
        game_state.game_ended = True
        await asyncio.sleep(1)
        await change_level('firstmap')
        return

    # В живых остался только один (не единственный) игрок
    if len(game_state.players) > 1 and sum([player.hp > 0 for player in game_state.players.values()]) == 1 \
            and not game_state.game_ended:
        game_state.game_ended = True
        await asyncio.sleep(1)
        await change_level('firstmap')
        return

    # Пробегаемся по все игрокам
    for (reader, writer), client_id in client_socket_to_id.items():

        # Игрок выпал за пределы карты
        if client_id in game_state.players.keys() and game_state.players[client_id].y > 3000:
            if game_state.players[client_id].hp == 0:
                continue
            game_state.players[client_id].hp = 0
            data_packet = DataPacket(DataPacket.HEALTH_POINTS, game_state.players[client_id].hp)
            await send(writer, data_packet)

    async def delete_bullet(bullet_id):  # Рассылает всем пакет, о том, что пуля с id=bullet_id удалена
        game_state.bullets.pop(bullet_id)
        for (reader, writer), client_id in client_socket_to_id.items():
            data_packet = DataPacket(DataPacket.DELETE_BULLET_FROM_SERVER, bullet_id)
            await send(writer, data_packet)

    for bullet_id in list(game_state.bullets.keys()):
        bullet = game_state.bullets[bullet_id]
        bullet.update(time_delta)
        if bullet.current_lifetime_seconds > bullet.max_lifetime_seconds or \
                game_state.level.collide_point(*bullet.get_position()):
            await delete_bullet(bullet_id)

    for bullet_id in list(game_state.bullets):
        bullet = game_state.bullets[bullet_id]
        for (reader, writer), client_id in client_socket_to_id.items():
            if game_state.players[client_id].hp <= 0:
                continue
            if GameState.STATUS_PLAYING not in game_state.players[client_id].flags:
                continue

            if game_state.players[client_id].sprite_rect.collidepoint(bullet.get_position()):
                game_state.players[client_id].hp -= bullet.damage
                data_packet = DataPacket(DataPacket.HEALTH_POINTS, game_state.players[client_id].hp)
                await send(writer, data_packet)
                await delete_bullet(bullet_id)


async def loop():
    last_tick = time.time()
    while True:
        time_delta = time.time() - last_tick
        last_tick = time.time()

        await update(time_delta)
        await asyncio.sleep(1 / TICK_RATE)


async def main():
    tcp_server = await asyncio.start_server(accept_connection, server, tcp_port)

    print("Server is up waiting...")

    loop_task = asyncio.create_task(loop())

    await loop_task
    async with tcp_server:
        await tcp_server.serve_forever()

    return


if __name__ == '__main__':
    asyncio.run(main(), debug=DEBUG)
