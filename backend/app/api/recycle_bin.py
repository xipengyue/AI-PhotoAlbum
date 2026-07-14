"""
回收站 API 路由
独立的路由文件，避免与 /{photo_id} 泛匹配冲突
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.api.deps import get_required_user
from app.models.user import User
from app.crud.photo import (
    get_photo_by_id_any,
    permanent_delete_photo,
    get_deleted_photos,
)
from app.schemas.photo import PhotoResponse, PhotoListResponse

router = APIRouter(prefix="/api/photos/recycle-bin", tags=["回收站"])


@router.get("/list", response_model=PhotoListResponse)
def list_recycle_bin(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """获取回收站中的照片列表"""
    photos = get_deleted_photos(db, str(current_user.id))
    items = [PhotoResponse.model_validate(p) for p in photos]
    return PhotoListResponse(
        total=len(items),
        page=1,
        page_size=len(items),
        items=items,
    )


@router.post("/empty")
def empty_recycle_bin(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """清空回收站"""
    photos = get_deleted_photos(db, str(current_user.id))
    count = 0
    for photo in photos:
        permanent_delete_photo(db, photo)
        count += 1
    return {"message": f"已清空回收站，共删除 {count} 张照片", "count": count}


@router.delete("/{photo_id}/permanent")
def permanent_delete(
    photo_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """永久删除单张照片"""
    photo = get_photo_by_id_any(db, photo_id)
    if not photo:
        raise HTTPException(404, "照片不存在")
    if str(photo.owner_id) != str(current_user.id):
        raise HTTPException(403, "无权操作此照片")
    if not photo.is_deleted:
        raise HTTPException(400, "请先移入回收站再彻底删除")
    permanent_delete_photo(db, photo)
    return {"message": "已永久删除", "photo_id": photo_id}
