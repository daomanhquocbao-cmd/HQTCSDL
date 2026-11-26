"""Cộng đồng (luồng 6): bài viết, hướng dẫn, thông báo workshop và bình luận."""
import math
import re
import unicodedata
from typing import Dict, List, Optional

from core.platform_settings import require_enabled
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


# ------------------------------------------------- tìm kiếm tri thức (semantic-lite)
STOPWORDS = {"la", "va", "cua", "cho", "cac", "nhung", "mot", "co", "khong", "the", "nao", "nhu", "gi", "de", "voi",
             "trong", "khi", "thi", "duoc", "can", "toi", "ban", "minh", "hay", "tai", "o", "tu", "den", "se", "da"}
# Từ đồng nghĩa / liên quan trong lĩnh vực nhiếp ảnh phim: một từ trong câu hỏi kéo theo các từ cùng nghĩa
SYNONYMS = {
    "trang": ["develop", "developing", "xu ly", "rua"],
    "rua": ["trang", "develop", "xu ly"],
    "develop": ["trang", "rua", "xu ly"],
    "toi": ["darkroom", "dark"],
    "darkroom": ["phong toi", "toi"],
    "am ban": ["negative", "phim am"],
    "negative": ["am ban"],
    "hoa chat": ["chemical", "thuoc", "developer", "fixer"],
    "giay": ["paper", "in anh"],
    "den": ["trang den", "bw", "b w", "monochrome"],
    "bw": ["den trang", "trang den"],
    "scan": ["quet", "scanner"],
    "may anh": ["camera", "body"],
    "ong kinh": ["lens"],
    "bao quan": ["luu tru", "storage", "bao ve"],
    "anh sang": ["lighting", "den", "exposure", "sang"],
    "phoi sang": ["exposure", "iso", "khau do"],
}


def fold(text: str) -> str:
    text = unicodedata.normalize("NFD", (text or "").lower().replace("đ", "d"))
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def tokens(text: str) -> List[str]:
    return [t for t in re.findall(r"[a-z0-9]+", fold(text)) if t not in STOPWORDS and len(t) > 1]


def expand_query(query: str) -> Dict[str, float]:
    """Từ khóa gốc trọng số 1, từ đồng nghĩa trọng số 0.5."""
    folded = fold(query)
    weights = {t: 1.0 for t in tokens(query)}
    for key, alts in SYNONYMS.items():
        if re.search(rf"\b{re.escape(key)}\b", folded):
            for alt in alts:
                for t in tokens(alt):
                    weights.setdefault(t, 0.5)
    return weights


def rank_documents(query: str, docs: List[dict], limit: int) -> List[dict]:
    """Xếp hạng kiểu TF-IDF: từ trong tiêu đề nặng gấp 3, từ hiếm (xuất hiện ở ít bài) nặng hơn, thêm điểm khi
    cả cụm câu hỏi xuất hiện nguyên văn. Chưa phải embedding nhưng đủ cho kho bài vài nghìn mục."""
    weights = expand_query(query)
    if not weights or not docs:
        return []
    prepared = []
    df: Dict[str, int] = {t: 0 for t in weights}
    for d in docs:
        title_t, body_t = tokens(d["title"]), tokens(d.get("content") or "")
        prepared.append((d, title_t, body_t))
        present = set(title_t) | set(body_t)
        for t in weights:
            if t in present:
                df[t] += 1
    n = len(docs)
    phrase = fold(query).strip()
    scored = []
    for d, title_t, body_t in prepared:
        score = 0.0
        for t, w in weights.items():
            tf = 3 * title_t.count(t) + body_t.count(t)
            if tf:
                score += w * (1 + math.log(tf)) * (math.log((n + 1) / (df[t] + 0.5)) + 1)
        if len(phrase) > 6 and phrase in fold(d["title"] + " " + (d.get("content") or "")):
            score += 3
        if score > 0:
            scored.append((score, d))
    scored.sort(key=lambda x: (-x[0], -x[1].get("id_sort", 0)))
    return [dict(d, score=round(s, 2)) for s, d in scored[:limit]]


def snippet(content: str, weights: Dict[str, float], size: int = 180) -> str:
    text = re.sub(r"\s+", " ", content or "").strip()
    folded = fold(text)
    pos = min((folded.find(t) for t in weights if folded.find(t) >= 0), default=0)
    start = max(0, pos - 40)
    out = text[start:start + size]
    return ("…" if start else "") + out + ("…" if start + size < len(text) else "")


def search_knowledge(query: str, limit: int = 8) -> List[dict]:
    """Tìm trong bài viết cộng đồng và workshop theo ý nghĩa gần đúng (đồng nghĩa + TF-IDF)."""
    require_enabled("ai.knowledge_search.enabled", "Tìm kiếm tri thức đang được quản trị viên tạm tắt")
    with _db() as cur:
        cur.execute("SELECT TOP 800 p.post_id AS id, 'POST' AS kind, p.post_type, p.title, p.content, p.created_at, "
                    "u.full_name AS author_name FROM dbo.CommunityPosts p JOIN dbo.Users u ON u.user_id = p.author_id "
                    "ORDER BY p.created_at DESC")
        docs = _rows(cur)
        cur.execute("SELECT TOP 200 w.workshop_id AS id, 'WORKSHOP' AS kind, 'WORKSHOP' AS post_type, w.title, "
                    "w.description AS content, w.created_at, u.full_name AS author_name FROM dbo.Workshops w "
                    "JOIN dbo.Users u ON u.user_id = w.expert_id ORDER BY w.created_at DESC")
        docs += _rows(cur)
    for i, d in enumerate(docs):
        d["id_sort"] = -i
    weights = expand_query(query)
    out = rank_documents(query, docs, limit)
    for d in out:
        d["snippet"] = snippet(d.pop("content", ""), weights)
        d.pop("id_sort", None)
    return out
