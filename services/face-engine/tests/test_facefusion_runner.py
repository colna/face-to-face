"""T2.3 FaceFusion 图片换脸封装单测(subprocess 注入 mock,不真跑推理)。"""

import subprocess
import sys
from pathlib import Path

import pytest

from engine.facefusion_runner import FaceFusionRunner, _default_runner
from engine.schemas import (
    FaceEnhancer,
    FaceSelection,
    FaceSelectorMode,
    ImageSwapRequest,
    SwapQuality,
)


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


def test_default_runner_uses_facefusion_directory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    options: dict[str, object] = {}

    def _run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess:
        options.update(kwargs)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", _run)

    _default_runner([sys.executable, "/opt/facefusion/facefusion.py", "--version"])

    assert options["cwd"] == Path("/opt/facefusion")


def test_build_command_has_core_flags(tmp_path: Path) -> None:
    runner = FaceFusionRunner(facefusion_dir="/opt/facefusion")
    cmd = runner.build_image_command(_req(tmp_path))
    joined = " ".join(cmd)
    assert "headless-run" in joined
    assert "-s" in cmd and "-t" in cmd and "-o" in cmd
    assert "hyperswap_1a_256" in joined
    assert "face_swapper" in joined and "face_enhancer" in joined
    assert "codeformer" in joined
    assert "30" in cmd  # face-enhancer-blend 默认
    assert cmd[cmd.index("--face-mask-types") + 1] == "box"
    assert cmd[cmd.index("--face-mask-blur") + 1] == "0.5"
    padding_index = cmd.index("--face-mask-padding")
    assert cmd[padding_index + 1 : padding_index + 5] == ["35", "25", "20", "25"]
    selector_index = cmd.index("--face-selector-mode")
    assert cmd[selector_index + 1] == "reference"
    assert "--reference-face-position" in cmd


def test_many_face_selector_omits_reference_options(tmp_path: Path) -> None:
    runner = FaceFusionRunner(facefusion_dir="/opt/facefusion")
    req = _req(tmp_path)
    req.face = FaceSelection(selector_mode=FaceSelectorMode.MANY)

    cmd = runner.build_image_command(req)

    selector_index = cmd.index("--face-selector-mode")
    assert cmd[selector_index + 1] == "many"
    assert "--reference-face-position" not in cmd
    assert "--reference-face-distance" not in cmd


def test_build_command_uses_execution_providers_from_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FACEFORGE_EXECUTION_PROVIDERS", "coreml cpu")
    runner = FaceFusionRunner(facefusion_dir="/opt/facefusion")

    cmd = runner.build_image_command(_req(tmp_path))

    assert cmd[-3:] == ["--execution-providers", "coreml", "cpu"]


def test_facefusion_python_from_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FACEFORGE_FACEFUSION_PYTHON", "/opt/facefusion/.venv/bin/python")
    runner = FaceFusionRunner(facefusion_dir="/opt/facefusion")

    cmd = runner.build_image_command(_req(tmp_path))

    assert cmd[0] == "/opt/facefusion/.venv/bin/python"


def test_explicit_runtime_options_override_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FACEFORGE_FACEFUSION_PYTHON", "/env/python")
    monkeypatch.setenv("FACEFORGE_EXECUTION_PROVIDERS", "cpu")
    runner = FaceFusionRunner(
        facefusion_dir="/opt/facefusion",
        python_executable=sys.executable,
        execution_providers=["coreml"],
    )

    cmd = runner.build_image_command(_req(tmp_path))

    assert cmd[0] == sys.executable
    assert cmd[-2:] == ["--execution-providers", "coreml"]


def test_occlusion_mask_toggle(tmp_path: Path) -> None:
    runner = FaceFusionRunner(facefusion_dir="/opt/facefusion")
    on = runner.build_image_command(_req(tmp_path, occlusion_mask=True))
    off = runner.build_image_command(_req(tmp_path, occlusion_mask=False))
    assert "occlusion" in on  # token 级判断,避开 tmp 路径子串误伤
    assert "occlusion" not in off


def test_custom_face_mask_options(tmp_path: Path) -> None:
    runner = FaceFusionRunner(facefusion_dir="/opt/facefusion")
    cmd = runner.build_image_command(
        _req(tmp_path, face_mask_blur=0.25, face_mask_padding=(10, 20, 30, 40))
    )

    assert cmd[cmd.index("--face-mask-blur") + 1] == "0.25"
    padding_index = cmd.index("--face-mask-padding")
    assert cmd[padding_index + 1 : padding_index + 5] == ["10", "20", "30", "40"]


def test_no_enhancer_omits_face_enhancer(tmp_path: Path) -> None:
    runner = FaceFusionRunner(facefusion_dir="/opt/facefusion")
    cmd = runner.build_image_command(_req(tmp_path, face_enhancer=FaceEnhancer.NONE))
    assert "face_enhancer" not in cmd


def test_gfpgan_uses_current_facefusion_model_name(tmp_path: Path) -> None:
    runner = FaceFusionRunner(facefusion_dir="/opt/facefusion")
    cmd = runner.build_image_command(_req(tmp_path, face_enhancer=FaceEnhancer.GFPGAN))

    assert "gfpgan_1.4" in cmd
    assert "gfpgan" not in cmd


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
