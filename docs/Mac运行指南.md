# FaceForge · Mac / Apple Silicon 原生运行指南(CoreML,不走 docker)

> 目标:在 Apple Silicon(如 M4)本机跑通 **图片 / 视频 / 实时** 三场景,浏览器里看效果。
> 关键差异:Mac **没有 NVIDIA CUDA**,走 **CoreML / CPU** 执行后端;`docker-compose.yml` 的 `nvidia/cuda` 路径在 Mac **不可用**,改为本机原生起服务。
> 本文只给方案,不含实际下载/安装。真实版本以 FaceFusion / Deep-Live-Cam 最新 README 为准。

## 一、性能预期(Apple Silicon,CoreML)

| 场景 | 能跑 | 体感(M4/16G) | 说明 |
|------|------|----------------|------|
| 图片换脸 | ✅ | 几秒/张 | 质量与 CUDA 一致(同模型),只是慢一点 |
| 视频换脸 | ✅ | 分钟级起(逐帧) | 时长×分辨率越大越慢;先用短片/低分辨率验证 |
| 实时换脸 | ⚠️ | 个位数~十几 fps | CoreML 比 CUDA 慢;降分辨率/关增强可提帧率 |

> **画质**和 NVIDIA 机器一样,差别只在**速度**。16G 内存下视频建议 ≤720p、先剪短。

## 二、本机现状(2026-07-28 实测)

| 项 | 状态 | 需要 |
|----|------|------|
| 架构 | arm64 ✅ | — |
| Python | 仅 3.9.6 ❌ | FaceFusion 3.x 需 **3.10–3.12**,要装新 Python |
| ffmpeg | 缺 ❌ | 视频/实时必需 |
| brew / conda / pyenv | 缺 | 用来装上面几样 |
| git | 有 ✅ | — |
| 磁盘 / 内存 | 232G 空闲 / 16G | 够;模型 + 依赖预计占用数 GB |

## 三、前置安装(按序)

```bash
# 1. Homebrew(若已装可跳过)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. Python 3.11 + ffmpeg
brew install python@3.11 ffmpeg

# 3. Node/pnpm(前端;若已装可跳过)
brew install node
corepack enable && corepack prepare pnpm@10 --activate
```

## 四、引擎适配:让 FaceFusionRunner 走 CoreML(需改 1 处代码)

现有 `services/face-engine/engine/facefusion_runner.py` 组装的是 CUDA/通用命令。Mac 上要显式指定 **CoreML** 执行后端。**待应用的改动**(方案,尚未落地):

1. `FaceFusionRunner.__init__` 增参 `execution_providers: list[str] | None = None`(默认读环境变量 `FACEFORGE_EXECUTION_PROVIDERS`,Mac 设 `coreml`)。
2. `build_image_command` / `build_video_command` 末尾追加:
   ```python
   cmd += ["--execution-providers", *self._execution_providers]  # Mac: ["coreml"]
   ```
3. 对应加一条单测:`--execution-providers coreml` 出现在 argv。

> 我可以一键把这段改动 + 测试落到代码里(仍不下载模型)。本文档按「只写方案」保留为待应用项。

## 五、图片 / 视频:接真实 FaceFusion(CoreML)

```bash
# 1. 拉 FaceFusion 3.x
git clone https://github.com/facefusion/facefusion ~/facefusion
cd ~/facefusion
python3.11 -m venv .venv && source .venv/bin/activate

# 2. 安装(选默认 onnxruntime,macOS 自带 CoreML EP)
python install.py --onnxruntime default --skip-conda

# 3. 自测一张(首次会自动下载模型到 ~/.facefusion)
python facefusion.py headless-run \
  -s /path/source.jpg -t /path/target.jpg -o /path/out.jpg \
  --processors face_swapper face_enhancer \
  --face-swapper-model hyperswap_1a_256 \
  --face-enhancer-model codeformer \
  --execution-providers coreml
```

接入 FaceForge:起 API 时指定 FaceFusion 目录与后端——

```bash
export FACEFORGE_FACEFUSION_DIR=~/facefusion
export FACEFORGE_EXECUTION_PROVIDERS=coreml   # 配合第四节改动
```

> ⚠️ `hyperswap_1a_256` 部分算子 CoreML 可能回退 CPU,能跑但更慢;先用它验证画质,再按需在真机核对/换模型。视频记得机器已装 ffmpeg。

## 六、实时:接 Deep-Live-Cam(CoreML)

```bash
git clone https://github.com/hacksider/Deep-Live-Cam ~/deep-live-cam
cd ~/deep-live-cam
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt        # macOS 用 onnxruntime-silicon
# 模型(inswapper / GFPGAN)按其 README 放到 models/
```

把 Deep-Live-Cam 的逐帧换脸函数包成 `processor: bytes->bytes`,注入到 `RealtimeSession`
(替换默认 GPU stub)。当前 `get_realtime_processor()` 默认返回 `None`,Mac 上改成返回这个 CoreML processor 即可。

## 七、本机起全栈(不走 docker)

```bash
# 终端 A —— API(引擎)
source .venv/bin/activate   # FaceForge 根目录的 venv
export FACEFORGE_FACEFUSION_DIR=~/facefusion
export FACEFORGE_EXECUTION_PROVIDERS=coreml
uvicorn app.main:app --reload --app-dir services/api   # :8000

# 终端 B —— Web
export NEXT_PUBLIC_API_BASE=http://localhost:8000
pnpm --filter web dev                                   # :3000
```

浏览器开 `http://localhost:3000`:

| 场景 | 操作 |
|------|------|
| 图片 | `/image` 传源脸 + 目标图 → 开始换脸 → 看结果图 |
| 视频 | `/video` 传源脸 + 短视频 → 进度条 → 下载结果 |
| 实时 | `/realtime` 填 source_face_path → 允许**前置**摄像头 → 开始 |

## 八、常见坑

- **Python 版本**:系统 3.9.6 跑不了 FaceFusion 3.x,务必用 `python3.11`。
- **ffmpeg 缺失**:视频/实时会失败,先 `brew install ffmpeg`。
- **CoreML 回退 CPU**:某些算子不被 CoreML 支持会静默回退,表现为慢;可试 `--execution-providers coreml cpu` 组合。
- **webcam 权限**:浏览器首次会弹权限;`facingMode:"user"` 已强制前置。
- **内存**:16G 下视频别上 1080p/长片,先短片低分辨率;实时降分辨率、关增强提帧率。
- **模型 license**:`inswapper` 非商用;商用换 `hyperswap` 系并逐个核对。

## 九、只想快速看一张(不接 FaceForge)

不想起整套,只想眼见为实:装完 FaceFusion 后直接跑第五节第 3 步的 `headless-run`,输出图就是真实换脸效果——最快验证画质的方式。
