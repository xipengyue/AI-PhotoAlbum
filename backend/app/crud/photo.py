"""
照片 CRUD 操作
"""
import hashlib
import uuid
from datetime import datetime
from typing import Optional, Tuple, List
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc
from app.models.photo import Photo, PhotoMetadata, FileType
from app.models.user import User


def _to_uuid(val) -> uuid.UUID:
    """将字符串或 UUID 转为 UUID 对象"""
    if isinstance(val, uuid.UUID):
        return val
    return uuid.UUID(str(val))


def _md5_from_bytes(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def create_photo(
    db: Session,
    owner_id,
    filename: str,
    original_name: str,
    file_path: str,
    file_size: int,
    width: int,
    height: int,
    photo_time: Optional[datetime] = None,
    md5: Optional[str] = None,
) -> Photo:
    """
    创建照片记录
    """
    photo = Photo(
        id=uuid.uuid4(),
        owner_id=_to_uuid(owner_id),
        filename=filename,
        original_name=original_name,
        file_path=file_path,
        file_size=file_size,
        width=width,
        height=height,
        photo_time=photo_time or datetime.now(),
        upload_time=datetime.now(),
        file_type=FileType.image,
        md5=md5,
        processed_tasks={},
    )
    db.add(photo)
    db.commit()
    db.refresh(photo)
    return photo


def get_photo_by_id(db: Session, photo_id) -> Optional[Photo]:
    """根据 ID 获取照片（不含已删除）"""
    return db.query(Photo).filter(
        Photo.id == _to_uuid(photo_id),
        Photo.is_deleted == False,
    ).first()


def get_photo_by_id_any(db: Session, photo_id) -> Optional[Photo]:
    """根据 ID 获取照片（含已删除）"""
    return db.query(Photo).filter(Photo.id == _to_uuid(photo_id)).first()


def get_photos_by_owner(
    db: Session,
    owner_id,
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "photo_time",
    sort_order: str = "desc",
) -> Tuple[List[Photo], int]:
    """
    获取用户照片列表（分页）

    Returns:
        (photo_list, total_count)
    """
    owner_uuid = _to_uuid(owner_id)
    query = db.query(Photo).filter(
        Photo.owner_id == owner_uuid,
        Photo.is_deleted == False,
    )

    # 排序
    sort_column = getattr(Photo, sort_by, Photo.photo_time)
    if sort_order == "asc":
        query = query.order_by(asc(sort_column))
    else:
        query = query.order_by(desc(sort_column))

    total = query.count()
    photos = query.offset((page - 1) * page_size).limit(page_size).all()

    return photos, total


def soft_delete_photo(db: Session, photo: Photo) -> Photo:
    """软删除照片"""
    photo.is_deleted = True
    photo.deleted_at = datetime.now()
    db.commit()
    db.refresh(photo)
    return photo


def restore_photo(db: Session, photo: Photo) -> Photo:
    """恢复已删除的照片"""
    photo.is_deleted = False
    photo.deleted_at = None
    db.commit()
    db.refresh(photo)
    return photo


def permanent_delete_photo(db: Session, photo: Photo) -> None:
    """永久删除照片（数据库记录 + 文件）"""
    import os
    from pathlib import Path

    # 删除文件和缩略图
    file_path = Path(photo.file_path)
    if file_path.exists():
        file_path.unlink()

    thumb_dir = Path("./data/thumbnails")
    thumb_path = thumb_dir / f"{photo.filename}_thumb.jpg"
    if thumb_path.exists():
        thumb_path.unlink()

    # 删除数据库记录（级联删除 metadata 等关联记录）
    db.delete(photo)
    db.commit()


def cleanup_expired_photos(db: Session, retention_days: int = 7) -> int:
    """
    清理超过保留天数的已删除照片

    Args:
        db: 数据库会话
        retention_days: 回收站保留天数，默认 7 天

    Returns:
        清理的照片数量
    """
    from datetime import timedelta

    cutoff = datetime.now() - timedelta(days=retention_days)
    expired = db.query(Photo).filter(
        Photo.is_deleted == True,
        Photo.deleted_at < cutoff,
    ).all()

    count = 0
    for photo in expired:
        permanent_delete_photo(db, photo)
        count += 1

    return count


def get_deleted_photos(db: Session, owner_id) -> List[Photo]:
    """获取回收站中的照片"""
    return db.query(Photo).filter(
        Photo.owner_id == _to_uuid(owner_id),
        Photo.is_deleted == True,
    ).order_by(desc(Photo.deleted_at)).all()


def get_photo_by_md5(db: Session, owner_id, md5: str) -> Optional[Photo]:
    """根据 MD5 查找用户已有的照片（去重）"""
    return db.query(Photo).filter(
        Photo.owner_id == _to_uuid(owner_id),
        Photo.md5 == md5,
    ).first()


def create_metadata(
    db: Session,
    photo_id,
    metadata_dict: dict,
) -> PhotoMetadata:
    """
    创建或更新照片 EXIF 元数据记录

    Args:
        db: 数据库会话
        photo_id: 照片 ID
        metadata_dict: EXIF 提取结果字典
    """
    pid = _to_uuid(photo_id)
    existing = db.query(PhotoMetadata).filter(
        PhotoMetadata.photo_id == pid
    ).first()

    if existing:
        for key, value in metadata_dict.items():
            if hasattr(existing, key) and value is not None:
                setattr(existing, key, value)
        db.commit()
        db.refresh(existing)
        return existing

    meta = PhotoMetadata(
        id=uuid.uuid4(),
        photo_id=pid,
        **{k: v for k, v in metadata_dict.items() if v is not None},
    )
    db.add(meta)
    db.commit()
    db.refresh(meta)
    return meta


def get_metadata(db: Session, photo_id) -> Optional[PhotoMetadata]:
    """获取照片的 EXIF 元数据"""
    return db.query(PhotoMetadata).filter(
        PhotoMetadata.photo_id == _to_uuid(photo_id)
    ).first()
