import os
import sys
import math
import glob
import cv2
import numpy as np
import pandas as pd
from ultralytics import YOLO

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from prepare_pose import crop_tube


def find_best_obb_model(cv_runs_dir):
    """Find the best OBB model across all CV folds by peak val mAP50."""
    best_map50 = -1.0
    best_path = None
    best_fold = None

    fold_dirs = glob.glob(os.path.join(cv_runs_dir, 'fold_*'))
    for fold_dir in fold_dirs:
        results_path = os.path.join(fold_dir, 'results.csv')
        weights_path = os.path.join(fold_dir, 'weights', 'best.pt')

        if not os.path.exists(results_path) or not os.path.exists(weights_path):
            continue

        try:
            df = pd.read_csv(results_path)
            df.columns = df.columns.str.strip()
            map_cols = [c for c in df.columns if 'mAP50' in c and '95' not in c]
            if not map_cols:
                continue
            val_map50 = df[map_cols[0]].max()
            if val_map50 > best_map50:
                best_map50 = val_map50
                best_path = weights_path
                best_fold = os.path.basename(fold_dir)
        except Exception as e:
            print(f"Error parsing {fold_dir}: {e}")

    return best_path, best_fold


def find_best_pose_model(pose_runs_dir):
    """Find the best Pose model across all CV folds by peak val mAP50."""
    best_map50 = -1.0
    best_path = None
    best_fold = None

    fold_dirs = glob.glob(os.path.join(pose_runs_dir, 'fold_*'))
    for fold_dir in fold_dirs:
        results_path = os.path.join(fold_dir, 'results.csv')
        weights_path = os.path.join(fold_dir, 'weights', 'best.pt')

        if not os.path.exists(results_path) or not os.path.exists(weights_path):
            continue

        try:
            df = pd.read_csv(results_path)
            df.columns = df.columns.str.strip()
            # Pose models have 'metrics/mAP50(P)' for pose keypoint mAP
            map_cols = [c for c in df.columns if 'mAP50' in c and '95' not in c]
            if not map_cols:
                continue
            val_map50 = df[map_cols[0]].max()
            if val_map50 > best_map50:
                best_map50 = val_map50
                best_path = weights_path
                best_fold = os.path.basename(fold_dir)
        except Exception as e:
            print(f"Error parsing {fold_dir}: {e}")

    return best_path, best_fold


def infer_single_image(image_path, obb_model, pose_model, conf_threshold=0.25,
                        padding_pct=0.20, save_dir=None):
    """
    Run the two-stage OBB → Pose inference pipeline on a single image.

    Args:
        image_path: path to the input image
        obb_model: loaded YOLO OBB model
        pose_model: loaded YOLO Pose model
        conf_threshold: OBB detection confidence threshold
        padding_pct: padding around OBB crop
        save_dir: if provided, save annotated image here

    Returns:
        list of dicts, one per detected tube:
            {image, center_x, center_y, bbox_x, bbox_y, bbox_w, bbox_h,
             bbox_rotation, angle_deg, confidence}
    """
    img = cv2.imread(image_path)
    if img is None:
        print(f"Error: Could not read {image_path}")
        return []

    img_name = os.path.basename(image_path)

    # --- Stage 1: OBB Detection ---
    obb_results = obb_model.predict(source=image_path, conf=conf_threshold, verbose=False)

    if not obb_results or len(obb_results) == 0:
        return []

    result = obb_results[0]
    predictions = []

    # Check if any OBB detections exist
    if result.obb is None or len(result.obb) == 0:
        return []

    obb_data = result.obb
    # obb_data.xyxyxyxy gives the 4 corner points as (N, 4, 2)
    # obb_data.conf gives confidence scores
    # obb_data.xywhr gives (cx, cy, w, h, rotation_rad)

    for i in range(len(obb_data)):
        conf = float(obb_data.conf[i])
        xywhr = obb_data.xywhr[i].cpu().numpy()  # [cx, cy, w, h, rotation_rad]

        obb_cx, obb_cy = float(xywhr[0]), float(xywhr[1])
        obb_w, obb_h = float(xywhr[2]), float(xywhr[3])
        obb_rot_rad = float(xywhr[4])
        obb_rot_deg = math.degrees(obb_rot_rad)

        # Build a row dict compatible with crop_tube()
        # bbox_x/bbox_y = top-left of the unrotated bbox
        bbox_x = obb_cx - obb_w / 2.0
        bbox_y = obb_cy - obb_h / 2.0
        row = {
            'bbox_x': bbox_x,
            'bbox_y': bbox_y,
            'bbox_w': obb_w,
            'bbox_h': obb_h,
            'bbox_rotation': obb_rot_deg,
        }

        crop_img, crop_meta = crop_tube(img, row, padding_pct)
        if crop_img is None:
            continue

        # --- Stage 2: Pose Estimation on crop ---
        pose_results = pose_model.predict(source=crop_img, verbose=False)

        if not pose_results or len(pose_results) == 0:
            continue

        pose_result = pose_results[0]

        # Extract keypoints
        if pose_result.keypoints is None or len(pose_result.keypoints) == 0:
            continue

        kpts = pose_result.keypoints.xy[0].cpu().numpy()  # shape (2, 2)

        if len(kpts) < 2:
            continue

        # Keypoints are in crop pixel coordinates
        kp0_crop_x, kp0_crop_y = float(kpts[0][0]), float(kpts[0][1])
        kp1_crop_x, kp1_crop_y = float(kpts[1][0]), float(kpts[1][1])

        # Transform back to full-image coordinates
        center_x = kp0_crop_x + crop_meta['crop_x0']
        center_y = kp0_crop_y + crop_meta['crop_y0']
        tab_x = kp1_crop_x + crop_meta['crop_x0']
        tab_y = kp1_crop_y + crop_meta['crop_y0']

        # Compute angle_deg from Center → Tab
        # Coordinate system: Y-down in image, but angle is CCW from positive X
        dx = tab_x - center_x
        dy = -(tab_y - center_y)  # negate Y for CCW convention
        angle_deg = math.degrees(math.atan2(dy, dx)) % 360

        predictions.append({
            'image': img_name,
            'center_x': round(center_x, 1),
            'center_y': round(center_y, 1),
            'bbox_x': round(bbox_x, 1),
            'bbox_y': round(bbox_y, 1),
            'bbox_w': round(obb_w, 1),
            'bbox_h': round(obb_h, 1),
            'bbox_rotation': round(obb_rot_deg, 1),
            'angle_deg': round(angle_deg, 1),
            'confidence': round(conf, 4),
        })

    # --- Annotated visualization ---
    if save_dir and predictions:
        vis_img = img.copy()
        for pred in predictions:
            cx_int = int(pred['center_x'])
            cy_int = int(pred['center_y'])

            # Draw OBB
            rect = ((pred['bbox_x'] + pred['bbox_w'] / 2, pred['bbox_y'] + pred['bbox_h'] / 2),
                    (pred['bbox_w'], pred['bbox_h']),
                    pred['bbox_rotation'])
            box = cv2.boxPoints(rect)
            box = np.int32(box)
            cv2.drawContours(vis_img, [box], 0, (0, 255, 255), 2)  # Yellow OBB

            # Draw center dot (Red)
            cv2.circle(vis_img, (cx_int, cy_int), 4, (0, 0, 255), -1)

            # Draw angle direction line (Green)
            R = max(pred['bbox_w'], pred['bbox_h']) / 2.0
            theta = math.radians(pred['angle_deg'])
            tab_x_vis = int(cx_int + R * math.cos(theta))
            tab_y_vis = int(cy_int - R * math.sin(theta))
            cv2.line(vis_img, (cx_int, cy_int), (tab_x_vis, tab_y_vis), (0, 255, 0), 2)

            # Draw tab dot (Blue)
            cv2.circle(vis_img, (tab_x_vis, tab_y_vis), 4, (255, 0, 0), -1)

            # Draw confidence text
            cv2.putText(vis_img, f"{pred['angle_deg']:.0f}deg",
                        (cx_int + 10, cy_int - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

        os.makedirs(save_dir, exist_ok=True)
        out_path = os.path.join(save_dir, f"pred_{img_name}")
        cv2.imwrite(out_path, vis_img)

    return predictions


def main():
    """Run inference on a single image (path from command line argument)."""
    if len(sys.argv) < 2:
        print("Usage: python infer.py <image_path>")
        print("Example: python infer.py dataset/test/images/example.png")
        return

    image_path = sys.argv[1]
    if not os.path.exists(image_path):
        print(f"Error: {image_path} not found.")
        return

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

    # --- Run inference ---
    save_dir = os.path.join(os.path.dirname(__file__), 'runs', 'pipeline')
    print(f"\nRunning two-stage inference on: {image_path}")

    predictions = infer_single_image(image_path, obb_model, pose_model, save_dir=save_dir)

    if not predictions:
        print("No tubes detected.")
        return

    # Print results
    print(f"\nDetected {len(predictions)} tube(s):")
    print("-" * 80)
    for p in predictions:
        print(f"  center=({p['center_x']}, {p['center_y']})  "
              f"angle={p['angle_deg']}°  conf={p['confidence']}")
    print("-" * 80)

    # Save predictions CSV
    df = pd.DataFrame(predictions)
    csv_path = os.path.join(save_dir, 'predictions.csv')
    df.to_csv(csv_path, index=False)
    print(f"Predictions saved to {csv_path}")
    print(f"Annotated image saved to {save_dir}")


if __name__ == "__main__":
    main()
