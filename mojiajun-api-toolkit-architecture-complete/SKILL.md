---
name: mojiajun-api-toolkit-architecture-complete
description: "墨家军所有第三方API工具的完整架构和设计原则，含GPT Image 2中文渲染验证+区域封锁+引擎选择决策树。"
---

# 墨家军 API Toolkit 完整架构

## 整体架构

```
task_queue → module_dispatcher → api_toolkit/
  ├── tt_api.py          (MJ生图 - 艺术风格)
  ├── crun_api.py        (GPT Image 2 / 视频)
  ├── fal_api.py         (FLUX / Ideogram Character)
  ├── siliconflow_api.py (Kolors)
  ├── photoroom_api.py   (智能抠图)
  ├── glm_ocr.py         (图片文字提取)
  ├── zhipu_vision.py    (图片理解问答)
  ├── smart_engine.py    (智能引擎选择)
  ├── content_pipeline.py(内容生产流水线)
  ├── fallback_engine.py (失败自动切换)
  ├── seedance_video.py  (Seedance 2.0 视频生成)
  ├── cover_maker.py     (封面合成)
  ├── cost_monitor.py    (成本监控)
  └── media_search.py    (图片检索)
```

## 引擎选择决策树（2026-05-04更新）

### 中文文字渲染 — 关键发现

| 引擎 | 中文渲染 | 验证 |
|:---|:---:|:---|
| **GPT Image 2** (Crun) | ✅ 逐字正确 | 3图验证：松鼠杯海报/角色表/攻略信息图 |
| Gemini (nano-banana) | ❌ 100%乱码 | "天青浅"→"天精謎"，"喝茶"→"嗫茶" |
| MJ niji | ❌ 100%乱码 | 历史经验 |
| FLUX | ❌ 100%乱码 | 历史经验 |

> **结论：GPT Image 2 是目前唯一能原生渲染正确简体中文的模型。** 任何需要中文文字出图的场景，只有 GPT Image 2 能用。其他引擎必须 PIL 后期叠加中文。

### 各引擎最佳用途

| 场景 | 推荐引擎 | 原因 |
|:----|:--------|:-----|
| 需要中文文字出图 | **GPT Image 2 (Crun)** | 唯一正确渲染中文 |
| 小红书封面/配图 | GPT Image 2 (Crun) | 真实感最强 |
| 漫画/插画（无中文文字需求） | MJ niji 6 | 画风最好 |
| AI视频生成 | Seedance 2.0 (AIMLAPI/ModelsLab) | 分镜图→可控视频，$0.06/8秒 |
| 人脸一致性 | **Fal.ai Ideogram Character** | 面部最像 |
| 快速出图 | Fal.ai FLUX | 0.15秒，$0.003/张 |
| 艺术风格 | TT API MJ | 创意构图 |
| 图片文字提取 | GLM-OCR | 免费5000万Token |
| 图片理解问答 | GLM-4.6V | 免费6000万Token |

## 区域封锁情况（2026-05-04验证）

| API 提供商 | 图模型 | 中国区域可用？ |
|:---|:---|:---:|
| **Crun API** | gpt-image-2 | ✅（可能间歇故障） |
| **Crun API** | gemini (nano-banana) | ✅ |
| **OpenRouter** | openai/gpt-5.4-image-2 | ❌ 区域封锁 |
| **OpenRouter** | 全部图模型 | ❌ 全封锁 |
| **OpenAI 直连** | gpt-image-2 | ❌ 银联卡不支付 |

> **结论：从中国接入 GPT Image 2，唯一可行路径是 Crun API。** OpenRouter 和 OpenAI 直连均不可用。

## Crun API gpt-image-2 可用性

- 端点可能间歇故障（Internal Error），通常几小时内恢复
- 备选：gemini 模型可以出图（构图OK），但中文乱码
- 恢复检测：`python3 retry_gpt2.py`（部署在 CORE-01）

## 设计原则

### 1. 图片下载必须等待CDN渲染
Fal.ai等API返回URL后，CDN可能还没渲染完成，立即下载会拿到破损图片。
**规则**：提交任务后至少等待60秒再下载，观察文件大小确认完整性。

### 2. 人脸一致性首选Fal.ai Ideogram Character
- Fal.ai Ideogram Character > GPT Image 2 图生图 > MJ cref

### 3. 统一入口设计
所有API通过 `api_entry.py` 暴露给 `module_dispatcher`，参数格式统一为 `{"args": {...}}`

### 4. 素材自动归档
所有生成的图片通过 `media_assets` 表统一管理。

## 使用task_queue的好处

走task_queue vs 直接调API:
- ✅ 全记录可追溯
- ✅ 墨家军全员可见协作
- ✅ 失败自动重试
- ✅ 排队控制防刷额度
- ✅ 素材自动归档
- ✅ 成本核算

## 故障排查

### GPT Image 2 不可用
1. 先跑 `python3 retry_gpt2.py` 检测
2. 如果持续 Internal Error → 改用 gemini 出构图（无中文）
3. 等几小时重试

### worker不输出module_result
payload 格式必须为 `{"args": {"prompt": "...", ...}}`，不能直接传参。

### 区域封锁
OpenRouter 图模型全部封锁中国 → 只能用 Crun API。
