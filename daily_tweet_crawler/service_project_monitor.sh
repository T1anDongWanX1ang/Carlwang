#!/bin/bash

# 项目推文服务监控脚本（TwitterAPI版）
# 建议cron: */5 * * * * /Users/qmk/Documents/QC/twitter/Carlwang/service_scripts/service_project_monitor.sh >/dev/null 2>&1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

SERVICE_NAME="twitter-crawler-project-twitterapi"
PID_FILE="$SCRIPT_DIR/${SERVICE_NAME}.pid"
LOG_FILE="$SCRIPT_DIR/service_project_twitterapi.log"
MONITOR_LOG="$SCRIPT_DIR/monitor_project.log"
START_CMD="$SCRIPT_DIR/start_service_project_twitterapi.sh start"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$MONITOR_LOG"
}

check_running() {
    if [ ! -f "$PID_FILE" ]; then
        log "PID文件不存在"
        return 1
    fi
    local pid=$(cat "$PID_FILE")
    if ! ps -p $pid > /dev/null 2>&1; then
        log "进程不存在 (PID: $pid)"
        return 1
    fi
    local cmdline=$(ps -p $pid -o command= 2>/dev/null)
    if [[ "$cmdline" != *"main.py"* ]] || [[ "$cmdline" != *"project-schedule"* ]]; then
        log "进程不是预期的项目爬虫: $cmdline"
        return 1
    fi
    # 日志是否近30分钟有更新
    if [ -f "$LOG_FILE" ]; then
        local mtime=$(stat -f %m "$LOG_FILE" 2>/dev/null || stat -c %Y "$LOG_FILE" 2>/dev/null)
        local now=$(date +%s)
        local diff=$((now - mtime))
        if [ $diff -gt 1800 ]; then
            log "日志30分钟未更新，可能卡住"
            return 1
        fi
    fi
    return 0
}

restart_service() {
    log "尝试重启服务..."
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if ps -p $pid > /dev/null 2>&1; then
            kill $pid
            sleep 3
            ps -p $pid > /dev/null 2>&1 && kill -9 $pid
        fi
        rm -f "$PID_FILE"
    fi
    eval "$START_CMD" >/dev/null 2>&1
    sleep 5
    if check_running; then
        log "重启成功"
    else
        log "重启失败，请手动检查"
    fi
}

# 避免并发运行
LOCK_FILE="/tmp/${SERVICE_NAME}_monitor.lock"
if [ -f "$LOCK_FILE" ]; then
    lock_time=$(stat -f %m "$LOCK_FILE" 2>/dev/null || stat -c %Y "$LOCK_FILE" 2>/dev/null)
    now=$(date +%s)
    if [ $((now - lock_time)) -lt 600 ]; then
        exit 0
    fi
fi

echo $$ > "$LOCK_FILE"

# 保持监控日志不膨胀
if [ -f "$MONITOR_LOG" ]; then
    tail -n 1000 "$MONITOR_LOG" > "$MONITOR_LOG.tmp" && mv "$MONITOR_LOG.tmp" "$MONITOR_LOG"
fi

if check_running; then
    exit 0
else
    restart_service
fi

rm -f "$LOCK_FILE"
