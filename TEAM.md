# Team

## Thông tin nhóm

- Tên nhóm (`TenNhom`, không dấu, không khoảng trắng): `11`
- Lớp: `L3B`
- Repo của bàn: `K5-L3B-DAY10-11-PoCtoPilotGate1`
- Thẻ sự cố đã bốc (S1–S8): `S2`

## Thành viên

Họ tên đầy đủ và MSSV của **mọi** thành viên; bàn 3 người thì để trống dòng 4. Vai: Kỹ sư cổng · Sản phẩm và kinh doanh · Vận hành và pháp lý (README mục 3, phút 0–15).

| STT | Họ và tên | MSSV | Vai | Trưởng nhóm |
| --: | --------- | ---- | --- | :---------: |
|   1 | Lê Anh Tuấn | 2A202603792 | Kỹ sư cổng (kiêm điều phối, gom bài) | ✔ |
|   2 |           |      |     |             |
|   3 |           |      |     |             |
|   4 |           |      |     |             |

Ghi `members` trong `submission/submission.json` theo dạng `"HoVaTen-MSSV"`, khớp bảng trên.

## Cá nhân

Mỗi thành viên tự viết một mục bên dưới (chép mẫu, đổi tiêu đề thành họ tên không dấu và MSSV, ví dụ `## NguyenVanAn-20241234`).

## LeAnhTuan-2A202603792

### Phần việc phụ trách

Trưởng nhóm, vai **Kỹ sư cổng**, kiêm điều phối và gom bài nộp.

- Câu 2.1, 2.2, 2.6–2.8 (Phiếu B mục B0, B1, B2, B7.1–B7.3), câu 3.0–3.1, 3.5–3.6 (Phiếu C mục C0–C2, C4, C7, C8).
- File: `lab10/guards.py` (cổng G1 hoàn tiền, G2 ghi lỗi hãng, G3 lọc dữ liệu gửi hãng + ghim chính sách), `lab10/monitors.py` (`instruction_injection_rate`, `merchant_payer_proposal_rate`), chạy các lệnh `eval`, `trace`, `gate`, `checkpoint`, nhận thẻ S2.
- Cùng bàn soạn và soát: `config/acceptance_criteria.json` + Phiếu A, `config/operating_gates.json`, Phiếu C mục C12 và `submission/submission.json`.

### Đóng góp cụ thể

- Ký tiêu chí và đẩy lên **trước** lần đánh giá đầu tiên; đo mốc base, dò `T-002@55` (model tin số ngày khách tự khai → hoàn sai 20.000đ, 1 lỗi oan cho VNX).
- Viết 3 cổng vòng 1 dựa trên nguồn sự thật (tracking DB, chính sách theo ngày hiệu lực, sổ cái, bảng phê duyệt), không xử lý theo mã ticket: bộ nền từ pass_rate 0,9909 lên 1,0, hoàn sai và lỗi oan về 0, không ca nào mới hỏng.
- Viết 3 ticket hiểm (`--adhoc`) cho behavioral test: khách khai sai số ngày, ticket cài lệnh "shop chịu", đơn quà tặng.
- Thẻ S2 (shop bị trừ tiền lạ): dò `S2-01`, `S2-04`, `S2-20`, `S2-44`; phát hiện cổng vòng 1 có lỗi lập trình (`ctx.log` nhận hai lần khoá `payer`) làm mốc prepared không chạy được; sửa ở `guards.py` vòng 2, giữ nguyên bản chốt và báo Lab Coach. Mốc after trên S2: trừ tiền shop 32.750.000đ → 0đ, pass_rate 0,4667 → 1,0.
- Thêm 2 chỉ số theo dõi bằng 0 trên bộ nền và sáng đèn trên S2 (0,47 · 0,40).
- **Dùng AI:** dùng Claude Code (trợ lý AI) để đọc code lab, gợi ý cách viết cổng và monitor, chạy lệnh và soạn nháp các phiếu A, B, C. Các ngưỡng tiêu chí, con số trong config và quyết định v1/v2 do bàn duyệt; tôi chịu trách nhiệm giải thích lúc demo.

### Bằng chứng

- Commit: `f117c5c` (Sign acceptance criteria) · `f704bb1` (Phiếu A) · `36ab926` (chốt cổng vòng 1, quyết định v1; hash vòng 1 `2ca48fc1`) · `b725251` (Nhận thẻ S2) · `6e54e8b` (vòng 2: sửa G1, 2 monitor, Phiếu C C0–C11).
- Lần chạy: `runs/R-base-before-20261119-221247-bde05c` (base) · `runs/R-base-prepared-20261119-221516-86dd9c` (prepared) · `runs/R-S2-before-20261119-223413-86dd9c` · `runs/R-S2-after-20261119-223433-0697e1` · `runs/R-S2-after-20261119-223453-0dc608` · `runs/R-base-after-20261119-223453-0dc608`.
- Phiếu B mục B0, B2, B7.1–B7.3; Phiếu C mục C0, C1, C2, C7, C8.

### Exit ticket


- **Một điều học được:** cổng an toàn đáng tin khi nó tính lại mọi con số từ nguồn sự thật thay vì cố nhận ra câu lệnh xấu trong chữ — nhờ vậy cổng viết ở vòng 1 chặn được cả kiểu tấn công qua `checkout_note` mà bàn chưa nghĩ tới.
- **Một điều còn chưa chắc:** làm sao bảo đảm chính cổng không tự hỏng ở nhánh chưa ai chạy qua (lỗi `ctx.log` chỉ lộ ra khi gặp thẻ S2); bộ nền 22 ticket không đủ, cần cách test phủ mọi nhánh của gate trước khi chốt.

## HoVaTen-MSSV

### Phần việc phụ trách

Vai trong bàn; câu nào của đề, mục nào của phiếu A/B/C, file nào (`lab10/guards.py`, `config/operating_gates.json`, …).

### Đóng góp cụ thể

...

### Bằng chứng

Mã commit, mã lần chạy (`runs/<mã>`), dòng trong phiếu.

### Exit ticket

Một điều học được, một điều còn chưa chắc.
