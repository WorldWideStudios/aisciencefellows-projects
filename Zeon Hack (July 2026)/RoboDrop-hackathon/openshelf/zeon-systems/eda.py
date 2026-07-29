import os
import cv2
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import scipy.stats as stats
from pathlib import Path
import math

def perform_eda(csv_path='annotations.csv', images_dir='images', output_dir='eda_outputs'):
    os.makedirs(output_dir, exist_ok=True)
    df = pd.read_csv(csv_path)
    
    print(f"Total annotations: {len(df)}")
    print(f"Total unique images: {df['image'].nunique()}")

    # 1. Distribution of tubes per image
    tubes_per_image = df.groupby('image').size()
    plt.figure(figsize=(8, 5))
    plt.hist(tubes_per_image, bins=range(0, 10), align='left', rwidth=0.8, color='skyblue', edgecolor='black')
    plt.title('Distribution of Tubes per Image')
    plt.xlabel('Number of Tubes')
    plt.ylabel('Frequency (Images)')
    plt.xticks(range(10))
    plt.grid(axis='y', alpha=0.75)
    plt.savefig(os.path.join(output_dir, 'tubes_per_image.png'))
    plt.close()

    # 2. Size Distribution (Bounding Box Width and Height)
    plt.figure(figsize=(10, 5))
    plt.subplot(1, 2, 1)
    plt.hist(df['bbox_w'], bins=20, color='lightgreen', edgecolor='black')
    plt.title('Bounding Box Width Distribution')
    plt.xlabel('Width (pixels)')
    plt.ylabel('Frequency')

    plt.subplot(1, 2, 2)
    plt.hist(df['bbox_h'], bins=20, color='salmon', edgecolor='black')
    plt.title('Bounding Box Height Distribution')
    plt.xlabel('Height (pixels)')
    plt.ylabel('Frequency')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'bbox_size_distribution.png'))
    plt.close()

    # 3. Angle Distribution & Normality Test
    angles = df['angle_deg'].values
    
    # Polar plot for angles
    plt.figure(figsize=(6, 6))
    ax = plt.subplot(111, polar=True)
    # Convert angles to radians for polar plot
    theta = np.radians(angles)
    bins = np.linspace(0.0, 2 * np.pi, 36) # 10-degree bins
    hist, _ = np.histogram(theta, bins=bins)
    width = 2 * np.pi / len(hist)
    bars = ax.bar(bins[:-1], hist, width=width, bottom=0.0, color='purple', alpha=0.6, edgecolor='black')
    ax.set_title('Distribution of Angles [0, 360)', va='bottom')
    plt.savefig(os.path.join(output_dir, 'angle_polar_distribution.png'))
    plt.close()

    # Normality test for angles
    # Note: Angles are circular, but we can check if they cluster normally around a specific mean
    stat, p_value = stats.shapiro(angles)
    print("\n--- Angle Normality Test (Shapiro-Wilk) ---")
    print(f"Test Statistic: {stat:.4f}, P-value: {p_value:.4e}")
    if p_value > 0.05:
        print("Result: Angles appear to be Normally Distributed (fail to reject H0).")
    else:
        print("Result: Angles are NOT Normally Distributed (reject H0).")
        
    # Test for Uniformity (Rayleigh test for circular uniformity)
    # A low p-value means the data is NOT uniform (it has a preferred direction)
    rayleigh_stat = np.sqrt(np.mean(np.cos(theta))**2 + np.mean(np.sin(theta))**2)
    n = len(angles)
    rayleigh_p = np.exp(np.sqrt(1 + 4*n + 4*(n**2 - rayleigh_stat**2)) - (1 + 2*n)) # Approx p-value
    print("\n--- Angle Uniformity Test (Rayleigh measure) ---")
    print(f"Rayleigh R-bar (0 = uniform, 1 = concentrated): {rayleigh_stat:.4f}")

    # 4. Background Color Analysis
    # We will compute the average RGB color of each image to see background clusters
    print("\n--- Analyzing Background Colors ---")
    avg_colors = []
    
    # Only sample a subset or just process all if it's small (70 images is fast)
    image_files = df['image'].unique()
    for img_name in image_files:
        img_path = os.path.join(images_dir, img_name)
        if not os.path.exists(img_path):
            continue
        img = cv2.imread(img_path)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Simple heuristic: average color of the whole image represents background mostly 
        # since tubes are small
        avg_color = img.mean(axis=(0, 1))
        avg_colors.append(avg_color)
        
    avg_colors = np.array(avg_colors)
    if len(avg_colors) > 0:
        plt.figure(figsize=(8, 6))
        # Plotting R vs B with G as color intensity to visualize clusters
        plt.scatter(avg_colors[:, 0], avg_colors[:, 2], c=avg_colors[:, 1]/255.0, cmap='viridis', edgecolors='k', s=100)
        plt.title('Image Average Color (Red vs Blue)\nPoints colored by Green channel intensity')
        plt.xlabel('Average Red Channel')
        plt.ylabel('Average Blue Channel')
        plt.grid(True)
        plt.savefig(os.path.join(output_dir, 'background_color_clusters.png'))
        plt.close()

    # 5. Data Integrity Check (Visualization)
    print("\n--- Generating Data Integrity Visualizations ---")
    np.random.seed(42)
    sample_images = np.random.choice(image_files, min(5, len(image_files)), replace=False)
    
    for img_name in sample_images:
        img_path = os.path.join(images_dir, img_name)
        if not os.path.exists(img_path):
            continue
            
        img = cv2.imread(img_path)
        img_annos = df[df['image'] == img_name]
        
        for _, row in img_annos.iterrows():
            cx, cy = int(row['center_x']), int(row['center_y'])
            angle_deg = row['angle_deg']
            
            # Dynamic Radius
            r = max(row['bbox_w'], row['bbox_h']) / 2.0
            
            # Tab coordinates (Keypoint 2)
            tab_x = int(cx + r * math.cos(math.radians(angle_deg)))
            tab_y = int(cy - r * math.sin(math.radians(angle_deg))) # - because Y is inverted
            
            # Draw Center
            cv2.circle(img, (cx, cy), 4, (0, 0, 255), -1) # Red center
            
            # Draw Line from Center to Tab
            cv2.line(img, (cx, cy), (tab_x, tab_y), (0, 255, 0), 2) # Green line
            
            # Draw Tab Point
            cv2.circle(img, (tab_x, tab_y), 4, (255, 0, 0), -1) # Blue tab
            
            # Optional: Draw the Oriented Bounding Box
            # For simplicity in EDA, drawing the predicted AABB corners from OBB
            rect = ((row['bbox_x'] + row['bbox_w']/2, row['bbox_y'] + row['bbox_h']/2), 
                    (row['bbox_w'], row['bbox_h']), 
                    row['bbox_rotation'])
            box = cv2.boxPoints(rect)
            box = np.int32(box)
            cv2.drawContours(img, [box], 0, (0, 255, 255), 2) # Yellow OBB

        out_path = os.path.join(output_dir, f'viz_{img_name}')
        cv2.imwrite(out_path, img)

    print(f"\nEDA Complete! All plots and visualizations saved to: '{os.path.abspath(output_dir)}'")

if __name__ == "__main__":
    perform_eda()
