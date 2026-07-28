"use client";

import { useRef, useState } from "react";
import { connectRealtime } from "@/lib/api";

interface Conn {
  sendFrame: (frame: Blob | ArrayBuffer) => void;
  close: () => void;
}

const FPS = 15;

export function RealtimeSwap() {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [outUrl, setOutUrl] = useState<string | null>(null);
  const [sourcePath, setSourcePath] = useState("");
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const connRef = useRef<Conn | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  function captureFrame() {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    canvas.width = video.videoWidth || 320;
    canvas.height = video.videoHeight || 240;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    canvas.toBlob((blob) => {
      if (blob) connRef.current?.sendFrame(blob);
    }, "image/jpeg");
  }

  async function start() {
    setError(null);
    try {
      // 自拍探真:强制前置摄像头
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user" },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) videoRef.current.srcObject = stream;
      connRef.current = connectRealtime(
        sourcePath,
        (frame) => setOutUrl(URL.createObjectURL(frame)),
        (msg) => setError(msg),
      );
      timerRef.current = setInterval(captureFrame, 1000 / FPS);
      setRunning(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "无法开启摄像头");
    }
  }

  function stop() {
    if (timerRef.current) clearInterval(timerRef.current);
    connRef.current?.close();
    streamRef.current?.getTracks().forEach((t) => t.stop());
    connRef.current = null;
    streamRef.current = null;
    setRunning(false);
  }

  return (
    <div className="flex flex-col gap-4">
      <label className="flex flex-col gap-1 text-sm">
        <span className="text-gray-600">源脸标识(source_face_path)</span>
        <input
          value={sourcePath}
          onChange={(e) => setSourcePath(e.target.value)}
          placeholder="/faces/a.jpg"
          className="rounded border border-gray-300 p-2"
        />
      </label>

      <div className="flex gap-4">
        {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
        <video ref={videoRef} autoPlay playsInline muted className="w-40 rounded bg-black" />
        {outUrl && (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={outUrl} alt="实时换脸输出" className="w-40 rounded" />
        )}
      </div>
      <canvas ref={canvasRef} className="hidden" />

      {!running ? (
        <button
          type="button"
          disabled={sourcePath === ""}
          onClick={start}
          className="rounded bg-black px-4 py-2 text-white disabled:opacity-40"
        >
          开始
        </button>
      ) : (
        <button
          type="button"
          onClick={stop}
          className="rounded border border-black px-4 py-2"
        >
          停止
        </button>
      )}

      {error && <p role="alert" className="text-red-600">{error}</p>}
    </div>
  );
}
