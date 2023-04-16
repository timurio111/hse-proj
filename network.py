import socket
import json
import selectors


class DataPacket:
    AUTH = 1
    GAME_STATE = 2
    DISCONNECT = 3
    GAME_INFO = 4
    PLAYERS_INFO = 5
    CLIENT_PLAYER_INFO = 6
    ADD_PLAYER_FLAG = 7
    REMOVE_PLAYER_FLAG = 8

    FLAG_READY = 100

    def __init__(self, data_type, data=None):
        self.data_type = data_type
        self.data = dict() if (data is None) else data

    @classmethod
    def from_bytes(cls, packet: bytes):
        packet = json.loads(packet)
        return DataPacket(packet['data_type'], packet['data'])

    def __setitem__(self, key, value):
        self.data[key] = value

    def __getitem__(self, item):
        return self.data[item]

    def encode(self) -> bytes:
        datagram = {
            'data_type': self.data_type,
            'data': self.data
        }
        return json.dumps(datagram).encode()


class Network:
    def __init__(self, server, port, callback):
        self.callback = callback
        self.server = server


        self.tcp_port = port
        self.tcp_address = (self.server, self.tcp_port)

        self.tcp_client_socket: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.tcp_client_socket.settimeout(3)
        self.sel = selectors.DefaultSelector()
        self.sel.register(self.tcp_client_socket, selectors.EVENT_READ, self.callback)

        self.id = -1

    def __del__(self):
        self.tcp_client_socket.close()

    def authorize(self):
        self.tcp_client_socket.connect(self.tcp_address)
        self.tcp_client_socket.setblocking(False)

    def send(self, data_packet: DataPacket):
        self.tcp_client_socket.send(data_packet.encode() + b'\n')

    def receive(self):
        while True:
            events = self.sel.select(timeout=0)
            if not events:
                break
            for key, mask in events:
                callback = key.data
                callback(key.fileobj, mask)
