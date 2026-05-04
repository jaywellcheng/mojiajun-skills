---
name: mojiajun-comic-bubble-overlay
description: 漫画气泡叠加标准流程——云状气泡+三角形尾巴+说话人前缀+位置精调
---

# 漫画气泡叠加标准流程

## 核心原则
1. 气泡靠近说话人，三角形尾巴指向说话人头部
2. "角色名："前缀明确说话人
3. 不遮挡人物面部
4. 每格位置独立调整，没有通用坐标

## PIL代码模式
```python
from PIL import Image, ImageDraw, ImageFont
font = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", 18)

# 云状气泡：12-14个变径小圆围边 + 半透明填充(alpha≈200)
# 三角形尾巴：polygon从气泡底部指向说话人
# 文字：深棕色(30,15,5)，逐行居中
```

## 已知陷阱
- 气泡文字不要放画面中央，必须偏移到说话人侧
- 小字号(16px)用于短台词，大字号(18px)用于长台词
- 原图可能自带文字(GPT Image BUG)，PIL遮盖会破坏画面，优先重出整格
- 群像场景气泡不要互相重叠
