# LabLens

LabLens is a local, privacy-first AI microbiology assistant that analyzes petri dish images and generates structured lab reports entirely on consumer hardware, no cloud APIs, no data leaving your machine.

The system combines traditional computer vision, a fine-tuned object detection model, and a local language model into a single cohesive pipeline.

---

## What It Does

Given a petri dish image, LabLens:

1. Counts bacterial colonies using OpenCV (Gaussian blur, Otsu thresholding, contour detection)
2. Detects contamination and plate defects using a custom-trained YOLOv11-Nano model
3. Generates a structured, factual lab notebook entry using a locally running Llama 3.2 (3B) model via Ollama
4. Logs every run to a local SQLite database for historical tracking and trend analysis

---

## Architecture

The pipeline is deliberately decoupled into three independent components:

```
Petri Dish Image
       |
       v
  [ OpenCV ]              — Colony counting via contour detection
       |
       v
  [ YOLOv11-Nano ]        — Contamination and defect localization
       |
       v
  [ Python Dictionary ]   — Unified data payload
       |
       v
  [ Llama 3.2 via Ollama ] — Lab report generation
       
       

```

This decoupled design runs efficiently on a consumer laptop (Intel i5, 8GB RAM) without requiring a GPU or internet connection at inference time.

---

## Stack

| Component | Tool | Purpose |
|---|---|---|
| Colony counting | OpenCV | Traditional CV blob detection |
| Contamination detection | YOLOv11-Nano | Custom-trained object detection |
| Report generation | Llama 3.2 3B via Ollama | Local language model inference |
| Data persistence | SQLite | Experiment history and logging |
| Prototyping environment | Jupyter Notebooks | End-to-end pipeline development |
| Model training | Kaggle (T4 GPU) | Cloud-accelerated YOLO training |

---

## Model Details

The YOLOv11-Nano model was trained on a curated subset of the AGAR dataset (Majchrowska et al., 2021) — a professionally annotated collection of 18,000 petri dish images across five microbial species.

The dataset was remapped from 7 species-level classes to 3 functional classes aligned with the LabLens use case:

- `colony` — standard bacterial or fungal growth
- `contamination` — unwanted biological contamination
- `defect` — physical plate artifacts that could affect counting accuracy

Training was performed for 25 epochs on a stratified, class-balanced subset of approximately 1,020 images using a T4 GPU on Kaggle. The resulting model weighs 5.5MB and runs on CPU at real-time speeds.

**Validation results (best.pt):**

| Class | mAP50 | Precision | Recall |
|---|---|---|---|
| colony | 48.5% | 42.6% | 62.0% |
| contamination | 37.7% | 76.2% | 33.6% |
| Overall | 28.7% | 39.4% | 31.9% |

---

## Hardware Requirements

- CPU: Intel i5 or equivalent (no GPU required for inference)
- RAM: 8GB minimum
- Disk: 4GB free space
- OS: Ubuntu 24 (recommended) or Windows

---

## Project Structure

```
lablens/
    models/
        best.pt              # Trained YOLOv11-Nano weights
    images/                  # Input petri dish images
    milestone1_opencv.ipynb  # OpenCV colony counting exploration
    lablens_pipeline.ipynb   # Full end-to-end pipeline (Block 4)
    lablens_env/             # Python virtual environment
```

---

## Setup

**1. Clone the repository**
```bash
git clone https://github.com/Moe-phantom/LabLens.git
cd LabLens
```

**2. Create and activate a virtual environment**
```bash
python3 -m venv lablens_env
source lablens_env/bin/activate
```

**3. Install dependencies**
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install opencv-python ultralytics jupyter ollama
```

**4. Install Ollama and pull the language model**
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2
```

**5. Launch Jupyter**
```bash
jupyter notebook
```

---

## Dataset

This project uses a subset of the AGAR dataset:

> Majchrowska, S., Pawlowski, J., Gula, G., et al. (2021). AGAR: A Microbial Colony Dataset for Deep Learning Detection. Research Square.

Dataset available at: https://agar.neurosys.com

---

## Development Roadmap

**Completed**
- OpenCV colony counting pipeline
- YOLOv11-Nano contamination detection model
- Llama 3.2 local lab report generation
- Stratified dataset curation and class balancing

**In Progress**
- Full pipeline integration (Block 4)
- SQLite experiment history logging
- Cross-experiment trend analysis via LLM

**Planned**
- Autonomous folder-watching monitoring agent
- Anomaly alert system for contamination spikes
- Multi-image batch processing and consolidated reports
- Improved contamination recall through additional training data

---

## Fellowship Context

LabLens is being developed as part of the Worldwide Studios Fellowship. The project demonstrates that production-grade AI pipelines can be built and deployed entirely on consumer hardware through careful architectural decisions — choosing lightweight models, CPU-optimized inference, and local LLM runtimes over cloud-dependent monolithic solutions.
