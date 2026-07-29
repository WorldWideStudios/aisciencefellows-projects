import os
import cv2
import pandas as pd
import numpy as np

def prepare_folder(split_dir):
    annotations_file = os.path.join(split_dir, 'annotations.csv')
    labels_dir = os.path.join(split_dir, 'labels')
    
    if not os.path.exists(annotations_file):
        print(f"Skipping {split_dir}: No annotations.csv found.")
        return
        
    os.makedirs(labels_dir, exist_ok=True)
    
    df = pd.read_csv(annotations_file)
    images_dir = os.path.join(split_dir, 'images')
    
    # Group by image to create one .txt per image
    grouped = df.groupby('image')
    
    for img_name, group in grouped:
        img_path = os.path.join(images_dir, img_name)
        img = cv2.imread(img_path)
        if img is None:
            print(f"Warning: Could not read {img_path}. Skipping.")
            continue
        img_h, img_w = img.shape[:2]
        
        txt_name = os.path.splitext(img_name)[0] + '.txt'
        txt_path = os.path.join(labels_dir, txt_name)
        
        lines = []
        for _, row in group.iterrows():
            bbox_x, bbox_y = row['bbox_x'], row['bbox_y']
            bbox_w, bbox_h = row['bbox_w'], row['bbox_h']
            bbox_rotation = row['bbox_rotation']
            
            # Get center
            cx = bbox_x + bbox_w / 2.0
            cy = bbox_y + bbox_h / 2.0
            
            # Get 4 corners using OpenCV's oriented bounding box logic
            rect = ((cx, cy), (bbox_w, bbox_h), bbox_rotation)
            box = cv2.boxPoints(rect) # Returns 4 points (x, y)
            
            # Normalize points to [0, 1] for YOLO
            box[:, 0] /= img_w
            box[:, 1] /= img_h
            
            # Format: class_index x1 y1 x2 y2 x3 y3 x4 y4
            class_idx = 0
            points_str = " ".join([f"{pt[0]:.6f} {pt[1]:.6f}" for pt in box])
            lines.append(f"{class_idx} {points_str}\n")
            
        with open(txt_path, 'w') as f:
            f.writelines(lines)
            
    print(f"Prepared YOLO OBB labels for {split_dir} ({len(grouped)} images).")

def create_yolo_obb_labels():
    splits = ['train', 'test']
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'dataset'))
    
    for split in splits:
        split_dir = os.path.join(base_dir, split)
        prepare_folder(split_dir)

def create_data_yaml():
    yaml_path = os.path.join(os.path.dirname(__file__), 'data.yaml')
    dataset_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'dataset'))
    # Use forward slashes to prevent issues with Ultralytics on Windows
    dataset_path = dataset_path.replace('\\', '/')
    
    yaml_content = f"""path: {dataset_path}
train: train/images
val: test/images
test: test/images

# Classes
names:
  0: tube
"""
    with open(yaml_path, 'w') as f:
        f.write(yaml_content)
    print(f"Created YOLO data configuration file at {yaml_path}")

if __name__ == "__main__":
    print("Preparing YOLOv8-OBB dataset...")
    create_yolo_obb_labels()
    create_data_yaml()
    print("Done!")