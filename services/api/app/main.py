"""FaceForge API 入口。"""
import os
import shutil
import tempfile
import uuid
from pathlib import Path

from engine.schemas import FaceEnhancer, ImageSwapRequest, SwapQuality
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import ValidationError

from app.deps import ImageSwapper, get_swapper

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
