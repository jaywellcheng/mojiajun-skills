---
name: siliconflow-image-generation
description: SiliconFlow 文生图 API 调用——正确模型名、参数格式、水印处理，踩坑总结
category: mojiajun
---

# SiliconFlow 文生图

## 可用模型

`Kwai-Kolors/Kolors` — 已验证可用。FLUX 系列已禁用（code:30003）。

## 正确调用格式

```
POST https://api.siliconflow.cn/v1/images/generations
Authorization: Bearer {KEY}
Content-Type: application/json

{
  "model": "Kwai-Kolors/Kolors",
  "prompt": "图片描述",
  "image_size": "1024x1024",  ← 注意：不是 "size"
  "batch_size": 1
}
```

## 返回值

`data.images[0].url` — 临时链接，1小时有效。需立即下载到本地。

## 已失效的 API

- AIMLAPI `/v1/images/generations/` — 端点存在但需充值（新号0余额）
- PIAPI — 密钥验证失败
- ZHIPUAI 生图 — 令牌过期

## CORE-01 部署

Key 存在 `/home/ubuntu/mojiajun-queue/.env` 的 `SILICONFLOW_KEY`。
tools_api.py 中 `text2img_siliconflow()` 函数处理生图+水印。
