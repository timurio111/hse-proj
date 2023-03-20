import asyncio
import json
import socket
import json
import selectors

from time import time, sleep


class Datagram:
    AUTH = 1
    GAME = 2
    DISCONNECT = 3

    def __init__(self, purpose, time=time(), data=None):
        self.purpose = purpose
        self.time = time
        self.data = dict() if (data is None) else data

    @classmethod
    def from_bytes(cls, datagram: bytes):
        datagram = json.loads(datagram)
        return Datagram(datagram['purpose'], datagram['time'], datagram['data'])

    def __setitem__(self, key, value):
        self.data[key] = value

    def __getitem__(self, item):
        return self.data[item]

    def encode(self) -> bytes:
        datagram = {
            'time': self.time,
            'purpose': self.purpose,
            'data': self.data
        }
        return json.dumps(datagram).encode()


class Network:
    def __init__(self):
        self.server = "192.168.50.255"
        self.port = 5555
        self.address = (self.server, self.port)

        self.udp_client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_client_socket.setblocking(False)

        self.sel = selectors.DefaultSelector()
        self.sel.register(self.udp_client_socket, selectors.EVENT_READ, self.handle_datagram)

        self.id = -1
        self.last_datagram = Datagram(Datagram.GAME, 0, {'data': {'data': {}}})

    def __del__(self):
        self.disconnect()

    def authorize(self):  # Надо обработать потерю пакета
        request = Datagram(purpose=Datagram.AUTH)
        request['id'] = self.id
        self.udp_client_socket.sendto(request.encode(), self.address)

    def disconnect(self):
        request = Datagram(purpose=Datagram.DISCONNECT)
        request['id'] = self.id
        self.udp_client_socket.sendto(request.encode(), self.address)

    def send_player_data(self, data):
        try:
            datagram = Datagram(Datagram.GAME, time())
            datagram['client_id'] = self.id
            datagram['data'] = data
            self.udp_client_socket.sendto(datagram.encode(), self.address)
        except socket.error as e:
            print(e)

    def handle_datagram(self, client_socket: socket.socket, mask):
        reply, address = client_socket.recvfrom(4096)
        datagram = Datagram.from_bytes(reply)
        if datagram.purpose == Datagram.AUTH:
            self.id = datagram['id']
        if datagram.purpose == Datagram.GAME:
            if self.last_datagram.time < datagram.time:
                self.last_datagram = datagram

    def receive(self):
        while True:
            events = self.sel.select(timeout=0)
            if not events:
                break
            for key, mask in events:
                callback = key.data
                callback(key.fileobj, mask)
