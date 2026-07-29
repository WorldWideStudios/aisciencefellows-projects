import pandas as pd
import numpy as np
import os
import shutil
import cv2

def main():
    np.random.seed(42)
    annotations_file = "annotations.csv"
    images_dir = "images"
    
    # Create directories
    train_dir = os.path.join("dataset", "train")
    test_dir = os.path.join("dataset", "test")
    
    # Clean previous splits if they exist to prevent mixing
    for directory in [train_dir, test_dir]:
        if os.path.exists(directory):
            shutil.rmtree(directory)
        os.makedirs(os.path.join(directory, "images"), exist_ok=True)
    
    # Read annotations
    try:
        df = pd.read_csv(annotations_file)
    except FileNotFoundError:
        print(f"Error: {annotations_file} not found.")
        return
        
    images = df['image'].unique()
    
    print("Extracting background colors for clustering...")
    avg_colors = []
    valid_images = []
    
    for img_name in images:
        img_path = os.path.join(images_dir, img_name)
        if not os.path.exists(img_path):
            print(f"Warning: {img_path} not found.")
            continue
        
        img = cv2.imread(img_path)
        if img is None:
            print(f"Warning: {img_path} could not be read.")
            continue
            
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        avg_color = img.mean(axis=(0, 1))
        avg_colors.append(avg_color)
        valid_images.append(img_name)
        
    avg_colors = np.float32(avg_colors)
    valid_images = np.array(valid_images)
    
    print("Clustering images into 4 background groups (Stratification)...")
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
    K = 4
    _, labels, _ = cv2.kmeans(avg_colors, K, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
    labels = labels.flatten()
    
    train_images = []
    test_images = []
    
    # Perform 80/20 split inside each cluster
    for cluster_id in range(K):
        cluster_imgs = valid_images[labels == cluster_id]
        np.random.shuffle(cluster_imgs)
        n = len(cluster_imgs)
        
        # Round ensures we don't systematically drop images across multiple clusters
        train_split_idx = round(n * 0.80)
        
        train_cluster = cluster_imgs[:train_split_idx]
        test_cluster = cluster_imgs[train_split_idx:]
        
        train_images.extend(train_cluster)
        test_images.extend(test_cluster)
        
        print(f"Cluster {cluster_id}: {n} total images -> {len(train_cluster)} Train, {len(test_cluster)} Test")
        
    # Create train and test DataFrames
    train_df = df[df['image'].isin(train_images)]
    test_df = df[df['image'].isin(test_images)]
    
    # Save annotations
    train_df.to_csv(os.path.join(train_dir, "annotations.csv"), index=False)
    test_df.to_csv(os.path.join(test_dir, "annotations.csv"), index=False)
    
    # Copy images function
    def copy_images(image_list, dest_dir):
        for img in image_list:
            src = os.path.join(images_dir, img)
            dst = os.path.join(dest_dir, "images", img)
            if os.path.exists(src):
                shutil.copy(src, dst)
                
    print("\nCopying images to their respective directories...")
    copy_images(train_images, train_dir)
    copy_images(test_images, test_dir)
            
    print("\nDataset stratified split complete!")
    print(f"Total valid images: {len(valid_images)}")
    print(f"Train set: {len(train_images)} images")
    print(f"Test set: {len(test_images)} images")

if __name__ == "__main__":
    main()
