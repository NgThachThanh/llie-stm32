# Báo cáo đề xuất dự án low-light enhancement near real-time trên STM32H750VBT6

> **Mục đích tài liệu:** Tài liệu này dùng để trình bày rõ ràng với giảng viên về ý tưởng, tính khả thi, hướng kỹ thuật, kế hoạch thực hiện, mốc triển khai và rủi ro của dự án tăng cường ảnh thiếu sáng chạy near real-time trên vi điều khiển STM32H750VBT6.

---

# 1. Tên đề tài đề xuất

**Thiết kế và triển khai pipeline tăng cường ảnh thiếu sáng near real-time trên thiết bị biên STM32H750VBT6 sử dụng camera OV5640 và màn hình LCD tích hợp**

---

# 2. Bối cảnh và lý do chọn đề tài

Trong các hệ thống nhúng thị giác máy tính cỡ nhỏ, việc thu nhận hình ảnh trong môi trường thiếu sáng là một bài toán rất thực tế. Khi ánh sáng yếu, ảnh từ camera thường bị tối, mất chi tiết, nhiễu nhiều và khó quan sát trực tiếp. Điều này ảnh hưởng lớn đến các ứng dụng như:

- camera giám sát chi phí thấp,
- thiết bị quan sát cầm tay,
- hệ thống robot hoặc IoT có camera,
- thiết bị hỗ trợ quan sát trong điều kiện ánh sáng kém.

Các phương pháp low-light enhancement hiện đại dựa trên deep learning thường cho chất lượng tốt, nhưng đa số cần GPU hoặc phần cứng mạnh. Nếu triển khai trực tiếp các mô hình đó lên vi điều khiển thì gần như không khả thi vì giới hạn nghiêm ngặt về:

- bộ nhớ RAM,
- flash lưu chương trình,
- tốc độ tính toán,
- băng thông truyền dữ liệu từ camera sang bộ đệm và từ bộ đệm ra màn hình.

Vì vậy, đề tài này hướng đến một mục tiêu thực tế hơn: **không cố chạy một mô hình lớn để tạo ra ảnh đẹp nhất, mà thiết kế một pipeline tối ưu riêng cho phần cứng vi điều khiển để vừa cải thiện chất lượng ảnh thiếu sáng, vừa giữ được cảm giác hiển thị liên tục như video**.

Nói cách khác, đề tài ưu tiên **tư duy system-centric** thay vì **model-centric**. Giá trị cốt lõi không nằm ở việc mang một model đẹp từ desktop xuống MCU, mà ở việc xây dựng được một chuỗi hoàn chỉnh:

```text
camera -> capture -> xử lý -> hiển thị
```

chạy được thực tế, đo được và bảo vệ được trên phần cứng thật.

---

# 3. Mục tiêu của dự án

## 3.1. Mục tiêu tổng quát

Xây dựng một hệ thống camera -> xử lý -> hiển thị trên nền STM32H750VBT6 có khả năng:

- thu ảnh liên tục từ camera OV5640,
- tăng cường ảnh thiếu sáng,
- hiển thị liên tục lên màn hình LCD tích hợp,
- đạt tính chất near real-time,
- sử dụng mô hình AI siêu nhẹ kết hợp xử lý ảnh cổ điển để phù hợp với giới hạn tài nguyên của vi điều khiển.

## 3.2. Mục tiêu cụ thể

- Khảo sát phần cứng board WeAct MiniSTM32H7xx dùng STM32H750VBT6.
- Tận dụng code mẫu sẵn có để giảm thời gian phát triển firmware nền.
- Phân tích các điểm nghẽn thực tế của hệ thống: RAM, DMA, cache, bus SPI LCD, kích thước buffer, activation memory.
- Đề xuất một kiến trúc xử lý low-light phù hợp với MCU thay vì sao chép nguyên mô hình từ bài báo chạy trên phần cứng khác.
- Thiết kế một mô hình học sâu siêu nhẹ (tiny student model) chỉ xử lý độ sáng (luma) ở độ phân giải thấp.
- Huấn luyện mô hình bằng dữ liệu low-light và xuất mô hình ở định dạng phù hợp để nhúng vào firmware.
- Tích hợp pipeline hoàn chỉnh trên board để đánh giá chất lượng ảnh và tốc độ hiển thị.

## 3.3. Định nghĩa mục tiêu near real-time

Trong phạm vi đề tài này, khái niệm **near real-time** không nên hiểu mơ hồ mà cần gắn với chỉ tiêu kỹ thuật cụ thể. Đề tài đề xuất dùng các mốc đánh giá sau:

- Mức tối thiểu chấp nhận được: **5 FPS**,
- Mức mục tiêu tốt: **8-10 FPS**,
- Độ phân giải đầu vào/hiển thị mục tiêu giai đoạn đầu: **160 x 120**,
- Độ trễ đầu-cuối kỳ vọng: **dưới 150-200 ms/frame**,
- Cần đo tách riêng các thành phần thời gian:
  - camera capture,
  - tiền xử lý,
  - model inference,
  - render tăng cường ảnh,
  - truyền ảnh ra LCD.

Việc định nghĩa rõ như vậy giúp đề tài có tiêu chí đánh giá minh bạch và dễ bảo vệ hơn trước giảng viên.

---

# 4. Đối tượng phần cứng sử dụng

## 4.1. Nền tảng phần cứng chính

Board mục tiêu của dự án là:

**WeAct MiniSTM32H7xx - STM32H750VBT6**

## 4.2. Các đặc điểm đáng chú ý của board

Qua khảo sát tài liệu và mã nguồn đi kèm, board có các thành phần phù hợp với bài toán:

- vi điều khiển **STM32H750VBT6**,
- khoảng **1 MB RAM**,
- **8 MB SPI Flash**,
- **8 MB QSPI Flash**,
- hỗ trợ giao tiếp camera qua **DCMI**,
- hỗ trợ các cảm biến camera như **OV5640**,
- có **màn hình LCD ST7735**,
- có thể mở rộng qua **thẻ nhớ SD/TF** nếu cần.

## 4.3. Ý nghĩa của việc chọn STM32H750

So với những nền tảng nhẹ hơn như ESP32-S3, STM32H750 có lợi thế lớn hơn về:

- tài nguyên RAM,
- xung nhịp xử lý,
- khả năng tổ chức buffer và pipeline tốt hơn,
- khả năng thử nghiệm mô hình AI nhẹ ở mức thực dụng hơn.

Tuy nhiên, đây vẫn là một MCU, không phải SoC có NPU/GPU, nên bài toán vẫn rất khó nếu chọn sai hướng mô hình.

## 4.4. Lưu ý về bộ nhớ và vùng lưu trữ chương trình

STM32H750VBT6 có lợi thế về RAM nhưng vùng lưu chương trình nội tại không lớn so với nhu cầu của một firmware có thêm thành phần AI. Board WeAct có bổ sung bộ nhớ ngoài như SPI Flash và QSPI Flash, do đó đề tài cần làm rõ ngay từ đầu các câu hỏi triển khai sau:

- chương trình chính nằm ở đâu,
- model INT8 được lưu ở internal flash hay external flash,
- có dùng QSPI/XIP hay không,
- frame buffer đặt ở vùng RAM nào,
- vùng nhớ nào DMA camera có thể truy cập trực tiếp,
- tensor arena hoặc activation workspace nên đặt ở đâu.

Đây là phần rất dễ bị hỏi trong lúc trao đổi với giảng viên vì nó liên quan trực tiếp đến tính khả thi của đề tài trên phần cứng thật.

---

# 5. Đầu vào cảm biến và đầu ra hiển thị

## 5.1. Camera

Dự án dự kiến sử dụng **OV5640** làm nguồn ảnh đầu vào.

Điểm quan trọng trong lựa chọn này là: **không nên để camera xuất ảnh độ phân giải quá cao rồi mới resize trong MCU**, vì như vậy sẽ gây tốn:

- băng thông đọc/ghi bộ nhớ,
- thời gian resize,
- bộ đệm trung gian,
- thời gian xử lý toàn hệ thống.

Do đó, hướng tối ưu là cấu hình camera **xuất trực tiếp ở độ phân giải nhỏ phù hợp**, ưu tiên khoảng:

- `160 x 120` hoặc
- `128 x 160`

trong giai đoạn đầu.

## 5.2. Màn hình

Màn hình LCD tích hợp dùng driver **ST7735** và giao tiếp **SPI**.

Qua phân tích mã nguồn ví dụ sẵn có, đường truyền LCD hiện tại đang:

- truyền theo kiểu **blocking**,
- gửi dữ liệu từng dòng ảnh,
- sử dụng `HAL_SPI_Transmit(...)`.

Điều này có nghĩa rằng ngay cả khi mô hình AI đủ nhẹ, tốc độ hiển thị cuối cùng vẫn bị ảnh hưởng mạnh bởi **băng thông đẩy ảnh ra LCD**.

Vì vậy, một phần việc bắt buộc của đề tài là phải đo riêng hiệu năng của đường truyền LCD trong các kịch bản:

- camera -> LCD chưa xử lý,
- camera -> xử lý cổ điển -> LCD,
- camera -> AI -> render -> LCD.

Nếu khả thi, các hướng tối ưu bổ sung có thể bao gồm:

- chuyển sang SPI DMA cho LCD,
- cập nhật theo line hoặc theo block,
- hạn chế copy buffer trung gian,
- giữ output ở định dạng RGB565 để giảm chi phí chuyển đổi.

---

# 6. Bài toán kỹ thuật cốt lõi của dự án

Nếu nhìn bề ngoài, bài toán có vẻ chỉ là “lấy ảnh tối rồi làm sáng lên”. Tuy nhiên trên MCU, thực tế đây là bài toán phối hợp giữa nhiều ràng buộc đồng thời:

## 6.1. Ràng buộc về bộ nhớ

Ngoài trọng số của mô hình, hệ thống còn phải chứa:

- buffer ảnh đầu vào,
- buffer ảnh đầu ra,
- vùng nhớ trung gian cho resize,
- activation tensors khi chạy model,
- stack và bộ nhớ của firmware.

Điểm khó nhất không nằm ở kích thước file model, mà thường nằm ở **activation memory** trong lúc suy luận.

## 6.2. Ràng buộc về dữ liệu thời gian thực

Pipeline camera và màn hình không chạy độc lập hoàn toàn. Nếu thiết kế sai, có thể xảy ra:

- xung đột giữa DMA camera và phần xử lý ảnh,
- ghi đè buffer chưa xử lý xong,
- tearing hoặc nhấp nháy,
- sụt FPS mạnh.

## 6.3. Ràng buộc về hiển thị

Do LCD truyền qua SPI, nếu độ phân giải quá cao hoặc phải cập nhật quá nhiều dữ liệu mỗi frame, tốc độ khung hình sẽ giảm đáng kể.

## 6.4. Ràng buộc về mô hình AI

Nếu chọn mô hình dạng image-to-image RGB đầy đủ, hệ thống sẽ rất khó đạt được:

- tốc độ đủ nhanh,
- bộ nhớ đủ dùng,
- độ ổn định qua nhiều frame liên tiếp.

---

# 7. Khảo sát mã nguồn nền có sẵn và khả năng tận dụng

Để giảm khối lượng phát triển từ đầu, dự án sẽ tận dụng mã nguồn ví dụ sẵn có trong repository của board.

## 7.1. Repository nền tảng

Repository mục tiêu:

**WeActStudio/MiniSTM32H7xx**

## 7.2. Ví dụ phù hợp nhất

Qua khảo sát, ví dụ phù hợp nhất để làm nền là:

`SDK/HAL/STM32H750/08-DCMI2LCD`

Ví dụ này đã có sẵn:

- khởi tạo camera,
- nhận dữ liệu qua DCMI + DMA,
- lưu ảnh vào buffer,
- hiển thị ảnh lên LCD.

## 7.3. Ý nghĩa của việc tận dụng example này

Điều này giúp dự án không phải xây lại toàn bộ firmware nền. Nhóm chỉ cần tập trung vào việc:

- chèn khối xử lý AI vào giữa camera và LCD,
- sửa cơ chế buffer,
- thêm phần tiền xử lý và hậu xử lý phù hợp.

---

# 8. Kết quả phân tích khả thi ban đầu

## 8.1. Độ phân giải làm việc đề xuất

Sau khi phân tích băng thông và bộ nhớ, độ phân giải hợp lý nhất để bắt đầu là:

**160 x 120**

Đây là điểm cân bằng tương đối tốt giữa:

- khả năng nhìn rõ trên màn hình,
- tốc độ đẩy LCD,
- chi phí xử lý,
- lượng bộ nhớ cần dùng.

## 8.2. Lý do không chọn 320x240 ở giai đoạn đầu

Dù 320x240 nhìn đẹp hơn, nhưng với LCD SPI blocking và pipeline cần thêm AI, mức này sẽ làm tăng mạnh:

- số byte mỗi frame,
- thời gian truyền ra LCD,
- thời gian xử lý,
- khả năng tràn/bế tắc pipeline.

Vì vậy, 320x240 không phải là điểm khởi đầu tốt cho một prototype near real-time.

## 8.3. Hướng xử lý được chọn

Hướng cuối cùng được đề xuất không phải là dùng một mô hình deep learning tạo lại toàn bộ ảnh RGB, mà là:

**pipeline lai giữa xử lý ảnh cổ điển và AI siêu nhẹ**

Cụ thể:

1. camera xuất ảnh ở độ phân giải nhỏ phù hợp,
2. trích xuất thành phần độ sáng (luma),
3. dùng một mô hình tiny AI để dự đoán tham số tăng cường ảnh,
4. áp dụng các tham số này lên ảnh bằng công thức xử lý nhanh,
5. ghép dữ liệu hiển thị và đẩy lên LCD.

## 8.4. Baseline truyền thống bắt buộc phải có

Trước khi tích hợp AI, đề tài cần có một baseline truyền thống đủ mạnh để làm mốc so sánh. Các thành phần baseline nên bao gồm:

- AEC/AGC của cảm biến OV5640 nếu tận dụng được,
- global gain,
- gamma LUT,
- adaptive gamma theo mean luma,
- temporal EMA cho các tham số toàn cục,
- nếu đủ tài nguyên thì có thể thử local contrast hoặc CLAHE đơn giản theo ô nhỏ.

Mục tiêu của baseline không AI là:

- chứng minh hệ thống camera -> xử lý -> LCD đã chạy ổn định,
- đo trần hiệu năng thực tế trước khi có model,
- tạo mốc để đánh giá xem AI có thực sự mang lại cải thiện đáng kể hay không.

---

# 9. Ý tưởng kỹ thuật trung tâm của dự án

## 9.1. Không để AI sinh toàn bộ ảnh

Trên máy tính mạnh, mô hình image-to-image thường sinh ra ảnh enhanced trực tiếp. Nhưng trên MCU, cách đó không tối ưu.

Thay vào đó, đề tài này đề xuất để AI chỉ làm nhiệm vụ:

- dự đoán mức tăng sáng toàn cục,
- dự đoán gamma toàn cục,
- dự đoán một bản đồ tăng sáng thô theo vùng.

Sau đó firmware sẽ dùng các giá trị này để tự thực hiện tăng cường ảnh.

## 9.2. Tư tưởng “AI điều khiển bộ lọc nhanh”

Có thể hiểu đơn giản rằng:

- AI đóng vai trò “bộ não nhỏ”,
- firmware đóng vai trò “cánh tay thực thi nhanh”.

Cách làm này giúp giảm rất mạnh khối lượng tính toán trong khi vẫn giữ được tính thích nghi theo nội dung ảnh.

---

# 10. Kiến trúc mô hình AI đề xuất

## 10.1. Tên mô hình nội bộ

Tạm gọi mô hình mục tiêu là:

**StudentV1**

## 10.2. Dữ liệu đầu vào

- Input của model: `96 x 96 x 1`
- Chỉ dùng **kênh luma Y**

Việc chỉ dùng luma giúp:

- giảm số chiều dữ liệu,
- giảm activation memory,
- tập trung đúng vào bài toán độ sáng,
- giảm chi phí suy luận.

## 10.3. Đầu ra của model

Model cho ra hai nhánh đầu ra:

### Nhánh 1: Global controls

Gồm 3 tham số:

- `gain_global`: mức tăng sáng tổng thể,
- `gamma_global`: tham số điều chỉnh đường cong sáng,
- `lift_black`: mức nâng vùng tối.

### Nhánh 2: Local controls

- `24 x 24 x 1` coarse gain map

Bản đồ này cho biết vùng nào của ảnh cần tăng sáng mạnh hơn hoặc nhẹ hơn.

## 10.4. Kiến trúc lớp cơ bản

Model được thiết kế rất nhỏ với các lớp thân thiện cho triển khai INT8 trên MCU:

- depthwise convolution,
- pointwise convolution,
- average pooling,
- fully connected nhỏ,
- ReLU.

Đây là một kiến trúc nhẹ, dễ lượng tử hóa và thực tế hơn nhiều so với các kiến trúc U-Net hoặc transformer cho bài toán này.

## 10.5. Vai trò của StudentV1 trong lộ trình nghiên cứu

Trong đề tài này, cần phân biệt rõ giữa **kiến trúc mục tiêu cuối cùng** và **milestone triển khai đầu tiên**.

StudentV1 là **target architecture** của đề tài, không nhất thiết là phiên bản đầu tiên phải chạy được trên board. Nói cách khác:

- StudentV1 không sai về thiết kế,
- nhưng nếu đưa StudentV1 đầy đủ vào milestone đầu tiên thì rủi ro demo sẽ cao.

Do đó, hướng an toàn hơn là triển khai tăng dần theo các phiên bản:

- **Student-G**: chỉ dự đoán global controls,
- **Student-MiniMap**: global controls + gain map nhỏ `8x8` hoặc `12x12`,
- **StudentV1**: global controls + gain map `24x24`.

Cách trình bày này giúp giữ được tham vọng kỹ thuật của đề tài, đồng thời giảm rủi ro khi demo và làm rõ quá trình ablation/prototype với giảng viên.

---

# 11. Cơ chế render tăng cường ảnh trong firmware

Sau khi model dự đoán các tham số, firmware sẽ áp dụng chúng lên ảnh luma full-resolution.

Công thức khái quát như sau:

1. Nâng nhẹ vùng tối bằng `lift_black`.
2. Nhân với `gain_global`.
3. Nhân thêm với `gain_map(x, y)` theo từng vị trí nếu phiên bản model có local map.
4. Áp gamma correction bằng `gamma_global`.
5. Giới hạn giá trị đầu ra trong khoảng hợp lệ.

Điểm mạnh của cách này là:

- đơn giản,
- chạy nhanh,
- dễ chuyển sang fixed-point,
- có thể dùng LUT cho gamma,
- phù hợp với firmware nhúng.

---

# 12. Chiến lược huấn luyện mô hình

## 12.1. Không dùng pretrained classifier truyền thống

Student model quá nhỏ và quá đặc thù, nên không cần bắt đầu từ các backbone như ResNet hay MobileNet pretrained trên ImageNet.

Thay vào đó, model sẽ được:

**train from scratch**

trên bài toán low-light enhancement.

## 12.2. Teacher model

Để tăng chất lượng học, dự án đề xuất dùng một teacher model chạy trên máy tính mạnh để sinh target tốt hơn cho student.

Teacher phù hợp nhất để bắt đầu là:

**Zero-DCE++**

Lý do chọn:

- cùng tinh thần curve-based,
- phù hợp với bài toán điều chỉnh sáng,
- dễ dùng làm nguồn pseudo-target cho student nhỏ.

Sau khi pipeline ổn định, có thể cân nhắc teacher mạnh hơn như:

- CPGA-Net+,
- Multinex-light,
- hoặc một mô hình LLIE chất lượng cao khác.

## 12.3. Nguyên tắc thiết kế target huấn luyện

Do student model không sinh ảnh enhanced trực tiếp mà chỉ dự đoán các tham số điều khiển bộ lọc, việc thiết kế target huấn luyện cần bám đúng bản chất đó. Hướng hợp lý là:

1. ảnh low-light được đưa qua teacher model để tạo ảnh enhanced chất lượng cao,
2. dùng một bộ offline fitter/optimizer để tìm bộ tham số `gain`, `gamma`, `lift`, `gain_map` sao cho ảnh render từ các tham số này gần với teacher output,
3. dùng bộ tham số đã fit làm pseudo-label cho student,
4. đồng thời vẫn tính loss trên ảnh render cuối cùng để tránh student bị phụ thuộc hoàn toàn vào pseudo-label.

Cách làm này phù hợp hơn so với việc huấn luyện student như một image-to-image model thu nhỏ.

## 12.4. Dữ liệu huấn luyện

Bộ dữ liệu dự kiến:

- LOL,
- LOL-v2,
- ảnh thực tế low-light tự thu hoặc quay từ camera tương tự,
- các đoạn video low-light để fine-tune temporal consistency.

## 12.5. Loss functions cơ bản

Các loss chính dự kiến bao gồm:

- `L1 loss`: giữ gần target,
- `SSIM loss`: giữ cấu trúc ảnh,
- `Exposure loss`: ép ảnh ra mức sáng hợp lý,
- `TV loss`: làm mượt coarse gain map,
- `Temporal consistency loss`: giảm nhấp nháy giữa các frame,
- `regularization loss`: tránh model dự đoán giá trị quá cực đoan.

## 12.6. Hybrid supervision cho student model

Một điểm quan trọng của đề tài là không nên chọn cực đoan một trong hai cách sau:

- chỉ học explicit pseudo-label tham số,
- hoặc chỉ học bằng image reconstruction loss sau render.

Hướng tốt hơn là **hybrid supervision**, trong đó tổng loss có thể được mô tả khái quát như sau:

```text
L_total =
  λ_param * L_param
+ λ_render * L_render
+ λ_reg * L_reg
+ λ_tv * L_tv_map
+ λ_temp * L_temporal
```

Trong đó:

- `L_param`: kéo output của student gần bộ pseudo-label tham số từ offline fitting,
- `L_render`: render ảnh từ output student rồi so với teacher image hoặc ground truth,
- `L_reg`: giới hạn `gain`, `gamma`, `lift` không đi tới giá trị cực đoan,
- `L_tv_map`: làm mượt gain map để tránh block artifact,
- `L_temporal`: làm giảm hiện tượng flicker giữa các frame liên tiếp.

Hướng hybrid này giúp student vừa học đúng “control interface” của firmware, vừa không bị phụ thuộc cứng nhắc vào một decomposition có thể chưa tối ưu từ bộ offline fitter.

## 12.7. Lượng tử hóa

Sau khi train xong, mô hình sẽ được đưa qua:

- quantization-aware training (QAT),
- xuất ra INT8,
- chuyển sang định dạng phù hợp để nhúng firmware.

---

# 13. Thiết kế pipeline hệ thống hoàn chỉnh

Pipeline tổng thể của hệ thống như sau:

```text
OV5640 camera
-> DCMI + DMA capture
-> frame buffer
-> tách luma Y
-> resize về 96x96 cho model
-> tiny AI suy luận tham số tăng cường
-> upscale coarse gain map nếu có
-> áp gain/gamma/lift lên ảnh Y full-res
-> ghép dữ liệu hiển thị
-> xuất lên LCD ST7735
```

Để pipeline chạy ổn định, firmware phải được chỉnh lại theo hướng:

- double buffering,
- tách buffer camera và buffer xử lý,
- chú ý cache coherency,
- tránh xử lý trực tiếp trên vùng DMA đang ghi.

---

# 14. Kế hoạch triển khai theo giai đoạn

## Giai đoạn 1: Khảo sát và dựng nền

Mục tiêu:

- nắm rõ phần cứng,
- nắm rõ code ví dụ camera -> LCD,
- xác định điểm chèn AI,
- đo và ước lượng các ràng buộc bộ nhớ, tốc độ và băng thông.

Sản phẩm đầu ra:

- báo cáo khảo sát,
- sơ đồ pipeline,
- quyết định độ phân giải làm việc ban đầu.

## Giai đoạn 2: Khóa baseline firmware và đo đạc hệ thống

Mục tiêu:

- sửa example sang double buffer,
- đảm bảo camera -> LCD chạy ổn định,
- thêm đo đạc thời gian cho từng khối,
- soak test để phát hiện lỗi buffer, DMA hoặc cache,
- thử baseline tăng sáng cổ điển như gain/gamma/LUT đơn giản.

Sản phẩm đầu ra:

- firmware baseline hiển thị liên tục,
- kết quả FPS camera -> LCD raw,
- số liệu thời gian và độ trễ sơ bộ,
- đánh giá hạn chế khi chưa dùng AI.

## Giai đoạn 3: Tích hợp pipeline enhancement theo chế độ identity/bypass

Mục tiêu:

- tích hợp đầy đủ đường ống xử lý mới,
- giữ output gần như ảnh gốc để kiểm tra tính đúng đắn của buffer và lịch chạy,
- xác minh rằng việc thêm pipeline không gây sụt hiệu năng bất thường hoặc phát sinh lỗi bộ nhớ.

Sản phẩm đầu ra:

- firmware có đầy đủ pipeline nhưng chưa bật tăng cường ảnh thực sự,
- báo cáo về overhead riêng của pipeline,
- xác nhận hệ thống ổn định trước khi thêm logic AI.

## Giai đoạn 4: Xây dựng baseline và model global-only

Mục tiêu:

- xây dựng code train trên máy tính,
- hoàn thiện baseline không AI mạnh,
- triển khai Student-G chỉ với global controls,
- đánh giá khả năng cải thiện ảnh với độ phức tạp tối thiểu.

Sản phẩm đầu ra:

- baseline truyền thống hoàn chỉnh,
- checkpoint Student-G,
- so sánh baseline không AI và AI global-only.

## Giai đoạn 5: Student-MiniMap và fine-tune theo video

Mục tiêu:

- mở rộng từ Student-G sang Student-MiniMap,
- thử gain map nhỏ `8x8` hoặc `12x12`,
- thêm temporal consistency,
- giảm flicker,
- đánh giá lợi ích thực sự của local adaptation.

Sản phẩm đầu ra:

- checkpoint Student-MiniMap,
- kết quả video test,
- báo cáo về chất lượng và độ ổn định theo thời gian.

## Giai đoạn 6: StudentV1 đầy đủ và lượng tử hóa INT8

Mục tiêu:

- nếu còn đủ thời gian và headroom, nâng lên StudentV1 với gain map `24x24`,
- thực hiện QAT,
- xuất model INT8,
- chuẩn bị cho nhúng firmware.

Sản phẩm đầu ra:

- model INT8 hoàn chỉnh,
- báo cáo so sánh Student-G, Student-MiniMap và StudentV1,
- quyết định phiên bản cuối cùng dùng để deploy.

## Giai đoạn 7: Tích hợp model vào STM32H750 và tối ưu hệ thống

Mục tiêu:

- nhúng model vào firmware,
- triển khai suy luận trên ảnh luma,
- tối ưu smoothing theo thời gian,
- tối ưu FPS, latency và chất lượng hiển thị,
- tổng hợp báo cáo cuối cùng.

Sản phẩm đầu ra:

- hệ thống demo hoàn chỉnh,
- bảng so sánh các phiên bản,
- báo cáo và slide bảo vệ.

---

# 15. Điểm mới và đóng góp kỳ vọng của đề tài

Đề tài không hướng tới việc đề xuất một mô hình học sâu hoàn toàn mới theo nghĩa học thuật thuần túy. Thay vào đó, giá trị của đề tài nằm ở các điểm sau:

## 15.1. Chuyển bài toán từ “model-centric” sang “system-centric”

Thay vì chỉ tập trung vào một mô hình đẹp trên desktop, đề tài tập trung vào cách làm sao để cả hệ thống camera -> AI -> màn hình chạy được thực tế trên MCU.

## 15.2. Đề xuất pipeline lai phù hợp với phần cứng nhỏ

Kết hợp:

- cảm biến cấu hình hợp lý,
- xử lý ảnh cổ điển,
- AI siêu nhẹ dự đoán tham số,
- hậu xử lý nhanh bằng firmware.

## 15.3. Tối ưu theo dữ liệu video liên tục

Nhiều nghiên cứu chỉ tối ưu trên ảnh tĩnh. Trong khi đó, đề tài này quan tâm trực tiếp đến:

- cảm giác hiển thị liên tục,
- sự ổn định giữa các frame,
- khả năng sử dụng thực tế trên thiết bị nhúng.

## 15.4. Khả năng vượt bài báo tham chiếu theo góc độ thực dụng

Nếu hệ thống đạt được:

- pipeline ổn định hơn,
- tốc độ tốt hơn,
- chất lượng hiển thị dễ chấp nhận hơn,
- cách triển khai rõ ràng hơn trên phần cứng MCU,

thì đề tài vẫn có giá trị rất tốt dù không nhất thiết vượt hoàn toàn mọi metric học thuật trên ảnh tĩnh.

---

# 16. Rủi ro kỹ thuật và hướng giảm thiểu

## 16.1. Rủi ro 1: model vẫn quá nặng so với MCU

**Giảm thiểu:**

- giữ input model ở 96x96,
- chỉ dùng luma,
- chỉ dự đoán control signals,
- ưu tiên các operator đơn giản.

## 16.2. Rủi ro 2: ảnh đẹp hơn nhưng FPS quá thấp

**Giảm thiểu:**

- bắt đầu ở 160x120,
- dùng baseline không AI để đo trần thực tế,
- tối ưu fixed-point renderer,
- làm mượt theo thời gian thay vì cố tăng chất lượng từng frame quá mức.

## 16.3. Rủi ro 3: output bị nhấp nháy giữa các frame

**Giảm thiểu:**

- thêm temporal consistency loss,
- thêm EMA smoothing trong runtime,
- giới hạn biên của output model.

## 16.4. Rủi ro 4: tích hợp firmware phát sinh lỗi DMA/cache/buffer

**Giảm thiểu:**

- chuyển sang double buffer,
- xử lý rõ cache coherency,
- test từng bước tách biệt trước khi ghép full pipeline.

## 16.5. Rủi ro 5: teacher target không phù hợp với ảnh thực tế

**Giảm thiểu:**

- kết hợp paired dataset với ảnh thực,
- tự thu thêm dữ liệu low-light,
- ưu tiên target nhìn tự nhiên hơn là target “quá đẹp”.

---

# 17. Kết quả kỳ vọng

Nếu dự án triển khai đúng hướng, kết quả kỳ vọng là:

- ảnh từ camera trong môi trường tối được cải thiện rõ rệt,
- hệ thống hiển thị liên tục lên LCD,
- FPS đủ để tạo cảm giác near real-time,
- mô hình AI chạy được thật trên STM32H750,
- quy trình từ train model đến deploy lên MCU được trình bày rõ ràng,
- có thể mở rộng cho các bài toán edge vision khác sau này.

Ngoài ra, đề tài kỳ vọng tạo ra được một bộ số liệu thực nghiệm đủ rõ ràng để bảo vệ trước giảng viên, bao gồm:

- FPS end-to-end,
- độ trễ trung bình mỗi frame,
- thời gian của từng công đoạn trong pipeline,
- ước lượng hoặc đo peak RAM sử dụng,
- so sánh giữa baseline không AI, Student-G, Student-MiniMap và StudentV1.

---

# 18. Kết luận

Dự án đề xuất một hướng tiếp cận thực dụng và phù hợp với điều kiện phần cứng nhúng: **không cố nhét một mô hình ảnh-to-ảnh lớn vào MCU, mà thiết kế lại toàn bộ pipeline theo tư duy tối ưu hệ thống**.

Điểm cốt lõi của đề tài là:

- tận dụng phần cứng có sẵn,
- phân tích đúng bottleneck thực tế,
- chọn độ phân giải hợp lý,
- dùng tiny AI model chỉ xử lý luma ở độ phân giải thấp,
- để firmware đảm nhiệm phần tăng cường full-resolution bằng phép toán nhanh,
- triển khai theo các milestone tăng dần từ baseline đến StudentV1 để giảm rủi ro demo.

Đây là một hướng có tính khả thi cao hơn nhiều so với các cách tiếp cận chỉ sao chép mô hình từ bài báo sang MCU. Nếu triển khai tốt, đề tài không chỉ có ý nghĩa học thuật mà còn có giá trị thực hành rõ rệt trong lĩnh vực thị giác máy tính trên thiết bị biên.

---

# 19. Đề xuất câu hỏi thảo luận với giảng viên

Khi mang đề tài này đi trao đổi với giảng viên, có thể tập trung vào các câu hỏi sau:

1. Phạm vi đề tài nên ưu tiên theo hướng nghiên cứu mô hình hay nghiên cứu hệ thống triển khai?
2. Có cần đặt mục tiêu so sánh định lượng với bài báo tham chiếu hay chỉ cần chứng minh tính khả thi và cải thiện thực tế?
3. Với khuôn khổ đồ án/môn học, có nên ưu tiên bản demo near real-time ổn định hơn là cố chạy mô hình phức tạp?
4. Có cần bổ sung phần đánh giá định lượng về năng lượng tiêu thụ, RAM sử dụng, thời gian suy luận hay không?
5. Có thể chấp nhận hướng “AI dự đoán tham số + firmware render nhanh” như một đóng góp kỹ thuật đủ mạnh cho đồ án không?
6. Trong khuôn khổ thời gian hiện có, giảng viên muốn ưu tiên bản demo ổn định ở mức Student-G/Student-MiniMap hay tiếp tục đẩy lên StudentV1 đầy đủ?

---

# 20. Tóm tắt ngắn gọn một đoạn để trình bày miệng

Đề tài của em hướng tới việc xây dựng một hệ thống tăng cường ảnh thiếu sáng near real-time trên STM32H750VBT6 với camera OV5640 và màn hình LCD tích hợp. Thay vì dùng một mô hình deep learning lớn sinh trực tiếp toàn bộ ảnh enhanced, em chọn hướng tối ưu theo phần cứng: dùng camera ở độ phân giải nhỏ, trích xuất luma, cho một mô hình AI siêu nhẹ dự đoán các tham số tăng sáng và một bản đồ tăng sáng thô, sau đó để firmware thực hiện phần tăng cường ảnh full-resolution bằng phép toán nhanh. Hướng này phù hợp hơn với giới hạn RAM, băng thông LCD và yêu cầu hiển thị liên tục của vi điều khiển, nên có tính khả thi và giá trị thực tiễn cao hơn cho đồ án.

---

# 21. Chốt plan triển khai cuối cùng

Để giảm rủi ro và tăng khả năng demo thành công, plan cuối cùng của đề tài được chốt theo hướng sau:

## 21.1. Plan kỹ thuật

- **Stage 0 / nền tảng:** camera -> LCD ổn định, double buffer, benchmark và soak test.
- **Stage 1 / bypass:** tích hợp đầy đủ pipeline mới nhưng cho output gần identity để kiểm tra overhead và tính ổn định.
- **Stage 2 / baseline mạnh không AI:** gain, gamma LUT, adaptive gamma, temporal EMA.
- **Stage 3 / Student-G:** AI chỉ dự đoán global controls.
- **Stage 4 / Student-MiniMap:** thêm gain map nhỏ `8x8` hoặc `12x12`.
- **Stage 5 / StudentV1:** chỉ triển khai nếu còn đủ thời gian và tài nguyên, dùng gain map `24x24`.
- **Stage 6 / deploy cuối:** chọn phiên bản có trade-off tốt nhất giữa chất lượng, FPS, RAM và độ ổn định để nhúng lên board.

## 21.2. Plan training

- Student model được train **from scratch**.
- Teacher khởi đầu là **Zero-DCE++**.
- Pseudo-label tham số được tạo bằng **offline fitting**.
- Loss dùng **hybrid supervision** gồm:
  - `L_param`,
  - `L_render`,
  - `L_reg`,
  - `L_tv_map`,
  - `L_temporal`.
- Sau khi model ổn định mới tiến tới **QAT INT8**.

## 21.3. Tiêu chí ra quyết định cuối

Phiên bản cuối cùng để báo cáo và demo không nhất thiết phải là bản phức tạp nhất, mà là bản có trade-off tốt nhất theo các tiêu chí:

- ảnh cải thiện rõ rệt trong môi trường tối,
- ít flicker,
- FPS đủ đạt mức near real-time,
- latency chấp nhận được,
- firmware ổn định trên board,
- dễ giải thích và dễ bảo vệ trước giảng viên.
