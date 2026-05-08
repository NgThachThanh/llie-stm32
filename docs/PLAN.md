# Kế Hoạch Dự Án

## Mục tiêu

Xây dựng pipeline tăng cường ảnh thiếu sáng chạy được trên `STM32H750VBT6`:

```text
camera -> xử lý nhẹ -> LCD
```

Mục tiêu là demo ổn định trên board thật, không phải benchmark SOTA.

## Hướng đang chọn

- Dùng firmware `08-DCMI2LCD` làm nền.
- Xử lý theo hướng luma-centric.
- Dùng model nhỏ `Student-G` để dự đoán control toàn cục.
- Firmware áp dụng gain/gamma nhanh lên ảnh.
- Luôn giữ baseline không AI để fallback.

## Baseline hiện tại

- Model: `student_global_only`
- Config: `workspace/configs/image_first.yaml`
- Checkpoint: `workspace/outputs/checkpoints_image_first/best.pt`
- Preview: `workspace/outputs/previews_image_first/`
- Export: `workspace/outputs/export_image_first_full/`
- Firmware base: `firmware/08-DCMI2LCD/`

## Dataset

Cấu trúc dataset:

```text
datasets/lol/
  train/low/
  train/high/
  val/low/
  val/high/

datasets/lol_v2_real/
datasets/lol_v2_synthetic/
```

Số lượng chính:

- `lol`: 486 train pairs, 15 val pairs
- `lol_v2_real`: 689 train pairs, 100 val pairs
- `lol_v2_synthetic`: 900 train pairs, 100 val pairs

## Luồng train

Chạy từ `workspace/`:

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

Tạo preview:

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

## Kế hoạch firmware

Khi test board, đi theo thứ tự:

1. Xác nhận raw `camera -> LCD` chạy.
2. Thêm processing hook dạng bypass trước LCD blit.
3. Chốt buffer ownership và D-cache policy.
4. Thêm baseline không AI: gain, gamma LUT, black lift, EMA.
5. Đo raw, bypass, baseline, rồi mới đến AI.
6. Chỉ tích hợp `Student-G` khi baseline ổn.

Hook chính:

```text
firmware/08-DCMI2LCD/Src/main.c
```

Xử lý phải nằm trong main loop trước `ST7735_FillRGBRect(...)`.
Không đặt xử lý nặng trong DCMI callback hoặc IRQ.

## Checklist test board

- Build và flash `firmware/08-DCMI2LCD`.
- Xác nhận camera sensor và hướng LCD.
- Ghi raw FPS.
- Thêm identity processing hook.
- So raw và bypass, output phải giống nhau.
- Thêm baseline enhancement.
- Đo FPS lại.
- So với preview đã lưu.
- Tích hợp AI sau cùng.

## Rủi ro

- Single-buffer circular DMA có thể tearing khi CPU/LCD đọc.
- AXI SRAM cacheable + DMA có thể gây stale/corrupt frame.
- LCD blocking transfer có thể là bottleneck chính.
- Preprocess Python có thể lệch với RGB565/luma trên MCU.
- TFLite export khớp PyTorch chưa đồng nghĩa MCU runtime sẵn sàng.
