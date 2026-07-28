"""T3.1 POST /swap/image 单测(swapper 注入 fake)。"""
from pathlib import Path

from engine.schemas import ImageSwapRequest
from fastapi.testclient import TestClient

from app.deps import get_swapper
from app.main import app


class _FakeSwapper:
    def swap_image(self, req: ImageSwapRequest) -> str:
        Path(req.output_path).write_bytes(b"swapped-bytes")
        return req.output_path


class _FailSwapper:
    def swap_image(self, req: ImageSwapRequest) -> str:
        raise RuntimeError("引擎炸了")


client = TestClient(app)


def _files() -> dict:
    return {
        "source": ("s.jpg", b"aaa", "image/jpeg"),
        "target": ("t.jpg", b"bbb", "image/jpeg"),
    }


def test_swap_image_ok() -> None:
    app.dependency_overrides[get_swapper] = lambda: _FakeSwapper()
    try:
        resp = client.post("/swap/image", files=_files())
        assert resp.status_code == 200
        assert resp.content == b"swapped-bytes"
        assert resp.headers["content-type"] == "image/jpeg"
    finally:
        app.dependency_overrides.clear()


def test_missing_file_422() -> None:
    resp = client.post("/swap/image", files={"source": ("s.jpg", b"aaa", "image/jpeg")})
    assert resp.status_code == 422


def test_invalid_blend_400() -> None:
    app.dependency_overrides[get_swapper] = lambda: _FakeSwapper()
    try:
        resp = client.post("/swap/image", files=_files(), data={"face_enhancer_blend": 999})
        assert resp.status_code == 400
    finally:
        app.dependency_overrides.clear()


def test_engine_failure_500() -> None:
    app.dependency_overrides[get_swapper] = lambda: _FailSwapper()
    try:
        resp = client.post("/swap/image", files=_files())
        assert resp.status_code == 500
        assert "引擎炸了" in resp.json()["detail"]
    finally:
        app.dependency_overrides.clear()
