"""Đo thời gian phản hồi các endpoint chính (yêu cầu đề tài: trung bình < 3 giây).

Chạy khi backend đang bật:  python scripts/measure_latency.py --base http://127.0.0.1:8000 --n 30
Dùng thư viện chuẩn, không cần cài thêm. In bảng trung bình / p95 / lớn nhất (ms) rồi kết luận đạt hay không.
Chạy trên dữ liệu seed lớn (database/05_seed_bulk.sql) để số liệu có ý nghĩa; ghi kết quả vào báo cáo.
"""
import argparse
import json
import statistics
import time
import urllib.request

PUBLIC = ["/api/customer/rooms?limit=20", "/api/customer/rooms/1", "/api/customer/cities", "/api/studios",
          "/api/community/posts", "/api/community/search?q=tr%C3%A1ng%20phim", "/api/ai/ask?q=phong%20toi%20duoi%20300k",
          "/api/ai/recommendations?top=5"]


def call(base, path, token=None):
    req = urllib.request.Request(base + path, headers={"Authorization": f"Bearer {token}"} if token else {})
    t = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            r.read()
            code = r.status
    except urllib.error.HTTPError as e:
        code = e.code
    return (time.perf_counter() - t) * 1000, code


def login(base, user, pw):
    req = urllib.request.Request(base + "/api/users/login", json.dumps({"username": user, "password": pw}).encode(),
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())["access_token"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--user")
    ap.add_argument("--password")
    a = ap.parse_args()
    paths = list(PUBLIC)
    token = None
    if a.user:
        token = login(a.base, a.user, a.password)
        paths += ["/api/customer/overview", "/api/customer/bookings"]
    allv, bad = [], False
    print(f"{'endpoint':55} {'avg':>8} {'p95':>8} {'max':>8}  codes")
    for p in paths:
        ms, codes = [], set()
        for _ in range(a.n):
            t, c = call(a.base, p, token)
            ms.append(t)
            codes.add(c)
        ms.sort()
        p95 = ms[int(len(ms) * 0.95) - 1] if len(ms) > 1 else ms[0]
        allv += ms
        bad |= statistics.mean(ms) >= 3000
        print(f"{p[:55]:55} {statistics.mean(ms):8.0f} {p95:8.0f} {ms[-1]:8.0f}  {sorted(codes)}")
    avg = statistics.mean(allv)
    print(f"\nTrung bình toàn bộ: {avg:.0f} ms -> {'ĐẠT' if avg < 3000 and not bad else 'KHÔNG ĐẠT'} (yêu cầu < 3000 ms)")


if __name__ == "__main__":
    main()
