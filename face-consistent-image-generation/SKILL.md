---
name: face-consistent-image-generation
description: 人物一致性生图方案对比与实践——GPT Image 2 vs MJ cref vs Fal Ideogram Character，最佳方案为Fal Ideogram
---

# 人物一致性生图实战经验

## 背景

需要将一张真人照片作为参考，在不同场景下生成同一个人的图片（不同服装、背景、姿势），同时美化（更年轻、更帅）。这是内容生产中最常见的需求之一。

## 方案对比

| 方案 | 引擎 | 面部相似度 | 场景多样性 | 速度 | 费用 | 结论 |
|:----|:----|:---------:|:---------:|:---:|:---:|:----|
| **GPT Image 2 图生图** | Crun.AI | ⭐⭐ | ⭐⭐⭐⭐ | 6min(排队) | $0.02 | 面部不太像，衣服变化好 |
| **MJ cref** | TT API | ⭐ | ⭐⭐⭐ | 45s | $0.035 | 面部完全不像 |
| **Fal Ideogram Character** | Fal.ai | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 18s+60s等待 | $0.01-0.02 | ✅ **最佳方案** |

## 最佳方案：Fal.ai Ideogram Character API

### 调用方式

```bash
curl -s -X POST "https://fal.run/fal-ai/ideogram/character" \
  -H "Authorization: Key {key_id}:{key_secret}" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A slim handsome Chinese man around 28, sharp facial features, warm smile, wearing beige linen shirt, tropical beach sunset, environmental portrait",
    "reference_image_urls": ["http://your-server/photo.jpg"],
    "style": "REALISTIC",
    "image_size": {"width": 1152, "height": 1536},
    "num_images": 1,
    "expand_prompt": false
  }'
```

### Python代码

```python
import requests, time

API_KEY = "{key_id}:{key_secret}"
URL = "https://fal.run/fal-ai/ideogram/character"

resp = requests.post(URL, 
    headers={"Authorization": f"Key {API_KEY}", "Content-Type": "application/json"},
    json={
        "prompt": "场景描述",
        "reference_image_urls": ["参考图URL"],
        "style": "REALISTIC",
        "image_size": {"width": 1152, "height": 1536},
        "num_images": 1,
        "expand_prompt": False,
    },
    timeout=30
)

img_url = resp.json()["images"][0]["url"]
time.sleep(60)  # 关键！等CDN渲染

img_resp = requests.get(img_url, timeout=180)
with open("output.png", "wb") as f:
    f.write(img_resp.content)
```

### 关键发现

#### 1. CDN渲染延迟
- API返回URL后CDN可能还在处理
- 立即下载 → 半成品（300-500KB，下半部分黑屏）
- 等60秒 → 完整图（~1MB）
- **这不是API的问题，是下载时机的问题！**

#### 2. 图片尺寸
- ❌ 预设字符串如 `"portrait_4_3"`、`"square_hd"` → 可能有黑边
- ✅ 自定义尺寸 `{"width": 1152, "height": 1536}` → 完美

#### 3. 控制构图
- ❌ `"close-up"` → 大头照不好看
- ✅ `"environmental portrait, three-quarter body shot"` → 半身环境人像
- ✅ `"person in scene"` → 人在场景中
- ⚠️ **身体比例问题**：Ideogram有已知bug，脖子过长、头部比例偏大
  - 缓解方案：先用 `"landscape_16_9"` 横版生成（无黑边），然后本地裁剪成竖版
  - 或用3/4全身prompt + "natural proportions"关键词
  - 终极方案需要GPU + ComfyUI/IPAdapter，暂缓

#### 4. 美化prompt
```
"prompt": "A slim handsome Chinese man looking 10 years younger around age 28, 
           fit lean body, sharp facial features, clear healthy skin, 
           confident relaxed smile, natural proportions, normal neck length..."
```

#### 5. 多图策略
- 同一个 `reference_image_urls` 给所有场景
- 每个场景不同的prompt
- 每张提交后等60秒再下一张（避免限流，也给上一张CDN时间）

## 不推荐的方案

### GPT Image 2图生图
通过Crun.AI调用，模型ID `openai/gpt-image-2`。虽然支持传base64图片生成变体，但面部一致性不够好。适合纯文生图（质量很高），不适合人物保持。

### MJ cref
TT API的MJ支持 `--cref URL` 参数，但需要公网可访问的图片URL。实测面部还原度差，完全不像。不推荐。

## 完整测试结果

| 测试内容 | 结果 |
|:--------|:----|
| 城市精英场景 | ✅ 面部像，完整1.0MB |
| 海边度假场景 | ✅ 面部像，需等60秒下载 |
| 文艺咖啡馆场景 | ✅ 面部像 |
| 景德镇制瓷场景 | ✅ 面部像 |
| 半身人像 | ✅ 但脖子可能被拉长 |
| 正方形尺寸 | ❌ 大面积黑边（CDN未渲染完） |
