# Chess AI Pro - Optimized

Game cờ vua GUI bằng Python với AI bot đánh theo nhiều mức độ khó.

## Tính năng
- GUI bằng `pygame`, giao diện menu và bàn cờ kèm thanh tác vụ bên phải.
- Luật cờ chuẩn nhờ `python-chess`: chiếu, chiếu hết, hòa, bắt tốt qua đường, phong cấp, nhập thành hợp lệ, cấm đi vào thế vua bị chiếu.
- Hỗ trợ kết thúc ván bởi:
  - checkmate
  - stalemate
  - insufficient material
  - fivefold repetition / seventy-five move rule
  - claim draw do threefold repetition / fifty-move rule
  - hết giờ
- AI bot dùng:
  - iterative deepening
  - negamax + alpha-beta pruning
  - quiescence search
  - transposition table
  - killer heuristic
  - history heuristic
  - move ordering với MVV-LVA, checks, promotions
  - evaluation gồm material, piece-square tables, mobility, pawn structure, bishop pair, king safety cơ bản
- Độ khó tăng dần theo giới hạn độ sâu và thời gian suy nghĩ.
- Chọn time control trước ván: 2 phút, 5 phút, 10 phút.
- Hiển thị quân đã ăn, lợi thế vật chất từng bên.

## Cài đặt
```bash
pip install -r requirements.txt
```

## Chạy game
```bash
python main.py
```

## Cấu trúc
- `main.py`: điểm vào chương trình
- `src/config.py`: cấu hình giao diện, màu, kích thước, preset
- `src/game_state.py`: trạng thái ván cờ, luật, timer, kết quả
- `src/evaluation.py`: hàm lượng giá
- `src/ai.py`: bot AI
- `src/gui.py`: toàn bộ phần giao diện và loop

## Ghi chú
- Khi đến lượt người chơi mà có thể yêu cầu hòa theo luật 3 lần lặp hoặc 50 nước, nút `CLAIM DRAW` sẽ hoạt động.
- AI sẽ tự phong hậu để giữ nhịp ván nhanh và mạnh hơn.
