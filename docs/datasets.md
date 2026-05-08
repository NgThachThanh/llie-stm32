# Prepared low-light datasets

Datasets have been downloaded and arranged into a simple paired format for the training workspace.

## Downloaded archives
- `downloads/LOL-v1.zip`
- `downloads/LOL-v2.zip`

## Extracted originals
- `extracted/lol_v1/LOLv1/...`
- `extracted/lol_v2/LOLv2/...`

## Canonical paired folders for this project

### 1. LOL-v1
Path:
`/home/stonies/projects/llie-stm32/datasets/lol`

Structure:
```text
lol/
├─ train/
│  ├─ low/   # 486 files
│  └─ high/  # 486 files
└─ val/
   ├─ low/   # 15 files
   └─ high/  # 15 files
```

Source mapping:
- `LOLv1/Train/input` -> `train/low`
- `LOLv1/Train/target` -> `train/high`
- `LOLv1/Test/input` -> `val/low`
- `LOLv1/Test/target` -> `val/high`

### 2. LOL-v2 Real
Path:
`/home/stonies/projects/llie-stm32/datasets/lol_v2_real`

Structure:
```text
lol_v2_real/
├─ train/
│  ├─ low/   # 689 files
│  └─ high/  # 689 files
└─ val/
   ├─ low/   # 100 files
   └─ high/  # 100 files
```

Source mapping:
- `LOLv2/Real_captured/Train/Low` -> `train/low`
- `LOLv2/Real_captured/Train/Normal` -> `train/high`
- `LOLv2/Real_captured/Test/Low` -> `val/low`
- `LOLv2/Real_captured/Test/Normal` -> `val/high`

### 3. LOL-v2 Synthetic
Path:
`/home/stonies/projects/llie-stm32/datasets/lol_v2_synthetic`

Structure:
```text
lol_v2_synthetic/
├─ train/
│  ├─ low/   # 900 files
│  └─ high/  # 900 files
└─ val/
   ├─ low/   # 100 files
   └─ high/  # 100 files
```

Source mapping:
- `LOLv2/Synthetic/Train/Low` -> `train/low`
- `LOLv2/Synthetic/Train/Normal` -> `train/high`
- `LOLv2/Synthetic/Test/Low` -> `val/low`
- `LOLv2/Synthetic/Test/Normal` -> `val/high`

## Recommended starting point
- Debug pipeline first with: `lol`
- Then train/evaluate on: `lol_v2_real`
- Use `lol_v2_synthetic` as extra data later if needed
