"""Endpoint bộ sưu tập ảnh: /api/collections/* (đăng nhập, mỗi người chỉ thấy bộ sưu tập của mình)."""
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel, Field

from core.security import get_current_user
from photos import service

router = APIRouter(prefix="/api/collections", tags=["Photo collections"])
User = Depends(get_current_user)


class CollectionIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class CollectionPatch(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class PhotoIn(BaseModel):
    data: str = Field(min_length=20, description="Ảnh mã hóa base64 (JPEG/PNG/WEBP, tối đa 6 MB)")
    caption: Optional[str] = Field(None, max_length=200)


class RestoreIn(BaseModel):
    mode: Literal["restore", "enhance", "negative"] = "restore"


@router.get("/shared/{token}")
def shared_collection(token: str):
    """Công khai (không cần đăng nhập): xem bộ sưu tập được chia sẻ bằng liên kết."""
    return service.shared_collection(token)


@router.post("/{collection_id}/share")
def share_collection(collection_id: int, user: dict = User):
    return service.set_sharing(user, collection_id, True)


@router.delete("/{collection_id}/share")
def unshare_collection(collection_id: int, user: dict = User):
    return service.set_sharing(user, collection_id, False)


@router.get("")
def list_collections(user: dict = User):
    return service.list_collections(user)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_collection(data: CollectionIn, user: dict = User):
    return service.create_collection(user, data.name.strip(), data.description)


@router.patch("/{collection_id}")
def update_collection(collection_id: int, data: CollectionPatch, user: dict = User):
    return service.update_collection(user, collection_id, data.name and data.name.strip(), data.description)


@router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_collection(collection_id: int, user: dict = User):
    service.delete_collection(user, collection_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{collection_id}/photos")
def list_photos(collection_id: int, user: dict = User):
    return service.list_photos(user, collection_id)


@router.post("/{collection_id}/photos", status_code=status.HTTP_201_CREATED)
def add_photo(collection_id: int, data: PhotoIn, user: dict = User):
    return service.add_photo(user, collection_id, data.data, data.caption)


@router.delete("/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_photo(photo_id: int, user: dict = User):
    service.delete_photo(user, photo_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/photos/{photo_id}/restore", status_code=status.HTTP_201_CREATED)
def restore_photo(photo_id: int, data: RestoreIn, user: dict = User):
    return service.restore_photo(user, photo_id, data.mode)
