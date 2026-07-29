import os
import glob
import pandas as pd
import numpy as np
from ultralytics import YOLO

def find_best_model(cv_runs_dir):
    """
    Finds the best model across all folds by looking at the results.csv of each fold.
    """
    best_map50 = -1.0
    best_model_path = None
    best_fold = None
    
    # Iterate over all fold directories
    fold_dirs = glob.glob(os.path.join(cv_runs_dir, 'fold_*'))
    
    if not fold_dirs:
        print(f"No fold directories found in {cv_runs_dir}. Has training completed?")
        return None, None
        
    for fold_dir in fold_dirs:
        results_path = os.path.join(fold_dir, 'results.csv')
        weights_path = os.path.join(fold_dir, 'weights', 'best.pt')
        
        if not os.path.exists(results_path) or not os.path.exists(weights_path):
            continue
            
        # Read the results.csv
        try:
            df = pd.read_csv(results_path)
            # YOLO results.csv column names often have leading spaces.
            # We strip column names to be safe.
            df.columns = df.columns.str.strip()
            
            # The column name for mAP50 is usually 'metrics/mAP50(B)' or 'metrics/mAP50(O)' for OBB
            map_cols = [c for c in df.columns if 'mAP50' in c and '95' not in c]
            if not map_cols:
                continue
                
            val_map50 = df[map_cols[0]].max()
            
            if val_map50 > best_map50:
                best_map50 = val_map50
                best_model_path = weights_path
                best_fold = os.path.basename(fold_dir)
                
        except Exception as e:
            print(f"Error parsing results for {fold_dir}: {e}")
            
    return best_model_path, best_fold

def validate_best_model():
    # 1. Load the OBB model from weights/ directory
    weights_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'weights'))
    best_model_path = os.path.join(weights_dir, 'obb_best.pt')
    
    if not os.path.exists(best_model_path):
        print(f"Error: OBB weights not found at {best_model_path}")
        return
        
    print(f"Loading OBB model from: {best_model_path}")
    
    # 2. Load the best model
    model = YOLO(best_model_path)
    
    # 3. Path to data.yaml
    # We generated data.yaml at the root during data prep. 
    # It has train, val (mapped to test), and test splits.
    data_yaml_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data.yaml'))
    
    if not os.path.exists(data_yaml_path):
        print(f"data.yaml not found at {data_yaml_path}. Did you run prepare_yolo.py?")
        return
        
    print(f"\nEvaluating on the holdout test set...")
    
    # 4. Validate on test set
    metrics = model.val(data=data_yaml_path, split='test', plots=True, exist_ok=True, name="test_eval")
    
    # YOLO ultralytics metric structure check
    # Depending on YOLO version/task, it might be in metrics.obb or metrics.box
    metric_group = getattr(metrics, 'obb', getattr(metrics, 'box', metrics))
    
    # Extract metrics
    precision = metric_group.mp
    recall = metric_group.mr
    map50 = metric_group.map50
    
    # Calculate F1 Score
    f1_score = 2 * (precision * recall) / (precision + recall + 1e-16)
    
    print("\n" + "="*50)
    print("Holdout Test Set Results (15 Images)")
    print("="*50)
    print(f"Precision: {precision:.4f}")
    print(f"Recall:    {recall:.4f}")
    print(f"F1-Score:  {f1_score:.4f}")
    print(f"mAP@50:    {map50:.4f} (often reported as Accuracy for Object Detection)")
    print("="*50)
    print("A detailed validation report (including confusion matrix and predictions) has been saved in the 'runs/obb/test_eval' directory.")
    
    # 5. Output individual predictions with drawn bounding boxes
    test_images_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'dataset', 'test', 'images'))
    
    if os.path.exists(test_images_dir):
        print("\nGenerating individual predictions with drawn bounding boxes...")
        model.predict(source=test_images_dir, save=True, save_txt=True, project='runs/obb', name='test_predictions', exist_ok=True)
        print("Individual predicted images have been saved in 'runs/obb/test_predictions'.")
    else:
        print(f"\nWarning: Test images directory not found at {test_images_dir}. Cannot generate individual predictions.")

if __name__ == "__main__":
    validate_best_model()
