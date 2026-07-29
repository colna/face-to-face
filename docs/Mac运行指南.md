# FaceForge · Mac / Apple Silicon 原生运行指南(CoreML,不走 docker)

> 目标:在 Apple Silicon(如 M4)本机跑通 **图片 / 视频 / 实时** 三场景,浏览器里看效果。
> 关键差异:Mac **没有 NVIDIA CUDA**,走 **CoreML / CPU** 执行后端;`docker-compose.yml` 的 `nvidia/cuda` 路径在 Mac **不可用**,改为本机原生起服务。
> 本文已按 FaceFusion 3.7.1 / Deep-Live-Cam 2.1.6 实机核对。上游升级后仍应以对应版本 README 与 CLI 为准。

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
| Python | 3.11.15 ✅ | FaceFusion / Deep-Live-Cam 独立 venv 均用 3.11 |
| ffmpeg | 7.1.1 ✅ | 视频/实时可用 |
| brew / Node / pnpm | 6.0.10 / 22.22.0 / 10.33.0 ✅ | 前端工具链可用 |
| git | 有 ✅ | — |
| 内存 | 16G | 视频建议先用短片和低分辨率 |

## 三、前置安装(按序)

```bash
# 1. Homebrew(若已装可跳过)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. Python 3.11 + ffmpeg
brew install python@3.11 ffmpeg

# 3. Node/pnpm(前端;若已装可跳过)
brew install node
corepack enable && corepack prepare pnpm@10 --activate

# 4. FaceForge 自身依赖(仓库根目录)
python3.11 -m venv .venv
.venv/bin/pip install -e "services/face-engine[dev]" -e "services/api[dev]"
pnpm install --frozen-lockfile
```

## 四、引擎适配:让 FaceFusionRunner 走 CoreML(已应用)

`services/face-engine/engine/facefusion_runner.py` 已支持 Mac 所需配置:

1. `FaceFusionRunner.__init__` 支持 `execution_providers`,默认读环境变量 `FACEFORGE_EXECUTION_PROVIDERS`(Mac 设 `coreml`)。
2. 图片 / 视频命令会追加:
   ```python
   cmd += ["--execution-providers", *self._execution_providers]  # Mac: ["coreml"]
   ```
3. `FACEFORGE_FACEFUSION_PYTHON` 可指向 FaceFusion 自己的 Python 3.11 环境,避免 API 的 Python 环境误跑 FaceFusion。
4. 对应单测覆盖 CoreML argv、解释器选择和显式参数优先级。

## 五、图片 / 视频:接真实 FaceFusion(CoreML)

```bash
# 1. 拉 FaceFusion 3.x
git clone https://github.com/facefusion/facefusion ~/facefusion
cd ~/facefusion
python3.11 -m venv .venv && source .venv/bin/activate

# 2. 安装(选默认 onnxruntime,macOS 自带 CoreML EP)
# FaceFusion 3.7.x 安装器使用位置参数;旧版 3.6.x 请以对应 README 为准
python install.py default --skip-conda

# 3. 自测一张(首次会自动下载模型到 ~/facefusion/.assets/models)
python facefusion.py headless-run \
  -s /path/source.jpg -t /path/target.jpg -o /path/out.jpg \
  --processors face_swapper face_enhancer \
  --face-swapper-model hyperswap_1a_256 \
  --face-swapper-pixel-boost 256x256 \
  --face-enhancer-model codeformer \
  --face-enhancer-blend 30 \
  --face-mask-types box \
  --face-mask-blur 0.5 \
  --face-mask-padding 35 25 20 25 \
  --face-selector-mode many \
  --execution-providers coreml
```

接入 FaceForge:起 API 时指定 FaceFusion 目录与后端——

```bash
export FACEFORGE_FACEFUSION_DIR=~/facefusion
export FACEFORGE_FACEFUSION_PYTHON=~/facefusion/.venv/bin/python
export FACEFORGE_EXECUTION_PROVIDERS=coreml
```

> ⚠️ `hyperswap_1a_256` 部分算子 CoreML 可能回退 CPU,能跑但更慢;先用它验证画质,再按需在真机核对/换模型。视频记得机器已装 ffmpeg。
>
> `CodeFormer` 的融合度越高,最终结果越偏向增强器重建。实测 `80-90` 会明显削弱源人物身份；默认使用 `30`。目标脸有大胡须等遮挡时,`occlusion` 蒙版也可能保留过多目标脸,因此默认只使用 `box`。

## 六、实时:接 Deep-Live-Cam(CoreML)

```bash
git clone https://github.com/hacksider/Deep-Live-Cam ~/deep-live-cam
cd ~/deep-live-cam
python3.11 -m venv venv && source venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt

# requirements.txt 在 Apple Silicon 上安装 onnxruntime-silicon==1.16.3。
# 不要再按旧 README 片段降级到 1.13.1,该版本没有 Python 3.11 wheel。
python run.py --execution-provider coreml
```

首次启动会自动下载 FP32 `models/inswapper_128.onnx`;Apple Silicon 当前不会选用
`inswapper_128_fp16.onnx`。只有启用 GFPGAN 增强时才另需当前代码指定的
`models/gfpgan-1024.onnx`。

把 Deep-Live-Cam 的逐帧换脸函数包成 `processor: bytes->bytes`,注入到 `RealtimeSession`
(替换默认 GPU stub)。当前 `get_realtime_processor()` 默认返回 `None`,所以安装完成并不代表
FaceForge `/realtime` 已可换脸;仍需实现并注入这个适配器。

## 七、本机起全栈(不走 docker)

```bash
# 终端 A —— API(引擎)
source .venv/bin/activate   # FaceForge 根目录的 venv
export FACEFORGE_FACEFUSION_DIR=~/facefusion
export FACEFORGE_FACEFUSION_PYTHON=~/facefusion/.venv/bin/python
export FACEFORGE_EXECUTION_PROVIDERS=coreml
uvicorn app.main:app --reload --app-dir services/api   # :8000

# 终端 B —— Web
export NEXT_PUBLIC_API_BASE=http://localhost:8000
pnpm --filter web dev                                   # :3000
```

若 `3000` 已被占用,Next.js 会自动改用 `3001`;API 已允许这两个本地开发来源跨域访问。

浏览器开 `http://localhost:3000`(若被占用则看 Next.js 输出,本机实测为 `http://localhost:3001`):

| 场景 | 操作 |
|------|------|
| 图片 | `/image` 传源脸 + 目标图 → 开始换脸 → 看结果图 |
| 视频 | `/video` 传源脸 + 短视频 → 进度条 → 下载结果 |
| 实时 | `/realtime` 填 source_face_path → 允许**前置**摄像头 → 开始 |

## 八、常见坑

- **Python 版本**:FaceFusion / Deep-Live-Cam 均固定使用各自的 Python 3.11 venv,不要误用系统或项目的其他 Python。
- **ffmpeg 缺失**:视频/实时会失败,先 `brew install ffmpeg`。
- **CoreML 回退 CPU**:某些算子不被 CoreML 支持会静默回退,表现为慢;可试 `--execution-providers coreml cpu` 组合。
- **webcam 权限**:浏览器首次会弹权限;`facingMode:"user"` 已强制前置。
- **内存**:16G 下视频别上 1080p/长片,先短片低分辨率;实时降分辨率、关增强提帧率。
- **模型 license**:`inswapper` 非商用;商用换 `hyperswap` 系并逐个核对。

## 九、只想快速看一张(不接 FaceForge)

不想起整套,只想眼见为实:装完 FaceFusion 后直接跑第五节第 3 步的 `headless-run`,输出图就是真实换脸效果——最快验证画质的方式。
