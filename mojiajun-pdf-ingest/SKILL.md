---
name: mojiajun-pdf-ingest
description: 墨家军PDF摄入——本地PDF→Markdown+元数据，免API/GPU/Java。引擎pymupdf4llm(0.732分,0.09s/页)，可升级到OpenDataLoader(0.907分)。
category: mojiajun
tags: [pdf, markdown, knowledge-base, pymupdf4llm, rag, opendataloader]
---

# PDF摄入模块

## 一句话
本地PDF→结构化Markdown，存入知识库。免API、免GPU、免Java（当前引擎pymupdf4llm）。

## 引擎

| 引擎 | 得分 | 速度 | 依赖 | 状态 |
|------|------|------|------|------|
| pymupdf4llm | 0.732 | 0.09s/页 | Python原生 | ✅ 当前 |
| OpenDataLoader | 0.907 (#1) | 0.46s/页 | Java 11+ | 日后升级 |

## 使用

### CLI (Mac)
```bash
python3 ~/bin/pdf_ingest.py 论文.pdf output_dir/
```

### module_dispatcher (CORE-01)
```python
dispatch("pdf_ingest", {
    "action": "convert",
    "pdf_path": "/path/to/file.pdf",
    "output_dir": "/home/ubuntu/mojiajun-queue/knowledge/"
})
```

### 批量
```python
dispatch("pdf_ingest", {
    "action": "batch",
    "folder": "/path/to/pdfs/",
    "recursive": True,
})
```

### 知识库对接
```python
dispatch("pdf_ingest", {
    "action": "to_kb",
    "pdf_path": "/path/to/book.pdf",
    "kb_dir": "/home/ubuntu/mojiajun-queue/knowledge/",
    "note": "双轨学习-道-陶瓷工艺"
})
# → 生成 book.md + book.meta.json
```

## 输出
- `.md` — 结构化Markdown
- `.meta.json` — 元数据（页码/字数/引擎/备注）

## 升级到OpenDataLoader
```bash
brew install openjdk@17                    # Mac
pip install opendataloader-pdf             # 引擎
# 修改 pdf_ingest.py 中引擎切换即可
```

## 位置
- Mac: `~/bin/pdf_ingest.py`
- CORE-01: `/home/ubuntu/mojiajun-queue/agent_outputs/mozi/pdf_ingest.py`
- module_dispatcher: `pdf_ingest` → `mozi/pdf_ingest.main()`
