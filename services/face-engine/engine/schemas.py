"""引擎入参/出参 schema(质量参数、人脸选择、任务状态)。"""
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class FaceEnhancer(str, Enum):
    """人脸增强器。"""

    NONE = "none"
    CODEFORMER = "codeformer"
    GFPGAN = "gfpgan"


class FaceSelectorMode(str, Enum):
    """人脸选择策略。"""

    REFERENCE = "reference"  # 按参考脸匹配(多脸场景锁定目标脸)
    ONE = "one"  # 只换第一张
    MANY = "many"  # 全部换


class JobStatus(str, Enum):
    """异步任务状态。"""

    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class SwapQuality(BaseModel):
    """换脸质量档位(默认走质量优先)。"""

    swapper_model: str = "hyperswap_1a_256"
    face_enhancer: FaceEnhancer = FaceEnhancer.CODEFORMER
    face_enhancer_blend: int = Field(default=80, ge=0, le=100)
    occlusion_mask: bool = True
    pixel_boost: str = "256x256"


class FaceSelection(BaseModel):
    """人脸选择参数。"""

    selector_mode: FaceSelectorMode = FaceSelectorMode.REFERENCE
    reference_face_position: int = Field(default=0, ge=0)
    reference_face_distance: float = Field(default=0.6, ge=0.0, le=1.5)


class ImageSwapRequest(BaseModel):
    """图片换脸请求。"""

    source_path: str
    target_path: str
    output_path: str
    quality: SwapQuality = Field(default_factory=SwapQuality)
    face: FaceSelection = Field(default_factory=FaceSelection)


class VideoSwapRequest(ImageSwapRequest):
    """视频换脸请求(可选裁剪帧区间)。"""

    trim_frame_start: Optional[int] = Field(default=None, ge=0)
    trim_frame_end: Optional[int] = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _check_trim(self) -> "VideoSwapRequest":
        if (
            self.trim_frame_start is not None
            and self.trim_frame_end is not None
            and self.trim_frame_end <= self.trim_frame_start
        ):
            raise ValueError("trim_frame_end 必须大于 trim_frame_start")
        return self


class JobState(BaseModel):
    """任务运行态。"""

    id: str
    status: JobStatus
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    output_path: Optional[str] = None
    error: Optional[str] = None
