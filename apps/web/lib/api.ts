// FaceForge API 客户端。base 由 NEXT_PUBLIC_API_BASE 提供。
import type { JobState, ModelsStatus, SwapParams } from "./types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

function buildForm(source: File, target: File, params: SwapParams): FormData {
  const fd = new FormData();
  fd.append("source", source);
  fd.append("target", target);
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null) fd.append(k, String(v));
  }
  return fd;
}

async function ensureOk(resp: Response): Promise<Response> {
  if (!resp.ok) {
    let detail = resp.statusText;
    try {
      const body = await resp.json();
      detail = body.detail ?? detail;
    } catch {
      /* 非 JSON 错误体,忽略 */
    }
    throw new Error(`API ${resp.status}: ${detail}`);
  }
  return resp;
}

/** 图片换脸,返回结果图 Blob。 */
export async function swapImage(
  source: File,
  target: File,
  params: SwapParams = {},
): Promise<Blob> {
  const resp = await fetch(`${API_BASE}/swap/image`, {
    method: "POST",
    body: buildForm(source, target, params),
  });
  await ensureOk(resp);
  return resp.blob();
}

/** 建视频换脸任务,返回 job id。 */
export async function createVideoJob(
  source: File,
  target: File,
  params: SwapParams = {},
): Promise<{ job_id: string; status: string }> {
  const resp = await fetch(`${API_BASE}/swap/video`, {
    method: "POST",
    body: buildForm(source, target, params),
  });
  await ensureOk(resp);
  return resp.json();
}

/** 查询任务进度/结果。 */
export async function getJob(jobId: string): Promise<JobState> {
  const resp = await fetch(`${API_BASE}/jobs/${jobId}`);
  await ensureOk(resp);
  return resp.json();
}

/** 下载已完成任务的产物。 */
export async function downloadJob(jobId: string): Promise<Blob> {
  const resp = await fetch(`${API_BASE}/jobs/${jobId}/download`);
  await ensureOk(resp);
  return resp.blob();
}

/** 模型清单与就绪状态。 */
export async function listModels(): Promise<ModelsStatus> {
  const resp = await fetch(`${API_BASE}/models`);
  await ensureOk(resp);
  return resp.json();
}

/** 实时换脸 WS 连接。onFrame 收到换脸后帧;返回发送帧与关闭句柄。 */
export function connectRealtime(
  sourceFacePath: string,
  onFrame: (frame: Blob) => void,
  onError?: (msg: string) => void,
): { sendFrame: (frame: Blob | ArrayBuffer) => void; close: () => void } {
  const wsBase = API_BASE.replace(/^http/, "ws");
  const ws = new WebSocket(`${wsBase}/ws/realtime`);
  ws.binaryType = "blob";
  ws.onopen = () => ws.send(JSON.stringify({ source_face_path: sourceFacePath }));
  ws.onmessage = (ev) => {
    if (typeof ev.data === "string") {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.error) onError?.(msg.error);
      } catch {
        /* 忽略非 JSON 文本 */
      }
    } else {
      onFrame(ev.data as Blob);
    }
  };
  return {
    sendFrame: (frame) => ws.send(frame),
    close: () => ws.close(),
  };
}
