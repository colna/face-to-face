"""实时换脸会话(Deep-Live-Cam 管线)。

吃一帧吐一帧。帧处理器 (`processor`) 可注入,便于单测;
生产默认加载 Deep-Live-Cam / inswapper 实时管线,需 GPU(🖥️)。
帧以 bytes 表示(编码后的图像帧,如 JPEG),便于走 WebSocket 传输。
"""
from typing import Callable, Optional

# 帧处理器签名:输入一帧字节,返回换脸后一帧字节。
FrameProcessor = Callable[[bytes], bytes]


def _gpu_processor_stub(source_face_path: str) -> FrameProcessor:
    """默认实时处理器占位:真实实现需在 GPU 机器加载 Deep-Live-Cam。"""

    def _proc(_frame: bytes) -> bytes:
        raise NotImplementedError(
            "实时换脸默认处理器需 GPU(Deep-Live-Cam);"
            "沙箱内请注入 processor 进行单测,真机部署时接真实引擎。"
        )

    return _proc


class RealtimeSession:
    """一路实时换脸会话:锁定 source 脸,逐帧处理。"""

    def __init__(
        self,
        source_face_path: str,
        processor: Optional[FrameProcessor] = None,
    ) -> None:
        if not source_face_path:
            raise ValueError("source_face_path 不能为空")
        self.source_face_path = source_face_path
        self._proc = processor or _gpu_processor_stub(source_face_path)
        self.frames_processed = 0

    def process_frame(self, frame: bytes) -> bytes:
        """处理一帧,返回换脸后帧。空帧抛 ValueError。"""
        if not frame:
            raise ValueError("空帧")
        out = self._proc(frame)
        self.frames_processed += 1
        return out
