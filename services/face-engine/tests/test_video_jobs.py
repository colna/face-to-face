"""T2.4 视频换脸命令 + 任务状态机单测(swap 注入 mock)。"""
from pathlib import Path
from typing import Callable

import pytest

from engine.facefusion_runner import FaceFusionRunner
from engine.jobs import VideoJobManager
from engine.schemas import JobStatus, VideoSwapRequest


def _vreq(tmp_path: Path, **kw: object) -> VideoSwapRequest:
    return VideoSwapRequest(
        source_path=str(tmp_path / "src.jpg"),
        target_path=str(tmp_path / "tgt.mp4"),
        output_path=str(tmp_path / "out.mp4"),
        **kw,  # type: ignore[arg-type]
    )


# ---------- 命令组装 ----------
def test_build_video_command_core_and_trim(tmp_path: Path) -> None:
    runner = FaceFusionRunner(facefusion_dir="/opt/facefusion")
    cmd = runner.build_video_command(_vreq(tmp_path, trim_frame_start=5, trim_frame_end=50))
    assert "headless-run" in cmd
    assert "--trim-frame-start" in cmd and "5" in cmd
    assert "--trim-frame-end" in cmd and "50" in cmd
    assert "hyperswap_1a_256" in " ".join(cmd)


def test_build_video_command_no_trim_omits_flags(tmp_path: Path) -> None:
    runner = FaceFusionRunner(facefusion_dir="/opt/facefusion")
    cmd = runner.build_video_command(_vreq(tmp_path))
    assert "--trim-frame-start" not in cmd
    assert "--trim-frame-end" not in cmd


# ---------- 状态机 ----------
def _ok_swap(output: Path) -> Callable[..., str]:
    def _swap(req: VideoSwapRequest, on_progress: Callable[[float], None]) -> str:
        on_progress(0.5)
        Path(req.output_path).write_bytes(b"video")
        on_progress(1.0)
        return req.output_path

    return _swap


def test_create_job_is_pending(tmp_path: Path) -> None:
    mgr = VideoJobManager(swap_fn=_ok_swap(tmp_path / "out.mp4"))
    job = mgr.create(_vreq(tmp_path))
    assert job.status == JobStatus.PENDING
    assert job.progress == 0.0
    assert mgr.get(job.id).status == JobStatus.PENDING


def test_execute_success_transitions_to_done(tmp_path: Path) -> None:
    req = _vreq(tmp_path)
    mgr = VideoJobManager(swap_fn=_ok_swap(Path(req.output_path)))
    job = mgr.create(req)
    final = mgr.execute(job.id)
    assert final.status == JobStatus.DONE
    assert final.progress == 1.0
    assert final.output_path == req.output_path
    assert Path(req.output_path).is_file()


def test_execute_records_progress(tmp_path: Path) -> None:
    req = _vreq(tmp_path)
    seen: list[float] = []
    mgr = VideoJobManager(swap_fn=_ok_swap(Path(req.output_path)), on_progress=seen.append)
    job = mgr.create(req)
    mgr.execute(job.id)
    assert 0.5 in seen and 1.0 in seen


def test_execute_failure_transitions_to_failed(tmp_path: Path) -> None:
    req = _vreq(tmp_path)

    def _boom(req: VideoSwapRequest, on_progress: Callable[[float], None]) -> str:
        raise RuntimeError("ffmpeg 爆了")

    mgr = VideoJobManager(swap_fn=_boom)
    job = mgr.create(req)
    final = mgr.execute(job.id)
    assert final.status == JobStatus.FAILED
    assert "ffmpeg" in (final.error or "")


def test_get_unknown_raises() -> None:
    mgr = VideoJobManager(swap_fn=lambda r, p: "")
    with pytest.raises(KeyError):
        mgr.get("nope")
