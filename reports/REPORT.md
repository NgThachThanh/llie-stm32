# Báo Cáo Dự Án

## Tên đề tài

Pipeline tăng cường ảnh thiếu sáng near real-time trên `STM32H750VBT6`.

## Lý do chọn hướng này

Ảnh camera trong môi trường thiếu sáng thường tối, nhiễu và khó quan sát. Các model low-light enhancement lớn chạy tốt trên PC/GPU nhưng không phù hợp MCU nhỏ. Vì vậy dự án chọn hướng thực dụng: thiết kế pipeline nhúng nhẹ, đo được trên board, có fallback không AI.

## Phần cứng mục tiêu

- Board: WeAct MiniSTM32H7xx / `STM32H750VBT6`
- Camera path: DCMI
- Màn hình: ST7735 LCD
- Firmware nền: `firmware/08-DCMI2LCD/`

## Hướng hệ thống

Pipeline mục tiêu:

```text
camera -> ước lượng luma/control -> render nhanh -> LCD
```

Nguyên tắc:

- không dùng full RGB image-to-image CNN trên MCU
- ưu tiên luma, độ phân giải nhỏ
- model nhỏ chỉ xuất control values
- firmware làm phần render nhanh
- baseline không AI luôn tồn tại để fallback

## Baseline AI hiện tại

- Model family: `Student-G`
- Model type: `student_global_only`
- Input: luma `96x96`
- Output: 3 control toàn cục
- Config: `workspace/configs/image_first.yaml`
- Checkpoint: `workspace/outputs/checkpoints_image_first/best.pt`
- Preview: `workspace/outputs/previews_image_first/`
- Export: `workspace/outputs/export_image_first_full/`

Sanity export:

- TFLite input shape: `[1, 96, 96, 1]`
- TFLite output shape: `[1, 3]`
- max diff so với PyTorch: `1.9073486328125e-06`
- mean diff so với PyTorch: `1.112619997911679e-06`

## Mốc train

### Smoke run

Mục tiêu: xác nhận pipeline teacher target, pseudo-control, training và preview chạy end-to-end.

Kết quả:

- teacher generation chạy được
- pseudo-control generation chạy được
- Student-G train được
- preview tạo được
- output tốt hơn ảnh low-light gốc nhưng vẫn hơi tối

Kết luận:

- smoke milestone pass
- chưa phải quality milestone cuối

### Image-first run

Mục tiêu: giảm under-enhancement bằng cách ưu tiên image target hơn.

Thay đổi chính:

- tăng `ssim`
- tăng `exposure`
- giảm áp lực `param` supervision

Kết quả:

- output sáng và hữu ích hơn
- không thấy over-bright nặng trong preview
- run này được chọn làm baseline canonical cũ

### Brightness test

Đã thử train bản sáng hơn để bám `high` image. Số đo sáng hơn, nhưng visual người dùng chọn bản old teacher-target vì nhìn hợp hơn. Các experiment high-bright đã bị bỏ, không dùng làm canonical.

## Nhận định firmware

Từ `08-DCMI2LCD`:

- DCMI DMA ghi vào RGB565 frame buffer.
- DCMI callback chỉ nên set ready flag.
- LCD write đang blocking, có thể là bottleneck chính.
- Stock firmware dùng single buffer, không đủ chắc cho pipeline xử lý.
- Hook xử lý nên nằm trong main loop trước LCD blit.

Rủi ro chính:

- DMA/cache coherency
- tearing do single-buffer circular DMA
- LCD transfer cost
- preprocess RGB565/luma lệch với Python
- RAM/runtime cho AI inference

## Việc nên làm trên board

1. Flash và xác nhận raw `camera -> LCD`.
2. Thêm identity/bypass processing hook.
3. Chốt buffer ownership và D-cache policy.
4. Thêm baseline không AI bằng gain/gamma LUT.
5. Đo FPS/latency cho raw, bypass, baseline.
6. Chỉ tích hợp Student-G sau khi baseline ổn.

## Trạng thái hiện tại

Repo đã sẵn sàng để bạn khác test board:

- có firmware base
- có checkpoint old canonical
- có preview output
- có export artifacts
- có dataset qua Git LFS

Việc quan trọng tiếp theo là xác nhận trên phần cứng thật, không phải train thêm offline.
