import os
import socket
import json
import selectors
from network import DataPacket

sel = selectors.DefaultSelector()


server = "127.0.0.1"
tcp_port = 5555

clients = []
current_id = 0
client_socket_to_id = {}
ids = set()
MAX_CONNECTIONS = 10
c = 0


class GameState:
    STATUS_WAIT = 1
    STATUS_CONNECTED = 2
    STATUS_PLAYING = 3

    def __init__(self):
        self.players_count = 0
        self.players_flags: dict[int, set[int]] = {}
        self.players_data = {}

        self.game_started = False
        self.level_name = ''


game_state = GameState()


def accept_connection(server_socket: socket.socket, mask):
    global current_id, client_socket_to_id

    client_socket, address = server_socket.accept()
    client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    client_socket.setblocking(False)

    client_socket_to_id[client_socket] = current_id
    ids.add(current_id)
    current_id += 1

    auth_data = {'id': client_socket_to_id[client_socket]}
    response = DataPacket(DataPacket.AUTH, auth_data).encode()
    client_socket.send(response + b'\n')

    game_data = {'level_name': 'lobby', 'position': [10, 10]}
    response = DataPacket(DataPacket.GAME_INFO, game_data).encode()
    client_socket.send(response + b'\n')

    game_state.players_count += 1
    game_state.players_flags[auth_data['id']] = set()
    game_state.players_flags[auth_data['id']].add(GameState.STATUS_CONNECTED)

    sel.register(fileobj=client_socket, events=selectors.EVENT_READ, data=handle_tcp)

    print(f"New connection from {address}. Id={client_socket_to_id[client_socket]}")


def disconnect(client_socket):
    sel.unregister(client_socket)
    client_socket.close()
    client_id = client_socket_to_id[client_socket]

    game_state.players_count -= 1
    game_state.players_data.pop(client_id)
    game_state.players_flags.pop(client_id)

    client_socket_to_id.pop(client_socket)
    ids.remove(client_id)
    print(f'client with id {client_id} disconnected')


def send_players_data(client_socket: socket.socket):
    players_data = {}
    for player_id in ids:
        if GameState.STATUS_PLAYING not in game_state.players_flags[player_id]:
            continue
        players_data[player_id] = {}
        players_data[player_id] = game_state.players_data[player_id]
    response = DataPacket(DataPacket.PLAYERS_INFO, players_data).encode()


    client_socket.send(response + b'\n')


def change_level():

    game_data = {'level_name': game_state.level_name, 'position': [20, 20]}
    response = DataPacket(DataPacket.GAME_INFO, game_data).encode()
    for client_socket, player_id in client_socket_to_id.items():
        game_state.players_flags[player_id].remove(GameState.STATUS_PLAYING)
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
    if data_packet.data_type == DataPacket.CLIENT_PLAYER_INFO:
        game_state.players_flags[client_id].add(GameState.STATUS_PLAYING)
        game_state.players_data[client_id] = data_packet['data']

    if data_packet.data_type == DataPacket.ADD_PLAYER_FLAG:
        game_state.players_flags[client_id].add(data_packet['data'])
    if data_packet.data_type == DataPacket.REMOVE_PLAYER_FLAG:
        flag = data_packet['data']
        if flag in game_state.players_flags[client_id]:
            game_state.players_flags[client_id].remove(flag)

    # print(f"received from {client_id} {data_bytes}")

    send_players_data(client_socket)
    # print(f"send to {client_id} {data_bytes}")


def get_tcp_socket():
    tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    tcp_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    tcp_socket.setblocking(False)
    tcp_socket.bind((server, tcp_port))
    tcp_socket.listen(MAX_CONNECTIONS)
    return tcp_socket

def update():
    if all([DataPacket.FLAG_READY in player_flags for player_flags in game_state.players_flags.values()]):
        for player_id, player_flags in game_state.players_flags.items():
            player_flags.remove(DataPacket.FLAG_READY)
        game_state.level_name = 'testmap'
        change_level()


def main():
    tcp_socket = get_tcp_socket()

    print("Server is up waiting...")

    sel.register(tcp_socket, selectors.EVENT_READ, data=accept_connection)

    while True:
        update()
        events = sel.select()
        for key, mask in events:
            callback = key.data
            callback(key.fileobj, mask)

if __name__ == '__main__':
    main()
