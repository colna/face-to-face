"""FaceForge API 入口。"""
from fastapi import FastAPI

app = FastAPI(title="FaceForge API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    """健康检查。"""
    return {"status": "ok", "service": "faceforge-api"}
