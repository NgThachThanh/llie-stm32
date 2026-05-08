# STM32H750 Low-Light Enhancement Project

Đây là thư mục gốc đã gom toàn bộ tài nguyên cho dự án **low-light enhancement near real-time trên STM32H750VBT6**.

## Root project
`/home/stonies/projects/llie-stm32`

---

## 1. Mục tiêu ngắn gọn
Dự án này tập trung vào việc xây dựng một pipeline:

```text
camera -> xử lý low-light -> hiển thị LCD
```

trên board `STM32H750VBT6`, theo hướng:
- tối ưu cho hệ thống thật
- không bê nguyên image-to-image model nặng lên MCU
- dùng AI như bộ dự đoán **control signals**
- firmware đảm nhiệm phần render nhanh

---

## 2. Nên đọc gì trước
Nếu mới mở project, đọc theo thứ tự này:

1. `reports/bao-cao-du-an-low-light-stm32h750.md`
2. `docs/stm32h750-lowlight-plan.md`
3. `STATUS.md`
4. `TODO.md`
5. `docs/references.md`
6. `docs/README-setup.md`
7. `workspace/README.md`

---

## 3. Cấu trúc thư mục

### `reports/`
Chứa báo cáo, proposal, tài liệu trình bày với giảng viên.

**File chính:**
- `reports/bao-cao-du-an-low-light-stm32h750.md`

---

### `docs/`
Chứa ghi chú kỹ thuật, kế hoạch, setup, dataset notes, references.

**File quan trọng:**
- `docs/stm32h750-lowlight-plan.md` — plan kỹ thuật tổng thể
- `docs/README-setup.md` — môi trường Python/GPU/train setup
- `docs/datasets.md` — mô tả dataset đã chuẩn bị
- `docs/references.md` — index các paper/repo tham chiếu

---

### `papers/`
Chứa các paper tham chiếu chính của dự án.

**Hiện có:**
- `papers/MIWAI2025_esp32_low_light_paper.pdf`
  - paper tham chiếu trước đó trên nền ESP32-S3-EYE

---

### `datasets/`
Chứa dataset thật đã tải, bản giải nén gốc, bản sắp xếp lại để train, và ghi chú dataset.

**Dataset đã chuẩn bị:**
- `datasets/lol`
- `datasets/lol_v2_real`
- `datasets/lol_v2_synthetic`

**Thư mục phụ:**
- `datasets/downloads/` — file zip gốc
- `datasets/extracted/` — cấu trúc giải nén ban đầu
- `datasets/README.md` — ghi chú mapping dataset

**Dùng để train trực tiếp:**
- `datasets/lol`
- `datasets/lol_v2_real`
- `datasets/lol_v2_synthetic`

---

### `repos/`
Chứa các repo tham chiếu mà project đang dùng.

**Hiện có:**
- `repos/Zero-DCE`
  - teacher baseline đầu tiên
- `repos/Retinexformer`
  - repo tham chiếu dataset/model mạnh hơn
- `repos/hardware/MiniSTM32H7xx`
  - repo code STM32H750/WeAct để khảo sát firmware thật

**Đặc biệt quan trọng:**
- `repos/hardware/MiniSTM32H7xx/SDK/HAL/STM32H750/08-DCMI2LCD`
  - insertion point chính cho pipeline camera -> process -> LCD

---

### `workspace/`
Chứa toàn bộ code train hiện tại.

**Bên trong có:**
- `workspace/configs/`
- `workspace/scripts/`
- `workspace/src/`
- `workspace/README.md`

**Code chính hiện có:**
- student model
- renderer luma
- losses
- image/video dataloader
- train scripts
- teacher target generation script
- offline fitting script
- preview / eval script
- export helper scripts

---

## 4. Trạng thái hiện tại của project
Hiện tại phần **chuẩn bị nền** gần như đã xong, nhưng hướng thực thi đã được chỉnh lại theo kiểu **firmware-first / system-first**:

- môi trường train đã cài
- GPU dùng được
- teacher repo đã có
- dataset thật đã có
- workspace train đã có
- report/docs đã gom về một chỗ
- paper/reference/hardware repo đã gom về một chỗ
- roadmap đã chỉnh theo hướng demo an toàn hơn

### Demo-critical path hiện tại
1. raw `camera -> LCD` trên STM32H750
2. processing hook / bypass path
3. baseline không AI mạnh trên MCU
4. đo FPS / latency / RAM
5. generate teacher targets
6. fit pseudo-controls
7. train `Student-G`
8. chỉ sau đó mới cân nhắc `MiniMap-8`

---

## 5. Mốc kỹ thuật đang theo
Roadmap chốt theo hướng an toàn:

1. **Baseline không AI**
2. **Student-G**: chỉ global controls — *main AI demo target*
3. **Student-MiniMap**: map nhỏ `8x8` hoặc `12x12` — *optional improvement*
4. **StudentV1 24x24** — *extension / stretch goal only*

---

## 6. File điều phối nhanh
- `STATUS.md` — project đang ở trạng thái nào
- `TODO.md` — các bước tiếp theo theo mức ưu tiên

## 7. Các file nên mở khi muốn làm việc tiếp

### Nếu muốn đọc để hiểu dự án
- `reports/bao-cao-du-an-low-light-stm32h750.md`
- `docs/stm32h750-lowlight-plan.md`

### Nếu muốn train
- `workspace/README.md`
- `workspace/configs/base.yaml`
- `workspace/scripts/train_float.py`
- `workspace/scripts/eval_preview.py`
- `workspace/scripts/train_temporal.py`

### Nếu muốn xem dataset
- `docs/datasets.md`
- `datasets/lol`
- `datasets/lol_v2_real`

### Nếu muốn xem firmware/hardware side
- `docs/references.md`
- `repos/hardware/MiniSTM32H7xx`

---

## 8. Gợi ý làm việc tiếp
Khi quay lại project, thứ tự hợp lý là:

1. kiểm tra `raw camera -> LCD` trên board
2. thêm bypass path và baseline không AI
3. đo timing / FPS / RAM
4. chạy teacher target generation trên `LOL-v1`
5. fit pseudo-controls
6. smoke test `Student-G`
7. dùng preview script để nhìn output thật
8. nếu ổn mới mở rộng tiếp

---

## 9. Ghi chú ngắn
Project này ưu tiên tư duy:

- **system-centric** hơn là model-centric
- **near real-time** hơn là chasing metric đẹp bằng mọi giá
- **deploy được thật trên STM32H750** hơn là làm model nặng nhưng khó nhúng
- **Student-G là demo chính**, không ép phải đạt `24x24 gain map`
