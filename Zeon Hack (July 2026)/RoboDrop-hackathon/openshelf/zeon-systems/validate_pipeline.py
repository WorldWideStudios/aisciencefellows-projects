import os
import sys
import math
import cv2
import numpy as np
import pandas as pd
from ultralytics import YOLO

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from infer import infer_single_image


def angular_error(pred_angle, gt_angle):
    """
    Compute the minimum angular error between two angles in [0, 360).
    Returns a value in [0, 180].
    """
    diff = abs(pred_angle - gt_angle)
    return min(diff, 360 - diff)


def compute_iou_obb(box1_pts, box2_pts):
    """
    Compute IoU between two oriented bounding boxes using cv2.
    box1_pts, box2_pts: arrays of shape (4, 2) — 4 corner points.
    """
    ret, region = cv2.intersectConvexConvex(
        np.float32(box1_pts), np.float32(box2_pts)
    )
    if ret <= 0 or region is None:
        return 0.0

    intersection_area = cv2.contourArea(region)
    area1 = cv2.contourArea(np.float32(box1_pts))
    area2 = cv2.contourArea(np.float32(box2_pts))
    union_area = area1 + area2 - intersection_area

    if union_area <= 0:
        return 0.0
    return intersection_area / union_area


def get_obb_corners(row):
    """Get 4 OBB corner points from an annotation/prediction row."""
    cx = row['bbox_x'] + row['bbox_w'] / 2.0
    cy = row['bbox_y'] + row['bbox_h'] / 2.0
    rect = ((cx, cy), (row['bbox_w'], row['bbox_h']), row['bbox_rotation'])
    return cv2.boxPoints(rect)


def validate_pipeline():
    """
    Evaluate the full two-stage OBB → Pose pipeline on the holdout test set.

    Metrics:
        1. Precision — TP / (TP + FP)
        2. Recall    — TP / (TP + FN)
        3. F1-Score  — 2 * P * R / (P + R)
        4. Angle Error — MAAE, Median AE, % within 15° and 30°
    """
    # --- Load models from weights/ directory ---
    weights_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'weights'))

    obb_path = os.path.join(weights_dir, 'obb_best.pt')
    pose_path = os.path.join(weights_dir, 'pose_best.pt')

    print("Loading OBB model...")
    if not os.path.exists(obb_path):
        print(f"Error: OBB weights not found at {obb_path}")
        return
    obb_model = YOLO(obb_path)
    print(f"  Loaded: {obb_path}")

    print("Loading Pose model...")
    if not os.path.exists(pose_path):
        print(f"Error: Pose weights not found at {pose_path}")
        return
    pose_model = YOLO(pose_path)
    print(f"  Loaded: {pose_path}")

    # --- Load ground truth ---
    test_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'dataset', 'test'))
    gt_csv = os.path.join(test_dir, 'annotations.csv')

    if not os.path.exists(gt_csv):
        print(f"Error: Ground truth not found at {gt_csv}")
        return

    gt_df = pd.read_csv(gt_csv)
    test_images_dir = os.path.join(test_dir, 'images')

    save_dir = os.path.join(os.path.dirname(__file__), 'runs', 'pipeline_eval')
    os.makedirs(save_dir, exist_ok=True)

    # --- Run inference on all test images ---
    print(f"\nRunning pipeline on {gt_df['image'].nunique()} test images...")
    all_predictions = []

    for img_name in gt_df['image'].unique():
        img_path = os.path.join(test_images_dir, img_name)
        if not os.path.exists(img_path):
            print(f"Warning: {img_path} not found. Skipping.")
            continue

        preds = infer_single_image(img_path, obb_model, pose_model, save_dir=save_dir)
        all_predictions.extend(preds)

    if not all_predictions:
        print("No predictions generated. Check model weights.")
        return

    pred_df = pd.DataFrame(all_predictions)
    pred_df.to_csv(os.path.join(save_dir, 'predictions.csv'), index=False)

    # --- Match predictions to ground truth (IoU-based) ---
    iou_threshold = 0.3  # Lower threshold since OBBs can have slight shifts
    tp = 0
    fp = 0
    fn = 0
    angle_errors = []

    for img_name in gt_df['image'].unique():
        gt_rows = gt_df[gt_df['image'] == img_name]
        pred_rows = pred_df[pred_df['image'] == img_name] if img_name in pred_df['image'].values else pd.DataFrame()

        gt_matched = set()
        pred_matched = set()

        # Build GT OBB corners
        gt_boxes = []
        for idx, row in gt_rows.iterrows():
            gt_boxes.append((idx, get_obb_corners(row), row))

        # Build Pred OBB corners
        pred_boxes = []
        for idx, row in pred_rows.iterrows():
            pred_boxes.append((idx, get_obb_corners(row), row))

        # Greedy matching: for each prediction, find best matching GT
        for p_idx, p_box, p_row in pred_boxes:
            best_iou = 0
            best_gt_idx = None
            best_gt_row = None

            for g_idx, g_box, g_row in gt_boxes:
                if g_idx in gt_matched:
                    continue
                iou = compute_iou_obb(p_box, g_box)
                if iou > best_iou:
                    best_iou = iou
                    best_gt_idx = g_idx
                    best_gt_row = g_row

            if best_iou >= iou_threshold and best_gt_idx is not None:
                tp += 1
                gt_matched.add(best_gt_idx)
                pred_matched.add(p_idx)

                # Compute angle error for this matched pair
                ae = angular_error(p_row['angle_deg'], best_gt_row['angle_deg'])
                angle_errors.append({
                    'image': img_name,
                    'pred_angle': p_row['angle_deg'],
                    'gt_angle': best_gt_row['angle_deg'],
                    'error': ae,
                })
            else:
                fp += 1

        # Unmatched GTs are false negatives
        fn += len(gt_rows) - len(gt_matched)

    # --- Compute metrics ---
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1_score = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    angle_error_values = [ae['error'] for ae in angle_errors]
    maae = np.mean(angle_error_values) if angle_error_values else float('nan')
    median_ae = np.median(angle_error_values) if angle_error_values else float('nan')
    within_15 = (np.array(angle_error_values) <= 15).mean() * 100 if angle_error_values else 0.0
    within_30 = (np.array(angle_error_values) <= 30).mean() * 100 if angle_error_values else 0.0

    # --- Print results ---
    print("\n" + "=" * 60)
    print("HOLDOUT TEST SET — FULL PIPELINE EVALUATION")
    print("=" * 60)
    print(f"\n  OBB Model:  {obb_fold} ({obb_path})")
    print(f"  Pose Model: {pose_fold} ({pose_path})")
    print(f"\n--- Detection Metrics ---")
    print(f"  True Positives:  {tp}")
    print(f"  False Positives: {fp}")
    print(f"  False Negatives: {fn}")
    print(f"  Precision:       {precision:.4f}")
    print(f"  Recall:          {recall:.4f}")
    print(f"  F1-Score:        {f1_score:.4f}")
    print(f"\n--- Angle Error (on {len(angle_errors)} matched tubes) ---")
    print(f"  Mean Absolute Angle Error:   {maae:.2f}°")
    print(f"  Median Angle Error:          {median_ae:.2f}°")
    print(f"  % within 15°:               {within_15:.1f}%")
    print(f"  % within 30°:               {within_30:.1f}%")
    print("=" * 60)

    # Save angle errors for further analysis
    if angle_errors:
        ae_df = pd.DataFrame(angle_errors)
        ae_df.to_csv(os.path.join(save_dir, 'angle_errors.csv'), index=False)
        print(f"\nDetailed angle errors saved to {os.path.join(save_dir, 'angle_errors.csv')}")

    print(f"Annotated images saved to {save_dir}")
    print(f"Predictions saved to {os.path.join(save_dir, 'predictions.csv')}")


if __name__ == "__main__":
    validate_pipeline()
