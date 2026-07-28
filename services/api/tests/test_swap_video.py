"""T3.2 POST /swap/video + GET /jobs/{id} 单测(VideoJobManager 注入 fake swap)。"""
from pathlib import Path
from typing import Callable

from engine.jobs import VideoJobManager
from engine.schemas import VideoSwapRequest
from fastapi.testclient import TestClient

from app.deps import get_video_manager
from app.main import app

client = TestClient(app)


def _files() -> dict:
    return {
        "source": ("s.jpg", b"aaa", "image/jpeg"),
        "target": ("t.mp4", b"bbb", "video/mp4"),
    }


def _ok_swap(req: VideoSwapRequest, on_progress: Callable[[float], None]) -> str:
    on_progress(0.5)
    Path(req.output_path).write_bytes(b"video-bytes")
    return req.output_path


def _boom(req: VideoSwapRequest, on_progress: Callable[[float], None]) -> str:
    raise RuntimeError("转码失败")


def _override(swap: Callable) -> Callable[[], VideoJobManager]:
    mgr = VideoJobManager(swap_fn=swap)
    return lambda: mgr


def test_video_job_lifecycle_done() -> None:
    app.dependency_overrides[get_video_manager] = _override(_ok_swap)
    try:
        resp = client.post("/swap/video", files=_files())
        assert resp.status_code == 200
        job_id = resp.json()["job_id"]
        assert resp.json()["status"] == "pending"
        # TestClient 会等后台任务执行完
        state = client.get(f"/jobs/{job_id}").json()
        assert state["status"] == "done"
        assert state["progress"] == 1.0
        # 下载产物
        dl = client.get(f"/jobs/{job_id}/download")
        assert dl.status_code == 200
        assert dl.content == b"video-bytes"
    finally:
        app.dependency_overrides.clear()


def test_video_job_failure() -> None:
    app.dependency_overrides[get_video_manager] = _override(_boom)
    try:
        job_id = client.post("/swap/video", files=_files()).json()["job_id"]
        state = client.get(f"/jobs/{job_id}").json()
        assert state["status"] == "failed"
        assert "转码失败" in state["error"]
        assert client.get(f"/jobs/{job_id}/download").status_code == 409
    finally:
        app.dependency_overrides.clear()


def test_get_unknown_job_404() -> None:
    app.dependency_overrides[get_video_manager] = _override(_ok_swap)
    try:
        assert client.get("/jobs/nope").status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_invalid_trim_400() -> None:
    app.dependency_overrides[get_video_manager] = _override(_ok_swap)
    try:
        resp = client.post(
            "/swap/video",
            files=_files(),
            data={"trim_frame_start": 100, "trim_frame_end": 10},
        )
        assert resp.status_code == 400
    finally:
        app.dependency_overrides.clear()
