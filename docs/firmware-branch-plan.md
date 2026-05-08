# Firmware-first branch plan for STM32H750 LLIE

> **Lưu ý thực tế hiện tại:** Tài liệu này mô tả nhánh firmware/system để dùng khi board sẵn sàng trở lại. Hiện tại execution chính của project tạm thời là AI-first offline do chưa có board để test tiếp.

## 1. Mục tiêu của nhánh firmware
Nhánh này không nhằm train model. Mục tiêu là chuẩn bị và ổn định pipeline firmware để sau này có thể nhúng `Student-G` vào mà không vỡ hệ thống.

Mục tiêu cụ thể:
- hiểu rõ pipeline `camera -> process -> LCD`
- xác định vị trí buffer, callback, và đường hiển thị
- thiết kế processing hook / bypass path
- chuẩn bị baseline không AI
- xác định các điểm cần đo FPS / latency / RAM
- chốt nơi sẽ gắn AI khi có board test lại

## 2. Repo và example cần bám
Repo firmware chính:
- `/home/stonies/projects/llie-stm32/repos/hardware/MiniSTM32H7xx`

Example quan trọng nhất:
- `/home/stonies/projects/llie-stm32/repos/hardware/MiniSTM32H7xx/SDK/HAL/STM32H750/08-DCMI2LCD`

Các file nên mở đầu tiên:
- `08-DCMI2LCD/Src/main.c`
- `08-DCMI2LCD/Drivers/BSP/Camera/camera.c`
- `08-DCMI2LCD/Drivers/BSP/Camera/camera.h`
- `08-DCMI2LCD/08-DCMI2LCD.ioc`

## 3. Những điểm kỹ thuật đã biết trước
- Example này là insertion point tốt nhất để chèn xử lý giữa camera và LCD.
- LCD path hiện tại là blocking, nên đây có khả năng là bottleneck lớn.
- Cần cực kỳ chú ý:
  - single vs double buffer
  - DMA-visible memory
  - cache coherency
  - copy buffer thừa

## 4. Roadmap của nhánh firmware

### Stage F0 — đọc và map pipeline
Mục tiêu:
- map rõ các đoạn:
  - start camera DMA
  - frame callback
  - main loop
  - LCD push
- ghi chú buffer nào đang được dùng

Deliverable:
- note rõ function nào / line nào liên quan tới capture, callback, display

### Stage F1 — thiết kế processing hook
Mục tiêu:
- thiết kế khung logic kiểu:

```c
if (frame_ready) {
    process_frame(src_buf, dst_buf);
    lcd_push(dst_buf);
}
```

Ban đầu `process_frame()` chỉ là bypass / identity.

Deliverable:
- pseudo-code rõ chèn ở đâu trong `main.c`
- xác định cần thêm buffer nào

### Stage F2 — baseline no-AI
Mục tiêu:
- chuẩn bị bản enhance không AI để sau này gắn vào firmware nhanh:
  - gain global
  - gamma LUT
  - lift black nhẹ
  - adaptive gamma theo mean luma
  - temporal EMA cho control values

Deliverable:
- spec baseline no-AI
- đề xuất data format cho LUT và fixed-point

### Stage F3 — timing plan
Mục tiêu:
- xác định khi có board sẽ đo các mốc:
  - raw camera -> LCD FPS
  - process cost
  - LCD transfer cost
  - end-to-end latency

Deliverable:
- checklist benchmark trên board

### Stage F4 — AI insertion plan
Mục tiêu:
- xác định khi có Student-G thì gắn ở đâu
- cần buffer nào:
  - Y full-res
  - Y 96x96
  - output params
- renderer firmware sẽ thay phần nào của baseline no-AI

Deliverable:
- sơ đồ nhúng Student-G vào pipeline firmware

## 5. Cấu trúc hàm đề xuất khi triển khai
Khi bắt đầu sửa firmware thật, nên tách logic thành các khối:

- `capture_frame_ready_flag`
- `prepare_luma_from_frame(...)`
- `process_frame_identity(...)`
- `process_frame_baseline(...)`
- `process_frame_ai_controls(...)`
- `lcd_push_frame(...)`

Ý tưởng là giữ interface xử lý ổn định, để có thể thay thế dần:
- identity
- baseline no-AI
- Student-G

## 6. Baseline không AI nên có gì
Bản baseline nên thật nhẹ và dễ chạy trên MCU:
- đo mean luma toàn frame
- chọn gain/gamma theo mean luma
- áp gamma LUT 256 entries
- lift nhẹ vùng tối
- EMA cho gain/gamma giữa các frame

Mục tiêu của baseline:
- tạo mốc so sánh với AI
- nếu AI chậm hoặc chưa ổn, baseline vẫn là fallback demo tốt

## 7. Chỗ cần đo khi có board
Khi có board lại, benchmark nên tách ít nhất các mode:

1. `raw camera -> LCD`
2. `bypass process -> LCD`
3. `baseline no-AI -> LCD`
4. `Student-G -> LCD`

Với mỗi mode nên đo:
- FPS
- latency/frame
- LCD transfer time
- process/inference time
- peak RAM nếu đo được

## 8. Quan hệ với nhánh AI hiện tại
Hiện tại nhánh AI offline có thể đi trước để tạo:
- teacher targets
- pseudo-controls
- Student-G checkpoint

Nhưng nhánh firmware vẫn giữ vai trò:
- xác định deploy feasibility thật
- chuẩn bị nơi gắn model
- tạo baseline/fallback không AI

## 9. Kết luận
Nhánh firmware không bị bỏ. Chỉ là tạm thời chưa phải execution branch chính vì thiếu board test. Khi board quay lại, tài liệu này sẽ là checklist để chuyển từ:

```text
AI offline results
-> firmware integration
-> board benchmark
-> final demo
```
