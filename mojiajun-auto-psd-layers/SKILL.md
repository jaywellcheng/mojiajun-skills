---
name: mojiajun-auto-psd-layers
description: 墨家军PSD分层自动工具 — 输入图片，rembg智能抠图，输出可编辑的PSD分层文件（背景层+主体层）。适用于产品图、海报、封面等需要提取主体分层编辑的场景。
category: mojiajun
tags: [psd, rembg, auto-layers, cutout, photoshop]
created: 2026-05-06
author: 小川
---

# 墨家军 PSD 分层自动工具 v2

> 2026-05-06 三大升级：u2net高精度 + 多元素分割 + OCR文字层

## 一句话描述
给一张图，一键生成多层PSD：u2net抠图 + N个独立元素层 + OCR文字层。

## 核心能力（v2三大升级）
- **① u2net高精度抠图**：双模型 `u2net`(176MB精度)/`silueta`(42MB速度)，onnxruntime直载绕过GitHub下载
- **② 多元素分割**：scipy连通域分析，抠图后alpha通道自动拆分N个独立元素→各占一个PSD层
- **③ OCR文字层**：Tesseract(chi_sim+eng)检测文字区域→文字像素独立图层，可在PS中编辑替换
- **PSD多层输出**：背景层 + 元素层(1~N) + 文字层(1~N)，Photoshop直接打开编辑

## 使用方式

### 方式1：task_queue派发（推荐）
```sql
INSERT INTO task_queue (task_id, task_type, target_agent, payload, status, priority, created_at)
VALUES ('psd_xxx', 'auto_psd_layers', 'mozi',
  '{"image_url":"图片URL/路径", "model":"u2net", "multi_element":true, "ocr_text":true}',
  'pending', 5, NOW());
```

### 方式2：dispatch调用
```python
r = dispatch("auto_psd_layers", {
    "image_url": "/path/to/img.png",
    "model": "u2net",        # u2net(hq) / silueta(fast)
    "multi_element": True,   # 多元素分割
    "multi_min_area": 0.005, # 最小元素面积占比
    "multi_max": 8,          # 最多元素数
    "ocr_text": True,        # OCR文字层
    "ocr_lang": "chi_sim+eng",
    "ocr_conf": 40,          # 置信度阈值
})
```

## 技术栈
| 组件 | 用途 | 备注 |
|------|------|------|
| onnxruntime + u2net.onnx | 高精度抠图 | 169MB，绕pooch直载 |
| rembg (silueta) | 快速抠图 | 42MB回退方案 |
| scipy.ndimage | 多元素连通域分析 | 轻量无GPU |
| Tesseract + pytesseract | 中文OCR文字检测 | chi_sim+eng |
| pytoshop 1.2.1 | PSD文件生成 | 多层/通道/透明度 |
| PIL/Pillow | 图片处理 | 格式转换/缩放 |

## 输出格式
```json
{
  "success": true,
  "psd_path": "/path/to/layered_xxx.psd",
  "size_kb": 5391.3,
  "width": 600, "height": 400,
  "model": "u2net",
  "num_layers": 5,
  "layers": ["background-original", "element-1(25.8%)", "element-2(19.2%)",
             "text-景德镇(conf93)", "text-Y598(conf92)"],
  "num_elements": 2,
  "num_text_regions": 2,
  "timing": {"cutout": 2.06, "segment": 0.03, "ocr": 0.31, "psd": 0.03, "total": 2.89}
}
```

## PSD图层结构（从底到顶）
- **Layer 1: background-original** — 原始图，全不透明
- **Layer 2~N: element-N(XX%)** — 多元素分割，每个独立连通域一层，面积降序
- **Layer N+1~M: text-内容(confXX)** — OCR检测的文字像素层

## 适用场景
- ✅ 产品图主体提取+元素分离（松鼠杯、陶瓷等）
- ✅ 海报多元素独立编辑
- ✅ 产品包装文字提取编辑
- ✅ 漫画/多面板元素分离
- ⚠️ 密集重叠元素精度有限（连通域依赖分离度）
- ⚠️ OCR受字体风格影响（艺术字/手写字检出率下降）

## 性能（CPU/3.7GB RAM CORE-01实测）
| 图片尺寸 | u2net抠图 | 多元素分段 | OCR | 总耗时 |
|----------|----------|-----------|-----|--------|
| 600×400 | 0.8s | <0.1s | 0.3s | ~1.1s |
| 1024×1024 | 2.1s | <0.1s | 0.7s | ~2.9s |

## 限制
- 首次部署需确保 u2net.onnx(169MB) 在 `~/.u2net/` 目录
- silueta.onnx(42MB) 做快速回退
- Tesseract中文识别受字体影响（P/手写/艺术字准确率低）
- 复杂背景下小元素可能被u2net误判为背景

## 踩坑：u2net模型国内下载

### 问题
rembg用pooch从GitHub下载u2net.onnx（176MB），国内超时。

### 方案
1. **hf-mirror下载**：`curl -L https://hf-mirror.com/rippertnt/upscale/resolve/main/u2net.onnx`
2. **绕过pooch**：写`_DirectSession`包装类，直接用onnxruntime加载本地模型：
```python
class _DirectSession:
    def __init__(self, ort_sess, name):
        self.inner_session = ort_sess  # onnxruntime.InferenceSession
    def normalize(self, img, mean, std, size): ...
    def predict(self, img): ...  # 与U2netSession.predict()完全一致
```
3. hf-mirror的MD5与rembg期望不同（`a49bc8...` ≠ `60024c...`），但模型可用
4. 部署：`scp u2net.onnx → ~/.u2net/u2net.onnx`，169MB约35秒完成
