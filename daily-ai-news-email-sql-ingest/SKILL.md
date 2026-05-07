---
name: daily-ai-news-email-sql-ingest
description: Process daily_ai_news SQL files sent by 小墨 (mobai_cheng@coze.email) via email attachment — extract base64 SQL from MIME, remap fields when schema mismatches, and ingest into Docker MySQL
version: 1.0.0
author: 小云
prerequisites:
  commands: [himalaya, mysql, python3]
  files:
    - ~/.config/himalaya/config.toml (IMAP/SMTP config for 76835298@qq.com)
---

# Daily AI News Email SQL Ingestion

## When to Use

小墨 (mobai_cheng@coze.email) sends daily AI news SQL files via email to 76835298@qq.com at ~3:00 AM each day. Use this workflow when:

- User says "收邮件" or "查小墨的邮件"
- You see emails with subject "AI日报数据入库SQL - YYYYMMDD" in the inbox
- The SQL needs to be ingested into `ceramic_db.daily_ai_news` table in Docker MySQL

## Step 1: List & Find the Emails

```bash
export PATH=$HOME/.local/bin:$PATH
himalaya envelope list --page 1 --page-size 50
```

Look for emails from `mobai_cheng@coze.email` with subject pattern `AI日报数据入库SQL - 2026xxxx`.

## Step 2: Check if Already Imported

Check the latest `news_date` in the table to avoid duplicates:

```bash
mysql -h 127.0.0.1 -P 3306 -u ceramic_remote -pceramic_2026 ceramic_db \
  -e "SELECT MAX(news_date) FROM daily_ai_news;"
```

## Step 3: Export Raw MIME & Extract Attachment

⚠️ **Important pitfall**: `himalaya attachment download <ID>` often fails with `/tmp/` path errors. 
**Workaround**: Export the full raw MIME and extract base64 manually.

```bash
# Export full MIME
cd /home/ubuntu
export PATH=$HOME/.local/bin:$PATH
himalaya message export <MSG_ID> 2>/dev/null > msg<MSG_ID>.eml
```

Then extract the base64 attachment with Python:

```python
import base64
with open(f'msg{msg_id}.eml', 'r', errors='replace') as f:
    content = f.read()

# Split on the attachment headers to find base64 content
_, after = content.split(
    'Content-Transfer-Encoding: base64\n'
    'Content-Type: application/octet-stream; name="daily_ai_news_YYYYMMDD.sql"\n\n'
)
b64, _ = after.split('\n\n--', 1)
b64 = ''.join(b64.strip().splitlines())
sql = base64.b64decode(b64).decode('utf-8')

with open(f'daily_ai_news_YYYYMMDD.sql', 'w') as f:
    f.write(sql)
```

## Step 4: Fix Database Name

The SQL uses `USE mojiajun;` but the actual database is `ceramic_db`. Fix:

```bash
sed 's/USE mojiajun;/USE ceramic_db;/' daily_ai_news_YYYYMMDD.sql > daily_ai_news_YYYYMMDD_fixed.sql
```

## Step 5: Handle Schema Mismatch

⚠️ **Key pitfall**: 小墨's SQL uses these columns:
- `category`, `keyword`, `title`, `content`, `source_url`, `published_at`, `created_at`

But the actual `ceramic_db.daily_ai_news` table has:
- `id` (auto_increment), `news_date`, `keyword`, `title`, `url`, `summary`, `source`, `created_at`

**Field mapping**:

| SQL Column | Table Column |
|-----------|-------------|
| `published_at` | `news_date` |
| `keyword` | `keyword` |
| `title` | `title` |
| `source_url` | `url` |
| `content` | `summary` |
| `category` | `source` |
| `created_at` | `created_at` |

Use a Python parser to remap. Extract the INSERT values, map fields, and regenerate:

```python
import re

sql = open('daily_ai_news_YYYYMMDD_fixed.sql').read()
inserts = re.findall(
    r"INSERT INTO daily_ai_news \((.*?)\) VALUES\n(.*?);", sql, re.DOTALL
)

field_map = {
    'category': 'source', 'keyword': 'keyword', 'title': 'title',
    'content': 'summary', 'source_url': 'url',
    'published_at': 'news_date', 'created_at': 'created_at'
}
new_fields_order = ['news_date', 'keyword', 'title', 'url', 'summary', 'source', 'created_at']

# Parse value tuples respecting quoted strings
rows = []
for fields_str, values_str in inserts:
    fields = [f.strip() for f in fields_str.split(',')]
    
    # Parse parenthesized value groups
    raw_rows = []
    depth = 0
    current = ''
    for c in values_str.strip():
        if c == '(' and depth == 0:
            current = '('; depth = 1
        elif c == '(':
            current += c; depth += 1
        elif c == ')':
            current += c; depth -= 1
            if depth == 0: raw_rows.append(current)
        else:
            if depth > 0: current += c
    
    for row in raw_rows:
        # Parse CSV respecting quotes
        vals = []
        cur = ''; in_q = False; qc = None
        for c in row[1:-1]:
            if in_q:
                cur += c
                if c == qc: in_q = False
            elif c in ("'", '"'):
                in_q = True; qc = c; cur = c
            elif c == ',':
                vals.append(cur.strip()); cur = ''
            else:
                cur += c
        if cur.strip(): vals.append(cur.strip())
        
        old_row = dict(zip(fields, vals))
        new_vals = [old_row.get(k, 'NULL') 
                     for k in ['published_at', 'keyword', 'title', 'source_url', 'content', 'category', 'created_at']]
        rows.append(new_vals)

# Generate converted SQL
new_sql_lines = [f"USE ceramic_db;\n"]
new_sql_lines.append(f"INSERT INTO daily_ai_news ({', '.join(new_fields_order)}) VALUES\n")
for i, vals in enumerate(rows):
    new_sql_lines.append(f"({' ,'.join(vals)})" + (',' if i < len(rows)-1 else ';') + '\n')

with open(f'daily_ai_news_YYYYMMDD_converted.sql', 'w') as f:
    f.writelines(new_sql_lines)
```

## Step 6: Execute

```bash
mysql -h 127.0.0.1 -P 3306 -u ceramic_remote -pceramic_2026 ceramic_db \
  < daily_ai_news_YYYYMMDD_converted.sql
```

## Step 7: Verify

```bash
mysql -h 127.0.0.1 -P 3306 -u ceramic_remote -pceramic_2026 ceramic_db \
  -e "SELECT id, news_date, keyword, LEFT(title, 40), LEFT(source, 10) FROM daily_ai_news ORDER BY id DESC LIMIT 5;"
```

## Troubleshooting

### Cannot find base64 delimiter
The email may use a different boundary string. Check the raw MIME:
```bash
grep -n "boundary" msg<ID>.eml
```
Then split on the actual boundary instead.

### Another INSERT format
Sometimes the SQL has multiple INSERT statements (separate from the main data). Parse each one separately.

### Docker MySQL not running
Check with `docker ps | grep mysql` — the container name is `ceramic-mysql`.
