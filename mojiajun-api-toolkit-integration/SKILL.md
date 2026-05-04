---
name: mojiajun-api-toolkit-integration
description: 墨家军第三方API工具集成方法 — 将各类第三方AI服务集成到Agent系统的完整工作流：base_client→具体模块→统一入口→dispatcher注册，包含各API认证/参数/踩坑记录
---

# 墨家军第三方API工具集成方法

## 适用场景

当需要给墨家军（或类似多Agent系统）增加一个新的第三方API工具时，按照本流程操作。

## 整体架构

```
墨家军Agent → task_queue → module_dispatcher → api_entry.py
                                                      ↓
                                               api_toolkit/
                                               ├── base_client.py      ← 基础HTTP（重试+轮询+SSL绕过）
                                               ├── tt_api.py           ← Midjourney
                                               ├── crun_api.py         ← Crun.AI(100+模型)
                                               ├── fal_api.py          ← FLUX + Ideogram Character
                                               ├── siliconflow_api.py  ← SiliconFlow
                                               ├── photoroom_api.py    ← 抠图换背景
                                               ├── glm_ocr.py          ← 图片文字识别
                                               └── ...
```

## 集成步骤

### 第一步：写API模块文件

放到 `agent_outputs/moyuan/api_toolkit/` 目录下。

模板结构：
```python
#!/usr/bin/env python3
"""新API模块"""
import json, os, logging, requests
logger = logging.getLogger("模块名")
API_KEY = "xxx"
OUTPUT_DIR = "/home/ubuntu/mojiajun-queue/agent_outputs/moqing/generated/xxx"

class Client:
    def __init__(self):
        self.api_key = API_KEY
        self.stats = {"calls": 0, "failures": 0, "generated": 0}
        os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    def generate(self, prompt, **kwargs):
        # 1. 调API
        # 2. 下载结果到OUTPUT_DIR
        # 3. 返回结构化dict
        pass

def generate(prompt, **kwargs):
    return Client().generate(prompt, **kwargs)
```

### 第二步：包装文件（如果dispatcher从不同目录找）

dispatcher从 `agent_outputs/{target_agent}/` 下找模块文件。如果模块实际在 `moyuan/api_toolkit/` 下，需要在 `moqing/` 下放包装文件：
```python
# agent_outputs/moqing/xxx_api.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
from agent_outputs.moyuan.api_toolkit.xxx_api import generate
```

### 第三步：注册到module_dispatcher

```python
# 在 TASK_MODULE_MAP 中添加：
"task_type_name": ("moqing", "模块文件名", "函数名"),
```

### 第四步：验证

```python
from module_dispatcher import dispatch
r = dispatch("task_type_name", {"args": {"prompt": "test"}}, "moqing")
print(r["success"])
```

## disaptcher参数传递

```python
func_args = payload.get("args", {})  # 只取args字段
return func(**func_args)              # 解包传入
```

payload必须用 `args` 包装：
```json
{"task": "...", "args": {"prompt": "...", "model": "..."}}
```

## 各API认证方式速查

| 服务 | 认证Header | 格式 |
|:----|:-----------|:-----|
| TT API (MJ) | `TT-API-KEY` | 直接UUID |
| Crun.AI | `X-API-KEY` | `ak_xxx` |
| Fal.ai | `Authorization` | `Key {key_id}:{key_secret}` |
| SiliconFlow | `Authorization` | `Bearer {key}` |
| Photoroom | `x-api-key` | `sk_pr_xxx` |
| GLM-OCR | `Authorization` | `Bearer {key}` |
| MiniMax | `Authorization` | `Bearer {key}` |
| Kling | `Authorization` | `Bearer {JWT}`（需用AccessKey+SecretKey生成） |

## 各API踩坑记录

### Fal.ai Ideogram Character（最重要）
- ⚠️ CDN渲染延迟：API返回URL后要**等60秒再下载**，否则半成品（下半黑屏）
- 完整图约1.0MB，未完成约300-500KB
- SSL验证需要 `session.verify = False`
- image_size建议用自定义 `{"width": 1152, "height": 1536}` 而非字符串预设
- 人物一致性prompt：不需要极度详细的面部描述，引擎会自动从参考图提取

### Crun.AI GPT Image 2
- 排队久（约6分钟），但效果最好
- 图生图用 `image` 字段传base64
- 模型名格式：`openai/gpt-image-2`, `google/nano-banana`

### Kling AI
- 认证需生成JWT token（AccessKey + SecretKey）
- 国内端点：`api.klingai.com`，国际：`api-singapore.klingai.com`
- 需要先在klingai.com开API权限才能用

### MiniMax
- 需要API Key + Group ID两个信息
- TTS端点：`POST https://api.minimax.io/v1/t2a_v2`
- 音色ID：`male-qn-qingse`（男声）、`female-shaonv`（女声）

## 图片输出目录规范

```
agent_outputs/moqing/generated/
├── crun/          # Crun.AI
├── fal/           # Fal.ai
├── siliconflow/   # SiliconFlow
├── photoroom/     # Photoroom
├── covers/        # 封面合成
├── kling/         # Kling视频
└── minimax/       # MiniMax音频
```

## 素材库与归档

所有生成的图应自动归档到 `media_assets` 表：
```sql
INSERT INTO media_assets 
(asset_id, filepath, filename, file_size, category, source_engine, created_at)
VALUES (%s, %s, %s, %s, %s, %s, NOW());
```

归档脚本：`/tmp/archive_media.py`

看板访问：`http://159.75.12.11:8888/index.html`

### Seedance 2.0 视频生成（2026-04-28新增）

Seedance 2.0 是 ByteDance 的多模态视频模型，支持 text-to-video 和 image-to-video。
核心方法论（来自Topview文章）：**分镜先行 — 先用生图工具锁画面，再用参考帧生成视频，10条里8条能用**。

**两个API提供商，格式完全不同：**

| 维度 | AIMLAPI | ModelsLab |
|------|---------|-----------|
| 端点 | `POST /v2/video/generations` | `POST /api/v6/video/text2video` |
| 认证 | `Authorization: Bearer {key}` | `{"key": "..."}` 在JSON body里 |
| 模型ID | `bytedance/seedance-2-0` | `seedance-t2v` / `seedance-i2v` |
| 轮询方式 | `GET ?generation_id=xxx` | POST `fetch_result` URL |
| 图生视频 | `image_urls` 数组(最多9张) | `init_image` base64(单图) |
| Key格式 | 短字符串 | `796cg6...` 长字符串 |
| 新号额度 | 有免费额度 | ⚠️ 实测新号可能0额度 |

**核心踩坑**：
- Key格式不同——AIMLAPI短Key，ModelsLab长Key。用错端点返回401
- ModelsLab图生视频只支持单张 `init_image`（base64），不像AIMLAPI支持多图串联
- ModelsLab轮询不是简单的GET，而是POST `fetch_result` 带 `{"key": ...}`
- 墨家军当前 `seedance_video.py` 写的是AIMLAPI格式。如果用ModelsLab Key，需要写适配器

**分镜→视频工作流（方法论，不绑定平台）**：
```
1. GPT Image 2/MJ 生成关键帧图片（锁定人物/场景/服装）
2. 图片URL/Base64 → 视频API的参考帧输入
3. Prompt中串联分镜: "@Image1: 场景1, then @Image2: 场景2"
4. 成本 ~$0.06/条8秒720p视频
```
