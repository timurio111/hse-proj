print('Initializing...')

from ultralytics import YOLO
import cv2
from network import DataPacket
import socket
import time

HOST = '127.0.0.1'
PORT = 5557


def raise_exception(exception_message):
    response = DataPacket(DataPacket.WEBCAM_EXCEPTION)
    response['data'] = exception_message
    response.headers['game_id'] = -1
    conn.send(response.encode())


model = YOLO('ml/Models/classify/recommended_to_use/weights/best.pt')
cap = cv2.VideoCapture(0)

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind((HOST, PORT))
sock.listen(1)

print('Waiting')
conn, addr = sock.accept()
print('Connected')

response = DataPacket(DataPacket.WEBCAM_READY)
response.headers['game_id'] = -1
conn.send(response.encode())

frames_counter = 0
start_time = 0
delta_time = 0
delta_start = 0
delta_end = 0
flag = False

while cap.isOpened():
    if not flag:
        delta_start = time.time()
    try:
        ret, frame = cap.read()
    except Exception as e:
        raise_exception(str(e))
        break
    results = model(frame, verbose=False)
    names_dict = results[0].names
    hands_up = float(results[0].probs.data[0])
    current_status = 'normal'
    print(f'hands_up confidence: {hands_up}')
    if hands_up >= 0.85:
        current_status = 'debuffed'
    if current_status == 'debuffed':
        if start_time == 0:
            start_time = time.time()
        frames_counter += 1
    current_time = time.time()
    if start_time != 0 and current_time - start_time >= 2:
        if frames_counter >= 2 * (
                1 / delta_time) * 0.8:  # TODO подобрать константу, чтобы учесть лосс + плавучесть дельты
            response = DataPacket(DataPacket.WEBCAM_RESPONSE)
            response['data'] = 'hands up'
            response.headers['game_id'] = -1
            conn.send(response.encode())
        frames_counter = 0
        start_time = 0
    try:
        cv2.imshow('Cam', frame)
    except Exception as e:
        raise_exception(str(e))
        break
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
    if not flag:
        delta_end = time.time()
        delta_time = delta_end - delta_start
        flag = True
cap.release()
cv2.destroyAllWindows()
raise_exception('Webcam exception')
