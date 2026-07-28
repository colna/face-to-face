"""封装 FaceFusion headless CLI(图片换脸)。

只负责命令组装 + 调用 + 结果校验;真实推理在有 GPU 的机器运行。
subprocess 调用可注入,便于单测。命令行 flag 以 FaceFusion 3.6.x headless-run 为准,
真机接入时再逐个核对(标 🖥️)。
"""
import subprocess
import sys
from pathlib import Path
from typing import Callable, Optional, Union

from engine.schemas import FaceEnhancer, ImageSwapRequest

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
        proc = self._run(cmd)
        if proc.returncode != 0:
            raise RuntimeError(f"FaceFusion 换脸失败(code={proc.returncode}): {proc.stderr}")
        if not Path(req.output_path).is_file():
            raise RuntimeError(f"FaceFusion 返回成功但未生成产物: {req.output_path}")
        return req.output_path
