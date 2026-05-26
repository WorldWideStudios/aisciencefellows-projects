from ultralytics import YOLO
import matplotlib.pyplot as plt
import cv2

print("Loading Custom LabLens Model...")

# 1. Load your newly trained local model
model = YOLO("models/lablens_v1.pt")

# 2. Run inference on the challenging image
# Setting conf=0.25 filters out weak, uncertain guesses
image_path = "/home/mohamed-alwathiq/Downloads/AGAR_demo/AGAR_representative/higher-resolution/bright/" 
results = model(image_path, conf=0.25)

# 3. Parse and count the detected objects
boxes = results[0].boxes
class_ids = boxes.cls.cpu().numpy()  # Get the numerical IDs of what was found
names = model.names                  # Get the dictionary of class names (e.g., 0: 'colony')

# Create a dictionary to keep track of the counts
counts = {name: 0 for name in names.values()}
for cls_id in class_ids:
    class_name = names[int(cls_id)]
    counts[class_name] += 1

print("\n=== LABLENS SENSOR DATA ===")
for name, count in counts.items():
    print(f"{name.capitalize()}: {count}")
print("===========================\n")

# 4. Visualize the "Aha!" Moment
annotated_img = results[0].plot() # This automatically draws the boxes and labels!
annotated_img_rgb = cv2.cvtColor(annotated_img, cv2.COLOR_BGR2RGB)

plt.figure(figsize=(12, 12))
plt.imshow(annotated_img_rgb)
plt.axis("off")
plt.title(f"LabLens AI Output - Colonies Detected: {counts.get('colony', 0)}")
plt.show()