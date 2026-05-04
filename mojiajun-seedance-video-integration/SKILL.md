---
name: mojiajun-seedance-video-integration
description: Seedance 2.0 AI视频生成集成到墨家军的完整方案——分镜图→可控视频工作流、PiAPI接入、dispatch注册、端到端测试。已验证C方案全链路贯通。核心方法论：分镜先行→视频可控，真实产品照优于AI生图。
tags: [mojiajun, seedance, video-generation, keyframe, ecommerce, content-production]
---

# 墨家军 Seedance 2.0 视频生成集成

## 核心方法论

来自 Topview.ai 文章的 insight（平台非必需，方法论可复制）：

```
旧方式：一段提示词 → AI抽卡猜画面 → 10条里2条能用
新方式：先生成关键帧图片（锁定画面）→ 用图片做参考帧生成视频 → 10条里8条能用
```

**本质**：将视频生成从"黑盒抽卡"变成"可控流水线"。

## Seedance 2.0 API 获取渠道

Seedance 2.0 是 ByteDance 的旗舰视频模型，通过以下 API 代理可调用：

### 渠道1: AIMLAPI（推荐，已集成）
- 端点: `POST https://api.aimlapi.com/v2/video/generations`
- 模型ID: `bytedance/seedance-2-0`
- 定价: ~$0.06/8秒 720p
- 注册: https://aimlapi.com/app/keys
- 免费额度: 新用户赠送

### 渠道2: ModelsLab（备选，免费额度多）
- 端点: `POST https://modelslab.com/api/v7/video-fusion/text-to-video`
- 模型ID: `seedance-20-multi-reference-to-video`
- 定价: $0.06~0.60/5秒 720p
- 注册: https://modelslab.com
- 免费额度: 新用户送额度，无需绑卡

### 关键参数
| 参数 | 说明 |
|------|------|
| `prompt` | 画面描述，用 @Image1, @Image2 引用参考图 |
| `image_urls` | 参考图URL列表（最多9张）← 核心：分镜串联 |
| `image_url` | 首帧图片 |
| `last_image_url` | 尾帧图片 |
| `aspect_ratio` | 16:9 / 9:16（竖屏小红书）/ 1:1 |
| `resolution` | 480p / 720p / 1080p |
| `duration` | 4 / 8 / 12 秒 |

## 部署架构

```
task_queue → module_dispatcher
  ├── gen_video_seedance   → moqing.api_entry.generate_video_seedance    # 直接调Seedance
  └── gen_keyframe_video   → moqing.api_entry.generate_keyframe_video    # 分镜串联模式
       ↓
  seedance_video.py (api_toolkit/)
    ├── SeedanceClient.create_video()    # 创建任务
    ├── SeedanceClient.poll_video()      # 轮询等结果
    ├── SeedanceClient.download_video()  # 下载到本地
    ├── SeedanceClient.generate()        # 一键: 创建+轮询+下载
    ├── SeedanceClient.generate_from_keyframes()  # 分镜串联: 3图+3描述→视频
    └── SeedanceClient.generate_single() # 单图生视频
```

## 文件位置

| 文件 | 路径 | 作用 |
|------|------|------|
| 核心模块 | `api_toolkit/seedance_video.py` | SeedanceClient 类 + 入口函数 |
| 统一入口 | `moqing/api_entry.py` (v3) | generate_video_seedance, generate_keyframe_video |
| 任务注册 | `module_dispatcher.py` | gen_video_seedance, gen_keyframe_video |
| API Key | `.env` → `AIMLAPI_KEY` | Bearer token |

## 分镜→视频工作流（天青浅松鼠杯示例）

### Step 1: 用 GPT Image 2 / MJ 生成分镜图

```
分镜1: "景德镇青花松鼠杯在白木茶桌上，午后阳光从窗外斜照，杯中茶汤金黄"
分镜2: "热水缓缓注入杯中，蒸汽袅袅升腾，松鼠捧松果图案清晰可见"
分镜3: "手捧杯子靠近唇边，背景虚化，温暖的家庭氛围"
```

### Step 2: 把分镜图放到可访问URL

可以上传到 CORE-01 的 media server: `http://159.75.12.11:8888/`

### Step 3: 调Seedance生成视频

```python
from agent_outputs.moyuan.api_toolkit.seedance_video import SeedanceClient

client = SeedanceClient()
result = client.generate_from_keyframes(
    keyframe_urls=[
        'http://159.75.12.11:8888/squirrel_cup_01.png',
        'http://159.75.12.11:8888/squirrel_cup_02.png', 
        'http://159.75.12.11:8888/squirrel_cup_03.png',
    ],
    scene_descriptions=[
        '青花松鼠杯在木茶桌上，午后阳光洒落',
        '热水注入杯中，蒸汽升腾',
        '手捧杯子抿一口，满足微笑',
    ],
    duration=8,
    aspect_ratio='9:16',  # 竖屏适配小红书
)
print(result['filepath'])  # 本地视频路径
print(result['usd_spent']) # 花费
```

### 通过 task_queue 派发

```sql
INSERT INTO task_queue (task_type, payload, priority) 
VALUES ('gen_keyframe_video', 
  '{"args": {
    "keyframe_urls": ["url1", "url2", "url3"],
    "scene_descriptions": ["场景1", "场景2", "场景3"],
    "duration": 8,
    "aspect_ratio": "9:16"
  }}', 
  5);
```

## 成本估算

| 视频长度 | 分辨率 | 价格 |
|----------|--------|------|
| 4秒 | 720p | ~$0.04 |
| 8秒 | 720p | ~$0.06 |
| 12秒 | 1080p | ~$0.12 |

对比传统拍视频（模特+摄影+灯光+剪辑 > ¥2000），成本可忽略不计。

## 对天青浅的适用场景

1. **产品展示视频**: 松鼠杯360°旋转 + 倒茶 + 喝茶（3张分镜→8秒视频）
2. **制陶过程**: 拉坯→修坯→画青花→上釉（4张分镜串联）
3. **景德镇风情**: 窑火→出窑→成品展示（氛围视频）
4. **跨境电商**: 直接生成英语产品视频发 TikTok/Instagram

## 踩坑记录

1. **图像URL必须公网可访问** — 不能用本地路径，需先上传到 media server 或使用CDN URL
2. **真实产品照片 >> AI生图** — 用真实照片做参考帧，产品零偏差；AI图（MJ/GPT）存在变形、细节不一致问题。正式产品视频必须用实拍。
   - ⚠️ **prompt必须锁定产品**：真实产品照做参考帧时，prompt只能描述环境和镜头，严禁加艺术风格标签
   - ❌ 禁用词：宫崎骏/吉卜力/anime风格/柔光滤镜/艺术化/手绘风 — AI会联想改动产品外形
   - ✅ 正确写法：「产品保持原样不动，杯型/把手/图案全部不变。仅改变环境：阳光、蒸汽、镜头推近」
   - ✅ 安全描述：光影（逆光/柔光/晨光）、镜头（推近/环绕/摇移）、环境（茶室/书房/窗边）、氛围（温暖/静谧/高级）
3. **CDN直传 vs 本地media server** — MJ CDN URL可直接给PiAPI省一步，但可能过期或被封IP；本地 `/tmp` + `http.server 8888` 更稳定
4. **轮询间隔15秒** — 生成5秒视频约需2-3分钟，8秒约需3-5分钟，首尾帧模式比纯文本慢
5. **dispatcher参数提取** — payload 必须用 `args` 包装，否则模块收空参（见 mojiajun-module-dispatch-pitfalls）
6. **task_id 字段必填** — task_queue 的 task_id 是 UNIQUE varchar，不能省略，需手动生成唯一ID
7. **target_agent 必填** — gen_video_seedance 和 gen_keyframe_video 的 target_agent 必须设为 `moqing`
8. **PiAPI临时URL会过期** — 视频的 ephemeral URL 仅短期有效，模块已自动下载到本地持久化
9. **5秒比8秒划算** — 5秒400万点(¥0.28) vs 8秒640万点(¥0.45)，首尾帧展示产品5秒足够

## C方案：全链路自动化（已验证 ✅ 2026-04-28）

### 三种模式的性能基准

| 模式 | 图片数 | 时长 | 耗时 | 点数 | 约¥ | 适用 |
|------|--------|------|------|------|------|------|
| text_to_video | 0 | 5s | ~2min | 400万 | 0.28 | 快速氛围 |
| text_to_video | 0 | 8s | ~2.5min | 640万 | 0.45 | 标准展示 |
| first_last_frames | 1张 | 5s | ~3min | 400万 | 0.28 | 单图动起来 |
| first_last_frames | 2张 | 8s | ~4.5min | 640万 | 0.45 | 首尾转场 |
| omni_reference | 3+张 | 8s | ~5min+ | 640万 | 0.45 | 多分镜串联 |

### 核心发现：真实产品照 >> AI生图

**最重要的结论**：用真实产品照片做参考帧，效果远好于MJ/GPT生成的AI图。AI图存在产品变形、细节不一致等问题，真实照片零偏差。推荐工作流：

```
手机拍产品照(2-3张不同角度)
  ↓
scp上传到 CORE-01:/tmp/
  ↓
通过 http://159.75.12.11:8888/ 访问
  ↓
派发 gen_keyframe_video(用本地URL)
  ↓
成品视频
```

MJ/CDN直传适用于没有实拍照片时快速出demo，但正式产品视频必须用真实照片。

### CDN直传技巧

MJ生成的图片自带CDN URL（`cdn.ttapi.io`），PiAPI可以直接访问，**无需上传到media server**。但如果CDN过期或PiAPI IP被封，就用本地media server兜底。

### task_queue 插入格式（完整字段）

```sql
-- text_to_video（无参考图）
INSERT INTO task_queue (task_id, target_agent, task_type, payload, priority)
VALUES ('vid_xxx', 'moqing', 'gen_video_seedance',
  '{"args": {"prompt": "...", "mode": "text_to_video", "duration": 5, "aspect_ratio": "9:16"}}', 5);

-- keyframe 单图（真实产品照）
INSERT INTO task_queue (task_id, target_agent, task_type, payload, priority)
VALUES ('kfv_xxx', 'moqing', 'gen_keyframe_video',
  '{"args": {"keyframe_urls": ["http://159.75.12.11:8888/photo.jpg"], "scene_descriptions": ["场景描述"], "duration": 5, "aspect_ratio": "9:16"}}', 5);

-- keyframe 双图（首尾帧转场）
INSERT INTO task_queue (task_id, target_agent, task_type, payload, priority)
VALUES ('kfv_xxx', 'moqing', 'gen_keyframe_video',
  '{"args": {"keyframe_urls": ["url1", "url2"], "scene_descriptions": ["场景1", "场景2"], "duration": 8, "aspect_ratio": "9:16"}}', 5);
```

⚠️ 注意：`task_id` 字段是必需的（UNIQUE varchar），不能省略。

### media server

CORE-01上 `python3 -m http.server 8888` 运行在 `/tmp` 目录。上传图片：
```bash
scp photo.jpg ubuntu@159.75.12.11:/tmp/
# 访问: http://159.75.12.11:8888/photo.jpg
```

### PiAPI临时URL会过期

视频的 `video_url`（`img.theapi.app/ephemeral/...`）是临时的，模块已自动下载到 `agent_outputs/moqing/generated/seedance/` 持久化。下载到本地：
```bash
scp ubuntu@159.75.12.11:/home/ubuntu/mojiajun-queue/agent_outputs/moqing/generated/seedance/*.mp4 ~/Desktop/
```

### C方案完整流程

```
产品实拍(2-3张不同角度) → scp到 /tmp/
  ↓
派发 gen_keyframe_video(keyframe_urls + scene_descriptions)
  ↓
PiAPI Seedance first_last_frames / omni_reference
  ↓
成品视频归档 seedance/ 目录
  ↓
配小红书文案 → 封面合成 → 准备发布
```
