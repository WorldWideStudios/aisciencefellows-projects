# cryovision 🧊📦

Ever spent 20 minutes digging through a freezer box looking for one tube? Same. CryoVision uses OpenCV and Claude's vision API to read your 10×10 cryobox from a single photo and exports the info so you can have it on hand. No more guessing which box has "Primer 132689."

Point it at a photo of your box and it returns a JSON map of every grid position (A1–J10) with whatever label text, cap color, or description it can read. Save that map for your own reference.

## Requirements

- Python 3.9+
- An [Anthropic API key](https://console.anthropic.com/)

## Setup

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY="sk-ant-..."
```

## Usage

```bash
# Accurate mode: grid detection + individual cell crops + thinking (default)
python cryovision.py --image box.jpg

# Fast mode: row strips, no thinking — quicker and cheaper
python cryovision.py --image box.jpg --fast

# Save as JSON
python cryovision.py --image box.jpg --output results.json

# Save as CSV (opens in Excel / Google Sheets)
python cryovision.py --image box.jpg --output results.csv

# Debug: save a copy of the image with the detected grid overlaid
python cryovision.py --image box.jpg --debug
```

Supported image formats: JPEG, PNG, GIF, WebP.

## Output

**JSON** — a map of all 100 positions. `null` means the slot is empty.

```json
{
  "A1": "SampleID-001",
  "A2": "red cap",
  "A3": null,
  ...
  "J10": "GAPDH-F"
}
```

**CSV** — four columns: `position`, `row`, `column`, `label`. Easy to open in Excel or Google Sheets and filter/sort by row or label.

```
position,row,column,label
A1,A,1,SampleID-001
A2,A,2,red cap
A3,A,3,
...
J10,J,10,GAPDH-F
```

**Grid view** — an aligned ASCII table with a filled/empty summary:

```
      1         2         3      ...    10
--------------------------------------------------
A  SampleID-001  red cap   ·····  ...
B  ·····         ·····     ·····  ...
...
J  ·····         ·····     ·····  GAPDH-F

Filled: 87/100   Empty/unread: 13/100
```

## How it works

1. **OpenCV preprocessing** — perspective correction (detects the box border and flattens tilt), CLAHE contrast enhancement, and sharpening to make labels more legible
2. **RF-DETR tube detection** — a Roboflow-trained RF-DETR Object Detection model locates tube caps and returns exact center coordinates and radii; falls back to HoughCircles if no Roboflow API key is set
3. **Circle-to-grid assignment** — detected circle centres are clustered by x and y coordinate to assign each tube a row (A–J) and column (1–10) label; no boundary lines are computed
4. **Circle-centered crops** — each occupied cell is cropped as a square centered directly on the detected tube cap center, sized to the detected radius; crops are guaranteed to be centered on the actual cap regardless of grid geometry
5. **Row compositing** — crops for each occupied row are tiled into a single labeled image with column numbers above each crop; empty rows are skipped entirely
6. **Claude vision** — each row composite is sent to `claude-opus-4-6` with thinking mode enabled; Claude sees only confirmed-occupied positions and reasons through each label
7. **Graceful fallback** — if a row can't be parsed, it's filled with `null` rather than crashing

The key design decision: rather than computing 10×10 grid boundary lines and cropping rectangular cells from those (which compounds any alignment error), the pipeline crops directly from the detected tube positions. The detector already knows exactly where each cap is — the grid is only used for labeling, not for cropping.

Use `--debug` to save a copy of the preprocessed image with each detected tube circled in cyan and labeled with its assigned grid position (e.g. A3, G7). This makes it easy to verify that detections are landing on the right caps and being assigned to the correct row/column.

### RF-DETR setup (optional but recommended)

RF-DETR gives significantly better tube detection than HoughCircles, especially for clear caps and mixed-color boxes. To enable it:

1. Create a free account at [Roboflow](https://roboflow.com/) and train a model on your own freezer box images (label the tube caps as a single `tube` class)
2. Export the model and note the model ID (e.g. `myworkspace/mymodel/1`)
3. Set environment variables:

```bash
export ROBOFLOW_API_KEY="your-api-key"
export ROBOFLOW_MODEL_ID="myworkspace/mymodel/1"
```

The tool will automatically use RF-DETR when the key is present and fall back to HoughCircles otherwise.

## Tips for best results

- Shoot straight-on (top-down) — perspective correction helps with mild tilt but can't fix extreme angles
- Use even lighting — shadows across caps are the main cause of misreads
- Higher resolution is better — more pixels per cap means more readable text
- For handwritten gene names on caps: good lighting + a close shot beats any amount of prompting

---

## Build log

### Background

Built for a molecular biology lab that stores DNA oligos and PCR primers in 10×10 cryoboxes. The problem: keeping track of which tube is where when caps are labeled by hand (gene names, primer IDs, etc.) and the box layout changes over time.

Initial approach: use Claude's vision API as a quick wrapper — no training data needed, works out of the box.

### v7 — RF-DETR integration via Roboflow

HoughCircles works well for boxes with uniform, high-contrast caps but struggles with clear caps, mixed cap colors, and partial occlusion. The lab's boxes often have green sticker caps, clear caps, and white caps in the same box, which caused frequent misses.

The fix: train a dedicated object detection model to find tube caps directly.

**Model training on Roboflow:**
- Created a Roboflow project and labeled freezer box photos with bounding boxes around each tube cap (single `tube` class)
- Trained using RF-DETR Object Detection (Small) — a transformer-based detector that handles varying cap appearances better than classical CV
- Starting dataset: ~4 images; enough to learn the basic cap shape but not yet robust to all lighting and color variations

**Detection pipeline changes:**
- `detect_tubes_rfdetr()` — calls the trained model via the Roboflow `inference` SDK at confidence=0.15; converts bounding box predictions to the same (cx, cy, r) format used by HoughCircles so the rest of the pipeline is unchanged
- `detect_grid()` now runs both RF-DETR and HoughCircles on every image; uses RF-DETR for grid geometry when it finds ≥40 tubes (more precise, no false positives), falls back to HoughCircles for grid geometry when RF-DETR is sparse — but always uses RF-DETR's detections for the presence map when available
- Confidence threshold tuned to 0.15 (down from 0.3) to maximize recall on an undertrained model; false positives are less harmful than missed tubes at this stage
- `ROBOFLOW_API_KEY` / `ROBOFLOW_MODEL_ID` env vars control the integration; the tool degrades gracefully to HoughCircles when they're not set

**Adaptive clustering with percentile-bin fallback:**
- `find_clusters_adaptive()` replaces the fixed `gap_ratio=3.0` used previously; it sweeps gap ratios from 7.0 down to 2.0 and picks the one that produces the closest to 10 clusters
- When no gap ratio achieves exactly 10 (e.g. perspective distortion makes some columns appear as 12 clusters), it falls back to percentile binning: sorts all detected x- or y-coordinates, splits into 10 equal-count bins, and takes the median of each bin — guaranteeing exactly 10 grid lines regardless of distribution

**Presence map:**
- After fitting the grid, each detected tube centre is mapped to its cell (i, j); cells with no detection are pre-emptively marked `null` at the CV level and skipped entirely when building row composites for Claude
- This eliminated the main source of hallucinated labels ("white cap", "green cap") on empty cardboard slots — Claude never sees those cells

**Circle-centered crops (the key accuracy fix):**
- Previous versions computed 11 horizontal and 11 vertical boundary lines, then cropped rectangular cells from those boundaries. Any error in boundary placement compounds: a line 10px off means every cell in that row is slightly wrong, and the tube cap might be cut off or the crop might include part of the adjacent cap.
- New approach: skip boundaries entirely. RF-DETR already returns the exact center (cx, cy) and size (r) of each tube cap. The crop is simply a square centered on (cx, cy) with side length proportional to r. No boundary lines are computed or needed.
- Grid position assignment (A1, B3, etc.) still uses clustering on the circle centers, but this is used only to label the crops — not to determine where to cut. The crops are always perfectly centered regardless of how well the grid clustering works.
- `assign_circles_to_grid()` handles the label assignment; `crop_circle_composite()` builds row composites from circle-centered crops; the debug overlay now shows each detected tube labeled with its assigned position rather than showing grid boundary lines.

### v6 — HoughCircles tuning: one circle per tube

The debug overlay showed cyan circles stacking on top of each other — two or three rings detected per tube instead of one. The cause: every cryotube cap has at least two visually distinct circular features: the raised outer screw rim and the flat inner surface. With the original parameters, HoughCircles was finding both rings on every tube.

Three parameter changes fixed it:

- **`minDist` raised from `short/14` → `short/10`** — this is the minimum pixel distance allowed between any two detected circles. Raising it to roughly one full tube-width means the algorithm physically cannot place a second circle on the same tube it already found.
- **`param2` raised from 30 → 50** — this is the accumulator threshold: how much evidence OpenCV requires before it commits to a circle. Higher = stricter = fewer false positives from cap ridges and reflections.
- **`param1` raised from 50 → 80** — the upper Canny edge threshold used internally. Higher = only the sharpest edges (cap rims) count toward circle evidence; softer gradients (label text, shadows) are ignored.

On top of that, the grid-fitting logic was upgraded from `np.linspace(min, max, 10)` to percentile-bin clustering: the detected circle centres are sorted and bucketed into 10 equal-percentile bins, and the median of each bin becomes the column or row centre. This means one outlier circle near the box edge can't drag the entire grid off — it just lands in a bin with a few other outliers and gets median'd away.

### v5 — circle-based grid detection + individual cell crops
- **Circle-based grid detection** — OpenCV detects tube caps as circles (HoughCircles) and fits the 10×10 grid to where the tubes actually are, rather than assuming equal spacing; falls back to equal division if too few circles are found
- **Individual cell crops** — each of the 100 tube positions is cropped individually and composited into a labelled row image before being sent to Claude; Claude now sees one tube at a time rather than a strip of 10
- **`--debug` flag** — saves the preprocessed image with green grid lines and cyan circles overlaid so you can verify detection before spending API credits
- **`--fast` mode** — row strips without thinking, for quicker cheaper runs

### v4 — CSV export
- `--output results.csv` exports a spreadsheet-friendly CSV with columns `position`, `row`, `column`, `label`
- `--output results.json` still works — format is auto-detected from the file extension

### v3 — OpenCV preprocessing + row-by-row analysis
*Motivation: shared with the lab group; feedback was that handwritten cap labels weren't parsing accurately. Group recommended pivoting to traditional CV (OpenCV, YOLO, SAM, Roboflow).*

- **OpenCV pipeline** added before Claude: perspective warp, CLAHE contrast enhancement, unsharp mask sharpening
- **Row-by-row splitting** replaces quadrants — Claude now sees a 1×10 strip per call (10 calls) instead of a 5×5 quadrant (4 calls), giving ~2.5× more pixels per tube
- **`--fast` flag** to fall back to quadrant mode when speed/cost matters

### v2 — improved accuracy
- **Quadrant splitting** — image divided into 4 sections before sending to Claude
- **Thinking mode** — Claude reasons through ambiguous labels before committing (`thinking: adaptive`)
- **Better prompting** — position-by-position instructions, cap color as fallback
- **Summary line** — filled vs empty count at the bottom of the grid

### v1 — initial release
- Single-image analysis via Claude vision API
- CLI with `--image` and `--output` flags
- JSON output + ASCII grid view

---

## Roadmap

The group recommended moving toward traditional computer vision for better accuracy on handwritten labels. Planned next steps:

- [x] **Individual tube crops** — detect tube caps as circles and crop each of the 100 cells individually before sending to Claude
- [x] **Circle-based grid detection** — fit the grid to detected tube centres rather than assuming equal spacing
- [x] **RF-DETR tube detection** — trained a Roboflow RF-DETR model to locate tube caps regardless of cap color or type; integrated with graceful HoughCircles fallback
- [x] **Roboflow training pipeline** — labeled freezer box images and trained via Roboflow; model handles green sticker caps, clear caps, and white caps
- [x] **Presence map** — CV-level null filter prevents Claude from hallucinating labels on empty cells
- [ ] **Expand training dataset** — currently ~4 images; need 50-100 for robust generalization to new boxes, lighting conditions, and cap types
- [ ] **Replace Claude with local OCR** — once tube positions are reliably detected, run Tesseract or a fine-tuned text recognition model on each crop for offline, zero-cost operation
