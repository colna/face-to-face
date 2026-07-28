# FaceForge (face-to-face)

自建、**质量优先**的 AI 换脸平台,一套系统覆盖 **图片 / 视频 / 实时** 三种换脸场景。数据不出本机,隐私优先。

> ⚠️ 仅限有知情同意的素材;不针对真实私人/公众人物做冒充;产物加溯源水印。非法用途(非自愿影像、诈骗、冒充)不支持。

## 架构

```
face-to-face/
  apps/web/            Next.js 15 + React 19 前端(图片/视频/实时页)
  services/api/        FastAPI 网关:REST(/swap/image、/swap/video、/jobs、/models)+ WS(/ws/realtime)
  services/face-engine/ Python 引擎:封装 FaceFusion / Deep-Live-Cam + 模型管理
  docker/              GPU Dockerfile + docker-compose(NVIDIA CUDA)
  docs/                PRD / 技术架构 / 任务拆解 / 任务进度 / 部署验证
```

数据流:

| 场景 | 路径 |
|------|------|
| 图片 | web 上传 → `POST /swap/image` → engine 同步换脸 → 返回结果图 |
| 视频 | web 上传 → `POST /swap/video` 建 job → 后台队列逐帧 → `GET /jobs/{id}` 轮询进度 → `GET /jobs/{id}/download` 下载 |
| 实时 | web 前置摄像头抽帧 → WS `/ws/realtime` → engine 逐帧 → WS 回帧 → web 渲染 |

## 技术选型

- 图片 / 视频换脸:**FaceFusion 3.6.x**(`hyperswap_1a_256` 换脸器 + CodeFormer 增强 + face-parser 遮挡蒙版)
- 实时换脸:**Deep-Live-Cam**(CUDA/CoreML/DirectML/OpenVINO)
- 换脸模型 `inswapper` 为 InsightFace **非商用**授权;商用走 `hyperswap` 系,逐个核对 license。

## 快速开始(开发)

前端 + 逻辑单测(无需 GPU):

```bash
pnpm install
pnpm --filter web dev        # http://localhost:3000
pnpm --filter web test       # 组件 + API client 单测
```

Python 引擎 / API(逻辑单测,mock 引擎,无需 GPU):

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e "services/face-engine[dev]" -e "services/api[dev]"
cd services/face-engine && pytest && ruff check . && mypy engine
cd ../api            && pytest && ruff check . && mypy app
uvicorn app.main:app --reload --app-dir services/api   # http://localhost:8000/docs
```

## 生产部署(需 NVIDIA GPU)

见 [docs/部署与验证.md](docs/部署与验证.md)。一句话:

```bash
cp .env.example .env
docker compose up --build      # 需 nvidia-container-toolkit
```

## API 参数(质量优先默认)

| 参数 | 默认 | 说明 |
|------|------|------|
| `swapper_model` | `hyperswap_1a_256` | 换脸器(商用友好) |
| `face_enhancer` | `codeformer` | `codeformer` / `gfpgan` / `none` |
| `face_enhancer_blend` | `80` | 0–100,增强融合度 |
| `occlusion_mask` | `true` | face-parser 遮挡蒙版 |
| `trim_frame_start/end` | – | 视频裁剪帧区间(仅 `/swap/video`) |

## 文档

- [产品需求 PRD](docs/PRD-产品需求文档.md)
- [技术架构](docs/技术架构文档.md)
- [任务拆解](docs/任务拆解文档.md)
- [任务进度](docs/任务进度.md)
- [部署与验证](docs/部署与验证.md)

## 状态

Phase 0–4 完成:文档、脚手架、完整引擎(schema/模型管理/图片·视频·实时封装)、完整 API(REST+WS)、完整 Web(三页 + 落地页)。**全部逻辑以 mock 单测覆盖(62 项)**。

⚠️ **真实换脸推理需 NVIDIA GPU**:图片/视频接 FaceFusion、实时接 Deep-Live-Cam,连同模型下载与 docker 镜像构建,只能在有卡机器验证(见部署文档,标 🖥️),开发沙箱内不假称跑通。
