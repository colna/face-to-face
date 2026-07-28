"""API 依赖装配:引擎实例(可被测试 override)。"""
import os
from typing import Optional, Protocol

from engine.facefusion_runner import FaceFusionRunner
from engine.jobs import VideoJobManager
from engine.realtime import FrameProcessor
from engine.schemas import ImageSwapRequest


class ImageSwapper(Protocol):
    """图片换脸能力协议(便于测试注入 fake)。"""

    def swap_image(self, req: ImageSwapRequest) -> str: ...


def _facefusion_dir() -> str:
    return os.environ.get("FACEFORGE_FACEFUSION_DIR", "/opt/facefusion")


def get_swapper() -> ImageSwapper:
    """默认图片换脸器(真机走 FaceFusion;测试用 dependency_overrides 替换)。"""
    return FaceFusionRunner(facefusion_dir=_facefusion_dir())


_video_manager: Optional[VideoJobManager] = None


def get_video_manager() -> VideoJobManager:
    """视频任务管理器单例(内存态,进程内共享;测试用 override 替换)。"""
    global _video_manager
    if _video_manager is None:
        runner = FaceFusionRunner(facefusion_dir=_facefusion_dir())
        _video_manager = VideoJobManager(swap_fn=runner.swap_video)
    return _video_manager


def get_realtime_processor() -> Optional[FrameProcessor]:
    """实时帧处理器。默认 None → RealtimeSession 用内置 GPU 引擎(🖥️);测试 override 注入 mock。"""
    return None
