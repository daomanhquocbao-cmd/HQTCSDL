"""Bộ sưu tập ảnh số của khách + phục hồi / tăng chất lượng ảnh (bảng PhotoCollections, Photos - file 08).

File ảnh lưu trên đĩa ở thư mục UPLOAD_DIR (mặc định backend/uploads), CSDL chỉ giữ đường dẫn tương đối.
Phục hồi ảnh dùng xử lý ảnh cổ điển của Pillow (cân bằng tương phản, khử nhiễu hạt/bụi, làm nét), KHÔNG phải mô hình
học sâu; chỗ gọi `restore_image` là điểm để thay bằng mô hình thật (Real-ESRGAN, API ảnh...) về sau.
"""
import base64
import binascii
import io
import os
import secrets
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import List, Optional

import pyodbc
from fastapi import HTTPException

from provider.service import _db, _err, _new_id, _one, _rows

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", Path(__file__).resolve().parent.parent / "uploads"))
MAX_BYTES = 6 * 1024 * 1024
MAX_PIXELS = 40_000_000
ALLOWED = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}
MODES = {"restore": "phục hồi ảnh cũ", "enhance": "tăng chất lượng ảnh scan", "negative": "đảo âm bản sang dương bản"}
MISSING = "Chưa có bảng ảnh trong CSDL. Hãy chạy database/08_collections_settings_ledger.sql rồi thử lại."


@contextmanager
def _db08():
    try:
        with _db() as cur:
            yield cur
    except HTTPException as exc:
        low = str(exc.detail).lower()
        if "invalid object name" in low or "invalid column name" in low:
            raise HTTPException(status_code=503, detail=MISSING) from exc
        raise


def _pil():
    try:
        from PIL import Image, ImageEnhance, ImageFilter, ImageOps
    except ImportError as exc:
        raise HTTPException(status_code=503, detail="Chưa cài Pillow. Chạy: pip install Pillow") from exc
    return Image, ImageEnhance, ImageFilter, ImageOps


def decode_image(data: str):
    """Chuỗi base64 (có thể kèm tiền tố data:image/...;base64,) -> (bytes, đối tượng ảnh, định dạng)."""
    Image = _pil()[0]
    if "," in data[:100] and data.lstrip().startswith("data:"):
        data = data.split(",", 1)[1]
    try:
        raw = base64.b64decode(data, validate=True)
    except (binascii.Error, ValueError):
        raise _err(400, "Dữ liệu ảnh không phải base64 hợp lệ")
    if not raw or len(raw) > MAX_BYTES:
        raise _err(413 if raw else 400, f"Ảnh phải nhỏ hơn {MAX_BYTES // (1024 * 1024)} MB")
    try:
        img = Image.open(io.BytesIO(raw))
        fmt = img.format
        img.load()
    except Exception:
        raise _err(400, "File không phải ảnh hợp lệ")
    if fmt not in ALLOWED:
        raise _err(400, "Chỉ nhận ảnh JPEG, PNG hoặc WEBP")
    if img.width * img.height > MAX_PIXELS:
        raise _err(400, "Ảnh quá lớn (tối đa khoảng 40 megapixel)")
    return raw, img, fmt


def restore_image(img, mode: str):
    """Xử lý ảnh theo chế độ; trả về ảnh RGB mới."""
    Image, ImageEnhance, ImageFilter, ImageOps = _pil()
    img = ImageOps.exif_transpose(img).convert("RGB")
    if mode == "restore":
        img = ImageOps.autocontrast(img, cutoff=1)                    # kéo giãn tương phản, bù ảnh bạc màu
        img = img.filter(ImageFilter.MedianFilter(3))                  # khử bụi / xước nhỏ
        img = ImageEnhance.Color(img).enhance(1.12)                    # lấy lại độ đậm màu
        img = img.filter(ImageFilter.UnsharpMask(radius=1.6, percent=110, threshold=3))
    elif mode == "enhance":
        longest = max(img.size)
        if longest < 2400:                                              # scan nhỏ thì phóng 2x (tối đa 4000 px)
            scale = min(2.0, 4000 / longest)
            img = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)
        img = ImageOps.autocontrast(img, cutoff=0.5)
        img = ImageEnhance.Contrast(img).enhance(1.08)
        img = img.filter(ImageFilter.UnsharpMask(radius=2.0, percent=140, threshold=2))
    elif mode == "negative":
        img = ImageOps.autocontrast(ImageOps.invert(img), cutoff=0.5)
    else:
        raise _err(400, "Chế độ không hợp lệ")
    return img


def _save(owner_id: int, img, fmt: str) -> tuple:
    ext = ALLOWED[fmt]
    rel = f"{owner_id}/{uuid.uuid4().hex}.{ext}"
    path = UPLOAD_DIR / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO()
    kwargs = {"quality": 92} if fmt in ("JPEG", "WEBP") else {}
    img.save(buf, format=fmt, **kwargs)
    path.write_bytes(buf.getvalue())
    return rel, len(buf.getvalue())


def _remove_file(rel: str) -> None:
    try:
        (UPLOAD_DIR / rel).resolve().relative_to(UPLOAD_DIR.resolve())     # chặn đường dẫn thoát khỏi uploads/
        (UPLOAD_DIR / rel).unlink(missing_ok=True)
    except (ValueError, OSError):
        pass


def _photo_out(row: dict) -> dict:
    row["url"] = "/uploads/" + row["file_path"]
    return row


# ------------------------------------------------------------------ chia sẻ bằng liên kết
def set_sharing(user: dict, collection_id: int, enable: bool) -> dict:
    """Bật chia sẻ (sinh token ngẫu nhiên, giữ token cũ nếu đã bật) hoặc thu hồi (xóa token)."""
    with _db08() as cur:
        _own_collection(cur, user, collection_id)
        if enable:
            cur.execute("SELECT share_token FROM dbo.PhotoCollections WHERE collection_id = ?", collection_id)
            token = cur.fetchone().share_token or secrets.token_urlsafe(16)[:22]
            cur.execute("UPDATE dbo.PhotoCollections SET share_token = ? WHERE collection_id = ?", token, collection_id)
        else:
            token = None
            cur.execute("UPDATE dbo.PhotoCollections SET share_token = NULL WHERE collection_id = ?", collection_id)
    return {"collection_id": collection_id, "shared": enable, "share_token": token,
            "share_path": f"/api/collections/shared/{token}" if token else None}


def shared_collection(token: str) -> dict:
    """Công khai, chỉ đọc: tên bộ sưu tập, chủ sở hữu, danh sách ảnh."""
    if not token or len(token) > 40:
        raise _err(404, "Liên kết không tồn tại hoặc đã bị thu hồi")
    with _db08() as cur:
        cur.execute("SELECT c.collection_id, c.name, c.description, u.full_name AS owner_name "
                    "FROM dbo.PhotoCollections c JOIN dbo.Users u ON u.user_id = c.owner_id "
                    "WHERE c.share_token = ?", token)
        col = _one(cur)
        if col is None:
            raise _err(404, "Liên kết không tồn tại hoặc đã bị thu hồi")
        cur.execute(PHOTO_SELECT + " ORDER BY created_at DESC, photo_id DESC", col["collection_id"])
        col["photos"] = [_photo_out(r) for r in _rows(cur)]
    col.pop("collection_id")
    return col


# ------------------------------------------------------------------ bộ sưu tập
COL_SELECT = ("SELECT c.collection_id, c.name, c.description, c.created_at, c.share_token, "
              "(SELECT COUNT(*) FROM dbo.Photos p WHERE p.collection_id = c.collection_id) AS photo_count, "
              "(SELECT TOP 1 p.file_path FROM dbo.Photos p WHERE p.collection_id = c.collection_id "
              " ORDER BY p.created_at DESC, p.photo_id DESC) AS cover_path "
              "FROM dbo.PhotoCollections c WHERE c.owner_id = ?")


def _cover(row: dict) -> dict:
    path = row.pop("cover_path", None)
    row["cover_url"] = "/uploads/" + path if path else None
    return row


def list_collections(user: dict) -> List[dict]:
    with _db08() as cur:
        cur.execute(COL_SELECT + " ORDER BY c.created_at DESC, c.collection_id DESC", user["user_id"])
        return [_cover(r) for r in _rows(cur)]


def create_collection(user: dict, name: str, description: Optional[str]) -> dict:
    with _db08() as cur:
        cur.execute("SELECT 1 FROM dbo.PhotoCollections WHERE owner_id = ? AND name = ?", user["user_id"], name)
        if cur.fetchone():
            raise _err(409, "Bạn đã có bộ sưu tập trùng tên này")
        cur.execute("INSERT INTO dbo.PhotoCollections (owner_id, name, description) VALUES (?, ?, ?)",
                    user["user_id"], name, description)
        cid = _new_id(cur)
        cur.execute(COL_SELECT + " AND c.collection_id = ?", user["user_id"], cid)
        return _cover(_one(cur))


def _own_collection(cur, user: dict, collection_id: int) -> None:
    cur.execute("SELECT owner_id FROM dbo.PhotoCollections WHERE collection_id = ?", collection_id)
    row = cur.fetchone()
    if row is None or row.owner_id != user["user_id"]:
        raise _err(404, "Không tìm thấy bộ sưu tập")


def update_collection(user: dict, collection_id: int, name: Optional[str], description: Optional[str]) -> dict:
    with _db08() as cur:
        _own_collection(cur, user, collection_id)
        if name is not None:
            cur.execute("SELECT 1 FROM dbo.PhotoCollections WHERE owner_id = ? AND name = ? AND collection_id <> ?",
                        user["user_id"], name, collection_id)
            if cur.fetchone():
                raise _err(409, "Bạn đã có bộ sưu tập trùng tên này")
            cur.execute("UPDATE dbo.PhotoCollections SET name = ? WHERE collection_id = ?", name, collection_id)
        if description is not None:
            cur.execute("UPDATE dbo.PhotoCollections SET description = ? WHERE collection_id = ?",
                        description, collection_id)
        cur.execute(COL_SELECT + " AND c.collection_id = ?", user["user_id"], collection_id)
        return _cover(_one(cur))


def delete_collection(user: dict, collection_id: int) -> None:
    with _db08() as cur:
        _own_collection(cur, user, collection_id)
        cur.execute("SELECT file_path FROM dbo.Photos WHERE collection_id = ?", collection_id)
        paths = [r[0] for r in cur.fetchall()]
        cur.execute("DELETE FROM dbo.PhotoCollections WHERE collection_id = ?", collection_id)   # ảnh xóa theo (CASCADE)
    for rel in paths:
        _remove_file(rel)


# ------------------------------------------------------------------------ ảnh
PHOTO_SELECT = ("SELECT photo_id, collection_id, file_path, caption, kind, size_bytes, created_at "
                "FROM dbo.Photos WHERE collection_id = ?")


def list_photos(user: dict, collection_id: int) -> List[dict]:
    with _db08() as cur:
        _own_collection(cur, user, collection_id)
        cur.execute(PHOTO_SELECT + " ORDER BY created_at DESC, photo_id DESC", collection_id)
        return [_photo_out(r) for r in _rows(cur)]


def add_photo(user: dict, collection_id: int, data: str, caption: Optional[str]) -> dict:
    raw, img, fmt = decode_image(data)
    with _db08() as cur:
        _own_collection(cur, user, collection_id)
        rel = f"{user['user_id']}/{uuid.uuid4().hex}.{ALLOWED[fmt]}"
        path = UPLOAD_DIR / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)                       # lưu nguyên bản ảnh khách tải lên
        try:
            cur.execute("INSERT INTO dbo.Photos (collection_id, file_path, caption, kind, size_bytes) "
                        "VALUES (?, ?, ?, 'ORIGINAL', ?)", collection_id, rel, caption, len(raw))
            pid = _new_id(cur)
        except Exception:
            _remove_file(rel)
            raise
        cur.execute(PHOTO_SELECT.replace("WHERE collection_id = ?", "WHERE photo_id = ?"), pid)
        return _photo_out(_one(cur))


def _own_photo(cur, user: dict, photo_id: int) -> dict:
    cur.execute("SELECT p.photo_id, p.collection_id, p.file_path, p.caption, p.kind FROM dbo.Photos p "
                "JOIN dbo.PhotoCollections c ON c.collection_id = p.collection_id "
                "WHERE p.photo_id = ? AND c.owner_id = ?", photo_id, user["user_id"])
    row = _one(cur)
    if row is None:
        raise _err(404, "Không tìm thấy ảnh")
    return row


def delete_photo(user: dict, photo_id: int) -> None:
    with _db08() as cur:
        photo = _own_photo(cur, user, photo_id)
        cur.execute("DELETE FROM dbo.Photos WHERE photo_id = ?", photo_id)
    _remove_file(photo["file_path"])


def restore_photo(user: dict, photo_id: int, mode: str) -> dict:
    """Đọc ảnh gốc -> xử lý -> lưu thành ảnh mới (kind RESTORED) trong cùng bộ sưu tập; ảnh gốc giữ nguyên."""
    if mode not in MODES:
        raise _err(400, "Chế độ phải là restore, enhance hoặc negative")
    from core.platform_settings import require_enabled
    require_enabled("ai.assistant.enabled", "Dịch vụ AI đang được quản trị viên tạm tắt")
    Image = _pil()[0]
    with _db08() as cur:
        photo = _own_photo(cur, user, photo_id)
        try:
            with Image.open(UPLOAD_DIR / photo["file_path"]) as src:
                fmt = src.format if src.format in ALLOWED else "JPEG"
                out = restore_image(src, mode)
        except FileNotFoundError:
            raise _err(404, "File ảnh không còn trên máy chủ")
        if fmt == "PNG" and mode != "negative":
            fmt = "JPEG"
        rel, size = _save(user["user_id"], out, fmt)
        caption = ((photo["caption"] or "Ảnh") + f" ({MODES[mode]})")[:200]
        try:
            cur.execute("INSERT INTO dbo.Photos (collection_id, file_path, caption, kind, size_bytes) "
                        "VALUES (?, ?, ?, 'RESTORED', ?)", photo["collection_id"], rel, caption, size)
            pid = _new_id(cur)
        except pyodbc.Error:
            _remove_file(rel)
            raise
        cur.execute(PHOTO_SELECT.replace("WHERE collection_id = ?", "WHERE photo_id = ?"), pid)
        return _photo_out(_one(cur))
