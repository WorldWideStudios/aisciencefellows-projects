import os
import shutil
import pandas as pd
import numpy as np
import sys
from ultralytics import YOLO

# Ensure we can import from the parent directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from augment_dataset import augment_dataset_folder
from prepare_yolo import prepare_folder

def setup_cv_pipeline():
    base_dataset_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'dataset'))
    cv_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'dataset_cv'))
    
    # 1. Gather images from train set
    train_csv = os.path.join(base_dataset_dir, 'train', 'annotations.csv')
    
    if not os.path.exists(train_csv):
        print("Error: train annotations not found. Did you run split_dataset.py?")
        return
        
    df_all = pd.read_csv(train_csv)
    
    # Filter out augmented images from previous runs to prevent nested augmentation
    df_all = df_all[~df_all['image'].str.startswith('aug_')]
    
    # Convert to standard list to avoid shuffle warnings on StringArray
    images = list(df_all['image'].unique())
    print(f"Total images for CV: {len(images)} (56 expected)")
    
    # Shuffle for K-Fold
    np.random.seed(42)
    np.random.shuffle(images)
    
    K = 5
    folds = np.array_split(images, K)
    
    # Helper to find image source path
    def get_img_src(img_name):
        p1 = os.path.join(base_dataset_dir, 'train', 'images', img_name)
        if os.path.exists(p1): return p1
        return None

    fold_metrics = []

    for k in range(K):
        print(f"\n{'='*50}")
        print(f"Starting FOLD {k+1}/{K}")
        print(f"{'='*50}")
        
        fold_dir = os.path.join(cv_dir, f"fold_{k+1}")
        
        # Validation set for this fold
        val_images = folds[k]
        # Train set is all other folds concatenated
        train_images = np.concatenate([folds[i] for i in range(K) if i != k])
        
        for split_name, split_imgs in [('train', train_images), ('val', val_images)]:
            split_dir = os.path.join(fold_dir, split_name)
            img_dir = os.path.join(split_dir, 'images')
            os.makedirs(img_dir, exist_ok=True)
            
            # Copy images
            for img in split_imgs:
                src = get_img_src(img)
                if src:
                    shutil.copy(src, os.path.join(img_dir, img))
                else:
                    print(f"Warning: Could not find source image {img}")
            
            # Save annotations
            split_df = df_all[df_all['image'].isin(split_imgs)]
            split_csv = os.path.join(split_dir, 'annotations.csv')
            split_df.to_csv(split_csv, index=False)
            
        print(f"Fold {k+1} Split: {len(train_images)} Train, {len(val_images)} Val")
        
        # 2. Augment strictly the train set
        print("Augmenting train set...")
        train_dir = os.path.join(fold_dir, 'train')
        augment_dataset_folder(
            images_dir=os.path.join(train_dir, 'images'),
            annotations_file=os.path.join(train_dir, 'annotations.csv'),
            output_images_dir=os.path.join(train_dir, 'images'),
            output_annotations_file=os.path.join(train_dir, 'annotations.csv'),
            num_augmentations_per_image=10
        )
        
        # 3. Prepare YOLO labels for both train and val
        print("Preparing YOLO OBB labels...")
        prepare_folder(os.path.join(fold_dir, 'train'))
        prepare_folder(os.path.join(fold_dir, 'val'))
        
        # 4. Create data.yaml
        yaml_path = os.path.join(fold_dir, 'data.yaml')
        yaml_content = f"path: {fold_dir.replace(chr(92), '/')}\ntrain: train/images\nval: val/images\nnames:\n  0: tube\n"
        with open(yaml_path, 'w') as f:
            f.write(yaml_content)
            
        # 5. Train YOLO
        print(f"Training YOLO26n-OBB on Fold {k+1}...")
        model = YOLO('yolo26n-obb.pt')  # Nano model has fewer parameters, harder to overfit
        
        results = model.train(
            data=yaml_path,
            epochs=50,
            imgsz=640,
            batch=16,
            workers=2,
            project=os.path.join(cv_dir, 'runs'),
            name=f"fold_{k+1}",
            exist_ok=True,
            verbose=False,
            device=0,
            dropout=0.3,
            weight_decay=0.001,
            patience=20,
            freeze=10,
            lr0=0.001,
            cos_lr=True,
            mixup=0.15,
            mosaic=1.0
        )
        
        # Collect final metrics on this fold's validation set
        metrics = model.val()
        fold_metrics.append(metrics)
        
    print(f"\n{'='*50}")
    print("Cross-Validation Complete!")
    print(f"{'='*50}")
    
    # Simple aggregation of map50
    maps = [m.box.map50 for m in fold_metrics]
    print(f"Fold mAP50 scores: {[round(m, 4) for m in maps]}")
    print(f"Average mAP50: {round(np.mean(maps), 4)} (+/- {round(np.std(maps), 4)})")

if __name__ == "__main__":
    setup_cv_pipeline()
