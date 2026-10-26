# Automated sieving robot: teammate workflow, deck and demo video

Contributed by the filtration-robot teammates (see `filtration-robot/`, PR #24). Added as received on 2026-10-25.

| File | What | Status |
|---|---|---|
| `sieving_demo.mp4` | 63 s animated simulation: observe, plan, preflight, stack, agitate/verify loop, collect | **Simulation, not hardware footage.** Purity 80% → 96% (target 95%) is illustrative, not measured |
| `render_demo.py` | Renders the video (numpy, opencv-python, pillow, ffmpeg): `python3 render_demo.py render` | Reproducible |
| `SIEVING_DEMO.md` | The teammates' original demo README (renamed so it does not replace `docs/demo/README.md`) | |
| `automated_sieving_robot_deck.pptx` | 13-slide design-intent and pitch deck | **Draft**: slides 5–8 and 13 still carry placeholders; slides 3 and 10 give an 8-step and a 6-step workflow |

The tray IDs in the video (PERF-5, GRID-4, HEX-2, SCREEN-1, pan) are the kit sieves in `print/filters/passage/`.
The shelf dimensions (130 × 110 × 304 mm) come from a `shelf.STL` that is not in this repo, so they are unhashed: a BREAK until that file is added.

## sha256
    feab5ba13ba572bb8a872eac495997162da286646dea80fe52b6ae39ce56455a  sieving_demo.mp4
    a6bf36424bd7b4062363c1451ddacee43a3d5dff2e0a0c7dfb1a9e944145247c  render_demo.py
    728a089130a08541af03eba84904cb9599526f27be1c0af7d1bfb0f34481bbdf  SIEVING_DEMO.md
    894f3571f598b2f1f57669bf81a339bb42d503ba2be8218d0c167f5fdba1c6f7  automated_sieving_robot_deck.pptx

## Live demo
Team folder (Google Drive, shared by Byron 2026-10-25): https://drive.google.com/drive/folders/11-WYJ-ADuBkXb53xUPbTeefuBf64radz
Not reviewed or hashed here: its contents are outside the repo, so any claim resting on them is a BREAK until the files are added.
