from _thread import start_new_thread
import socket
import json

server = ""
port = 5555

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

try:
    s.bind((server, port))
except socket.error as e:
    print(e)

print("Server is up, waiting")

players_data: dict[int, str] = {}
clients = []

current_id = 0


def authorize(udp_socket: socket.socket, address):
    global current_id
    clients.append(current_id)
    udp_socket.sendto(current_id.to_bytes(1, 'little'), address)
    print(f'{address} with id {current_id} connected')
    current_id += 1


def disconnect(client_id, address, udp_socket: socket.socket):
    udp_socket.sendto('ok'.encode(), address)
    clients.remove(client_id)
    players_data.pop(client_id)
    print(f'{address} with id {client_id} disconnected')


while True:
    data, address = s.recvfrom(2048)
    data = json.loads(data.decode('utf-8'))
    client_id, data = data['id'], data['data']
    if data == 'auth':
        authorize(s, address)
        continue

    if data == 'disconnect':
        disconnect(client_id, address, s)
        continue

    players_data[client_id] = data
    reply = json.dumps(players_data).encode()
    s.sendto(reply, address)
