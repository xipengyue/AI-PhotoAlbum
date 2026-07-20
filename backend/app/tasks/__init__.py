"""Tasks module."""
from app.tasks.vector_tasks import process_photo_vector, run_batch_vector_generation
from app.tasks.detection_tasks import process_photo_detection, run_pending_object_detection_tasks

__all__ = [
    "process_photo_vector",
    "run_batch_vector_generation",
    "process_photo_detection",
    "run_pending_object_detection_tasks",
]
