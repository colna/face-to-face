"""T2.5 实时换脸单测(帧处理器注入 mock,不加载真实 GPU 引擎)。"""
import pytest

from engine.realtime import RealtimeSession


def _echo_upper() -> object:
    """mock 帧处理器:把帧字节反转,代表"处理过"。"""
    calls = {"n": 0}

    def _proc(frame: bytes) -> bytes:
        calls["n"] += 1
        return frame[::-1]

    _proc.calls = calls  # type: ignore[attr-defined]
    return _proc


def test_process_frame_uses_processor() -> None:
    proc = _echo_upper()
    sess = RealtimeSession(source_face_path="/faces/a.jpg", processor=proc)  # type: ignore[arg-type]
    out = sess.process_frame(b"abc")
    assert out == b"cba"
    assert sess.frames_processed == 1
    assert proc.calls["n"] == 1  # type: ignore[attr-defined]


def test_multiple_frames_count() -> None:
    sess = RealtimeSession(source_face_path="/faces/a.jpg", processor=_echo_upper())  # type: ignore[arg-type]
    for f in (b"a", b"bb", b"ccc"):
        sess.process_frame(f)
    assert sess.frames_processed == 3


def test_empty_frame_raises() -> None:
    sess = RealtimeSession(source_face_path="/faces/a.jpg", processor=_echo_upper())  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="空帧"):
        sess.process_frame(b"")


def test_empty_source_raises() -> None:
    with pytest.raises(ValueError, match="source"):
        RealtimeSession(source_face_path="", processor=_echo_upper())  # type: ignore[arg-type]


def test_default_processor_requires_gpu_engine() -> None:
    """未注入处理器 → 默认走真实引擎,非 GPU 环境调用应给出明确报错。"""
    sess = RealtimeSession(source_face_path="/faces/a.jpg")
    with pytest.raises(NotImplementedError, match="GPU"):
        sess.process_frame(b"frame")
