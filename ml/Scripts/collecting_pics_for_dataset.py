import cv2
import time
import uuid
import os
from ml.Scripts.augmentation import augmentation

PICS_AMOUNT = 50
PICS_PATH = os.path.join('pics', '../../data/CollectedPics')

LABELS = ['debuffed', 'normal']

if not os.path.exists(PICS_PATH):
    os.mkdir(PICS_PATH)

for label in LABELS:
    CURRENT_PIC_PATH = os.path.join(PICS_PATH, label)
    if not os.path.exists(CURRENT_PIC_PATH):
        os.mkdir(CURRENT_PIC_PATH)

for label in LABELS:
    cap = cv2.VideoCapture(0)
    print("takin picZ for {}".format(label))
    time.sleep(7)
    for num in range(PICS_AMOUNT):
        print("ive just shot NIGGA numba {}".format(num + 1))
        ret, frame = cap.read()
        pic_name = os.path.join(PICS_PATH, label, label + '.' + '{}.jpg'.format(str(uuid.uuid1())))
        cv2.imwrite(pic_name, frame)
        cv2.imshow('i_just_wanna_be_happy', frame)
        time.sleep(1)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
cap.release()
cv2.destroyAllWindows()


augmentation('train', 'debuffed', 25)
augmentation('train', 'normal', 25)
augmentation('val', 'debuffed', 5)
augmentation('val', 'normal', 5)
