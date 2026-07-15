# Niv Lab Resources (Princeton)
Source: https://nivlab.github.io/

## NivTurk — Online Experiment Platform
- **Repo**: github.com/nivlab/nivturk
- **Docs**: nivlab.github.io/nivturk
- **Stack**: Python/Flask backend + jsPsych frontend
- **What it does**: Lightweight platform for running behavioral experiments on MTurk/Prolific
- **Architecture**:
  - Flask serves sequential pages: consent → instructions → experiment → completion
  - Dual participant tracking: platform ID + browser cookie (prevents re-participation)
  - Anonymous alphanumeric subject IDs for deidentification
  - File-based storage: metadata dir, data dir, incomplete dir (no database)
  - Data saved at experiment completion or page close only

### Patterns relevant to ThinkHigher:
- **Multi-stage experiments** (`/docs/cookbook/multi-stage/`): Each stage = own route + HTML template + data dir. Stages advance via success callbacks. Resume from last incomplete stage on refresh. Validates our StageDefinition schema.
- **Message passing** (`/docs/cookbook/message-pass/`): `pass_message()` logs timestamped events to metadata files. Analogous to our TranscriptEntry.
- **Variable passing** (`/docs/cookbook/variable-passing/`): Data flows between stages via route params.
- **Longitudinal** (`/docs/cookbook/longitudinal/`): Cookie-based session continuity across visits.
- **Subject monitoring** (`/docs/cookbook/monitoring/`): Real-time participant tracking.
- **Online rejection** (`/docs/cookbook/online-rejection/`): Quality control mid-experiment.

## jsPsych Demos — Task Library
- **Repo**: github.com/nivlab/jspsych-demos
- **Docs**: nivlab.github.io/jspsych-demos

### Reinforcement Learning Tasks
- 2-arm bandit (canvas)
- 3-arm reversal learning (gamified fishing theme)
- Risk-sensitive learning v1 (apple harvest, canvas) & v2 (fishing, CSS, child-friendly)
- Modified risk sensitivity task
- Risky investment task (stock market framing)
- Pavlovian Go/No-Go (robot theme)
- Relative value learning (sci-fi theme, counterfactual learning)
- Horizons task (temporal discounting)
- Two-step task (model-based vs model-free, space theme)

### Decision-Making
- Prospect theory gambles (icon array visualization)

### Executive Function
- Raven's Progressive Matrices (9-item abbreviated, Forms A & B)
- MaRs-IB matrix reasoning (web-friendly)
- Spatial recall (forwards/backwards, 3 scoring methods)
- Digit symbol matching (WAIS-style processing speed)
- Vocabulary test (20 items, crystallized intelligence)

### Self-Report & QC
- Likert scale survey plugin (template-based, reusable)
- Demographics form (NIMH-compliant)
- Feedback form (difficulty, enjoyability, strategy)
- Consent forms (Niv Lab / Daw Lab)
- Audio test (attention check)
- Screen resolution check

### Design notes
- Tasks use canvas (compute-heavy) or CSS (accessible)
- Many gamified with themes (fishing, robots, space) for engagement
- Two-step and bandit tasks = natural future ThinkHigher scenarios

## OpenCogData — Behavioral Dataset Index
- **Redirects to**: nimh-dsst.github.io/OpenCogData/
- Curated public cognitive datasets (OSF, GitHub, Zenodo)
- Includes: multi-armed bandits, RL across development, perceptual decision-making, working memory
- Data formats: raw behavioral + processed + analysis scripts
- Relevant for benchmarking our assessment data against published norms

## NivStan — Cognitive Modeling in Stan
- **Repo**: github.com/nivlab/nivstan
- **Docs**: nivlab.github.io/nivstan
- Stan tutorials for fitting computational cognitive models:
  - **hBayesDM**: Hierarchical Bayesian analysis of decision-making models (R + Stan)
  - **Bayesian Q-Learning**: RL model implementation
  - **Individual Differences**: Parameter variation across participants
- Hierarchical approach: group-level + individual-level parameters simultaneously
- Once we persist RT + choice data (Track C), these models can be fitted to participant behavior

## NivLink — Eye-Tracking Preprocessing
- **Repo**: github.com/nivlab/NivLink
- **Docs**: nivlink.readthedocs.io
- Python tools for preprocessing eye-tracking data
- Lower priority for ThinkHigher unless we add webcam-based gaze tracking
