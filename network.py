import json
import socket
import json


class Network:
    def __init__(self):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server = ""
        self.port = 5555
        self.address = (self.server, self.port)
        self.id = -1
        self.id = self.authorize()
        self.client.settimeout(0.005)

        print(self.id)

    def __del__(self):
        self.disconnect()

    def authorize(self):
        try:
            b = self.send('auth')
            return int.from_bytes(b, 'little')
        except Exception as e:
            print(e)

    def disconnect(self):
        self.client.settimeout(1)
        self.send('disconnect')

    def send(self, data):

        try:
            data = json.dumps({'id': self.id, 'data': data}).encode()
            self.client.sendto(data, self.address)
            b, address = self.client.recvfrom(2048)
            return b
        except socket.error as e:
            print(e)

