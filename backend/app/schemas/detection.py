"""
对象检测 Schema
"""
import uuid
from typing import Any, Optional, List
from pydantic import BaseModel, field_validator


class DetectionResult(BaseModel):
    """单个检测结果"""
    label: str
    confidence: float
    bbox_x: float
    bbox_y: float
    bbox_w: float
    bbox_h: float
    class_id: int


class DetectionItem(BaseModel):
    """带 ID 的检测记录（数据库返回）"""
    id: str
    photo_id: str
    label: str
    confidence: float
    bbox_x: float
    bbox_y: float
    bbox_w: float
    bbox_h: float
    class_id: int

    @field_validator("id", "photo_id", mode="before")
    @classmethod
    def coerce_uuid(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        return str(v) if isinstance(v, uuid.UUID) else v

    model_config = {"from_attributes": True}


class DetectionResponse(BaseModel):
    """检测响应"""
    photo_id: str
    detections: List[DetectionItem]
    total: int
    model: str = "YOLO11 (COCO)"


class DetectionSummary(BaseModel):
    """检测摘要（去重类别统计）"""
    label: str
    count: int
    max_confidence: float


class DetectionSummaryResponse(BaseModel):
    """检测摘要响应"""
    photo_id: str
    summaries: List[DetectionSummary]
    total_objects: int
    unique_labels: int
    model: str = "YOLO11 (COCO)"
