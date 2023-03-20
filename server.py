import socket
import json
import selectors
from time import time
from network import Datagram

sel = selectors.DefaultSelector()

server = "192.168.50.255"
port = 5555
players_data: dict[int, str] = {}
clients = []
current_id = 0
address_to_id = {}
address_last_datagram = {}


def authorize(server_socket: socket.socket, address):
    global current_id, address_to_id
    if address not in address_to_id.keys():
        address_to_id[address] = current_id
        current_id += 1
    else:
        print(f'already authorized: {address} with id {address_to_id[address]}')

    reply = Datagram(Datagram.AUTH, time(), {'id': address_to_id[address]})
    server_socket.sendto(reply.encode(), address)
    print(f'{address} with id {address_to_id[address]} connected')


def disconnect(server_socket: socket.socket, address):
    if address in address_to_id.keys():
        client_id = address_to_id[address]
        if client_id in players_data.keys():
            players_data.pop(client_id)
        address_to_id.pop(address)
        print(f'{address} with id {client_id} disconnected')


def send_players_data(server_socket: socket.socket, address):
    reply = Datagram(Datagram.GAME, time())
    reply['data'] = {'data': players_data}
    server_socket.sendto(reply.encode(), address)
    print(f'sent to {address} with id {address_to_id[address]} {reply}')


def handle_datagram(server_socket: socket.socket, mask):
    global players_data
    data, address = server_socket.recvfrom(4096)
    datagram = Datagram.from_bytes(data)
    if datagram.purpose == Datagram.AUTH:
        authorize(server_socket, address)
        return

    elif datagram.purpose == Datagram.DISCONNECT:
        disconnect(server_socket, address)
        return

    elif datagram.purpose == Datagram.GAME:
        if datagram['client_id'] == -1:
            return
        players_data[datagram['client_id']] = json.loads(datagram['data'])
        send_players_data(server_socket, address)


def main():
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.setblocking(False)
    try:
        udp_socket.bind((server, port))
    except Exception as e:
        print(e)
        raise e

    print("Server is up waiting...")

    sel.register(udp_socket, selectors.EVENT_READ, data=handle_datagram)
    while True:
        events = sel.select(timeout=1)
        for key, mask in events:
            callback = key.data
            callback(key.fileobj, mask)


if __name__ == '__main__':
    main()
