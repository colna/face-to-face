"""T3.4 GET /models + 入参校验单测。"""
from pathlib import Path

from engine.models import ModelManager
from engine.schemas import ImageSwapRequest
from fastapi.testclient import TestClient

from app.deps import get_model_manager, get_swapper
from app.main import app

client = TestClient(app)


class _FakeSwapper:
    def swap_image(self, req: ImageSwapRequest) -> str:
        Path(req.output_path).write_bytes(b"x")
        return req.output_path


def test_models_lists_catalog(tmp_path: Path) -> None:
    app.dependency_overrides[get_model_manager] = lambda: ModelManager(models_dir=tmp_path)
    try:
        resp = client.get("/models")
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body["models"], list) and len(body["models"]) > 0
        first = body["models"][0]
        assert {"name", "category", "present"} <= set(first)
        assert body["all_ready"] is False  # 空目录 → 未就绪
    finally:
        app.dependency_overrides.clear()


def test_invalid_enhancer_returns_400() -> None:
    app.dependency_overrides[get_swapper] = lambda: _FakeSwapper()
    try:
        resp = client.post(
            "/swap/image",
            files={
                "source": ("s.jpg", b"a", "image/jpeg"),
                "target": ("t.jpg", b"b", "image/jpeg"),
            },
            data={"face_enhancer": "banana"},  # 非法枚举
        )
        assert resp.status_code == 400
    finally:
        app.dependency_overrides.clear()
