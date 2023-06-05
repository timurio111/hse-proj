from ultralytics import YOLO
import cv2
from network import DataPacket
import socket


HOST = '127.0.0.1'
PORT = 5557

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind((HOST, PORT))
s.listen(1)
print('waiting')
conn, addr = s.accept()


frames_counter = 0
frames_counter_global = 0
model = YOLO('runs/classify/recommended_to_use/weights/best.pt')  # load a custom model
cap = cv2.VideoCapture(0)
while cap.isOpened():
    ret, frame = cap.read()
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
    cv2.imshow('YOLO', frame)
    if cv2.waitKey(10) & 0xFF == ord('q'):
        break
cap.release()
cv2.destroyAllWindows()
