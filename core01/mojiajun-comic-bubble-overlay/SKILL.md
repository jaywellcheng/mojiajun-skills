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

## PIL代码模式（已验证参数 2026-05-04）
```python
from PIL import Image, ImageDraw, ImageFont
# macOS: /System/Library/Fonts/STHeiti Light.ttc
# Linux: /usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc
font = ImageFont.truetype(font_path, 52)  # 52px — 1086x1448图上的正确尺寸
pad, radius = 35, 20

# 气泡：rounded_rectangle + 三角形尾巴（简单够用，不需要12圆云状）
# 填充：(255,255,255,242) 半透明白底，描边：(100,100,100,220) 3px
# 三角形：polygon从气泡底部中心向下22px，宽36px
# 文字：(25,10,5) 深棕，贴气泡内左上pad偏移
```

## 位置参数（1086x1448单格图，反复验证）
- **单角色面板**：y_pct=0.015（贴顶），x_pct按角色位置（左0.28/中0.50/右0.63）
- **气泡紧贴图片顶部边缘**，三角形尾巴向下指向下方人物——不挡脸
- **位置是百分比 × 图片像素**，每格需看图微调，没有通用坐标
- **本地PIL迭代比远程comic_bubbler快**：改参数→跑脚本→看结果，30秒一轮

## 已知陷阱
- 气泡不要放画面中央——必须偏移到说话人侧（用x_pct控制）
- **52px不是越大越好**——超过4个字的台词可能需要缩小或换行
- **GPT Image 2生图用`NO text`**防止自带乱码文字，PIL后叠加对白
- 群像格的气泡位置需逐个手动调，容易重叠
- macOS字体路径`/System/Library/Fonts/STHeiti Light.ttc`有效，PingFang.ttc无法用PIL打开
- **单格漫画（非2×2拼图）**用col=0,row=0即可，无需按格子计算偏移
- **本地PIL迭代速度远快于远程comic_bubbler**——改参数→跑脚本→看结果，30秒一轮。远程需走task_queue排队，每次2-5分钟
