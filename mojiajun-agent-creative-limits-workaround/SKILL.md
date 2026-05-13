---
name: mojiajun-agent-creative-limits-workaround
description: 墨家军Agent创作能力边界、模块限制及替代方案 — 包含小红书内容创作绕过、封面图本地加工流程、module_dispatcher修复技巧
category: devops
---

# 墨家军Agent创作能力边界与替代方案

## Agent创作能力矩阵

| Agent | 角色 | data_analysis模块 | xiaohongshu_note模块 | 自由创作能力 |
|:------|:-----|:-----------------:|:--------------------:|:----------:|
| 墨橙 | 数据 | ✅ 分析报告 | ❌ | ❌ |
| 墨红 | 服务 | ✅ 分析报告 | ❌ | ❌ |
| 墨金 | 产品 | ✅ 分析报告 | ❌ | ❌ |
| 墨蓝 | 内容 | ❌ | ✅ **但被product模板限制** | ⚠️ |
| 墨渊 | 研究 | ✅ 分析报告 | ❌ | ❌ |
| 墨紫 | 设计 | ✅ 分析报告 | ❌ | ❌ |
| 墨青 | 图像 | ❌ | ❌ | ❌ |
| 墨创 | 营销 | ✅ 分析报告 | ❌ | ❌ |

## 关键发现

### 墨蓝的 xiaohongshu_note 模块限制
- 硬编码了 `mode: "product"`，固定输出松鼠杯产品参数
- payload中写明"不限主题、不限产品"仍被无视
- 即使给molan派 `data_analysis` 任务也只出分析报告不产出正文
- 触发条件：只要有 `note` 相关的payload，模块自动进入 product 模式

### 替代方案
```
小川本地创作 ← 推荐
└─ payload写清楚需求 → Agent完成基础分析 → 小川本地根据分析+人设手工写文
```

适用于：精确人设控制、口吻调整、产品不暴露的复杂创作场景

## iPhone实拍照片加工成小红书封面流程

### 格式预处理
iPhone实况照片存为JPEG但EXIF含多帧，vision_analyze可能报mpo错误：
```bash
sips -s format jpeg 001.jpg --out 001_conv.jpg
```

### 封面裁切
```python
from PIL import Image, ImageDraw, ImageFont

img = Image.open('photo.jpg')
w, h = img.size
# 小红书竖版 3:4，目标1080x1440
new_w = int(h * 3/4)
left = (w - new_w) // 2
cropped = img.crop((left, 0, left + new_w, h))
resized = cropped.resize((1080, 1440), Image.LANCZOS)

# 横版配图 4:3，目标1440x1080
target_w, target_h = 1440, 1080
left = (w - target_w) // 2
top = (h - target_h) // 2
cropped = img.crop((left, top, left+target_w, top+target_h))
resized = cropped.resize((1440, 1080), Image.LANCZOS)
```

### 中文字体路径
- macOS: `/System/Library/Fonts/STHeiti Medium.ttc`（华文黑体中）
- macOS备用: `/System/Library/Fonts/Supplemental/Songti.ttc`（宋体）
- f-string中不可包含反斜杠路径表达式，需先赋值给变量

### 文字叠加技巧
```python
draw = ImageDraw.Draw(img)

# 文字阴影（可读性提升）
draw.text((x+2, y+2), text, fill=(0,0,0,160), font=font_large)
draw.text((x, y), text, fill='white', font=font_large)

# 底部半透明条
overlay = Image.new('RGBA', (1080, 80), (0,0,0,130))
img.paste(overlay, (0, 1440-80), overlay)
```

### 纯色+文字风格图
```python
img = Image.new('RGB', (1080, 1440), '#FFF8F0')
d4 = ImageDraw.Draw(img)
# 暖色渐变
for y in range(1440):
    r = int(255 - y * 0.05)
    g = int(248 - y * 0.04)
    b = int(240 - y * 0.06)
    d4.line([(0, y), (1080, y)], fill=(max(r,200), max(g,190), max(b,170)))
```

## module_dispatcher 引号修复
当sed操作破坏Python字典key引号时，不要用sed逐行修复。

### 推荐修复方式
写一个Python修复脚本上传到服务器执行：
```python
with open('/home/ubuntu/mojiajun-queue/module_dispatcher.py', 'r') as f:
    lines = f.readlines()

# 直接替换指定行
old_line = lines[29]
new_line = '    "sample_analysis":       ("moyuan",   "sample_analyzer",        "analyze"),\\n'
lines[29] = new_line

with open('/home/ubuntu/mojiajun-queue/module_dispatcher.py', 'w') as f:
    f.writelines(lines)
```

### 全局key修复（批量处理所有残缺引号）
```python
import re
with open('module_dispatcher.py', 'r') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    m = re.match(r'^(\\s+)(\\w[\\w_]*)(\\s*:\\s*\\()', line)
    if m and not m.group(2).startswith('"'):
        lines[i] = f'{m.group(1)}"{m.group(2)}":{m.group(3)}'

with open('module_dispatcher.py', 'w') as f:
    f.writelines(lines)
```

### 语法验证
```bash
python3 -c 'import py_compile; py_compile.compile("/path/to/module_dispatcher.py", doraise=True); print("syntax OK")'
```

## 注意事项
- textbbox 返回值是 (left, top, right, bottom)，文字宽度 = right - left
- Quality=95 的JPEG输出平衡文件大小和画质
- 多任务批量派发时注意 task_id 不能重复，用 `CONCAT('prefix_', UNIX_TIMESTAMP(), '_suffix')` 生成
