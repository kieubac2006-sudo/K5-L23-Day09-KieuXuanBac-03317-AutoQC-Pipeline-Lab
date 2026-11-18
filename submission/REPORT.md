# Báo cáo Day 09 — Kiều Xuân Bắc, 03317

## 1. Kết luận trước
Pipeline kết luận **HOLD** (mã thoát `10`; xuất bản nháp vào `submission/export/clean_v1` để thử nghiệm, chưa phát hành chính thức). Từ **224** ảnh thô ban đầu, bước tiếp nhận (intake) loại **21** ảnh lỗi/trùng/rò rỉ và giữ lại **203** ảnh đưa vào dataset. Sau khi máy tự sửa xong toàn bộ lỗi quy tắc và người duyệt xử lý hết ngân sách **80/125** ảnh trong hàng đợi (kéo số lỗi bắt buộc về **0**), vẫn còn **38/203** ảnh (**18,72%**) mang cảnh báo chưa được kiểm tra, vượt ngưỡng cổng chặn **10,00%** (`0.10`).

## 2. Lỗi và phân việc

| Mã lỗi | Số ảnh/dòng | Ai sửa (máy/người) | Vì sao |
|---|---:|---|---|
| `DUP_IMAGE_EXACT` | 8 ảnh | Máy (intake/autofix) | Trùng byte MD5 100%, loại tự động an toàn không cần người xem. |
| `DUP_IMAGE_NEAR` | 3 ảnh | Máy (intake/autofix) | Gần trùng về cấu trúc hình ảnh (`phash_dist <= 8`), loại bớt tránh lệch phân phối. |
| `LEAK_TEST` | 5 ảnh | Máy (intake/autofix) | Trùng ảnh với tập `data/test`, bắt buộc loại để chống rò rỉ dữ liệu đánh giá. |
| `BAD_SIZE` | 3 ảnh | Máy (intake/autofix) | Cạnh ngắn `< 250px`, không đạt chuẩn chất lượng đầu vào tối thiểu. |
| `CORRUPT_IMAGE` | 2 ảnh | Máy (intake/autofix) | File ảnh hỏng cấu trúc, không thể giải mã bằng thư viện ảnh. |
| `BAD_CLASS_NAME` | 2 dòng (`data.yaml`) | Máy (`rename_classes`) | Sai chữ hoa/thường (`'Person'`, `'Bus'`), chuẩn hóa về danh sách lớp cố định. |
| `BAD_CLASS_ID` | 6 dòng | Máy (`drop_line`) | ID lớp ngoài phạm vi `0..3` (`-1`, `4`, `7`, `93`), không thể tự đoán đúng lớp. |
| `BAD_FORMAT` | 3 dòng | Máy (`drop_line`) | Thiếu cột hoặc chứa giá trị `nan/inf`, sai quy tắc cú pháp YOLO. |
| `BOX_ZERO` | 4 dòng | Máy (`drop_line`) | Chiều rộng hoặc chiều cao `<= 0`, bounding box vô nghĩa. |
| `DUP_BOX` | 7 dòng | Máy (`drop_line`) | Trùng lặp box cùng lớp (`IoU > 0.9`) trên cùng một ảnh, xóa dòng lặp phía sau. |
| `BOX_OUT_OF_IMAGE` | 8 dòng | Máy (`clip_box`) | Tọa độ mép vượt `[0, 1]` quá `0.002`, cắt gọn về biên ảnh an toàn. |
| `MISSING_LABEL_FILE` | 6 ảnh | Người (`needs_label`) | Ảnh không có file `.txt`; máy không được tự bịa nhãn nên đẩy lên đầu hàng đợi cho người gán. |
| `POSSIBLE_MISSING` | 53 cảnh báo | Người (hàng đợi) | Model lớn (`yolo26l`) phát hiện vật thể nhưng thiếu nhãn; cần người xác nhận ngữ nghĩa. |
| `POSSIBLE_FALSE_POS` | 29 cảnh báo | Người (hàng đợi) | Box nhãn gốc không khớp dự đoán nào của model; cần người kiểm tra nhãn thừa/nhiễu. |
| `POSSIBLE_LOOSE_BOX` | 28 cảnh báo | Người (hàng đợi) | Khớp đúng lớp nhưng `IoU < 0.5`; cần người quyết định có cần siết lại khung hay không. |
| `POSSIBLE_WRONG_CLASS` | 18 cảnh báo | Người (hàng đợi) | Nghi nhầm giữa các lớp hợp lệ (ví dụ `car` vs `truck/bus`); máy chỉ cảnh báo để người chốt. |
| `EMPTY_LABEL` | 12 ảnh | Người (hàng đợi) | File nhãn rỗng; cần người phân biệt ảnh nền thật sự hay bị bỏ sót gán nhãn. |
| `BOX_TINY` / `BOX_HUGE` | 6 / 3 dòng | Người (hàng đợi) | Box quá nhỏ (`< 12px`) hoặc quá lớn (`> 95%` diện tích), cần người kiểm tra ngữ cảnh. |
| `CLASS_RARE` | 4 cảnh báo | Hệ quả từ `BAD_CLASS_ID` | Các ID lớp lạ (`-1, 4, 7, 93`) chỉ xuất hiện 1–2 lần; tự biến mất sau khi `autofix` xóa dòng sai ID. |

* **Lý do sắp xếp `05_review_queue.csv` và hiệu quả ngân sách 80 ảnh:** Hàng đợi sắp xếp giảm dần theo điểm ưu tiên cộng dồn từ trọng số mã lỗi và độ tự tin (`conf`) của model. Nhờ vậy, các ca vừa bị máy sửa cấu trúc vừa có nhiều nghi vấn ngữ nghĩa (`img_0020` đạt `11.524` điểm) và toàn bộ **6** ảnh `NEEDS_LABEL` (`10.0` điểm) được đẩy lên đầu hàng để người duyệt xử lý trước tiên. Với ngân sách **80/125** ảnh (**64,0%** hàng đợi), người duyệt đã giải quyết dứt điểm **6/6** ảnh thiếu file nhãn, **8/12** ảnh `EMPTY_LABEL` và giảm số cảnh báo ngữ nghĩa của `second_opinion` từ **128** xuống còn **57** dòng (xử lý được **71** cảnh báo, trong đó 4 dòng lỗi hình học đã được `autofix` dọn trước và **67** cảnh báo ngữ nghĩa được người duyệt trực tiếp xử lý).

## 3. Calibration (2 ngưỡng)

| Tham số | Khởi đầu | Đã chọn | Precision / Recall (trước → sau) | Lý do (đánh đổi) |
|---|---:|---|---|---|
| `duplicates.phash_dist` | 2 | **8** | `DUP_IMAGE_NEAR`: `1.00 / 0.50` → `1.00 / 0.67` (`DUP_IMAGE_EXACT` giữ `1.00 / 1.00`) | Tăng recall bắt ảnh gần trùng mà vẫn giữ `precision = 1.00` (tránh xóa nhầm ảnh tốt); thực tế trên `raw` đã bắt thêm được `img_0223` trùng với `img_0077` ở `phash = 6`. |
| `second_opinion.conf` | 0.25 | **0.6** | `MISSING`: `0.50 / 1.00` → `0.57 / 1.00`; `WRONG_CLASS`: `0.56 / 0.83` → `0.62 / 0.83` | Giảm đáng kể báo động giả (FP) để tiết kiệm ngân sách 80 ảnh duyệt, trong khi vẫn giữ nguyên `recall = 1.00` cho lỗi thiếu nhãn và `0.83` cho nhầm lớp. |

* **Một chỗ calibration có thể đánh lừa:** Trên bảng sweep tập `calib` (39 ảnh), `phash_dist = 16` cho F1 cao nhất (`0.91`), nhưng ngay ở mức `20` thì cả `DUP_IMAGE_EXACT` và `DUP_IMAGE_NEAR` đều sụt mạnh (`recall` còn `0.33` và `0.50`) do hiện tượng gộp nhầm cụm giữa các ảnh không liên quan. Vì tập `calib` quá nhỏ và các ảnh gốc khác biệt rõ rệt, việc chạy theo F1 tối đa ở ngưỡng `16` dễ đánh lừa ta chọn ngưỡng quá lỏng, gây nguy cơ xóa oan các cặp ảnh chụp cùng bối cảnh giao thông trên tập `raw` (224 ảnh). Chọn `8` (giữa vùng ổn định `4–14`) an toàn hơn nhiều.

## 4. Cửa chặn và điều pipeline KHÔNG bắt được
* **(a) Chứng minh cửa chặn hoạt động đúng:** Khi chạy `python -m pipeline.run --budget 0 --reports work/rep_nb --export-dir work/exp_nb` (không có người duyệt), 6 ảnh `MISSING_LABEL_FILE` không được gán nhãn nên vòng 3 vẫn còn `n_errors = 6` và `112/203` ảnh mang cảnh báo (`55,17%`). Cửa chặn `Gate` lập tức trả về kết luận **REWORK**, thoát với mã **`20`** (`$LASTEXITCODE = 20`) và **không tạo thư mục xuất dữ liệu** (`Test-Path work/exp_nb` trả về `False`).
* **(b) Hai điểm mù đã biết của pipeline:**
  1. **Thiếu nhãn ở vật thể nhỏ hoặc bị che khuất một phần:** Khi kiểm tra trực quan bằng `viz_labels.py` (ví dụ trên `img_0001`, `img_0030`), một số người đi bộ/xe ở xa bị thiếu nhãn nhưng model `yolo26l` có độ tự tin thấp (`conf < 0.6`) hoặc diện tích nhỏ hơn `min_area_px = 600px` nên `second_opinion` bỏ qua, dẫn đến lọt nhãn thiếu.
  2. **Box lỏng mức độ nhẹ (`0.5 <= IoU < 0.7`) hoặc nhầm lớp mà model lớn cũng sai:** Do `iou_loose` cố định ở `0.5`, các bounding box vẽ hơi rộng quanh người/xe nhưng vẫn đạt `IoU >= 0.5` sẽ không bị gắn cờ. Tương tự, các ca nhầm lẫn khó giữa xe bán tải/xe tải (`car` vs `truck`) mà chính `yolo26l` cũng dự đoán giống nhãn sai thì `second_opinion` không thể phát hiện.

## 5. Train: raw vs clean (tùy chọn, chấm riêng)
Chưa chạy (tập trung hoàn thiện và kiểm chứng toàn bộ phần lõi pipeline QC tự động trước; sẽ bổ sung thực nghiệm train trên Google Colab sau nếu cần).

## 6. Quyết định và ghi chú AI
* **(a) Quyết định cuối & hướng xử lý để đạt `Release`:** Chấp nhận trạng thái **HOLD** hiện tại, không phát hành lô dữ liệu `clean_v1` vào huấn luyện chính thức. Để chuyển từ **HOLD** sang **RELEASE**, cần cấp thêm ngân sách người duyệt cho **38** ảnh cảnh báo còn tồn đọng ở vòng 3 (tối thiểu duyệt thêm **18** ảnh để đưa số ảnh cảnh báo chưa duyệt xuống `<= 20/203`, tức `< 10%`).
* **(b) Ghi chú sử dụng AI:**
  * *Prompt chính:* Yêu cầu phân tích từng module (`label_format`, `gate`, `autofix`, `second_opinion`) theo đúng docstring và các ca biên trong file `tests/`, sau đó đối chiếu số liệu từ `calibration_report.md` và `02_error_list_v1.txt` để lập bảng tổng hợp.
  * *Cách kiểm code AI:* Đối chiếu từng nhánh điều kiện với docstring, chạy `pytest` cho từng module độc lập rồi chạy toàn bộ 79 unit test, đồng thời chạy thử nghiệm kịch bản `--budget 0` để kiểm tra mã thoát và hành vi không xuất file.
  * *Một lần AI sai:* Khi khởi tạo khung hàm `label_format.py`, đoạn code mẫu ban đầu để lại hàm `run()` cũ phía trên và phần thân vòng lặp chỉ có chú thích khiến Python báo `IndentationError`; đã khắc phục bằng cách xóa stub cũ và hoàn thiện đầy đủ logic kiểm tra cấu trúc lẫn hình học.