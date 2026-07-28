"""T2.2 模型管理单测(下载器可注入,不触网)。"""
import hashlib
from pathlib import Path

import pytest

from engine.models import MODEL_CATALOG, ModelManager, ModelSpec


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


@pytest.fixture()
def spec() -> ModelSpec:
    data = b"fake-model-bytes"
    return ModelSpec(
        name="dummy_swapper",
        filename="dummy.onnx",
        url="https://example.com/dummy.onnx",
        sha256=_sha(data),
        category="swapper",
    )


def _make_downloader(payload: bytes):
    calls = {"n": 0}

    def _dl(url: str, dest: Path) -> None:
        calls["n"] += 1
        dest.write_bytes(payload)

    _dl.calls = calls  # type: ignore[attr-defined]
    return _dl


def test_catalog_nonempty_and_has_swapper() -> None:
    assert len(MODEL_CATALOG) > 0
    assert any(m.category == "swapper" for m in MODEL_CATALOG)


def test_missing_then_present_after_ensure(tmp_path: Path, spec: ModelSpec) -> None:
    dl = _make_downloader(b"fake-model-bytes")
    mgr = ModelManager(models_dir=tmp_path, downloader=dl)
    assert mgr.is_present(spec) is False
    mgr.ensure(spec)
    assert mgr.is_present(spec) is True
    assert dl.calls["n"] == 1  # type: ignore[attr-defined]


def test_ensure_idempotent_when_valid(tmp_path: Path, spec: ModelSpec) -> None:
    dl = _make_downloader(b"fake-model-bytes")
    mgr = ModelManager(models_dir=tmp_path, downloader=dl)
    mgr.ensure(spec)
    mgr.ensure(spec)  # 已存在且校验通过 → 不再下载
    assert dl.calls["n"] == 1  # type: ignore[attr-defined]


def test_corrupt_file_redownloaded(tmp_path: Path, spec: ModelSpec) -> None:
    dl = _make_downloader(b"fake-model-bytes")
    mgr = ModelManager(models_dir=tmp_path, downloader=dl)
    mgr.model_path(spec).write_bytes(b"corrupted")
    assert mgr.is_present(spec) is False  # sha256 不匹配
    mgr.ensure(spec)
    assert mgr.is_present(spec) is True
    assert dl.calls["n"] == 1  # type: ignore[attr-defined]


def test_download_failing_verification_raises(tmp_path: Path, spec: ModelSpec) -> None:
    bad_dl = _make_downloader(b"wrong-bytes")  # sha 对不上
    mgr = ModelManager(models_dir=tmp_path, downloader=bad_dl)
    with pytest.raises(RuntimeError):
        mgr.ensure(spec)


def test_self_check_reports_status(tmp_path: Path, spec: ModelSpec) -> None:
    dl = _make_downloader(b"fake-model-bytes")
    mgr = ModelManager(models_dir=tmp_path, downloader=dl)
    status = mgr.self_check([spec])
    assert status == {"dummy_swapper": False}
    mgr.ensure(spec)
    assert mgr.self_check([spec]) == {"dummy_swapper": True}
