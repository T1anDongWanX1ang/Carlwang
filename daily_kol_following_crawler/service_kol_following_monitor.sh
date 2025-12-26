#!/bin/bash

# KOL Following 服务监控脚本
# 由 cron 定时运行，检查服务状态并自动重启

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_SCRIPT="$SCRIPT_DIR/start_service_kol_following.sh"
PID_FILE="$SCRIPT_DIR/twitter-crawler-kol-following.pid"
MONITOR_LOG="$SCRIPT_DIR/monitor_kol_following.log"

# 写入监控日志
log_monitor() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$MONITOR_LOG"
}

# 检查服务状态
check_service() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            return 0  # 服务运行中
        fi
    fi

    # 检查是否有运行中的进程（即使没有PID文件）
    RUNNING_PROCS=$(ps -ef | grep "[P]ython.*fetch_kol_followings" | wc -l | tr -d ' ')
    if [ "$RUNNING_PROCS" -gt 0 ]; then
        return 0  # 服务运行中
    fi

    return 1  # 服务未运行
}

# 主监控逻辑
if check_service; then
    log_monitor "✓ KOL Following 服务运行正常"
else
    log_monitor "✗ KOL Following 服务已停止，尝试重启..."

    if [ -f "$SERVICE_SCRIPT" ]; then
        "$SERVICE_SCRIPT" start >> "$MONITOR_LOG" 2>&1

        sleep 5

        if check_service; then
            log_monitor "✓ KOL Following 服务重启成功"
        else
            log_monitor "✗ KOL Following 服务重启失败"
        fi
    else
        log_monitor "✗ 服务管理脚本不存在: $SERVICE_SCRIPT"
    fi
fi

# 清理旧日志（保留最近1000行）
if [ -f "$MONITOR_LOG" ]; then
    LINE_COUNT=$(wc -l < "$MONITOR_LOG")
    if [ $LINE_COUNT -gt 1000 ]; then
        tail -n 1000 "$MONITOR_LOG" > "$MONITOR_LOG.tmp"
        mv "$MONITOR_LOG.tmp" "$MONITOR_LOG"
    fi
fi
