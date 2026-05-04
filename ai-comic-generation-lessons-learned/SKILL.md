---
name: ai-comic-generation-lessons-learned
description: >-
  AI工具4格漫画实战踩坑 — 多工具对比、失败原因、API响应陷阱、替代方案。
  适用于多场景叙事+角色一致性+中文文字的漫画配图任务。
---

# AI 4格漫画生成 — 踩坑与方案

## 核心结论
当前没有任何AI生图工具能可靠生成多场景叙事+角色一致+中文文字的4格漫画。
需要组合策略或降维替代方案。

## 工具对比

| 工具 | 风格 | 场景控制 | 角色一致 | 中文 | 结论 |
|------|------|---------|---------|------|------|
| FLUX | ❌差 | ⚠️中 | ⚠️中 | ❌乱码 | 不适合漫画 |
| MJ niji单张4格 | ✅好 | ❌失控 | ⚠️还行 | ❌乱码 | 场景混合 |
| MJ niji分格+seed | ✅好 | ✅单场景OK | ❌不同人 | ❌乱码 | seed不锁角色 |
| MJ --cref | ✅好 | ✅单场景OK | ❌不像 | ❌乱码 | cref效果差 |
| PIL纯代码 | — | ✅精确 | ✅100% | ✅完美 | ❌太简陋 |
| GPT Image(Crun) | ✅最强 | ✅最好 | 未测 | 未测 | Key截断 |

## TT API (MJ) 陷阱

### 图片URL字段
正确字段是 `cdnImage`，不是 `image_url`。变体在 `data.images[]` 数组。

### --niji 6 参数
不支持 `--style` 参数，传入会报 Invalid style code。

### --seed 不锁角色
同seed保证风格一致（色调笔触），不保证角色长相一致。

### 多场景失控
单prompt描述4个场景时MJ倾向于融合或自由发挥。

### 轮询参数
正常45-180秒，5秒间隔轮询，最多200秒超时。

## FLUX 陷阱
- 中文生成乱码，只能做视觉底图+PIL加字
- 漫画风格差，适合写实/设计感
- Fal Key格式: `key_id:key_secret` 冒号分隔
- 国内服务器访问Fal CDN需 `verify=False`

## 替代方案

### A. 聊天截图风格（推荐）
PIL模拟微信对话截图，头像固定角色100%一致，中文完美。

### B. 单图封面+正文
MJ一张封面图+文字叙事，小红书图文标配。

### C. 4张独立图（接受差异）
分4次生成，不追求角色一致。

## CORE-01 字体路径
```
/usr/share/fonts/truetype/wqy/wqy-microhei.ttc
/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf
```

## 未来方向
GPT Image 2最值得测试（理解力最强），等Crun Key恢复。
MJ Moodboards/sref 2025新特性可能改善角色一致性。
