from ultralytics import YOLO
import numpy as np
import cv2
from network import DataPacket
import socket


HOST = '127.0.0.1'
PORT = 5557

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((HOST, PORT))
s.listen(1)
conn, addr = s.accept()


frames_counter = 0
frames_counter_global = 0
model = YOLO('./runs/classify/train5/weights/last.pt')  # load a custom model
cap = cv2.VideoCapture(0)
while cap.isOpened():
    ret, frame = cap.read()
    results = model(frame, verbose=False)
    names_dict = results[0].names
    probs = results[0].probs.tolist()
    current_status = names_dict[np.argmax(probs)]
    # print(current_status)
    if current_status == 'debuffed':
        frames_counter += 1
    if frames_counter > 0:
        frames_counter_global += 1
    if frames_counter_global == 48:
        if frames_counter >= 40:
            response = DataPacket(DataPacket.WEBCAM_RESPONSE)
            response['data'] = 'hands up'
            response.headers['game_id'] = -1
        frames_counter = 0
        frames_counter_global = 0
    cv2.imshow('YOLO', frame)
    if cv2.waitKey(10) & 0xFF == ord('q'):
        break
cap.release()
cv2.destroyAllWindows()
