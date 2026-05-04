---
name: fal-ai-ideogram-character-face-consistency
description: "用Fal.ai Ideogram Character API做人物一致性生图，以一张照片为参考在不同场景生成新图。包含CDN下载时机（关键经验）、prompt技巧、参数调优。"
---

# Fal.ai Ideogram Character - 人脸一致性生图

## 适用场景
需要以某张照片中的人物为主角，生成不同场景/服装/姿态的新图，同时保持面部特征一致。

## 引擎选择
**Fal.ai Ideogram Character API** 效果最好，面部一致性远优于：
- GPT Image 2 图生图（面部不够像）
- MJ cref（完全不像）

## 核心参数

### API端点
```
POST https://fal.run/fal-ai/ideogram/character
Authorization: Key {key_id}:{key_secret}
```

### 必填参数
- `prompt`: 场景描述
- `reference_image_urls`: [参考照片URL]
- `style`: "REALISTIC"

### 推荐参数
- `expand_prompt`: false（关掉自动扩写，防止画蛇添足）
- `image_size`: `{"width": 1152, "height": 1536}`（自定义尺寸比预设字符串更稳定）
- `num_images`: 1

## 关键经验（通过多次试错总结）

### 1. CDN下载时机（最重要！）
**API返回URL后必须等待至少60秒再下载。** 否则CDN上的图片还没渲染完成，下载到的图片下半部分是黑色的。

| 等待时间 | 文件大小 | 结果 |
|:--------:|:--------:|:----|
| 立即下载 | 3xx-6xx KB | ❌ 下半部分黑色 |
| 等30秒 | 6xx-8xx KB | ⚠️ 可能仍有黑边 |
| **等60秒** | **1.0-1.1 MB** | **✅ 完整无黑边** |

正确流程：
```
1. POST提交任务 → 拿到image_url ✅（约15-20秒）
2. 等待60秒让CDN完全渲染
3. 再下载图片 ✅（1MB左右，完整无黑边）
```

### 2. 图片尺寸格式
| 格式 | 黑边情况 | 说明 |
|:----|:--------|:----|
| 自定义 `{"width":1152,"height":1536}` | ✅ 稳定 | 推荐 |
| 预设 `"portrait_4_3"` | ⚠️ 有时出黑边 | 不推荐 |
| 预设 `"square_hd"` | ❌ 大面积黑边 | 不推荐 |
| 预设 `"landscape_16_9"` | ✅ 稳定 | 横版可用，后期裁竖版 |

结论：**竖版用自定义尺寸，横版用预设landscape_16_9。**

### 3. Prompt技巧
- 加 `"slim, fit"` → 修瘦
- 加 `"younger, around 28"` → 年轻化
- 加 `"normal proportions, not elongated"` → 防止人脸被拉长
- 加 `"sharp facial features, clear skin"` → 提升精致度
- 避免 `"close-up"` → 否则出大头照
- 用 `"half body, environmental portrait"` → 半身环境人像

### 4. 参考照片要求
- 必须公网可访问URL（CORE-01 8888端口）
- 单人正面照效果最好
- 格式: JPEG/PNG/WebP
- 单张不超过10MB

## 通过task_queue调用

```sql
-- 注册在module_dispatcher中: gen_ideogram
INSERT INTO task_queue (task_id, target_agent, task_type, payload, priority, status, source, created_at)
VALUES ('ideogram_01', 'moqing', 'gen_ideogram',
 '{"args":{"prompt":"场景描述","ref_image":"http://159.75.12.11:8888/me.jpg"}}',
 5, 'pending', 'xiaochuan', NOW());
```

## 费用
约$0.003-0.025/张，通过Fal.ai余额扣费。

## 代方案对比
| 方法 | 面部一致性 | 速度 | 需要 |
|:----|:---------:|:----:|:----|
| **Fal Ideogram Character** | ⭐⭐⭐⭐⭐ | ~80s | API Key |
| GPT Image 2 (Crun) | ⭐⭐⭐ | 3-15min | Crun credits |
| MJ cref (TT API) | ⭐⭐ | 45-60s | TT API Key |
| ComfyUI+IPAdapter | ⭐⭐⭐⭐⭐ | ~30s | GPU服务器 |