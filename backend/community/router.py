"""Endpoint cộng đồng: /api/community/*. Đọc công khai; đăng bài / bình luận cần đăng nhập."""
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query, Response, status
from pydantic import BaseModel, Field

from community import service
from core.security import get_current_user

router = APIRouter(prefix="/api/community", tags=["Community"])
PostType = Literal["ARTICLE", "TUTORIAL", "EQUIPMENT_REVIEW", "DISCUSSION", "WORKSHOP_ANNOUNCEMENT"]


class PostIn(BaseModel):
    post_type: PostType = "DISCUSSION"
    title: str = Field(min_length=3, max_length=200)
    content: str = Field(min_length=1, max_length=20000)
    image_url: Optional[str] = Field(default=None, max_length=500)


class CommentIn(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


@router.get("/posts")
def posts(post_type: Optional[PostType] = Query(None), q: Optional[str] = Query(None, max_length=100),
          limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0)):
    return service.list_posts(post_type, q, limit, offset)


@router.get("/posts/{post_id}")
def post(post_id: int):
    return service.get_post(post_id)


@router.post("/posts", status_code=status.HTTP_201_CREATED)
def create_post(data: PostIn, user: dict = Depends(get_current_user)):
    return service.create_post(user, data)


@router.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(post_id: int, user: dict = Depends(get_current_user)):
    service.delete_post(user, post_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/posts/{post_id}/comments", status_code=status.HTTP_201_CREATED)
def comment(post_id: int, data: CommentIn, user: dict = Depends(get_current_user)):
    return service.add_comment(user, post_id, data.content)


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(comment_id: int, user: dict = Depends(get_current_user)):
    service.delete_comment(user, comment_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
