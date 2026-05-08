# Image-First Improvement Report — Student-G on LOL-v1

## Goal
Cải thiện kết quả từ smoke milestone trước đó, vốn bị **under-enhanced** do pseudo-controls còn saturate mạnh.

Chiến lược được reviewer phụ đề xuất:
- giảm ảnh hưởng của `param` supervision
- tăng ưu tiên bám `teacher_y` image target
- tăng nhẹ lực kéo sáng/contrast

## Config change
Tạo config mới:
- `workspace/configs/image_first.yaml`

So với `base.yaml`, thay đổi chính:
- `ssim: 0.5 -> 0.7`
- `exposure: 0.2 -> 0.3`
- `param: 0.5 -> 0.05`

Các trọng số khác giữ nguyên.

## Training outcome
Checkpoint mới:
- `workspace/outputs/checkpoints_image_first/best.pt`
- `workspace/outputs/checkpoints_image_first/last.pt`

Loss curve:
- epoch 1: 0.921350
- epoch 2: 0.834752
- epoch 3: 0.623665
- epoch 4: 0.278633
- epoch 5: 0.224636
- epoch 10: 0.216652
- epoch 15: 0.215645
- epoch 20: 0.215763

Reviewer assessment:
- run này **đủ khỏe để đi thẳng sang visual preview**
- không so trị số loss tuyệt đối trực tiếp với run cũ, vì objective/weights đã đổi
- nhưng shape của curve là tốt và ổn định

## Preview output
Đã xuất preview mới tại:
- `workspace/outputs/previews_image_first`

Số lượng preview panel:
- 8 ảnh

## Visual comparison summary
### Baseline smoke cũ
- `pred` tốt hơn `low`
- nhưng còn **under-enhanced**
- còn tối hơn `teacher/high`
- còn hơi phẳng / muddy

### Image-first run mới
Quan sát preview `1_preview.png`:
- `pred` sáng hơn rõ rệt so với `low`
- dark regions được lift tốt hơn
- chi tiết vùng tối hiện rõ hơn
- chưa thấy over-bright nghiêm trọng
- chưa thấy artifact nặng
- vẫn còn hơi bảo thủ hơn `high/teacher`, nhưng mức under-enhancement đã giảm

## Practical interpretation
So với smoke run trước, image-first run có tín hiệu tốt hơn ở đúng điểm ta muốn sửa:
- giảm tình trạng **under-enhancement**
- giữ được tính ổn định, không bùng cháy sáng rõ rệt
- cho cảm giác preview cân bằng hơn

Nói ngắn gọn:
- smoke cũ: quá tối / quá an toàn
- image-first: sáng hơn, hữu ích hơn, gần target hơn

## What improved
1. Model ít bị kéo bởi pseudo-controls saturate hơn
2. `pred` lift shadow tốt hơn
3. Không thấy trả giá bằng artifact lớn hoặc overexposure nặng
4. Đây là hướng cải thiện có hiệu quả và rẻ về thời gian train

## What is still not solved
1. Pseudo-controls gốc vẫn còn saturate mạnh
2. `pred` vẫn chưa đạt tới độ sáng/contrast của `teacher/high`
3. Chưa có metric định lượng (PSNR/SSIM/MAE trên val)
4. Chưa biết global-only path có đủ expressive cho kết quả cuối không

## Reviewer-influenced conclusion
Reviewer phụ chốt rằng image-first là bước đúng để sửa run under-enhanced hiện tại.

Kết quả mới xác nhận điều đó là hợp lý:
- visual output đã cải thiện
- direction này nên được giữ cho vòng tiếp theo

## Recommended next steps
### Option A — tiếp tục tối ưu Student-G
- giữ hướng image-first
- thử tăng thêm nhẹ `exposure`
- thử `param: 0.0` cho một run đối chứng
- thêm metric val đơn giản

### Option B — chuyển sang MiniMap-8 khi đã có baseline tốt hơn
- nếu Student-G global-only bắt đầu chạm trần
- MiniMap-8 có thể giúp tăng local adaptation

## Bottom line
Image-first improvement run: **PASS**

So với smoke run cũ:
- **có cải thiện thực tế về mặt hình ảnh**
- đặc biệt ở vấn đề under-enhancement

Đây chưa phải bản cuối, nhưng là **bước tiến tốt và hợp lý**.
