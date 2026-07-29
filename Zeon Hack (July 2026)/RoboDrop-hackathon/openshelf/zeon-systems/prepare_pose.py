import os
import cv2
import pandas as pd
import numpy as np
from pathlib import Path


def crop_tube(img, row, padding_pct=0.15):
    """
    Crop a single tube from the full image using OBB + padding.

    Returns:
        crop_img: the cropped image (numpy array)
        crop_meta: dict with crop_x0, crop_y0, crop_w, crop_h in full-image pixels
        Returns (None, None) if crop is invalid.
    """
    img_h, img_w = img.shape[:2]

    # Compute 4 OBB corner points
    cx = row['bbox_x'] + row['bbox_w'] / 2.0
    cy = row['bbox_y'] + row['bbox_h'] / 2.0
    rect = ((cx, cy), (row['bbox_w'], row['bbox_h']), row['bbox_rotation'])
    box = cv2.boxPoints(rect)

    # Axis-aligned bounding box of the 4 OBB corners
    x_min, y_min = box.min(axis=0)
    x_max, y_max = box.max(axis=0)
    aabb_w = x_max - x_min
    aabb_h = y_max - y_min

    # Add padding
    pad_x = aabb_w * padding_pct
    pad_y = aabb_h * padding_pct

    crop_x0 = int(max(0, x_min - pad_x))
    crop_y0 = int(max(0, y_min - pad_y))
    crop_x1 = int(min(img_w, x_max + pad_x))
    crop_y1 = int(min(img_h, y_max + pad_y))

    crop_w = crop_x1 - crop_x0
    crop_h = crop_y1 - crop_y0

    if crop_w < 5 or crop_h < 5:
        return None, None

    crop_img = img[crop_y0:crop_y1, crop_x0:crop_x1].copy()

    crop_meta = {
        'crop_x0': crop_x0,
        'crop_y0': crop_y0,
        'crop_w': crop_w,
        'crop_h': crop_h,
    }
    return crop_img, crop_meta


def compute_pose_label(row, crop_meta):
    """
    Compute the YOLO-Pose label for a single tube crop.

    Keypoints:
        kp0 = Center (tube joint)
        kp1 = Tab (flap direction, derived from angle_deg)

    Coordinate system:
        Origin: top-left, X → right, Y → down
        angle_deg: 0° = rightward, increases counter-clockwise
        Tab = center + R * (cos(θ), -sin(θ))  [Y negated for image coords]

    Returns:
        label_line: YOLO-Pose format string
        Returns None if keypoints fall outside crop.
    """
    cx0 = crop_meta['crop_x0']
    cy0 = crop_meta['crop_y0']
    cw = crop_meta['crop_w']
    ch = crop_meta['crop_h']

    center_x = row['center_x']
    center_y = row['center_y']

    # Dynamic radius: half the major axis of the OBB
    R = max(row['bbox_w'], row['bbox_h']) / 2.0

    # Tab position in full-image coordinates
    theta_rad = np.radians(row['angle_deg'])
    tab_x = center_x + R * np.cos(theta_rad)
    tab_y = center_y - R * np.sin(theta_rad)  # Y-axis inverted in image coords

    # Convert to crop-relative normalized coordinates
    kp0_x = (center_x - cx0) / cw
    kp0_y = (center_y - cy0) / ch
    kp1_x = (tab_x - cx0) / cw
    kp1_y = (tab_y - cy0) / ch

    # Check keypoints are within [0, 1]
    for v in [kp0_x, kp0_y, kp1_x, kp1_y]:
        if v < -0.01 or v > 1.01:
            return None

    # Clamp to [0, 1]
    kp0_x = np.clip(kp0_x, 0.0, 1.0)
    kp0_y = np.clip(kp0_y, 0.0, 1.0)
    kp1_x = np.clip(kp1_x, 0.0, 1.0)
    kp1_y = np.clip(kp1_y, 0.0, 1.0)

    # Bounding box covers the entire crop (since each crop = 1 tube)
    bbox_cx = 0.5
    bbox_cy = 0.5
    bbox_w = 1.0
    bbox_h = 1.0

    # YOLO-Pose format: class cx cy w h  kp0_x kp0_y kp0_v  kp1_x kp1_y kp1_v
    label_line = (
        f"0 {bbox_cx:.6f} {bbox_cy:.6f} {bbox_w:.6f} {bbox_h:.6f} "
        f"{kp0_x:.6f} {kp0_y:.6f} 2 "
        f"{kp1_x:.6f} {kp1_y:.6f} 2"
    )
    return label_line


def prepare_pose_crops_for_split(split_dir, output_dir, padding_pct=0.20):
    """
    Generate pose crops and YOLO-Pose labels for a single split (train or test).

    Args:
        split_dir: path containing images/ and annotations.csv
        output_dir: path to write cropped images and labels
        padding_pct: padding as fraction of OBB AABB dimensions
    """
    annotations_file = os.path.join(split_dir, 'annotations.csv')
    images_dir = os.path.join(split_dir, 'images')

    if not os.path.exists(annotations_file):
        print(f"Skipping {split_dir}: No annotations.csv found.")
        return

    df = pd.read_csv(annotations_file)

    out_images_dir = os.path.join(output_dir, 'images')
    out_labels_dir = os.path.join(output_dir, 'labels')
    os.makedirs(out_images_dir, exist_ok=True)
    os.makedirs(out_labels_dir, exist_ok=True)

    # Track crop metadata for traceability
    crop_records = []
    total_crops = 0
    skipped = 0

    grouped = df.groupby('image')

    for img_name, group in grouped:
        img_path = os.path.join(images_dir, img_name)
        img = cv2.imread(img_path)
        if img is None:
            print(f"Warning: Could not read {img_path}. Skipping.")
            continue

        for tube_idx, (_, row) in enumerate(group.iterrows()):
            crop_img, crop_meta = crop_tube(img, row, padding_pct)
            if crop_img is None:
                skipped += 1
                continue

            label_line = compute_pose_label(row, crop_meta)
            if label_line is None:
                skipped += 1
                continue

            # Name: <image_stem>_tube<idx>.png
            stem = os.path.splitext(img_name)[0]
            crop_name = f"{stem}_tube{tube_idx}.png"
            txt_name = f"{stem}_tube{tube_idx}.txt"

            cv2.imwrite(os.path.join(out_images_dir, crop_name), crop_img)

            with open(os.path.join(out_labels_dir, txt_name), 'w') as f:
                f.write(label_line + '\n')

            # Save record for traceability
            crop_records.append({
                'crop_image': crop_name,
                'source_image': img_name,
                'center_x': row['center_x'],
                'center_y': row['center_y'],
                'angle_deg': row['angle_deg'],
                'crop_x0': crop_meta['crop_x0'],
                'crop_y0': crop_meta['crop_y0'],
                'crop_w': crop_meta['crop_w'],
                'crop_h': crop_meta['crop_h'],
            })
            total_crops += 1

    # Save crop annotations CSV
    if crop_records:
        crop_df = pd.DataFrame(crop_records)
        crop_df.to_csv(os.path.join(output_dir, 'crop_annotations.csv'), index=False)

    print(f"Prepared {total_crops} pose crops for {split_dir} (skipped {skipped}).")


def create_pose_yaml(output_base_dir):
    """Create the YOLO-Pose data.yaml file."""
    yaml_path = os.path.join(output_base_dir, 'pose_crops.yaml')
    base_path = os.path.abspath(output_base_dir).replace('\\', '/')

    yaml_content = f"""path: {base_path}
train: train/images
val: test/images

names:
  0: tube

kpt_shape: [2, 3]
"""
    with open(yaml_path, 'w') as f:
        f.write(yaml_content)
    print(f"Created pose_crops.yaml at {yaml_path}")


def main():
    """Generate pose crops from the existing dataset/train and dataset/test splits."""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'dataset'))
    output_base = os.path.abspath(os.path.join(os.path.dirname(__file__), 'dataset_pose_crops'))

    print("=" * 50)
    print("Preparing YOLO-Pose Crop Dataset")
    print("=" * 50)

    for split in ['train', 'test']:
        split_dir = os.path.join(base_dir, split)
        output_dir = os.path.join(output_base, split)
        print(f"\nProcessing {split} split...")
        prepare_pose_crops_for_split(split_dir, output_dir, padding_pct=0.20)

    create_pose_yaml(output_base)

    print("\n" + "=" * 50)
    print("Pose crop dataset generation complete!")
    print("=" * 50)


if __name__ == "__main__":
    main()
