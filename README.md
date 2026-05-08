# llie-stm32

Dự án tăng cường ảnh thiếu sáng cho `STM32H750VBT6`.

Pipeline mục tiêu:

```text
camera -> tăng cường ảnh nhẹ -> LCD
```

Ý tưởng chính: không đưa model image-to-image nặng lên MCU. Model `Student-G` chỉ dự đoán các tham số điều khiển toàn cục, còn firmware áp dụng gain/gamma nhanh trên ảnh.

## Có gì trong repo

- Code train/export: `workspace/`
- Plan kỹ thuật gọn: `docs/PLAN.md`
- Report gọn: `reports/REPORT.md`
- Dataset qua Git LFS: `datasets/`
- Firmware nền để test board: `firmware/08-DCMI2LCD/`
- Output baseline đã chốt:
  - `workspace/outputs/checkpoints_image_first/`
  - `workspace/outputs/previews_image_first/`
  - `workspace/outputs/export_image_first_full/`

Không track:

- `.venv/`
- `repos/`
- `STATUS.md`
- `TODO.md`

`STATUS.md` và `TODO.md` chỉ để local.

## Clone và chuẩn bị

```bash
git clone git@github.com:NgThachThanh/llie-stm32.git
cd llie-stm32
git lfs pull

python3 -m venv .venv
source .venv/bin/activate
pip install torch torchvision numpy scipy pyyaml opencv-python-headless

python -m compileall workspace/scripts workspace/src
```

## Cấu trúc

```text
docs/        plan kỹ thuật
reports/     báo cáo dự án
firmware/    firmware STM32H750 để test board
datasets/    LOL / LOL-v2 qua Git LFS
papers/      paper tham chiếu
workspace/   code train, preview, export
repos/       repo tham chiếu local, không track
```

## Dataset

Dataset chính:

```text
datasets/lol/
  train/low/
  train/high/
  val/low/
  val/high/
```

Dataset khác có kèm:

```text
datasets/lol_v2_real/
datasets/lol_v2_synthetic/
```

Teacher target và pseudo-control nằm ở:

```text
datasets/lol/train/teacher_y/
datasets/lol/train/pseudo_ctrl_v2/
```

## Baseline hiện tại

- Model: `Student-G`
- Config: `workspace/configs/image_first.yaml`
- Checkpoint: `workspace/outputs/checkpoints_image_first/best.pt`
- Export: `workspace/outputs/export_image_first_full/`
- Preview: `workspace/outputs/previews_image_first/`

## Train / preview / export

Chạy từ `workspace/`.

Train:

```bash
python scripts/train_float.py \
  --config configs/image_first.yaml \
  --low-dir ../datasets/lol/train/low \
  --high-dir ../datasets/lol/train/high \
  --teacher-dir ../datasets/lol/train/teacher_y \
  --param-dir ../datasets/lol/train/pseudo_ctrl_v2 \
  --val-low-dir ../datasets/lol/val/low \
  --val-high-dir ../datasets/lol/val/high \
  --val-teacher-dir ../datasets/lol/val/teacher_y \
  --outdir outputs/checkpoints_image_first
```

Preview:

```bash
python scripts/eval_preview.py \
  --config configs/image_first.yaml \
  --checkpoint outputs/checkpoints_image_first/best.pt \
  --low-dir ../datasets/lol/val/low \
  --high-dir ../datasets/lol/val/high \
  --teacher-dir ../datasets/lol/val/teacher_y \
  --output-dir outputs/previews_image_first
```

Export:

```bash
python scripts/export_tflite.py \
  --config configs/image_first.yaml \
  --checkpoint outputs/checkpoints_image_first/best.pt \
  --output-dir outputs/export_image_first_full
```

## Việc tiếp theo trên board

1. Flash và xác nhận raw `camera -> LCD`.
2. Thêm processing hook dạng bypass.
3. Chốt buffer ownership và D-cache policy.
4. Thêm baseline không AI: gain/gamma LUT.
5. Đo FPS/latency.
6. Chỉ tích hợp `Student-G` sau khi baseline ổn.
