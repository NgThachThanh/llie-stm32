# Smoke Train Report — Student-G on LOL-v1

## Scope
Báo cáo ngắn cho vòng execution AI-first đầu tiên của dự án low-light STM32H750.

Mục tiêu vòng này:
- xác nhận pipeline teacher -> pseudo-controls -> train -> preview chạy end-to-end
- lấy checkpoint Student-G đầu tiên
- chưa coi đây là vòng chất lượng cuối cùng

## Reviewer involvement
Có reviewer phụ tham gia ở các mốc:
- trước full teacher generation
- sau pseudo-control fit
- sau refit v2
- sau smoke training

Kết luận reviewer nhất quán:
- pipeline có thể tiếp tục
- nhưng pseudo-controls đang còn saturate mạnh, nên kết quả hiện tại chỉ nên xem là **smoke milestone**, chưa phải quality milestone

## What was completed
### 1. Teacher target generation
Đã tạo `teacher_y` cho LOL-v1:
- train: 485 / 485 thành công
- val: 15 / 15 thành công

Scripts/changes:
- thêm `workspace/scripts/zero_dce_infer_single_folder.py`
- harden `workspace/scripts/prepare_teacher_targets.py`
- giới hạn Zero-DCE infer đúng folder cần dùng, tránh quét DICM/LIME

### 2. Pseudo-control fitting
Fit v1:
- success: 485
- skipped: 0
- boundhits: 481

Fit v2 với bounds rộng hơn:
- success: 485
- skipped: 0
- boundhits: 471

Pseudo-control v2 được dùng cho smoke train:
- path: `datasets/lol/train/pseudo_ctrl_v2`

### 3. Student-G smoke training
Checkpoint path:
- `workspace/outputs/checkpoints_smoke_debug/best.pt`
- `workspace/outputs/checkpoints_smoke_debug/last.pt`

Loss curve:
- epoch 1: 5.241693
- epoch 2: 4.198884
- epoch 3: 2.056195
- epoch 4: 0.701393
- epoch 5: 0.588018
- epoch 10: 0.550368
- epoch 15: 0.543733
- epoch 20: 0.543847

Reviewer assessment:
- healthy enough for first smoke milestone
- training loop / optimizer / supervision path đều hoạt động
- chưa đủ để kết luận model quality cuối cùng

### 4. Preview generation
Đã tạo preview trên LOL-v1 val:
- output dir: `workspace/outputs/previews_smoke`
- số preview panels: 8

## Visual summary
Dựa trên preview đầu tiên (`1_preview.png`):
- `pred` rõ ràng tốt hơn `low`
- chưa thấy over-bright nghiêm trọng
- chưa thấy artifact thảm hoạ
- vấn đề chính là **under-enhanced**
- `pred` còn tối hơn `high` và `teacher`
- ảnh còn hơi phẳng / hơi muddy

Kết luận ngắn:
- vòng smoke hiện tại **có triển vọng**
- nhưng enhancement còn bảo thủ
- chưa match được mức sáng/contrast của teacher/high

## Important issues found
### 1. Pseudo-controls vẫn saturate mạnh
Fit v2 vẫn còn:
- boundhits 471 / 485

Điều này cho thấy ít nhất một trong các khả năng:
- bounds vẫn chưa hợp lý
- global-controls model chưa fit tốt teacher
- teacher target đang đòi hỏi local correction nhiều hơn global-only path

### 2. Dataset loader bug was fixed
Trong `workspace/src/data/image_dataset.py`:
- đã sửa lỗi scalar load từ `.npz` gây crash DataLoader

### 3. Script quality improved
Đã thêm / sửa:
- `prepare_teacher_targets.py`
- `fit_teacher_controls.py`
- `eval_preview.py`
- `zero_dce_infer_single_folder.py`

## Current status
### Passed
- teacher generation
- pseudo-control generation
- Student-G smoke train
- preview export

### Not solved yet
- pseudo-control saturation
- preview vẫn under-enhanced so với teacher/high
- chưa có metric định lượng
- chưa có deploy path/TFLite final

## Practical interpretation
Hiện tại có thể nói:
- pipeline AI-first offline đã **chạy end-to-end thành công**
- Student-G đã có checkpoint đầu tiên
- result đủ tốt để chứng minh hướng đi có khả thi
- nhưng quality hiện tại chưa đủ để xem là bản train nghiêm túc cuối

## Recommended next steps
1. preview thêm vài ảnh val để xác nhận pattern under-enhancement có lặp lại không
2. làm `fit v3` hoặc đổi chiến lược pseudo-label cho global path
3. cân nhắc train một run chỉ bám `teacher_y` image loss mạnh hơn, giảm phụ thuộc pseudo-controls bị saturate
4. nếu vẫn under-enhanced, thử tăng khả năng biểu diễn của control path hoặc đi sớm sang `MiniMap-8`

## Bottom line
Smoke milestone: **PASS**

Quality milestone: **NOT YET**

Dự án hiện đã có:
- checkpoint Student-G đầu tiên
- preview output đầu tiên
- bằng chứng pipeline chạy được

Nhưng để tiến tới kết quả đáng tin hơn, bước tiếp theo phải tập trung vào **giảm saturation của pseudo-controls** và **tăng mức enhancement của pred so với teacher/high**.
