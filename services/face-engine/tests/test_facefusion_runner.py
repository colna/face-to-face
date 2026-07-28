"""T2.3 FaceFusion 图片换脸封装单测(subprocess 注入 mock,不真跑推理)。"""
import subprocess
from pathlib import Path

import pytest

from engine.facefusion_runner import FaceFusionRunner
from engine.schemas import FaceEnhancer, ImageSwapRequest, SwapQuality


def _req(tmp_path: Path, **q: object) -> ImageSwapRequest:
    return ImageSwapRequest(
        source_path=str(tmp_path / "src.jpg"),
        target_path=str(tmp_path / "tgt.jpg"),
        output_path=str(tmp_path / "out.jpg"),
        quality=SwapQuality(**q),  # type: ignore[arg-type]
    )


def _ok_runner(output: Path):
    """模拟成功:写出 output 文件并返回 returncode=0。"""
    calls: list[list[str]] = []

    def _run(cmd: list[str]) -> subprocess.CompletedProcess:
        calls.append(cmd)
        output.write_bytes(b"swapped")
        return subprocess.CompletedProcess(cmd, 0, stdout="done", stderr="")

    _run.calls = calls  # type: ignore[attr-defined]
    return _run


def test_build_command_has_core_flags(tmp_path: Path) -> None:
    runner = FaceFusionRunner(facefusion_dir="/opt/facefusion")
    cmd = runner.build_image_command(_req(tmp_path))
    joined = " ".join(cmd)
    assert "headless-run" in joined
    assert "-s" in cmd and "-t" in cmd and "-o" in cmd
    assert "hyperswap_1a_256" in joined
    assert "face_swapper" in joined and "face_enhancer" in joined
    assert "codeformer" in joined
    assert "80" in cmd  # face-enhancer-blend 默认


def test_occlusion_mask_toggle(tmp_path: Path) -> None:
    runner = FaceFusionRunner(facefusion_dir="/opt/facefusion")
    on = runner.build_image_command(_req(tmp_path, occlusion_mask=True))
    off = runner.build_image_command(_req(tmp_path, occlusion_mask=False))
    assert "occlusion" in on  # token 级判断,避开 tmp 路径子串误伤
    assert "occlusion" not in off


def test_no_enhancer_omits_face_enhancer(tmp_path: Path) -> None:
    runner = FaceFusionRunner(facefusion_dir="/opt/facefusion")
    cmd = runner.build_image_command(_req(tmp_path, face_enhancer=FaceEnhancer.NONE))
    assert "face_enhancer" not in cmd


def test_swap_image_success(tmp_path: Path) -> None:
    req = _req(tmp_path)
    run = _ok_runner(Path(req.output_path))
    runner = FaceFusionRunner(facefusion_dir="/opt/facefusion", runner=run)
    out = runner.swap_image(req)
    assert out == req.output_path
    assert Path(out).is_file()
    assert run.calls  # type: ignore[attr-defined]


def test_swap_image_nonzero_returncode_raises(tmp_path: Path) -> None:
    req = _req(tmp_path)

    def _fail(cmd: list[str]) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="boom")

    runner = FaceFusionRunner(facefusion_dir="/opt/facefusion", runner=_fail)
    with pytest.raises(RuntimeError, match="boom"):
        runner.swap_image(req)


def test_swap_image_missing_output_raises(tmp_path: Path) -> None:
    req = _req(tmp_path)

    def _no_output(cmd: list[str]) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    runner = FaceFusionRunner(facefusion_dir="/opt/facefusion", runner=_no_output)
    with pytest.raises(RuntimeError, match="产物"):
        runner.swap_image(req)
