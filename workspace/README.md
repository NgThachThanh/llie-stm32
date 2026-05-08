# STM32H750 LLIE Training Workspace

Workspace train/deploy cho dự án low-light enhancement trên STM32H750.

## 1. Environment
```bash
source /home/stonies/venvs/llie-train/bin/activate
```

## 2. Current canonical run
- Config: `configs/image_first.yaml`
- Winner: `loss.param = 0.02`
- Canonical checkpoint: `outputs/checkpoints_image_first/best.pt`
- Canonical previews: `outputs/previews_image_first/`
- Canonical export dir: `outputs/export_image_first_full/`
- Sanity checker: `scripts/test_export_sanity.py`

Current verified export sanity:
- TFLite input shape: `[1, 96, 96, 1]`
- TFLite output shape: `[1, 3]`
- `max_abs_diff = 1.9073486328125e-06`
- `mean_abs_diff = 1.112619997911679e-06`

Meaning:
- current TFLite artifact matches PyTorch at float-rounding level
- current export is trustworthy for further integration work
- but this is still a **float export**, not yet an INT8/QAT deploy-ready MCU path

## 3. Cấu trúc chính
- `configs/` — config yaml
- `src/data/` — dataloader ảnh và video
- `src/models/` — Student-G, StudentV1
- `src/render/` — decode + render luma
- `src/losses/` — hybrid loss
- `scripts/` — train, teacher targets, offline fitting, preview/eval, export
- `outputs/` — checkpoints, previews, comparisons, export artifacts

## 4. Dataset root
```text
/home/stonies/projects/llie-stm32/datasets
```

Ví dụ dataset paired:
```text
datasets/lol/
├─ train/
│  ├─ low/
│  └─ high/
└─ val/
   ├─ low/
   └─ high/
```

## 5. Teacher repo
```text
/home/stonies/projects/llie-stm32/repos/Zero-DCE
```

## 6. Preflight checklist
Trước khi chạy thật:
- activate venv `llie-train`
- xác nhận CUDA usable nếu định chạy teacher path
- xác nhận teacher weights tồn tại trong `repos/Zero-DCE/snapshots/Epoch99.pth`
- xác nhận dataset folder đã có ảnh thật
- nên chạy thử trên **tiny subset** trước khi chạy full LOL-v1 khi rebuild pipeline từ đầu

## 7. Canonical flow hiện tại

### Bước A — teacher target generation nếu cần rebuild
```bash
python scripts/prepare_teacher_targets.py \
  --teacher-repo /home/stonies/projects/llie-stm32/repos/Zero-DCE \
  --input-dir /home/stonies/projects/llie-stm32/datasets/lol/train/low \
  --output-dir /home/stonies/projects/llie-stm32/datasets/lol/train/teacher_y \
  --limit 10 \
  --fail-on-missing
```

### Bước B — fit teacher outputs thành pseudo-controls
```bash
python scripts/fit_teacher_controls.py \
  --low-dir /home/stonies/projects/llie-stm32/datasets/lol/train/low \
  --teacher-dir /home/stonies/projects/llie-stm32/datasets/lol/train/teacher_y \
  --output-dir /home/stonies/projects/llie-stm32/datasets/lol/train/pseudo_ctrl_v2 \
  --map-size 8
# canonical pseudo-control directory currently in use: datasets/lol/train/pseudo_ctrl_v2
```

### Bước C — train canonical image-first model
```bash
python scripts/train_float.py \
  --config configs/image_first.yaml \
  --low-dir /home/stonies/projects/llie-stm32/datasets/lol/train/low \
  --high-dir /home/stonies/projects/llie-stm32/datasets/lol/train/high \
  --teacher-dir /home/stonies/projects/llie-stm32/datasets/lol/train/teacher_y \
  --param-dir /home/stonies/projects/llie-stm32/datasets/lol/train/pseudo_ctrl_v2 \
  --val-low-dir /home/stonies/projects/llie-stm32/datasets/lol/val/low \
  --val-high-dir /home/stonies/projects/llie-stm32/datasets/lol/val/high \
  --val-teacher-dir /home/stonies/projects/llie-stm32/datasets/lol/val/teacher_y \
  --outdir /home/stonies/projects/llie-stm32/workspace/outputs/checkpoints_image_first
```

### Bước D — preview canonical checkpoint
```bash
python scripts/eval_preview.py \
  --config configs/image_first.yaml \
  --checkpoint /home/stonies/projects/llie-stm32/workspace/outputs/checkpoints_image_first/best.pt \
  --low-dir /home/stonies/projects/llie-stm32/datasets/lol/val/low \
  --high-dir /home/stonies/projects/llie-stm32/datasets/lol/val/high \
  --teacher-dir /home/stonies/projects/llie-stm32/datasets/lol/val/teacher_y \
  --output-dir /home/stonies/projects/llie-stm32/workspace/outputs/previews_image_first
```

### Bước E — export canonical checkpoint
```bash
python scripts/export_tflite.py \
  --config configs/image_first.yaml \
  --checkpoint /home/stonies/projects/llie-stm32/workspace/outputs/checkpoints_image_first/best.pt \
  --output-dir /home/stonies/projects/llie-stm32/workspace/outputs/export_image_first_full
```

### Bước F — verify PyTorch vs TFLite
```bash
python scripts/test_export_sanity.py \
  --config /home/stonies/projects/llie-stm32/workspace/configs/image_first.yaml \
  --checkpoint /home/stonies/projects/llie-stm32/workspace/outputs/checkpoints_image_first/best.pt \
  --tflite /home/stonies/projects/llie-stm32/workspace/outputs/export_image_first_full/model.tflite \
  --image /home/stonies/projects/llie-stm32/datasets/lol/val/low/1.png
```

## 8. Model milestones
- `student_global_only` = Student-G
- `student_v1` + `map_size: 8` = Student-MiniMap 8x8
- `student_v1` + `map_size: 12` = Student-MiniMap 12x12
- `student_v1` + `map_size: 24` = StudentV1 target architecture

## 9. Lưu ý thực tế
- GTX 1050 Ti 4GB phù hợp để train batch nhỏ.
- Nên bắt đầu với LOL-v1 trước để debug pipeline.
- Teacher targets nên generate trước rồi mới train student.
- `eval_preview.py` là script bắt buộc nên dùng để nhìn output thật, không chỉ nhìn loss.
- `export_tflite.py` **đã dùng được** và đã tạo TorchScript/ONNX/TFLite/C-header artifacts cho canonical winner.
- `train_float.py` hiện đã được bổ sung logging có cấu trúc (`train_log.csv`, `metrics.yaml`) và validation loss optional cho các run sau.
- Canonical run hiện tại vẫn không có raw per-epoch historical CSV vì nó được tạo trước khi thêm logging.
- Workspace này hỗ trợ training path; **demo-critical path của project tổng vẫn là firmware baseline + integration trên board**.
