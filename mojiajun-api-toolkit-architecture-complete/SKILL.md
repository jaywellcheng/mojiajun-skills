---
name: mojiajun-api-toolkit-architecture-complete
description: "墨家军所有第三方API工具的完整架构和设计原则，包括统一调度层、智能引擎选择、失败切换等"
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

## 设计原则

### 1. 图片下载必须等待CDN渲染
Fal.ai等API返回URL后，CDN可能还没渲染完成，立即下载会拿到破损图片。
**规则**：提交任务后至少等待60秒再下载，观察文件大小确认完整性。

### 2. 人脸一致性首选Fal.ai Ideogram Character
- Fal.ai Ideogram Character > GPT Image 2 图生图 > MJ cref
- 需要有参考照片的公网URL
- 下载时机影响图片完整性

### 3. 统一入口设计
所有API通过 `api_entry.py` 暴露给 `module_dispatcher`，参数格式统一为 `{"args": {...}}`

### 4. 素材自动归档
所有生成的图片通过 `media_assets` 表统一管理，支持按分类/引擎/日期检索。

## 各引擎最佳用途

| 场景 | 推荐引擎 | 原因 |
|:----|:--------|:-----|
| 小红书封面/配图 | GPT Image 2 (Crun) | 真实感最强 |
| AI视频生成 | Seedance 2.0 (AIMLAPI/ModelsLab) | 分镜图→可控视频，$0.06/8秒 |
| 人脸一致性 | **Fal.ai Ideogram Character** | 面部最像（详情见 face-consistent-image-generation skill） |
| 快速出图 | Fal.ai FLUX | 0.15秒，$0.003/张 |
| 艺术风格 | TT API MJ | 创意构图，但真实感不如GPT2 |
| 图片文字提取 | GLM-OCR | 免费5000万Token |
| 图片理解问答 | GLM-4.6V | 免费6000万Token |

## 引擎选择策略（2026-04-26实验结论）

**人脸一致性排名：**
1. 🥇 Fal.ai Ideogram Character — 面部几乎一模一样
2. 🥈 GPT Image 2 图生图 — 面部不太像
3. ❌ MJ cref — 完全不像

**真实感排名：**
1. 🥇 GPT Image 2 — 物理真实感最强
2. 🥈 Fal.ai FLUX — 快速但质量好
3. 🥉 TT API MJ — 艺术风格好但真实感不如前两者

## 素材库看板

- URL: http://159.75.12.11:8888
- 自动归档cron: 每10分钟
- 支持搜索、分类筛选、点击放大预览
- 敏感图片（人像）需从web目录删除

## 使用task_queue的好处

走task_queue vs 直接调API:
- ✅ 全记录可追溯
- ✅ 墨家军全员可见协作
- ✅ 失败自动重试
- ✅ 排队控制防刷额度
- ✅ 素材自动归档
- ✅ 成本核算
- 额外延迟：最多多等5秒（Worker轮询间隔）

## 故障排查

### worker不输出module_result
Dispatcher从 `payload.get("args", {})` 取参数作为 `**kwargs` 传给模块函数。
如果payload没有args字段，传进去的是空字典 `{}`，模块收不到参数。
**修复：** payload格式必须为 `{"args": {"prompt": "...", ...}}`
