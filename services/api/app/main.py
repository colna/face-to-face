"""FaceForge API 入口。"""
import os
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Optional

from engine.jobs import VideoJobManager
from engine.realtime import FrameProcessor, RealtimeSession
from engine.schemas import (
    FaceEnhancer,
    ImageSwapRequest,
    JobState,
    JobStatus,
    SwapQuality,
    VideoSwapRequest,
)
from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import FileResponse
from pydantic import ValidationError

from app.deps import (
    ImageSwapper,
    get_realtime_processor,
    get_swapper,
    get_video_manager,
)

app = FastAPI(title="FaceForge API", version="0.1.0")

WORK_DIR = Path(os.environ.get("FACEFORGE_WORK_DIR", tempfile.gettempdir())) / "faceforge"


@app.get("/health")
def health() -> dict[str, str]:
    """健康检查。"""
    return {"status": "ok", "service": "faceforge-api"}


def _save_upload(upload: UploadFile, dest: Path) -> None:
    with open(dest, "wb") as f:
        shutil.copyfileobj(upload.file, f)


@app.post("/swap/image")
async def swap_image(
    source: UploadFile = File(...),
    target: UploadFile = File(...),
    swapper_model: str = Form("hyperswap_1a_256"),
    face_enhancer: str = Form("codeformer"),
    face_enhancer_blend: int = Form(80),
    occlusion_mask: bool = Form(True),
    swapper: ImageSwapper = Depends(get_swapper),
) -> FileResponse:
    """图片换脸:上传 source/target,返回换脸产物。"""
    job_dir = WORK_DIR / uuid.uuid4().hex
    job_dir.mkdir(parents=True, exist_ok=True)
    src_path = job_dir / "source.img"
    tgt_path = job_dir / "target.img"
    out_path = job_dir / "result.jpg"
    _save_upload(source, src_path)
    _save_upload(target, tgt_path)

    try:
        quality = SwapQuality(
            swapper_model=swapper_model,
            face_enhancer=FaceEnhancer(face_enhancer),
            face_enhancer_blend=face_enhancer_blend,
            occlusion_mask=occlusion_mask,
        )
        req = ImageSwapRequest(
            source_path=str(src_path),
            target_path=str(tgt_path),
            output_path=str(out_path),
            quality=quality,
        )
    except (ValidationError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"参数不合法: {exc}") from exc

    try:
        result = swapper.swap_image(req)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return FileResponse(result, media_type="image/jpeg", filename="result.jpg")


@app.post("/swap/video")
async def swap_video(
    background: BackgroundTasks,
    source: UploadFile = File(...),
    target: UploadFile = File(...),
    swapper_model: str = Form("hyperswap_1a_256"),
    face_enhancer: str = Form("codeformer"),
    face_enhancer_blend: int = Form(80),
    occlusion_mask: bool = Form(True),
    trim_frame_start: Optional[int] = Form(None),
    trim_frame_end: Optional[int] = Form(None),
    mgr: VideoJobManager = Depends(get_video_manager),
) -> dict[str, str]:
    """视频换脸:建异步任务,后台执行,返回 job_id。"""
    job_dir = WORK_DIR / uuid.uuid4().hex
    job_dir.mkdir(parents=True, exist_ok=True)
    src_path = job_dir / "source.img"
    tgt_path = job_dir / "target.mp4"
    out_path = job_dir / "result.mp4"
    _save_upload(source, src_path)
    _save_upload(target, tgt_path)

    try:
        quality = SwapQuality(
            swapper_model=swapper_model,
            face_enhancer=FaceEnhancer(face_enhancer),
            face_enhancer_blend=face_enhancer_blend,
            occlusion_mask=occlusion_mask,
        )
        req = VideoSwapRequest(
            source_path=str(src_path),
            target_path=str(tgt_path),
            output_path=str(out_path),
            quality=quality,
            trim_frame_start=trim_frame_start,
            trim_frame_end=trim_frame_end,
        )
    except (ValidationError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"参数不合法: {exc}") from exc

    job = mgr.create(req)
    background.add_task(mgr.execute, job.id)
    return {"job_id": job.id, "status": job.status.value}


@app.get("/jobs/{job_id}")
def get_job(
    job_id: str,
    mgr: VideoJobManager = Depends(get_video_manager),
) -> JobState:
    """查询视频任务进度/结果。"""
    try:
        return mgr.get(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="任务不存在") from exc


@app.get("/jobs/{job_id}/download")
def download_job(
    job_id: str,
    mgr: VideoJobManager = Depends(get_video_manager),
) -> FileResponse:
    """下载已完成的视频产物。"""
    try:
        state = mgr.get(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="任务不存在") from exc
    if state.status != JobStatus.DONE or not state.output_path:
        raise HTTPException(status_code=409, detail=f"任务未完成(status={state.status.value})")
    return FileResponse(state.output_path, media_type="video/mp4", filename="result.mp4")


@app.websocket("/ws/realtime")
async def ws_realtime(
    ws: WebSocket,
    processor: Optional[FrameProcessor] = Depends(get_realtime_processor),
) -> None:
    """实时换脸:首条 JSON 配置 {source_face_path},随后逐帧二进制收发。"""
    await ws.accept()
    cfg = await ws.receive_json()
    source = cfg.get("source_face_path", "")
    if not source:
        await ws.send_json({"error": "source_face_path 不能为空"})
        await ws.close()
        return
    session = RealtimeSession(source_face_path=source, processor=processor)
    try:
        while True:
            frame = await ws.receive_bytes()
            try:
                out = session.process_frame(frame)
            except (ValueError, NotImplementedError) as exc:
                await ws.send_json({"error": str(exc)})
                continue
            await ws.send_bytes(out)
    except WebSocketDisconnect:
        return
