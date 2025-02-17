import socket
import time
from selectors import DefaultSelector, EVENT_READ

import cv2
from ultralytics import YOLO

from config import WEBCAM_SERVER_PORT
from network import DataPacket

HOST = '127.0.0.1'
PORT = WEBCAM_SERVER_PORT

sel = DefaultSelector()
sender = None

connections = []


def accept_connection(sock: socket.socket):
    global sender

    conn, addr = sock.accept()
    connections.append(sender)
    sender = conn


def receive():
    while True:
        events = sel.select(timeout=0)
        if not events:
            return
        for key, mask in events:
            if key.data is None:
                accept_connection(key.fileobj)
            else:
                pass


def run():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((HOST, PORT))
    sock.listen(1)
    sock.setblocking(False)

    sel.register(sock, EVENT_READ, data=None)

    def raise_exception(exception_message):
        response = DataPacket(DataPacket.WEBCAM_EXCEPTION)
        response['data'] = exception_message
        response.headers['game_id'] = -1
        if sender:
            sender.send(response.encode())

    model = YOLO('ml/Models/classify/final/weights/best.pt')
    cap = cv2.VideoCapture(0)

    frames_counter = 0
    cooldown = 0

    while cap.isOpened():
        receive()

        try:
            ret, frame = cap.read()
        except Exception as e:
            raise_exception(str(e))
            break

        results = model(frame, verbose=False)
        hands_up = float(results[0].probs.data[0])
        current_status = 'normal'
        if hands_up >= 0.85:
            current_status = 'debuffed'

        current_time = time.time()
        if current_status == 'debuffed' and (current_time - cooldown) >= 3:
            frames_counter += 1
        if frames_counter >= 18:
            response = DataPacket(DataPacket.WEBCAM_RESPONSE)
            response['data'] = 'hands up'
            response.headers['game_id'] = -1
            if sender:
                try:
                    sender.send(response.encode())
                except Exception as e:
                    print(e)
            frames_counter = 0
            cooldown = time.time()

        try:
            frame = cv2.resize(frame, (320, 200))
            cv2.imshow('Cam', frame)
        except Exception as e:
            raise_exception(str(e))
            break

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        cv2.waitKey(45)

    cap.release()
    cv2.destroyAllWindows()
    raise_exception('Webcam exception')


if __name__ == '__main__':
    run()
