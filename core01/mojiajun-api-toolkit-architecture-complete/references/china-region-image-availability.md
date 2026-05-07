# 中国区域图引擎可用性实测 (2026-05-04)

## 中文渲染能力矩阵

| 引擎 | 中文渲染 | 中国可用 | 实测结论 |
|:---|:---:|:---:|:---|
| **GPT Image 2** (Crun) | ✅ 唯一原生正确 | ⚠️ 端点常挂 | 3次 Internal Error |
| **Gemini NB** (Crun) | ❌ 全乱码 | ✅ 能用 | 构图正确，每个汉字被替换为随机形近字 |
| **GPT Image 2** (OpenRouter) | — | ❌ | 403: not available in your region |
| **Gemini NB** (OpenRouter) | — | ❌ | 同上，锁区 |
| **Seedream 4.5** (OpenRouter) | — | ❌ | 404 端点不存在 |
| **FLUX.2 Pro** (OpenRouter) | — | ❌ | No endpoints for image modality |
| **MJ niji** (TT API) | ❌ 乱码 | ✅ 能用 | 漫画画风碾压，中文需 PIL 后期叠加 |
| **FLUX** (Fal.ai) | ❌ 乱码 | ✅ 能用 | 快速出图，$0.003/张 |

## 中文测试 Prompt

三张测试图（角色表/产品海报/信息图），每张都包含精确的简体中文文本。

**Gemini 实测**：
- "喝茶" → "嗫茶" ❌
- "天青浅·松鼠杯" → "天精謎·粉鬆筆" ❌
- "景德镇三日攻略" → "悶徑埃三日頰路" ❌

**结论**：Gemini 只能生成"看起来像中文"的字符，无法精确还原指定文字。

## 接入路径

| 路径 | 状态 | 说明 |
|:---|:---|:---|
| Crun GPT Image 2 | ⏳ 等恢复 | 唯一可行路径，有 `retry_gpt2.py` 在CORE-01 |
| OpenAI 直连 | ❌ | 不支持银联卡 |
| OpenRouter | ❌ | 全锁区 |
| MJ+PIL | ✅ 当前方案 | 出图后用PIL叠加中文 |

## 相关文件

- prompt-forge Skill: `creative/gpt-image-2-prompt-forge/SKILL.md`
- 重试脚本: CORE-01 `/home/ubuntu/mojiajun-queue/retry_gpt2.py`
- Crun API: CORE-01 `agent_outputs/moyuan/api_toolkit/crun_api.py`
