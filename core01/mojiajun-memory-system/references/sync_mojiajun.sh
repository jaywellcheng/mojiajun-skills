#!/bin/bash
# 墨家军 双端同步脚本 — Mac(小川) ↔ CORE-01(小云)
# 用法: bash sync_mojiajun.sh [push|pull|status]

set -e

CORE01="core01"
REMOTE_SKILLS="/home/ubuntu/.hermes/skills/mojiajun"
REMOTE_QUEUE="/home/ubuntu/mojiajun-queue"
LOCAL_SKILLS="$HOME/.hermes/skills/mojiajun"
LOCAL_DESKTOP="$HOME/Desktop/墨家军资料库"

SYNC_ITEMS=(
    # (描述, 本地路径, 远程路径)
    "Skills|$LOCAL_SKILLS/mojiajun-memory-system/|$REMOTE_SKILLS/mojiajun-memory-system/"
    "Skills|$LOCAL_SKILLS/mojiajun-self-evolution/|$REMOTE_SKILLS/mojiajun-self-evolution/"
    "program.md|$LOCAL_DESKTOP/墨蓝_program.md|$REMOTE_QUEUE/program_墨蓝.md"
    "program.md|$LOCAL_DESKTOP/墨青_program.md|$REMOTE_QUEUE/program_墨青.md"
)

do_push() {
    echo "📤 推送到 CORE-01..."
    for item in "${SYNC_ITEMS[@]}"; do
        IFS='|' read -r desc local remote <<< "$item"
        if [ -e "$local" ]; then
            if [ -d "$local" ]; then
                ssh "$CORE01" "mkdir -p $remote" 2>/dev/null
                rsync -avz --delete "$local" "$CORE01:$remote" 2>&1 | tail -1
                echo "  ✅ $desc"
            else
                scp "$local" "$CORE01:$remote" 2>/dev/null && echo "  ✅ $desc"
            fi
        else
            echo "  ⚠️ $desc (本地不存在)"
        fi
    done
    echo "✅ Push 完成"
}

do_pull() {
    echo "📥 从 CORE-01 拉取..."
    for item in "${SYNC_ITEMS[@]}"; do
        IFS='|' read -r desc local remote <<< "$item"
        if [ -d "$local" ]; then
            mkdir -p "$local"
            rsync -avz "$CORE01:$remote" "$local" 2>&1 | tail -1
            echo "  ✅ $desc"
        else
            scp "$CORE01:$remote" "$local" 2>/dev/null && echo "  ✅ $desc"
        fi
    done
    echo "✅ Pull 完成"
}

do_status() {
    echo "📊 双端同步状态"
    echo ""
    for item in "${SYNC_ITEMS[@]}"; do
        IFS='|' read -r desc local remote <<< "$item"
        local_exists="❌"
        remote_exists="❌"
        [ -e "$local" ] && local_exists="✅"
        ssh "$CORE01" "[ -e $remote ]" 2>/dev/null && remote_exists="✅"
        printf "  %-40s 本地:%s  小云:%s\n" "$desc" "$local_exists" "$remote_exists"
    done
    
    echo ""
    echo "=== CORE-01 生产模块 ==="
    ssh "$CORE01" 'for f in lcm_tools.py lcm_map.py session_hooks.py context_monitor.py schema_validator.py memory_truncate.py phase2_utils.py; do
        if [ -f /home/ubuntu/mojiajun-queue/$f ]; then
            echo "  ✅ $f ($(wc -c < /home/ubuntu/mojiajun-queue/$f) bytes)"
        else
            echo "  ❌ $f"
        fi
    done'
    
    echo ""
    echo "=== 本地 Skill references ==="
    ls "$LOCAL_SKILLS/mojiajun-memory-system/references/" 2>/dev/null | while read f; do
        echo "  ✅ $f"
    done
}

case "${1:-status}" in
    push) do_push ;;
    pull) do_pull ;;
    status) do_status ;;
    *) echo "用法: $0 [push|pull|status]" ;;
esac
