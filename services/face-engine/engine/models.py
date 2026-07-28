"""模型清单 / 下载 / 校验(sha256)/ 缓存,启动自检。

下载器 (`downloader`) 可注入,便于单测不触网;生产默认用 HTTP 流式下载。
"""
import hashlib
from pathlib import Path
from typing import Callable, Optional, Union

from pydantic import BaseModel

# 下载器签名:(url, dest) -> None,负责把 url 写到 dest。
Downloader = Callable[[str, Path], None]

_CHUNK = 1 << 20  # 1 MiB


class ModelSpec(BaseModel):
    """单个模型的清单项。"""

    name: str
    filename: str
    url: str
    sha256: str
    category: str  # swapper / enhancer / detector / parser


# 默认模型清单(sha256 待接真实模型时补齐;此处 URL/hash 为占位,真实值在有卡机器核对)。
MODEL_CATALOG: list[ModelSpec] = [
    ModelSpec(
        name="hyperswap_1a_256",
        filename="hyperswap_1a_256.onnx",
        url="https://models.faceforge.local/hyperswap_1a_256.onnx",
        sha256="0" * 64,
        category="swapper",
    ),
    ModelSpec(
        name="codeformer",
        filename="codeformer.onnx",
        url="https://models.faceforge.local/codeformer.onnx",
        sha256="0" * 64,
        category="enhancer",
    ),
    ModelSpec(
        name="face_parser",
        filename="face_parser.onnx",
        url="https://models.faceforge.local/face_parser.onnx",
        sha256="0" * 64,
        category="parser",
    ),
]


def _default_downloader(url: str, dest: Path) -> None:
    """生产默认下载器:HTTP 流式落盘(仅在有网机器调用)。"""
    import urllib.request

    with urllib.request.urlopen(url) as resp, open(dest, "wb") as f:
        while chunk := resp.read(_CHUNK):
            f.write(chunk)


def sha256_of(path: Path) -> str:
    """计算文件 sha256。"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(_CHUNK):
            h.update(chunk)
    return h.hexdigest()


class ModelManager:
    """模型缓存目录管理:存在性/完整性校验、按需下载、启动自检。"""

    def __init__(
        self,
        models_dir: Union[str, Path],
        downloader: Optional[Downloader] = None,
    ) -> None:
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self._download = downloader or _default_downloader

    def model_path(self, spec: ModelSpec) -> Path:
        """模型在缓存目录中的落盘路径。"""
        return self.models_dir / spec.filename

    def is_present(self, spec: ModelSpec) -> bool:
        """文件存在且 sha256 匹配才算就绪。"""
        path = self.model_path(spec)
        if not path.is_file():
            return False
        return sha256_of(path) == spec.sha256

    def ensure(self, spec: ModelSpec) -> Path:
        """确保模型就绪:缺失或损坏则下载,下载后校验 sha256。"""
        path = self.model_path(spec)
        if self.is_present(spec):
            return path
        self._download(spec.url, path)
        if sha256_of(path) != spec.sha256:
            path.unlink(missing_ok=True)
            raise RuntimeError(f"模型 {spec.name} 下载后 sha256 校验失败")
        return path

    def self_check(self, specs: Optional[list[ModelSpec]] = None) -> dict[str, bool]:
        """启动自检:返回 {模型名: 是否就绪}。"""
        specs = specs if specs is not None else MODEL_CATALOG
        return {s.name: self.is_present(s) for s in specs}
