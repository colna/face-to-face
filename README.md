# FaceForge (face-to-face)

自建、**质量优先**的 AI 换脸平台,一套系统覆盖 **图片 / 视频 / 实时** 三种换脸场景。数据不出本机,隐私优先。

> ⚠️ 仅限有知情同意的素材;不针对真实私人/公众人物做冒充;产物加溯源水印。非法用途(非自愿影像、诈骗、冒充)不支持。

## 技术选型
- 图片 / 视频换脸:**FaceFusion 3.6.x**(256 换脸器 + CodeFormer 增强 + 遮挡蒙版)
- 实时换脸:**Deep-Live-Cam**(CUDA/CoreML/DirectML/OpenVINO)
- 架构:monorepo —— `apps/web`(Next.js)+ `services/api`(FastAPI)+ `services/face-engine`(Python 引擎)

## 文档
- [产品需求 PRD](docs/PRD-产品需求文档.md)
- [技术架构](docs/技术架构文档.md)
- [任务拆解](docs/任务拆解文档.md)
- [任务进度](docs/任务进度.md)

## 状态
🚧 开发中(创造模式,文档先行 → Phase→Task 逐步实现)。**真实换脸推理需 NVIDIA GPU 机器**;开发沙箱内以 mock 单测覆盖编排逻辑。
