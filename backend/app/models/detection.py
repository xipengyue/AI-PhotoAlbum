"""
对象检测结果模型
存储 YOLO 模型对照片的检测结果（标注框 + 类别 + 置信度）
"""
import uuid
from sqlalchemy import (
    Column, String, Float, ForeignKey, Integer, Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database.session import Base


class ObjectDetection(Base):
    """YOLO 目标检测结果"""
    __tablename__ = "object_detections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    photo_id = Column(UUID(as_uuid=True), ForeignKey("photos.id"), nullable=False, index=True)
    label = Column(String(100), nullable=False, index=True, comment="检测到的物体类别（如 person, car, dog）")
    confidence = Column(Float, nullable=False, comment="置信度 0-1")
    bbox_x = Column(Float, nullable=False, comment="边界框中心 X（归一化 0-1）")
    bbox_y = Column(Float, nullable=False, comment="边界框中心 Y（归一化 0-1）")
    bbox_w = Column(Float, nullable=False, comment="边界框宽度（归一化 0-1）")
    bbox_h = Column(Float, nullable=False, comment="边界框高度（归一化 0-1）")
    class_id = Column(Integer, nullable=False, comment="COCO 类别 ID")

    photo = relationship("Photo", backref="detections")

    __table_args__ = (
        Index("idx_detection_photo_label", "photo_id", "label"),
    )
