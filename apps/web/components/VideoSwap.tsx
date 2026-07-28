"use client";

import { useState } from "react";
import { createVideoJob, downloadJob, getJob } from "@/lib/api";
import type { JobStatus, SwapParams } from "@/lib/types";
import { FilePicker } from "./FilePicker";

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

interface Props {
  pollMs?: number;
}

export function VideoSwap({ pollMs = 1000 }: Props) {
  const [source, setSource] = useState<File | null>(null);
  const [target, setTarget] = useState<File | null>(null);
  const [occlusion, setOcclusion] = useState(true);
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<JobStatus | null>(null);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const busy = status === "pending" || status === "running";
  const canSubmit = source !== null && target !== null && !busy;

  async function poll(id: string) {
    for (;;) {
      const job = await getJob(id);
      setStatus(job.status);
      setProgress(job.progress);
      if (job.status === "done") return;
      if (job.status === "failed") {
        setError(job.error ?? "换脸失败");
        return;
      }
      await sleep(pollMs);
    }
  }

  async function onSubmit() {
    if (!source || !target) return;
    setError(null);
    setProgress(0);
    setStatus("pending");
    try {
      const params: SwapParams = { occlusion_mask: occlusion };
      const { job_id } = await createVideoJob(source, target, params);
      setJobId(job_id);
      await poll(job_id);
    } catch (e) {
      setStatus("failed");
      setError(e instanceof Error ? e.message : "换脸失败");
    }
  }

  async function onDownload() {
    if (!jobId) return;
    const blob = await downloadJob(jobId);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "result.mp4";
    a.click();
  }

  return (
    <div className="flex flex-col gap-4">
      <FilePicker label="源脸(Source)" accept="image/*" onSelect={setSource} />
      <FilePicker label="目标视频(Target)" accept="video/*" onSelect={setTarget} />

      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={occlusion}
          onChange={(e) => setOcclusion(e.target.checked)}
        />
        <span className="text-gray-600">遮挡蒙版</span>
      </label>

      <button
        type="button"
        disabled={!canSubmit}
        onClick={onSubmit}
        className="rounded bg-black px-4 py-2 text-white disabled:opacity-40"
      >
        {busy ? "换脸中…" : "开始换脸"}
      </button>

      {status && (
        <div className="flex flex-col gap-1 text-sm text-gray-600">
          <span>状态:{status}</span>
          <progress value={progress} max={1} className="w-full" />
        </div>
      )}

      {status === "done" && (
        <button
          type="button"
          onClick={onDownload}
          className="rounded border border-black px-4 py-2"
        >
          下载结果
        </button>
      )}

      {error && <p role="alert" className="text-red-600">{error}</p>}
    </div>
  );
}
