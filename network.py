from __future__ import annotations

import json
import selectors
import socket
from time import time


class DataPacket:
    AUTH = 1
    INITIAL_INFO = 2
    GAME_STATE = 3
    DISCONNECT = 4
    GAME_INFO = 5
    PLAYERS_INFO = 6
    CLIENT_PLAYER_INFO = 7
    ADD_PLAYER_FLAG = 8
    REMOVE_PLAYER_FLAG = 9
    NEW_SHOT_FROM_CLIENT = 10
    NEW_SHOT_FROM_SERVER = 11
    DELETE_BULLET_FROM_SERVER = 12
    HEALTH_POINTS = 13
    NEW_WEAPON_FROM_SERVER = 14
    CLIENT_PICKED_WEAPON = 15
    CLIENT_DROPPED_WEAPON = 16
    CLIENT_PICK_WEAPON_REQUEST = 17
    GAME_ALREADY_STARTED = 18

    FLAG_READY = 100

    delimiter_byte = b'\n'

    def __init__(self, data_type, data=None, headers=None):
        self.data_type = data_type
        self.data = dict() if (data is None) else data
        self.headers = dict() if (headers is None) else headers

    @classmethod
    def from_bytes(cls, packet: bytes) -> DataPacket:
        packet = json.loads(packet)
        return DataPacket(packet['data_type'], packet['data'], packet['headers'])

    def __setitem__(self, key, value) -> None:
        self.data[key] = value

    def __getitem__(self, item):
        return self.data[item]

    def encode(self) -> bytes:
        datagram = {
            'data_type': self.data_type,
            'data': self.data,
            'headers': self.headers
        }
        return json.dumps(datagram).encode() + DataPacket.delimiter_byte


class Network:
    last_udp_packet_time = 0
    start_time = int(time())

    def __init__(self, server, port, callback):
        self.callback = callback
        self.server = server

        self.tcp_port = port
        self.tcp_address = (self.server, self.tcp_port)

        self.udp_port = port + 1
        self.udp_address = (self.server, self.udp_port)

        self.tcp_client_socket: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

        self.udp_client_socket: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self.sel = selectors.DefaultSelector()
        self.sel.register(self.tcp_client_socket, selectors.EVENT_READ, self.callback)
        self.sel.register(self.udp_client_socket, selectors.EVENT_READ, self.callback)

        self.id = -1

    def __del__(self):
        self.tcp_client_socket.close()

    def authorize(self):
        self.tcp_client_socket.settimeout(5)
        self.tcp_client_socket.connect(self.tcp_address)

    def send_tcp(self, data_packet: DataPacket):
        self.tcp_client_socket.send(data_packet.encode())

    def send_udp(self, data_packet: DataPacket):
        data_packet.headers['time'] = round(time() - Network.start_time, 3)
        self.udp_client_socket.sendto(data_packet.encode(), self.udp_address)

    @staticmethod
    def read_packet(sock: socket.socket):
        if sock.type == socket.SOCK_DGRAM:
            data = sock.recv(1024)
            data_packet = DataPacket.from_bytes(data)
            if data_packet.headers['time'] < Network.last_udp_packet_time:
                return None
            Network.last_udp_packet_time = data_packet.headers['time']
            return data_packet
        else:
            data = b''
            while True:
                byte = sock.recv(1)
                if byte == b'':
                    raise Exception('Disconnected')
                if byte == DataPacket.delimiter_byte:
                    break
                data += byte
            return DataPacket.from_bytes(data)

    def receive(self):
        received = False

        while True:
            events = self.sel.select(timeout=0)
            if not events:
                break
            for key, mask in events:
                data_packet = Network.read_packet(key.fileobj)
                if data_packet is not None:
                    received = True
                    callback = key.data
                    callback(data_packet, mask)

        return received
