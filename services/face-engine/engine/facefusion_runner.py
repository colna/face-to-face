"""封装 FaceFusion headless CLI(图片换脸)。

只负责命令组装 + 调用 + 结果校验;真实推理在有 GPU 的机器运行。
subprocess 调用可注入,便于单测。命令行 flag 以 FaceFusion 3.6.x headless-run 为准,
真机接入时再逐个核对(标 🖥️)。
"""
import subprocess
import sys
from pathlib import Path
from typing import Callable, Optional, Union

from engine.schemas import FaceEnhancer, ImageSwapRequest, VideoSwapRequest

# 注入点:接收命令 argv,返回 CompletedProcess。
Runner = Callable[[list[str]], "subprocess.CompletedProcess[str]"]


def _default_runner(cmd: list[str]) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


class FaceFusionRunner:
    """FaceFusion 图片换脸封装。"""

    def __init__(
        self,
        facefusion_dir: Union[str, Path],
        runner: Optional[Runner] = None,
        python_executable: Optional[str] = None,
    ) -> None:
        self.facefusion_dir = Path(facefusion_dir)
        self._run = runner or _default_runner
        self._python = python_executable or sys.executable

    def build_image_command(self, req: ImageSwapRequest) -> list[str]:
        """把请求编译成 FaceFusion headless-run argv。"""
        q = req.quality
        processors = ["face_swapper"]
        if q.face_enhancer != FaceEnhancer.NONE:
            processors.append("face_enhancer")

        cmd: list[str] = [
            self._python,
            str(self.facefusion_dir / "facefusion.py"),
            "headless-run",
            "-s",
            req.source_path,
            "-t",
            req.target_path,
            "-o",
            req.output_path,
            "--processors",
            *processors,
            "--face-swapper-model",
            q.swapper_model,
            "--face-swapper-pixel-boost",
            q.pixel_boost,
        ]
        if q.face_enhancer != FaceEnhancer.NONE:
            cmd += [
                "--face-enhancer-model",
                q.face_enhancer.value,
                "--face-enhancer-blend",
                str(q.face_enhancer_blend),
            ]
        if q.occlusion_mask:
            cmd += ["--face-mask-types", "box", "occlusion"]

        cmd += [
            "--face-selector-mode",
            req.face.selector_mode.value,
            "--reference-face-position",
            str(req.face.reference_face_position),
            "--reference-face-distance",
            str(req.face.reference_face_distance),
        ]
        return cmd

    def swap_image(self, req: ImageSwapRequest) -> str:
        """执行图片换脸,成功返回产物路径,失败抛 RuntimeError。"""
        cmd = self.build_image_command(req)
        return self._run_and_verify(cmd, req.output_path)

    def build_video_command(self, req: VideoSwapRequest) -> list[str]:
        """把视频请求编译成 FaceFusion headless-run argv(在图片命令基础上加裁剪帧)。"""
        cmd = self.build_image_command(req)
        cmd += ["--output-video-encoder", "libx264"]
        if req.trim_frame_start is not None:
            cmd += ["--trim-frame-start", str(req.trim_frame_start)]
        if req.trim_frame_end is not None:
            cmd += ["--trim-frame-end", str(req.trim_frame_end)]
        return cmd

    def swap_video(
        self,
        req: VideoSwapRequest,
        on_progress: Optional[Callable[[float], None]] = None,
    ) -> str:
        """执行视频换脸。progress 的逐帧上报待真机接 FaceFusion 输出解析(🖥️);
        当前实现完成后置 1.0。"""
        cmd = self.build_video_command(req)
        out = self._run_and_verify(cmd, req.output_path)
        if on_progress is not None:
            on_progress(1.0)
        return out

    def _run_and_verify(self, cmd: list[str], output_path: str) -> str:
        proc = self._run(cmd)
        if proc.returncode != 0:
            raise RuntimeError(f"FaceFusion 换脸失败(code={proc.returncode}): {proc.stderr}")
        if not Path(output_path).is_file():
            raise RuntimeError(f"FaceFusion 返回成功但未生成产物: {output_path}")
        return output_path
