import os
import cv2
import pandas as pd
import numpy as np
import albumentations as A

def encode_keypoints(row):
    """
    Encode the spatial annotations of a single tube into 6 keypoints.
    Returns:
        list of 6 keypoints: [Center, AngleDir, Box1, Box2, Box3, Box4]
    """
    bbox_w, bbox_h = row['bbox_w'], row['bbox_h']
    # Dynamic radius: half the major axis length of the OBB
    R_obb = max(bbox_w, bbox_h) / 2.0
    
    center_x, center_y = row['center_x'], row['center_y']
    C = [center_x, center_y]
    
    angle_deg = row['angle_deg']
    theta_rad = np.radians(angle_deg)
    A = [center_x + R_obb * np.cos(theta_rad), center_y + R_obb * np.sin(theta_rad)]
    
    bbox_x, bbox_y = row['bbox_x'], row['bbox_y']

    bbox_rotation = row['bbox_rotation']
    
    cx = bbox_x + bbox_w / 2.0
    cy = bbox_y + bbox_h / 2.0
    rect = ((cx, cy), (bbox_w, bbox_h), bbox_rotation)
    box = cv2.boxPoints(rect)
    
    return [C, A, list(box[0]), list(box[1]), list(box[2]), list(box[3])]

def decode_keypoints(kpts, original_row, img_w=640, img_h=480):
    """
    Decode the 6 transformed keypoints back into a dictionary representing a row.
    Returns None if the center of the tube is out of bounds.
    """
    C = kpts[0]
    A = kpts[1]
    box_pts = np.array(kpts[2:6], dtype=np.float32)
    
    # New Center
    new_center_x, new_center_y = C[0], C[1]
    
    # Check out of bounds - ensure the ENTIRE tube bounding box is inside the image
    xs = box_pts[:, 0]
    ys = box_pts[:, 1]
    
    if np.any(xs < 0) or np.any(xs > img_w) or np.any(ys < 0) or np.any(ys > img_h):
        return None
    
    # New Angle
    dx = A[0] - C[0]
    dy = A[1] - C[1]
    new_angle_deg = np.degrees(np.arctan2(dy, dx)) % 360.0
    
    # New Bounding Box
    rect = cv2.minAreaRect(box_pts)
    (cx, cy), (w, h), rot = rect
    
    bbox_x = cx - w / 2.0
    bbox_y = cy - h / 2.0
    
    new_row = {
        'center_x': new_center_x,
        'center_y': new_center_y,
        'bbox_x': bbox_x,
        'bbox_y': bbox_y,
        'bbox_w': w,
        'bbox_h': h,
        'bbox_rotation': rot,
        'angle_deg': new_angle_deg
    }
    return new_row

def get_augmentation_pipeline():
    """
    Define the Albumentations augmentation pipeline.
    """
    return A.Compose([
        # --- 1. PIXEL-LEVEL AUGMENTATIONS (Simulate lighting and camera variations) ---
        A.RandomBrightnessContrast(brightness_limit=0.2, contrast_limit=0.2, p=0.4),
        A.HueSaturationValue(hue_shift_limit=15, sat_shift_limit=20, val_shift_limit=15, p=0.4),
        A.CLAHE(clip_limit=2.0, tile_grid_size=(8, 8), p=0.3),
        
        # Add Noise and Blur (Use OneOf to ensure we don't apply multiple blurring effects at once)
        A.OneOf([
            A.GaussianBlur(blur_limit=(3, 5), p=1.0),
            A.MedianBlur(blur_limit=5, p=1.0),
            A.MotionBlur(blur_limit=5, p=1.0),
        ], p=0.3),
        
        A.OneOf([
            A.GaussNoise(std_range=(0.1, 0.3), p=1.0),
            A.ISONoise(p=1.0),
            A.ImageCompression(quality_range=(70, 100), p=1.0),
        ], p=0.3),

        # --- 2. SPATIAL AUGMENTATIONS (Vary object pose and scale) ---
        A.HorizontalFlip(p=0.5),
        A.VerticalFlip(p=0.5),
        # Increased scale range and added shear for more geometric variations
        A.Affine(
            scale=(0.8, 1.4), 
            translate_percent=(-0.1, 0.1), 
            rotate=(-180, 180), 
            shear=(-10, 10), 
            p=0.8
        ),

        # --- 3. OCCLUSION (Prevent memorization of specific features) ---
        # CoarseDropout randomly masks parts of the image, acting as a strong regularizer.
        # This is especially crucial for small datasets.
        A.CoarseDropout(
            num_holes_range=(1, 4), 
            hole_height_range=(0.05, 0.15), 
            hole_width_range=(0.05, 0.15), 
            fill=0, 
            p=0.5
        ),
    ], keypoint_params=A.KeypointParams(format='xy', remove_invisible=False))

def augment_dataset_folder(images_dir, annotations_file, output_images_dir, output_annotations_file, num_augmentations_per_image=20):
    os.makedirs(output_images_dir, exist_ok=True)
    
    df = pd.read_csv(annotations_file)
    grouped = df.groupby('image')
    
    transform = get_augmentation_pipeline()
    
    new_rows = []
    
    for img_name, group in grouped:
        img_path = os.path.join(images_dir, img_name)
        if not os.path.exists(img_path):
            print(f"Warning: {img_path} not found. Skipping.")
            continue
            
        img = cv2.imread(img_path)
        if img is None:
            print(f"Warning: Failed to read {img_path}. Skipping.")
            continue
            
        # Extract all keypoints for the current image
        all_keypoints = []
        for _, row in group.iterrows():
            kpts = encode_keypoints(row)
            all_keypoints.extend(kpts)
            
        # Generate N augmented versions
        for i in range(num_augmentations_per_image):
            augmented = transform(image=img, keypoints=all_keypoints)
            aug_img = augmented['image']
            aug_kpts = augmented['keypoints']
            
            aug_img_name = f"aug_{i}_{img_name}"
            
            # Reconstruct rows
            # Since each tube has 6 keypoints, we decode them in chunks of 6
            valid_image = True
            temp_rows = []
            for t_idx, (_, row) in enumerate(group.iterrows()):
                start_idx = t_idx * 6
                end_idx = start_idx + 6
                tube_kpts = aug_kpts[start_idx:end_idx]
                
                decoded_row = decode_keypoints(tube_kpts, row)
                if decoded_row is None:
                    valid_image = False
                    break # A tube was cut off!
                
                decoded_row['image'] = aug_img_name
                temp_rows.append(decoded_row)
                
            if not valid_image:
                # Skip saving this augmented image to avoid unannotated partial tubes
                continue
                
            new_rows.extend(temp_rows)
            # Save augmented image
            cv2.imwrite(os.path.join(output_images_dir, aug_img_name), aug_img)
            
        print(f"Processed {img_name} -> generated {num_augmentations_per_image} augmented versions.")
        
    # Save the new annotations
    # Combine original and new annotations? Or just new?
    # Let's combine them so the final csv has both original and augmented data.
    new_df = pd.DataFrame(new_rows)
    # Ensure column order matches original
    cols = ['image', 'center_x', 'center_y', 'bbox_x', 'bbox_y', 'bbox_w', 'bbox_h', 'bbox_rotation', 'angle_deg']
    new_df = new_df[cols]
    
    combined_df = pd.concat([df, new_df], ignore_index=True)
    combined_df.to_csv(output_annotations_file, index=False)
    
    print(f"\nDone! Augmented dataset generated.")
    print(f"Total images: {len(grouped) * (num_augmentations_per_image + 1)} (Original + Augmented)")
    print(f"Annotations saved to {output_annotations_file}")

def main():
    images_dir = os.path.join("dataset", "train", "images")
    annotations_file = os.path.join("dataset", "train", "annotations.csv")
    augment_dataset_folder(images_dir, annotations_file, images_dir, annotations_file, 20)

if __name__ == "__main__":
    main()
