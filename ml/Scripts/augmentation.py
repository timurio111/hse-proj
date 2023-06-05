import os
import cv2
import numpy as np
import albumentations as A
from albumentations.pytorch import ToTensorV2
import torchvision.utils
from tqdm import tqdm
import uuid


def augmentation(data_class: str, label: str, pics_amount: int):
    transform = A.Compose(
        [
            A.Rotate(limit=40, p=0.4),
            A.HorizontalFlip(p=0.5),
            A.VerticalFlip(p=0.1),
            A.RGBShift(r_shift_limit=35, g_shift_limit=35, b_shift_limit=35, p=0.9),
            A.OneOf(
                [
                    A.Blur(blur_limit=6, p=0.5),
                    A.ColorJitter(p=0.5),
                ],
                p=1.0,
            ),
            A.Normalize(
                mean=[0, 0, 0],
                std=[1, 1, 1],
                max_pixel_value=255,
            ),
            ToTensorV2(),
        ]
    )

    folder = os.path.join('data', 'collected_pics', data_class, label)
    for filename in os.listdir(folder):
        image = cv2.imread(os.path.join(folder, filename))
        image = np.array(image)
        for i in tqdm(range(pics_amount)):
            augmentations = transform(image=image)
            new_filename = str(uuid.uuid1()) + filename[:-4] + str(i) + filename[len(filename) - 4:]
            augmented_filename = './data/collected_pics/{0}/augmented/{1}/{2}'.format(data_class, label, new_filename)
            torchvision.utils.save_image(augmentations['image'], augmented_filename)
