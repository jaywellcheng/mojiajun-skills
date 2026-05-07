---
name: fal-ai-ssl-cdn-timeout
description: Fal.ai FLUX图片生成 + Ideogram Character API集成经验——SSL绕过、CDN下载超时(110s)、认证格式、人物一致性生图、CDN渲染延迟
---

# Fal.ai FLUX + Ideogram Character API 集成经验

## 背景

Fal.ai提供极快的FLUX图片生成服务（0.15秒出图）和Ideogram Character API（人物一致性生图），但在中国大陆服务器上使用时有几个关键坑。

## 快速参考

### 认证方式
```bash
# 正确格式
curl -X POST "https://fal.run/fal-ai/flux/schnell" \
  -H "Authorization: Key {key_id}:{key_secret}" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"test","image_size":"square_hd","num_inference_steps":4}'
```

**不要用** `-u key:secret`（Basic Auth）——报401。
**不要用** `Authorization: Bearer xxx`——Fal.ai专用格式。

Python代码：
```python
self._headers = lambda: {"Authorization": f"Key {FAL_KEY}", "Content-Type": "application/json"}
```

### SSL验证问题（腾讯云服务器）

Python requests访问Fal.ai时SSL握手失败。curl正常但requests超时。
**解决方案：** 统一使用 `requests.Session()` + `session.verify = False`

```python
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class FalClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.verify = False  # 全局跳过SSL
```

### CDN下载速度
Fal.ai图片存储在海外CDN（`v3b.fal.media`），国内下载极慢：
- FLUX生成的图：约110秒/242KB
- Ideogram生成的图：约60-120秒/1MB
- **下载超时一定要设到180秒以上**

```python
def _download(self, url, index):
    resp = self.session.get(url, timeout=180)
```

### image_size参数
Fal.ai用预定义字符串，不能用像素值：

```python
VALID_SIZES = {
    "square_hd": "square_hd",       # 1024x1024
    "square": "square",             # 512x512  
    "portrait_4_3": "portrait_4_3", # 864x1152
    "portrait_16_9": "portrait_16_9",
    "landscape_4_3": "landscape_4_3",
    "landscape_16_9": "landscape_16_9",
}
```

**Ideogram Character API 建议用自定义尺寸：**
```json
"image_size": {"width": 1152, "height": 1536}
```

---

## Ideogram Character API（重点）

专门用于**上传参考照片、生成同一人物在不同场景下的新图**。效果比MJ cref好得多。

### 端点
```
POST https://fal.run/fal-ai/ideogram/character
```

### 请求参数
| 参数 | 必填 | 说明 |
|------|:----:|------|
| `prompt` | ✅ | 场景描述 |
| `reference_image_urls` | ✅ | 参考图URL数组（只支持1张） |
| `style` | 否 | `AUTO`/`REALISTIC`/`FICTION` 默认AUTO |
| `image_size` | 否 | 建议用自定义 `{"width": 1152, "height": 1536}` |
| `expand_prompt` | 否 | 默认`true`，设为`false`减少AI自由发挥 |
| `num_images` | 否 | 1 |

### 关键经验（踩坑记录）

### 人物一致性方案对比（2026-04-26实验结论）

| 方案 | 面部还原度 | 速度 | 费用 | 结论 |
|:----|:---------:|:----:|:----:|:----|
| **MJ cref** (TT API) | ❌ 完全不像 | 45s | $0.035 | 废弃 |
| **GPT Image 2 图生图** (Crun) | ⚠️ 一般 | 6min排队 | $0.02 | 可用但不够像 |
| **GPT Image 2 纯文字描述** | ❌ 更差 | 6min | $0.02 | 不如参考图 |
| **Fal Ideogram Character** | ✅✅ **基本一致** | 18-30s+60s | $0.015 | **最优方案** |

### Ideogram Character 终极工作流

```python
import requests, time

# 1. 提交任务（自定义尺寸+关闭expand_prompt）
resp = requests.post(
    "https://fal.run/fal-ai/ideogram/character",
    headers={"Authorization": f"Key {FAL_KEY}", "Content-Type": "application/json"},
    json={
        "prompt": "A slim handsome Chinese man around 28, ...场景描述...",
        "reference_image_urls": [REF_IMAGE_URL],
        "style": "REALISTIC",
        "image_size": {"width": 1152, "height": 1536},  # ← 必须自定义尺寸！
        "num_images": 1,
        "expand_prompt": False,  # ← 关闭!
    },
    timeout=30
)
img_url = resp.json()["images"][0]["url"]

# 2. ⏳ 核心：等60秒让CDN渲染
time.sleep(60)

# 3. 下载（完整图片约1MB）
img_resp = requests.get(img_url, timeout=180)
assert len(img_resp.content) > 800 * 1024  # 应>800KB
```

#### 1. ⚠️ CDN渲染延迟——最重要的发现

Fal API返回图片URL时CDN可能还没渲染完。**立刻下载会拿到半成品**（下半截黑屏、文件偏小）。

**症状：**
- 文件 <500KB → ❌ 未完成（下半部分黑屏，横版竖版都一样）
- 文件 ~1.0MB+ → ✅ 完整

**注意：** 这不是尺寸/比例问题——横版(landscape_16_9)也会黑边，正方形(square_hd)也会黑边。根因100%是CDN渲染未完成。**不是图片比例问题，不是API参数问题，就是CDN太慢。**

**正确流程：**
```python
# 1. 提交任务
resp = requests.post("https://fal.run/fal-ai/ideogram/character", ...)
img_url = resp.json()["images"][0]["url"]

# 2. ⏳ 必须等60秒以上让CDN完全渲染
time.sleep(60)

# 3. 再下载
resp2 = requests.get(img_url, timeout=120)
assert len(resp2.content) > 800000  # 应该>800KB
```

**验证完整性：**
```python
# 在服务器上验证（不要传回本地再检查，传回也会丢数据）
from PIL import Image
img = Image.open(filepath)
img.load()  # 强制加载全部像素
print(f"OK: {img.size} {len(open(filepath,'rb').read())//1024}KB")
```

**传输问题：** SSH管道 `cat file | ssh > local` 经常会截断图片。用 `scp` 或先在服务器验证完再传。

#### 2. 图片传输问题

SCP/管道传回本地经常不完整（图片截断）。
**安全做法：** 在服务器上用Python验证完整性后再传。

```python
from PIL import Image
img = Image.open(filepath)
img.load()  # 强制加载全部像素
print(f"OK: {img.size}")
```

#### 3. Prompt工程

**面部特征：** 要详细描述，但不需要太过精确——Ideogram Character API会自动从参考图提取。

**控制构图：**
- ❌ `"close-up"` → 大头照，不好看
- ✅ `"environmental portrait, three-quarter body shot"` → 半身环境人像
- ✅ `"person in scene"` → 人在场景中

**优化容貌（年轻帅气版）：**
```
"prompt": "A slim handsome Chinese man looking 10 years younger around age 28, fit lean body, sharp facial features, clear healthy skin, confident relaxed smile..."
```

**避免比例问题：**
- 有时脖子会被拉长（长颈鹿效果）→ 加 `"normal proportions, natural neck length"`
- 有时身材精壮但脸显得大 → 在prompt里平衡描述

#### 4. 多场景生成策略

如果要生成4张不同场景的图：
1. 用同一个 `reference_image_urls`
2. 每个场景不同的prompt
3. 每张提交后等60秒再下一张（避免限流）

---

## FLUX模型参数

- FLUX Schnell：4步推理，最快
- FLUX Dev：28步推理，质量更好
- FLUX Pro：高质量，但贵

## 费用参考

| 模型 | 约$ | 速度 |
|:----|:---|:----|
| FLUX Schnell | $0.003 | 0.15s |
| FLUX Pro | $0.025 | 1-2s |
| Ideogram Character | $0.01-0.02 | 18-30s |
