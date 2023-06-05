print('Initializing...')

from ultralytics import YOLO
import cv2
from network import DataPacket
import socket

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
frames_counter_global = 0

while cap.isOpened():
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
    if hands_up > 0.85:
        current_status = 'debuffed'
    if current_status == 'debuffed':
        frames_counter += 1
    if frames_counter > 0:
        frames_counter_global += 1
    if frames_counter_global == 48:
        if frames_counter >= 40:
            response = DataPacket(DataPacket.WEBCAM_RESPONSE)
            response['data'] = 'hands up'
            response.headers['game_id'] = -1
            conn.send(response.encode())
        frames_counter = 0
        frames_counter_global = 0
    try:
        cv2.imshow('YOLO', frame)
    except Exception as e:
        raise_exception(str(e))
        break
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
cap.release()
cv2.destroyAllWindows()
raise_exception('webcam exception')

