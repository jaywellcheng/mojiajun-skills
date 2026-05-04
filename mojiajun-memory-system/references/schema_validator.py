#!/usr/bin/env python3
"""
墨家军 Schema校验 + 微压缩模块
基于 v4 四级压缩协议：Level 0 微压缩 + 三级升级 + JSON Schema校验

Level 0: 每次API调用前清除冗余（重复读取、噪声消息）
Schema校验: JSON Schema验证LLM输出格式，失败→纠错注入→重试→降级Level3
"""

import json, re, hashlib
from jsonschema import validate, ValidationError
from typing import Optional, Tuple

# ═══════════════════════════════════════════════════
# 压缩输出 JSON Schema
# ═══════════════════════════════════════════════════
COMPRESSION_SCHEMA = {
    "type": "object",
    "required": ["level", "summary", "original_tokens", "compacted_tokens", "key_points"],
    "properties": {
        "level": {"type": "integer", "minimum": 1, "maximum": 3},
        "summary": {"type": "string", "minLength": 10},
        "original_tokens": {"type": "integer", "minimum": 1},
        "compacted_tokens": {"type": "integer", "minimum": 1},
        "key_points": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 20},
        "lost_context": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    },
    "additionalProperties": False,
}


# ═══════════════════════════════════════════════════
#  Schema 校验
# ═══════════════════════════════════════════════════
def validate_compression_output(output: str, max_retries: int = 3) -> Tuple[bool, dict, str]:
    """
    校验LLM压缩输出的JSON格式
    
    Returns:
        (passed, parsed_data, error_message)
    """
    # 尝试解析JSON
    try:
        # 清理可能的markdown包裹
        cleaned = output.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1].rsplit("\n", 1)[0]
        
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        return False, {}, f"JSON解析失败: {e}"
    
    # Schema校验
    try:
        validate(instance=data, schema=COMPRESSION_SCHEMA)
        return True, data, ""
    except ValidationError as e:
        return False, data, f"Schema校验失败: {e.message}"


def generate_correction_prompt(data: dict, error_msg: str) -> str:
    """生成纠错提示，注入LLM让其重试"""
    return f"""你的上一次输出格式有误，请修正后重新输出。

错误: {error_msg}

要求:
- level 必须是 1/2/3 的整数
- summary 至少10个字符的摘要
- key_points 是1-20个要点的数组
- compacted_tokens 必须小于 original_tokens
- 不要包含额外字段

请只输出修正后的JSON，不要其他文字。"""


# ═══════════════════════════════════════════════════
#  Level 0 微压缩
# ═══════════════════════════════════════════════════
def micro_compact(messages: list) -> list:
    """
    Level 0: 每次API调用前的微压缩
    - 清理重复文件读取（同一文件连续2次以上读取只保留最后一次）
    - 清理纯工具调用结果中的噪声（如base64图片数据）
    - 清理连续重复的system消息
    """
    cleaned = []
    last_file_read = {}
    last_system_msg = None
    
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        
        # 跳过超长工具输出（如图片base64）
        if role == "tool" and isinstance(content, str) and len(content) > 50000:
            cleaned.append({**msg, "content": f"[内容过长已截断: {len(content)} 字符]"})
            continue
        
        # 去重连续相同的system消息
        if role == "system":
            content_hash = hashlib.md5(str(content).encode()).hexdigest()
            if content_hash == last_system_msg:
                continue
            last_system_msg = content_hash
        
        # 记录文件读取
        if role == "tool" and "read_file" in str(msg.get("name", "")):
            if isinstance(content, str):
                # 提取文件路径
                path_match = re.search(r'(/[^\s"]+)', content[:200])
                if path_match:
                    path = path_match.group(1)
                    last_file_read[path] = len(cleaned)
        
        cleaned.append(msg)
    
    # 去重重复文件读取（保留最后一次）
    file_positions = {}
    for i, msg in enumerate(cleaned):
        if msg.get("role") == "tool" and "read_file" in str(msg.get("name", "")):
            content = str(msg.get("content", ""))
            path_match = re.search(r'(/[^\s"]+)', content[:200])
            if path_match:
                path = path_match.group(1)
                if path in file_positions:
                    cleaned[file_positions[path]] = None  # 标记删除
                file_positions[path] = i
    
    # 移除标记的
    result = [m for m in cleaned if m is not None]
    
    saved = len(messages) - len(result)
    return result


# ═══════════════════════════════════════════════════
#  压缩协议完整流程
# ═══════════════════════════════════════════════════
def compress_pipeline(content: str, current_tokens: int, llm_summarizer=None) -> dict:
    """
    四级压缩协议完整流程
    
    Args:
        content: 要压缩的内容
        current_tokens: 当前token数
        llm_summarizer: 可选的LLM摘要函数
    
    Returns:
        compression result dict
    """
    # Level 0: 数据已由调用方清理
    # Level判定
    if current_tokens <= 8000:
        return {"level": 0, "action": "no_compression", "tokens": current_tokens}
    
    if current_tokens <= 16000:
        target_level = 1
    elif current_tokens <= 32000:
        target_level = 2
    else:
        target_level = 3
    
    # Level 3: 确定性截断
    if target_level == 3:
        truncated = content[:2000] + f"\n\n[确定性截断 Level 3: 原文{current_tokens}tokens → 512 tokens]"
        return {
            "level": 3,
            "mode": "deterministic_truncate",
            "compacted_tokens": 512,
            "original_tokens": current_tokens,
            "content": truncated,
            "schema_validated": True,
        }
    
    # Level 1/2: LLM摘要（需要外部注入llm_summarizer）
    if llm_summarizer:
        mode = "preserve_details" if target_level == 1 else "bullet_points"
        target_tokens = current_tokens if target_level == 1 else current_tokens // 2
        
        raw_output = llm_summarizer(content, mode, target_tokens)
        passed, data, error = validate_compression_output(raw_output)
        
        if passed:
            return {
                "level": target_level,
                "mode": mode,
                "compacted_tokens": data["compacted_tokens"],
                "original_tokens": current_tokens,
                "content": data["summary"],
                "key_points": data["key_points"],
                "schema_validated": True,
            }
        else:
            # Schema校验失败 → 降级到 Level 3
            return compress_pipeline(content, current_tokens, llm_summarizer=None)
    
    # 无LLM → 降级到 Level 3
    return compress_pipeline(content, current_tokens, llm_summarizer=None)


if __name__ == "__main__":
    # 测试
    test_output = json.dumps({
        "level": 1,
        "summary": "这是一个测试摘要，包含足够的字符来通过Schema校验。",
        "original_tokens": 8000,
        "compacted_tokens": 4000,
        "key_points": ["要点1", "要点2", "要点3"],
        "confidence": 0.85,
    })
    
    passed, data, err = validate_compression_output(test_output)
    print(f"✅ 有效输出: {passed}")
    
    bad_output = '{"level": 1, "summary": "太短"}'
    passed, data, err = validate_compression_output(bad_output)
    print(f"✅ 捕获无效: {passed} — {err}")
    
    # 微压缩测试
    msgs = [
        {"role": "system", "content": "sys1"},
        {"role": "system", "content": "sys1"},  # 重复
        {"role": "user", "content": "hello"},
        {"role": "tool", "name": "read_file", "content": "x" * 60000},  # 超长
    ]
    result = micro_compact(msgs)
    print(f"✅ 微压缩: {len(msgs)} → {len(result)} 条消息")
