"""Photo vector generation service"""
import logging, uuid
from pathlib import Path
from typing import Optional
from sqlalchemy.orm import Session
from app.models.description import ImageVector
from app.models.photo import Photo
logger = logging.getLogger(__name__)

def _to_uuid(val):
    if isinstance(val, uuid.UUID):
        return val
    return uuid.UUID(str(val))

def has_vector(db: Session, photo_id) -> bool:
    pid = _to_uuid(photo_id)
    return db.query(ImageVector).filter(ImageVector.photo_id == pid).count() > 0

def generate_photo_vector(db: Session, photo_id, image_path: str) -> Optional[ImageVector]:
    pid = _to_uuid(photo_id)
    if has_vector(db, pid):
        return None
    if not Path(image_path).exists():
        return None
    from app.services.ai_providers.embedding import get_image_embedding
    try:
        with open(image_path, "rb") as f:
            image_bytes = f.read()
    except Exception as e:
        logger.error(f"read failed: {e}")
        return None
    embedding = get_image_embedding(image_bytes)
    if embedding is None:
        return None
    try:
        vec = ImageVector(id=uuid.uuid4(), photo_id=pid, embedding=embedding)
        db.add(vec)
        db.commit()
        db.refresh(vec)
        return vec
    except Exception as e:
        db.rollback()
        logger.error(f"save failed: {e}")
        return None

def batch_generate_vectors(db: Session, batch_size: int = 10, max_count: int = None) -> dict:
    sub = db.query(ImageVector.photo_id).subquery()
    photos = db.query(Photo).filter(Photo.id.notin_(sub), Photo.is_deleted == False
        ).order_by(Photo.upload_time.desc()).limit(max_count or 10000).all()
    if not photos:
        return {"processed": 0, "succeeded": 0, "failed": 0, "skipped": 0}
    stats = {"processed": 0, "succeeded": 0, "failed": 0, "skipped": 0}
    for i, photo in enumerate(photos):
        if batch_size and i >= batch_size:
            break
        stats["processed"] += 1
        if has_vector(db, photo.id):
            stats["skipped"] += 1
            continue
        result = generate_photo_vector(db, str(photo.id), photo.file_path)
        if result:
            stats["succeeded"] += 1
        else:
            stats["failed"] += 1
        if (i + 1) % 10 == 0:
            db.commit()
    db.commit()
    return stats

__all__ = ["generate_photo_vector", "batch_generate_vectors", "has_vector"]
