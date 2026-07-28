// 与 services/face-engine 的 pydantic schema 对齐(手工同步;真源见 engine/schemas.py)。

export type FaceEnhancer = "none" | "codeformer" | "gfpgan";
export type FaceSelectorMode = "reference" | "one" | "many";
export type JobStatus = "pending" | "running" | "done" | "failed";

export interface SwapQuality {
  swapper_model: string;
  face_enhancer: FaceEnhancer;
  face_enhancer_blend: number; // 0-100
  occlusion_mask: boolean;
}

export interface SwapParams extends Partial<SwapQuality> {
  trim_frame_start?: number;
  trim_frame_end?: number;
}

export interface JobState {
  id: string;
  status: JobStatus;
  progress: number; // 0-1
  output_path?: string | null;
  error?: string | null;
}

export interface ModelInfo {
  name: string;
  category: string;
  present: boolean;
}

export interface ModelsStatus {
  models: ModelInfo[];
  all_ready: boolean;
}
