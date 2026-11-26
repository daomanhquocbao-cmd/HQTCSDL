"""Chứng minh đặt phòng an toàn khi nhiều người đặt cùng lúc (yêu cầu phi chức năng "transaction-safe").

Chạy trong thư mục backend (cần SQL Server đã có dữ liệu):
    python scripts/concurrency_test.py --room 1 --customer 5 --threads 12
Cho N luồng gọi sp_CreateReservation vào CÙNG một phòng, CÙNG khung giờ. Đúng thiết kế thì chỉ 1 luồng thành công,
các luồng còn lại nhận lỗi 50108 (phòng đã có người đặt). Xong script tự hủy đơn thử để không để lại rác.
"""
import argparse
import os
import sys
import threading
from datetime import datetime, timedelta

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(BACKEND_DIR, ".env"))

from database import get_db_connection  # noqa: E402


def attempt(room_id, customer_id, start, end, results, barrier, idx):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        barrier.wait()                      # cả nhóm xuất phát cùng lúc
        cur.execute("EXEC dbo.sp_CreateReservation @room_id = ?, @customer_id = ?, @start_time = ?, @end_time = ?",
                    room_id, customer_id, start, end)
        row = cur.fetchone()
        conn.commit()
        results[idx] = ("OK", row[0] if row else None)
    except Exception as exc:                # noqa: BLE001
        conn.rollback()
        results[idx] = ("LỖI", str(exc).split("]")[-1].strip()[:90])
    finally:
        conn.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--room", type=int, required=True)
    ap.add_argument("--customer", type=int, required=True, help="user_id của một khách ACTIVE")
    ap.add_argument("--threads", type=int, default=10)
    ap.add_argument("--days-ahead", type=int, default=30, help="đặt vào ngày cách hôm nay bấy nhiêu ngày")
    args = ap.parse_args()

    day = (datetime.now() + timedelta(days=args.days_ahead)).replace(hour=10, minute=0, second=0, microsecond=0)
    start, end = day, day + timedelta(hours=1)
    results = [None] * args.threads
    barrier = threading.Barrier(args.threads)
    threads = [threading.Thread(target=attempt, args=(args.room, args.customer, start, end, results, barrier, i))
               for i in range(args.threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    ok = [r for r in results if r and r[0] == "OK"]
    print(f"{args.threads} luồng cùng đặt phòng {args.room} lúc {start:%d/%m/%Y %H:%M}:")
    for i, r in enumerate(results):
        print(f"  luồng {i:>2}: {r[0]:<4} {r[1]}")
    print(f"=> {len(ok)} thành công, {args.threads - len(ok)} bị từ chối.")

    conn = get_db_connection()            # dọn dẹp đơn thử
    try:
        cur = conn.cursor()
        for _, rid in ok:
            cur.execute("EXEC dbo.sp_CancelReservation @reservation_id = ?, @actor_id = ?", rid, args.customer)
        conn.commit()
    finally:
        conn.close()
    if len(ok) == 1:
        print("ĐẠT: không có đặt trùng lịch.")
        return 0
    print("KHÔNG ĐẠT: số đơn thành công khác 1 (xem lại phòng / khách / giờ mở cửa studio).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
