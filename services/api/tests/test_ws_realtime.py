"""T3.3 WS /ws/realtime 单测(帧处理器注入 mock)。"""
from fastapi.testclient import TestClient

from app.deps import get_realtime_processor
from app.main import app

client = TestClient(app)


def _reverser(frame: bytes) -> bytes:
    return frame[::-1]


def test_realtime_frames_roundtrip() -> None:
    app.dependency_overrides[get_realtime_processor] = lambda: _reverser
    try:
        with client.websocket_connect("/ws/realtime") as ws:
            ws.send_json({"source_face_path": "/faces/a.jpg"})
            ws.send_bytes(b"abc")
            assert ws.receive_bytes() == b"cba"
            ws.send_bytes(b"hello")
            assert ws.receive_bytes() == b"olleh"
    finally:
        app.dependency_overrides.clear()


def test_realtime_empty_frame_error() -> None:
    app.dependency_overrides[get_realtime_processor] = lambda: _reverser
    try:
        with client.websocket_connect("/ws/realtime") as ws:
            ws.send_json({"source_face_path": "/faces/a.jpg"})
            ws.send_bytes(b"")
            msg = ws.receive_json()
            assert "空帧" in msg["error"]
    finally:
        app.dependency_overrides.clear()


def test_realtime_missing_source_closes() -> None:
    app.dependency_overrides[get_realtime_processor] = lambda: _reverser
    try:
        with client.websocket_connect("/ws/realtime") as ws:
            ws.send_json({"source_face_path": ""})
            msg = ws.receive_json()
            assert "source_face_path" in msg["error"]
    finally:
        app.dependency_overrides.clear()


def test_realtime_default_processor_needs_gpu() -> None:
    """未注入 → 默认 GPU 引擎,非 GPU 环境返回明确错误(不崩)。"""
    with client.websocket_connect("/ws/realtime") as ws:
        ws.send_json({"source_face_path": "/faces/a.jpg"})
        ws.send_bytes(b"frame")
        msg = ws.receive_json()
        assert "GPU" in msg["error"]
