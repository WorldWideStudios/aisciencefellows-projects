import os
import shutil
import pandas as pd
import numpy as np
import sys
from ultralytics import YOLO

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from prepare_pose import prepare_pose_crops_for_split
from augment_pose import augment_pose_crops


def setup_pose_cv_pipeline():
    """
    5-Fold Cross-Validation training for YOLO26n-Pose on tube crops.
    Mirrors the structure of train_cv.py but operates on pose crop datasets.

    Prerequisites:
        - OBB cross-validation completed (dataset_cv/fold_*/train|val with annotations.csv)
        - yolo26n-pose.pt base weights available
    """
    cv_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'dataset_cv'))
    pose_runs_dir = os.path.join(cv_dir, 'pose_runs')

    K = 5
    fold_metrics = []

    for k in range(K):
        print(f"\n{'='*50}")
        print(f"POSE TRAINING — FOLD {k+1}/{K}")
        print(f"{'='*50}")

        fold_dir = os.path.join(cv_dir, f"fold_{k+1}")

        # Check that the fold directory from OBB training exists
        if not os.path.exists(fold_dir):
            print(f"Error: {fold_dir} not found. Run train_cv.py first.")
            return

        # --- 1. Generate pose crops from fold's train & val splits ---
        pose_train_dir = os.path.join(fold_dir, 'pose_train')
        pose_val_dir = os.path.join(fold_dir, 'pose_val')

        # Clean previous pose crop data for this fold
        for d in [pose_train_dir, pose_val_dir]:
            if os.path.exists(d):
                shutil.rmtree(d)

        print("Generating pose crops from train split...")
        prepare_pose_crops_for_split(
            split_dir=os.path.join(fold_dir, 'train'),
            output_dir=pose_train_dir,
            padding_pct=0.20
        )

        print("Generating pose crops from val split...")
        prepare_pose_crops_for_split(
            split_dir=os.path.join(fold_dir, 'val'),
            output_dir=pose_val_dir,
            padding_pct=0.20
        )

        # --- 2. Augment ONLY train crops ---
        print("Augmenting train pose crops (10× per crop)...")
        augment_pose_crops(
            images_dir=os.path.join(pose_train_dir, 'images'),
            labels_dir=os.path.join(pose_train_dir, 'labels'),
            num_augmentations=5
        )

        # --- 3. Create pose data.yaml for this fold ---
        yaml_path = os.path.join(fold_dir, 'pose_data.yaml')
        fold_abs = fold_dir.replace('\\', '/')
        yaml_content = (
            f"path: {fold_abs}\n"
            f"train: pose_train/images\n"
            f"val: pose_val/images\n"
            f"\n"
            f"names:\n"
            f"  0: tube\n"
            f"\n"
            f"kpt_shape: [2, 3]\n"
        )
        with open(yaml_path, 'w') as f:
            f.write(yaml_content)

        # --- 4. Train YOLO26n-Pose ---
        print(f"Training YOLO26n-Pose on Fold {k+1}...")
        model = YOLO('yolo26n-pose.pt')

        results = model.train(
            data=yaml_path,
            epochs=25,
            imgsz=256,
            batch=16,
            workers=2,
            project=pose_runs_dir,
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
            mosaic=1.0,
        )

        # --- 5. Validate and collect metrics ---
        metrics = model.val()
        fold_metrics.append(metrics)

    # --- 6. Report aggregate results ---
    print(f"\n{'='*50}")
    print("Pose Cross-Validation Complete!")
    print(f"{'='*50}")

    # Extract pose mAP50 from each fold
    pose_maps = []
    for m in fold_metrics:
        # YOLO pose metrics are under metrics.pose.map50
        pose_group = getattr(m, 'pose', getattr(m, 'box', m))
        pose_maps.append(pose_group.map50)

    print(f"Fold Pose mAP50 scores: {[round(m, 4) for m in pose_maps]}")
    print(f"Average Pose mAP50: {round(np.mean(pose_maps), 4)} "
          f"(+/- {round(np.std(pose_maps), 4)})")


if __name__ == "__main__":
    setup_pose_cv_pipeline()
