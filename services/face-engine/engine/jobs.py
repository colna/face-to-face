"""视频换脸任务状态机(内存版 MVP)。

状态流转:pending → running → done / failed。
换脸执行 (`swap_fn`) 可注入,便于单测;生产默认接 FaceFusionRunner.swap_video。
并发队列/持久化留到 P1(Redis/RQ)。
"""
import uuid
from typing import Callable, Optional

from engine.schemas import JobState, JobStatus, VideoSwapRequest

# 换脸执行签名:(请求, 进度回调) -> 产物路径。
SwapFn = Callable[[VideoSwapRequest, Callable[[float], None]], str]


class VideoJobManager:
    """内存任务管理器:创建、执行、查询视频换脸任务。"""

    def __init__(
        self,
        swap_fn: SwapFn,
        on_progress: Optional[Callable[[float], None]] = None,
    ) -> None:
        self._swap = swap_fn
        self._on_progress = on_progress
        self._jobs: dict[str, JobState] = {}
        self._reqs: dict[str, VideoSwapRequest] = {}

    def create(self, req: VideoSwapRequest) -> JobState:
        """登记任务,初始 pending。"""
        job_id = uuid.uuid4().hex
        state = JobState(id=job_id, status=JobStatus.PENDING, progress=0.0)
        self._jobs[job_id] = state
        self._reqs[job_id] = req
        return state

    def get(self, job_id: str) -> JobState:
        """查询任务状态(不存在抛 KeyError)。"""
        return self._jobs[job_id]

    def execute(self, job_id: str) -> JobState:
        """同步执行任务(由 worker/后台线程调用),流转状态与进度。"""
        req = self._reqs[job_id]
        self._update(job_id, status=JobStatus.RUNNING, progress=0.0)

        def _progress(p: float) -> None:
            self._update(job_id, progress=p)
            if self._on_progress is not None:
                self._on_progress(p)

        try:
            output = self._swap(req, _progress)
        except Exception as exc:  # noqa: BLE001 — 任何引擎异常都落 failed
            return self._update(job_id, status=JobStatus.FAILED, error=str(exc))
        return self._update(
            job_id, status=JobStatus.DONE, progress=1.0, output_path=output
        )

    def _update(self, job_id: str, **fields: object) -> JobState:
        state = self._jobs[job_id]
        updated = state.model_copy(update=fields)
        self._jobs[job_id] = updated
        return updated
