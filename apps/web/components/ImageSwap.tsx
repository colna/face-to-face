"use client";

import { useState } from "react";
import { swapImage } from "@/lib/api";
import type {
  FaceEnhancer,
  FaceSelectorMode,
  QualityPreset,
  SwapParams,
} from "@/lib/types";
import { FilePicker } from "./FilePicker";

type PresetChoice = "custom" | QualityPreset;

export function ImageSwap() {
  const [source, setSource] = useState<File | null>(null);
  const [target, setTarget] = useState<File | null>(null);
  const [preset, setPreset] = useState<PresetChoice>("custom");
  const [enhancer, setEnhancer] = useState<FaceEnhancer>("codeformer");
  const [blend, setBlend] = useState(30);
  const [occlusion, setOcclusion] = useState(false);
  const [faceSelectorMode, setFaceSelectorMode] =
    useState<FaceSelectorMode>("many");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resultUrl, setResultUrl] = useState<string | null>(null);

  const canSubmit = source !== null && target !== null && !loading;

  async function onSubmit() {
    if (!source || !target) return;
    setLoading(true);
    setError(null);
    setResultUrl(null);
    try {
      const params: SwapParams =
        preset === "custom"
          ? {
              face_enhancer: enhancer,
              face_enhancer_blend: blend,
              occlusion_mask: occlusion,
              face_selector_mode: faceSelectorMode,
            }
          : { preset, face_selector_mode: faceSelectorMode };
      const blob = await swapImage(source, target, params);
      setResultUrl(URL.createObjectURL(blob));
    } catch (e) {
      setError(e instanceof Error ? e.message : "换脸失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <FilePicker label="源脸(Source)" accept="image/*" onSelect={setSource} />
      <FilePicker
        label="目标图(Target)"
        accept="image/*"
        onSelect={setTarget}
      />

      <label className="flex flex-col gap-1 text-sm">
        <span className="text-gray-600">换脸范围</span>
        <select
          value={faceSelectorMode}
          onChange={(e) =>
            setFaceSelectorMode(e.target.value as FaceSelectorMode)
          }
          className="rounded border border-gray-300 p-2"
        >
          <option value="many">全部人脸</option>
          <option value="one">第一张人脸</option>
          <option value="reference">参考脸匹配</option>
        </select>
      </label>

      <label className="flex flex-col gap-1 text-sm">
        <span className="text-gray-600">质量预设</span>
        <select
          value={preset}
          onChange={(e) => setPreset(e.target.value as PresetChoice)}
          className="rounded border border-gray-300 p-2"
        >
          <option value="custom">自定义</option>
          <option value="fast">快速</option>
          <option value="balanced">均衡</option>
          <option value="quality">质量优先</option>
        </select>
      </label>

      {preset === "custom" && (
        <>
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-gray-600">增强器</span>
            <select
              value={enhancer}
              onChange={(e) => setEnhancer(e.target.value as FaceEnhancer)}
              className="rounded border border-gray-300 p-2"
            >
              <option value="codeformer">CodeFormer</option>
              <option value="gfpgan">GFPGAN</option>
              <option value="none">不增强</option>
            </select>
          </label>

          <label className="flex flex-col gap-1 text-sm">
            <span className="text-gray-600">增强融合度 {blend}</span>
            <input
              type="range"
              min={0}
              max={100}
              value={blend}
              onChange={(e) => setBlend(Number(e.target.value))}
            />
          </label>

          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={occlusion}
              onChange={(e) => setOcclusion(e.target.checked)}
            />
            <span className="text-gray-600">遮挡蒙版</span>
          </label>
        </>
      )}

      <button
        type="button"
        disabled={!canSubmit}
        onClick={onSubmit}
        className="rounded bg-black px-4 py-2 text-white disabled:opacity-40"
      >
        {loading ? "换脸中…" : "开始换脸"}
      </button>

      {error && (
        <p role="alert" className="text-red-600">
          {error}
        </p>
      )}
      {resultUrl && (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={resultUrl} alt="换脸结果" className="max-w-full rounded" />
      )}
    </div>
  );
}
