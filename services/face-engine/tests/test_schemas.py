"""T2.1 schemas 单测(TDD:先写)。"""
import pytest
from pydantic import ValidationError

from engine.schemas import (
    FaceEnhancer,
    FaceSelection,
    FaceSelectorMode,
    ImageSwapRequest,
    JobState,
    JobStatus,
    SwapQuality,
    VideoSwapRequest,
)


def test_swap_quality_defaults() -> None:
    q = SwapQuality()
    assert q.swapper_model == "hyperswap_1a_256"
    assert q.face_enhancer == FaceEnhancer.CODEFORMER
    assert q.face_enhancer_blend == 80
    assert q.occlusion_mask is True


def test_swap_quality_blend_range() -> None:
    with pytest.raises(ValidationError):
        SwapQuality(face_enhancer_blend=101)
    with pytest.raises(ValidationError):
        SwapQuality(face_enhancer_blend=-1)


def test_face_selection_defaults_and_range() -> None:
    f = FaceSelection()
    assert f.selector_mode == FaceSelectorMode.REFERENCE
    assert f.reference_face_position == 0
    with pytest.raises(ValidationError):
        FaceSelection(reference_face_distance=2.0)


def test_image_request_nested_defaults() -> None:
    req = ImageSwapRequest(
        source_path="/in/src.jpg",
        target_path="/in/tgt.jpg",
        output_path="/out/res.jpg",
    )
    assert req.quality.occlusion_mask is True
    assert req.face.selector_mode == FaceSelectorMode.REFERENCE


def test_video_request_trim_validation() -> None:
    req = VideoSwapRequest(
        source_path="/in/src.jpg",
        target_path="/in/tgt.mp4",
        output_path="/out/res.mp4",
        trim_frame_start=10,
        trim_frame_end=100,
    )
    assert req.trim_frame_end == 100
    # end 必须 > start
    with pytest.raises(ValidationError):
        VideoSwapRequest(
            source_path="/in/src.jpg",
            target_path="/in/tgt.mp4",
            output_path="/out/res.mp4",
            trim_frame_start=100,
            trim_frame_end=10,
        )


def test_job_state_progress_range() -> None:
    job = JobState(id="j1", status=JobStatus.RUNNING, progress=0.5)
    assert job.status == JobStatus.RUNNING
    with pytest.raises(ValidationError):
        JobState(id="j2", status=JobStatus.PENDING, progress=1.5)


def test_enum_serialization() -> None:
    assert JobStatus.DONE.value == "done"
    assert FaceEnhancer.NONE.value == "none"


def test_quality_presets() -> None:
    from engine.schemas import FaceEnhancer, QualityPreset, resolve_preset

    fast = resolve_preset(QualityPreset.FAST)
    assert fast.face_enhancer == FaceEnhancer.NONE
    assert fast.occlusion_mask is False

    quality = resolve_preset(QualityPreset.QUALITY)
    assert quality.face_enhancer == FaceEnhancer.CODEFORMER
    assert quality.face_enhancer_blend == 90
    assert quality.pixel_boost == "512x512"
    assert quality.occlusion_mask is True

    balanced = resolve_preset(QualityPreset.BALANCED)
    assert balanced.face_enhancer_blend == 60
