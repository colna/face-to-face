"""T3.1 POST /swap/image 单测(swapper 注入 fake)。"""

from pathlib import Path

from engine.schemas import FaceSelectorMode, ImageSwapRequest
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


class _SuffixCheckingSwapper:
    def swap_image(self, req: ImageSwapRequest) -> str:
        assert Path(req.source_path).suffix == ".png"
        assert Path(req.target_path).suffix == ".webp"
        Path(req.output_path).write_bytes(b"swapped-bytes")
        return req.output_path


class _SelectorCheckingSwapper:
    def __init__(self, expected: FaceSelectorMode) -> None:
        self.expected = expected

    def swap_image(self, req: ImageSwapRequest) -> str:
        assert req.face.selector_mode == self.expected
        Path(req.output_path).write_bytes(b"swapped-bytes")
        return req.output_path


class _QualityCheckingSwapper:
    def swap_image(self, req: ImageSwapRequest) -> str:
        assert req.quality.swapper_model == "hyperswap_1a_256"
        assert req.quality.face_enhancer_blend == 30
        assert req.quality.occlusion_mask is False
        assert req.quality.pixel_boost == "256x256"
        assert req.quality.face_mask_blur == 0.5
        assert req.quality.face_mask_padding == (35, 25, 20, 25)
        Path(req.output_path).write_bytes(b"swapped-bytes")
        return req.output_path


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


def test_swap_image_preserves_supported_file_suffixes() -> None:
    app.dependency_overrides[get_swapper] = lambda: _SuffixCheckingSwapper()
    files = {
        "source": ("source.PNG", b"aaa", "image/png"),
        "target": ("target.webp", b"bbb", "image/webp"),
    }
    try:
        resp = client.post("/swap/image", files=files)
        assert resp.status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_swap_image_defaults_to_all_faces() -> None:
    app.dependency_overrides[get_swapper] = lambda: _SelectorCheckingSwapper(FaceSelectorMode.MANY)
    try:
        resp = client.post("/swap/image", files=_files())
        assert resp.status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_swap_image_uses_identity_preserving_quality_defaults() -> None:
    app.dependency_overrides[get_swapper] = lambda: _QualityCheckingSwapper()
    try:
        resp = client.post("/swap/image", files=_files())
        assert resp.status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_swap_image_accepts_reference_selector() -> None:
    app.dependency_overrides[get_swapper] = lambda: _SelectorCheckingSwapper(
        FaceSelectorMode.REFERENCE
    )
    try:
        resp = client.post("/swap/image", files=_files(), data={"face_selector_mode": "reference"})
        assert resp.status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_invalid_face_selector_mode_400() -> None:
    app.dependency_overrides[get_swapper] = lambda: _FakeSwapper()
    try:
        resp = client.post("/swap/image", files=_files(), data={"face_selector_mode": "unknown"})
        assert resp.status_code == 400
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


def test_preset_quality() -> None:
    """preset=quality 时应正常换脸(走预设档位)。"""
    app.dependency_overrides[get_swapper] = lambda: _QualityCheckingSwapper()
    try:
        resp = client.post("/swap/image", files=_files(), data={"preset": "quality"})
        assert resp.status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_invalid_preset_400() -> None:
    app.dependency_overrides[get_swapper] = lambda: _FakeSwapper()
    try:
        resp = client.post("/swap/image", files=_files(), data={"preset": "ultra"})
        assert resp.status_code == 400
    finally:
        app.dependency_overrides.clear()
