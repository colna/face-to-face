"""API 依赖装配:引擎实例(可被测试 override)。"""
import os
from typing import Protocol

from engine.facefusion_runner import FaceFusionRunner
from engine.schemas import ImageSwapRequest, VideoSwapRequest


class ImageSwapper(Protocol):
    """图片换脸能力协议(便于测试注入 fake)。"""

    def swap_image(self, req: ImageSwapRequest) -> str: ...


class VideoSwapper(Protocol):
    """视频换脸能力协议。"""

    def build_video_command(self, req: VideoSwapRequest) -> list[str]: ...

    def swap_video(self, req: VideoSwapRequest, on_progress: object = ...) -> str: ...


def _facefusion_dir() -> str:
    return os.environ.get("FACEFORGE_FACEFUSION_DIR", "/opt/facefusion")


def get_swapper() -> ImageSwapper:
    """默认图片换脸器(真机走 FaceFusion;测试用 dependency_overrides 替换)。"""
    return FaceFusionRunner(facefusion_dir=_facefusion_dir())
