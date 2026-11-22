"""Cộng đồng (luồng 6): bài viết, hướng dẫn, thông báo workshop và bình luận."""
from typing import List, Optional

from provider.service import _db, _err, _new_id, _one, _rows

STAFF_ONLY_TYPES = {"WORKSHOP_ANNOUNCEMENT", "TUTORIAL", "ARTICLE"}
STAFF_ROLES = {"EXPERT", "PROVIDER", "ADMIN"}

POST_SELECT = ("SELECT p.post_id, p.author_id, u.full_name AS author_name, u.role AS author_role, p.post_type, "
               "p.title, p.content, p.image_url, p.created_at, "
               "(SELECT COUNT(*) FROM dbo.PostComments c WHERE c.post_id = p.post_id) AS comment_count "
               "FROM dbo.CommunityPosts p JOIN dbo.Users u ON u.user_id = p.author_id WHERE 1 = 1")


def list_posts(post_type: Optional[str], q: Optional[str], limit: int, offset: int) -> List[dict]:
    sql, params = POST_SELECT, []
    if post_type:
        sql += " AND p.post_type = ?"
        params.append(post_type)
    if q:
        sql += " AND (p.title LIKE ? OR p.content LIKE ?)"
        params += [f"%{q}%", f"%{q}%"]
    sql += " ORDER BY p.created_at DESC, p.post_id DESC OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
    with _db() as cur:
        cur.execute(sql, *params, offset, limit)
        return _rows(cur)


def get_post(post_id: int) -> dict:
    with _db() as cur:
        cur.execute(POST_SELECT + " AND p.post_id = ?", post_id)
        post = _one(cur)
        if post is None:
            raise _err(404, "Không tìm thấy bài viết")
        cur.execute("SELECT c.comment_id, c.user_id, u.full_name AS user_name, u.role AS user_role, c.content, "
                    "c.created_at FROM dbo.PostComments c JOIN dbo.Users u ON u.user_id = c.user_id "
                    "WHERE c.post_id = ? ORDER BY c.created_at, c.comment_id", post_id)
        post["comments"] = _rows(cur)
        return post


def create_post(user: dict, data) -> dict:
    role = str(user["role"]).upper()
    if data.post_type in STAFF_ONLY_TYPES and role not in STAFF_ROLES:
        raise _err(403, "Bạn không có quyền đăng loại bài này (chỉ chuyên gia / nhà cung cấp / quản trị)")
    with _db() as cur:
        cur.execute("INSERT INTO dbo.CommunityPosts (author_id, post_type, title, content, image_url) "
                    "VALUES (?, ?, ?, ?, ?)", user["user_id"], data.post_type, data.title, data.content, data.image_url)
        post_id = _new_id(cur)
        cur.execute(POST_SELECT + " AND p.post_id = ?", post_id)
        return _one(cur)


def add_comment(user: dict, post_id: int, content: str) -> dict:
    with _db() as cur:
        cur.execute("SELECT 1 FROM dbo.CommunityPosts WHERE post_id = ?", post_id)
        if cur.fetchone() is None:
            raise _err(404, "Không tìm thấy bài viết")
        cur.execute("INSERT INTO dbo.PostComments (post_id, user_id, content) VALUES (?, ?, ?)",
                    post_id, user["user_id"], content)
        cid = _new_id(cur)
        cur.execute("SELECT c.comment_id, c.user_id, u.full_name AS user_name, u.role AS user_role, c.content, "
                    "c.created_at FROM dbo.PostComments c JOIN dbo.Users u ON u.user_id = c.user_id "
                    "WHERE c.comment_id = ?", cid)
        return _one(cur)


def delete_post(user: dict, post_id: int) -> None:
    with _db() as cur:
        cur.execute("SELECT author_id FROM dbo.CommunityPosts WHERE post_id = ?", post_id)
        row = cur.fetchone()
        if row is None:
            raise _err(404, "Không tìm thấy bài viết")
        if row.author_id != user["user_id"] and str(user["role"]).upper() != "ADMIN":
            raise _err(403, "Bạn không có quyền xóa bài này")
        cur.execute("DELETE FROM dbo.CommunityPosts WHERE post_id = ?", post_id)   # bình luận xóa theo (CASCADE)


def delete_comment(user: dict, comment_id: int) -> None:
    with _db() as cur:
        cur.execute("SELECT user_id FROM dbo.PostComments WHERE comment_id = ?", comment_id)
        row = cur.fetchone()
        if row is None:
            raise _err(404, "Không tìm thấy bình luận")
        if row.user_id != user["user_id"] and str(user["role"]).upper() != "ADMIN":
            raise _err(403, "Bạn không có quyền xóa bình luận này")
        cur.execute("DELETE FROM dbo.PostComments WHERE comment_id = ?", comment_id)
