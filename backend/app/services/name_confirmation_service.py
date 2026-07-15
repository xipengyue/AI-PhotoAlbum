"""
身份名称确认管理服务

管理"首次提及称呼 → 用户选择人脸"的待确认会话。
使用内存字典存储 pending 状态，生产环境建议改用 Redis。
"""

import json
import time
import uuid as _uuid
import logging
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.face import Face, FaceIdentity

logger = logging.getLogger(__name__)

# 内存存储（生产环境应替换为 Redis）
_pending_store: dict = {}
DEFAULT_PENDING_TTL = 600  # 10分钟


def _store_setex(key: str, ttl: int, value: str):
    _pending_store[key] = {"value": value, "expires_at": time.time() + ttl}


def _store_get(key: str) -> Optional[str]:
    entry = _pending_store.get(key)
    if not entry:
        return None
    if time.time() > entry["expires_at"]:
        del _pending_store[key]
        return None
    return entry["value"]


def _store_delete(key: str):
    _pending_store.pop(key, None)


def _pending_key(session_id: str, query: str) -> str:
    return f"name_confirm:{session_id}:{hash(query)}"


def create_pending(
    session_id: str,
    query: str,
    candidates: List[dict],
    ttl: int = DEFAULT_PENDING_TTL,
) -> str:
    """
    创建一个待确认会话

    Args:
        session_id: 用户会话标识（如 JWT sub）
        query: 用户原始查询
        candidates: 候选聚类列表
        ttl: 过期时间（秒）

    Returns:
        pending_key
    """
    key = _pending_key(session_id, query)
    payload = {
        "query": query,
        "candidates": candidates,
        "created_at": time.time(),
        "status": "pending",
    }
    _store_setex(key, ttl, json.dumps(payload, ensure_ascii=False))
    logger.info(f"创建待确认会话: {key}, 候选项: {len(candidates)} 个")
    return key


def get_pending(session_id: str, query: str) -> Optional[dict]:
    key = _pending_key(session_id, query)
    raw = _store_get(key)
    if not raw:
        return None
    return json.loads(raw)


def confirm_name(
    db: Session,
    session_id: str,
    query: str,
    cluster_id: str,
    name: str,
    aliases: Optional[List[str]] = None,
) -> bool:
    """
    确认并绑定称呼到指定聚类

    流程：
      1. 检查 pending 会话是否存在
      2. 更新对应 FaceIdentity 的 identity_name
      3. 清除 pending 会话

    Args:
        db: 数据库会话
        session_id: 用户会话标识
        query: 用户原始查询
        cluster_id: 用户选中的聚类 ID
        name: 确定的称呼
        aliases: 可替换称呼列表

    Returns:
        是否成功
    """
    cid = _uuid.UUID(cluster_id) if not isinstance(cluster_id, _uuid.UUID) else cluster_id

    pending = get_pending(session_id, query)
    if not pending:
        logger.warning(f"未找到待确认会话: session={session_id}, query={query}")
        return False

    _store_delete(_pending_key(session_id, query))

    identity = db.query(FaceIdentity).filter(FaceIdentity.id == cid).first()
    if not identity:
        logger.error(f"聚类不存在: {cluster_id}")
        return False

    identity.identity_name = name

    # 更新该聚类下所有 Face 记录
    faces = db.query(Face).filter(Face.face_identity_id == cid).all()
    for face in faces:
        face.face_name = name
        if aliases:
            face.face_aliases = aliases

    db.commit()
    logger.info(f"身份确认成功: cluster={cluster_id}, name={name}")
    return True


def clear_pending(session_id: str, query: str):
    _store_delete(_pending_key(session_id, query))


def find_clusters_by_name(db: Session, owner_id, name: str) -> List[dict]:
    """
    根据称呼查找已命名的聚类

    Args:
        db: 数据库会话
        owner_id: 用户 ID
        name: 称呼

    Returns:
        [{"cluster_id": str, "identity_name": str, "face_count": int, "photo_ids": [str]}, ...]
    """
    from app.services.face_cluster_service import get_cluster_face_photos

    owner_uuid = _uuid.UUID(str(owner_id)) if not isinstance(owner_id, _uuid.UUID) else owner_id
    identities = (
        db.query(FaceIdentity)
        .filter(
            FaceIdentity.owner_id == owner_uuid,
            FaceIdentity.identity_name.isnot(None),
            FaceIdentity.identity_name == name,
        )
        .all()
    )

    # 精确匹配无结果时尝试模糊匹配
    if not identities:
        identities = (
            db.query(FaceIdentity)
            .filter(
                FaceIdentity.owner_id == owner_uuid,
                FaceIdentity.identity_name.isnot(None),
                FaceIdentity.identity_name.like(f"%{name}%"),
            )
            .all()
        )

    results = []
    for identity in identities:
        photo_ids = get_cluster_face_photos(db, identity.id)
        results.append({
            "cluster_id": str(identity.id),
            "identity_name": identity.identity_name,
            "face_count": len(photo_ids),
            "photo_ids": photo_ids,
        })

    return results


__all__ = [
    "create_pending",
    "get_pending",
    "confirm_name",
    "clear_pending",
    "find_clusters_by_name",
]
