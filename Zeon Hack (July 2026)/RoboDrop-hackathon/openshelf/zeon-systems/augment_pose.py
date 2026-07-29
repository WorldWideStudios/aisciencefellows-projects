import os
import cv2
import numpy as np
import albumentations as A


def get_pose_crop_augmentation_pipeline():
    """
    Albumentations pipeline for augmenting pose crop images with 2 keypoints.

    Adapted from augment_dataset.py for small single-tube crops:
    - Smaller blur limits (crops are ~50px)
    - Conservative scale/translate (tube fills the crop)
    - Full rotation for angle diversity
    - No CoarseDropout (crops are too small, would mask the entire tube)
    """
    return A.Compose([
        # --- 1. PIXEL-LEVEL (Simulate lighting / camera variations) ---
        A.RandomBrightnessContrast(brightness_limit=0.2, contrast_limit=0.2, p=0.4),
        A.HueSaturationValue(hue_shift_limit=15, sat_shift_limit=20, val_shift_limit=15, p=0.4),
        A.CLAHE(clip_limit=2.0, tile_grid_size=(4, 4), p=0.3),

        A.OneOf([
            A.GaussianBlur(blur_limit=(3, 5), p=1.0),
            A.MedianBlur(blur_limit=3, p=1.0),
            A.MotionBlur(blur_limit=3, p=1.0),
        ], p=0.3),

        A.OneOf([
            A.GaussNoise(std_range=(0.1, 0.3), p=1.0),
            A.ISONoise(p=1.0),
            A.ImageCompression(quality_range=(70, 100), p=1.0),
        ], p=0.3),

        # --- 2. SPATIAL (Geometric diversity for angle learning) ---
        A.HorizontalFlip(p=0.5),
        A.VerticalFlip(p=0.5),
        A.Affine(
            scale=(0.85, 1.15),
            translate_percent=(-0.05, 0.05),
            rotate=(-180, 180),
            shear=(-5, 5),
            p=0.8
        ),
    ], keypoint_params=A.KeypointParams(format='xy', remove_invisible=False))


def augment_pose_crops(images_dir, labels_dir, num_augmentations=10):
    """
    Augment pose crop images and their YOLO-Pose labels in-place.

    For each crop image + label pair:
    1. Read the image and parse the 2 keypoints from the label
    2. Apply the augmentation pipeline
    3. Discard if either keypoint falls outside the image
    4. Save augmented image + label with aug_ prefix

    Args:
        images_dir: directory containing crop .png files
        labels_dir: directory containing YOLO-Pose .txt labels
        num_augmentations: number of augmented versions per crop
    """
    transform = get_pose_crop_augmentation_pipeline()

    image_files = sorted([f for f in os.listdir(images_dir) if f.endswith(('.png', '.jpg'))])
    # Filter out already-augmented images to prevent nested augmentation
    image_files = [f for f in image_files if not f.startswith('aug_')]

    total_generated = 0
    total_discarded = 0

    for img_name in image_files:
        img_path = os.path.join(images_dir, img_name)
        txt_name = os.path.splitext(img_name)[0] + '.txt'
        txt_path = os.path.join(labels_dir, txt_name)

        if not os.path.exists(txt_path):
            continue

        img = cv2.imread(img_path)
        if img is None:
            continue

        img_h, img_w = img.shape[:2]

        # Parse the YOLO-Pose label
        # Format: class cx cy w h kp0_x kp0_y kp0_v kp1_x kp1_y kp1_v
        with open(txt_path, 'r') as f:
            line = f.readline().strip()

        parts = line.split()
        if len(parts) < 11:
            continue

        # Extract keypoints in absolute pixel coordinates
        kp0_x = float(parts[5]) * img_w
        kp0_y = float(parts[6]) * img_h
        kp1_x = float(parts[8]) * img_w
        kp1_y = float(parts[9]) * img_h

        keypoints = [(kp0_x, kp0_y), (kp1_x, kp1_y)]

        for aug_idx in range(num_augmentations):
            try:
                augmented = transform(image=img, keypoints=keypoints)
            except Exception:
                total_discarded += 1
                continue

            aug_img = augmented['image']
            aug_kpts = augmented['keypoints']

            if len(aug_kpts) < 2:
                total_discarded += 1
                continue

            aug_h, aug_w = aug_img.shape[:2]

            # Check both keypoints are within image bounds
            valid = True
            for kp in aug_kpts:
                if kp[0] < 0 or kp[0] > aug_w or kp[1] < 0 or kp[1] > aug_h:
                    valid = False
                    break

            if not valid:
                total_discarded += 1
                continue

            # Normalize keypoints back to [0, 1]
            new_kp0_x = np.clip(aug_kpts[0][0] / aug_w, 0.0, 1.0)
            new_kp0_y = np.clip(aug_kpts[0][1] / aug_h, 0.0, 1.0)
            new_kp1_x = np.clip(aug_kpts[1][0] / aug_w, 0.0, 1.0)
            new_kp1_y = np.clip(aug_kpts[1][1] / aug_h, 0.0, 1.0)

            # Write augmented label (bbox stays 0.5 0.5 1.0 1.0 for the whole crop)
            aug_label = (
                f"0 0.500000 0.500000 1.000000 1.000000 "
                f"{new_kp0_x:.6f} {new_kp0_y:.6f} 2 "
                f"{new_kp1_x:.6f} {new_kp1_y:.6f} 2"
            )

            aug_img_name = f"aug_{aug_idx}_{img_name}"
            aug_txt_name = f"aug_{aug_idx}_{txt_name}"

            cv2.imwrite(os.path.join(images_dir, aug_img_name), aug_img)
            with open(os.path.join(labels_dir, aug_txt_name), 'w') as f:
                f.write(aug_label + '\n')

            total_generated += 1

    print(f"Augmentation complete: {total_generated} augmented crops generated, "
          f"{total_discarded} discarded (keypoints out of bounds).")


def main():
    """Augment the train pose crops."""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'dataset_pose_crops', 'train'))

    images_dir = os.path.join(base_dir, 'images')
    labels_dir = os.path.join(base_dir, 'labels')

    if not os.path.exists(images_dir):
        print(f"Error: {images_dir} not found. Run prepare_pose_crops.py first.")
        return

    print("=" * 50)
    print("Augmenting Pose Crop Training Set")
    print("=" * 50)

    augment_pose_crops(images_dir, labels_dir, num_augmentations=10)


if __name__ == "__main__":
    main()
