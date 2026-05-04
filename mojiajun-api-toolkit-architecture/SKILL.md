---
name: mojiajun-api-toolkit-architecture
description: Complete architecture of the 墨家军 api_toolkit — unified gateway for all third-party AI APIs (TT API/MJ, Crun.AI, Fal.ai, SiliconFlow, Photoroom), smart engine selection, fallback chains, and integration with module_dispatcher.
---

# 墨家军 API Toolkit 架构

## 目录结构
```
agent_outputs/moyuan/api_toolkit/
├── __init__.py              # 统一入口，导出所有模块
├── base_client.py           # 基础HTTP客户端（重试+轮询+超时）
├── tt_api.py                # TT API (Midjourney)
├── crun_api.py              # Crun.AI (GPT-Image-2/Gemini/视频)
├── fal_api.py               # Fal.ai (FLUX/Ideogram Character)
├── siliconflow_api.py       # SiliconFlow (Kolors)
├── photoroom_api.py         # Photoroom (抠图)
├── kling_api.py             # Kling (视频/待开权限)
├── minimax_api.py           # MiniMax (TTS语音/已充值未用)
├── glm_ocr.py               # 智谱GLM-OCR (图片文字提取)
├── zhipu_vision.py          # 智谱GLM-4.6V (图片理解问答)
├── smart_engine.py          # 智能引擎选择器
├── content_pipeline.py      # 内容生产流水线
├── fallback_engine.py       # 失败自动切换引擎
├── cover_maker.py           # 小红书封面合成
├── cost_monitor.py          # 成本监控
├── media_search.py          # 图片检索
└── watermark.py             # 图片加水印
```

## 统一入口 api_entry.py
所有API模块通过 `agent_outputs/moqing/api_entry.py` 暴露给 module_dispatcher。

```python
# 统一生图
def generate(**kwargs)      # 根据engine参数自动选择
def generate_mj(**kwargs)
def generate_flux(**kwargs)
def generate_crun(**kwargs)
def generate_ideogram(**kwargs)  # Fal Ideogram人脸一致

# 视频
def generate_video(**kwargs)

# 封面
def make_cover(**kwargs)     # 图片+文字=小红书封面
```

## 注册到 module_dispatcher
所有API通过 task_type 注册到 `TASK_MODULE_MAP`：

```python
"gen_image_flux":  ("moqing", "api_entry", "generate_flux"),
"gen_image_mj":    ("moqing", "api_entry", "generate_mj"),
"gen_image_crun":  ("moqing", "api_entry", "generate_crun"),
"gen_ideogram":    ("moqing", "api_entry", "generate_ideogram"),
"gen_video":       ("moqing", "api_entry", "generate_video"),
"make_cover":      ("moqing", "api_entry", "make_cover"),
"glm_ocr":         ("moyuan", "glm_ocr",   "parse"),
"glm_vision":      ("moyuan", "zhipu_vision", "analyze"),
"add_watermark":   ("moyuan", "watermark", "add_watermark"),
```

## 智能引擎选择
`smart_engine.py` 根据描述自动推荐最优引擎：

| 场景 | 推荐引擎 |
|:----|:--------|
| 小红书封面/配图 | GPT Image 2 (质量优先) |
| 产品图/快速出图 | Fal.ai FLUX |
| 艺术创意图 | TT API MJ |
| 人物一致性 | Fal Ideogram Character |

## 失败自动切换
`fallback_engine.py` 定义了引擎切换链：
```
GPT2失败 → FLUX → Gemini
FLUX失败 → Gemini → GPT2
MJ失败 → GPT2 → FLUX
```

## 视频生成
通过 Crun.AI 支持 Veo 3.1 / Sora 2 / Wan 2.6

## 关键注意事项
1. **Fal Ideogram下载必须等60秒CDN渲染**，不然有黑边
2. **参数传递**: dispatcher用 `payload.get("args", {})` 传给模块函数
3. **图片URL**: Fal/Crun返回的图片URL有时效性，需立即下载
4. **SSL验证**: Fal.ai的CDN在国内访问慢，`requests.get(verify=False)`
5. **智谱GLM**: 用Bearer token认证，端点 `api.z.ai/api/paas/v4/`
6. **Crun模型名**: 带路径格式如 `openai/gpt-image-2`、`google/veo3-1-t2v`
