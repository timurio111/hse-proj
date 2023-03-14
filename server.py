from _thread import start_new_thread
import socket
import json

server = ""
port = 5555

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
    s.bind((server, port))
except socket.error as e:
    print(e)

s.listen(8)
print("Waiting")

players_data: dict[int, str] = {}


def handle_client(connection: socket.socket, client_id):
    connection.send(str.encode(str(client_id)))
    while True:
        try:
            data = connection.recv(2048)
            players_data[client_id] = data.decode('utf-8')

            if not data:
                break
            else:
                print("OK")

            reply = json.dumps(players_data).encode()
            connection.sendall(reply)

        except Exception as e:
            print(e)

    print("Disconnected")
    players_data.pop(client_id)
    connection.close()


current_id = 0
while True:
    connection, address = s.accept()
    print(f"{address} connected")
    current_id += 1
    start_new_thread(handle_client, (connection, current_id,))
