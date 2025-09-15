#!/bin/bash

# 服务监控脚本 - 确保Twitter爬虫服务持续运行
# 建议通过cron每5分钟运行一次: */5 * * * * /path/to/service_monitor.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

SERVICE_NAME="twitter-crawler"
PID_FILE="$SCRIPT_DIR/${SERVICE_NAME}.pid"
LOG_FILE="$SCRIPT_DIR/service.log"
MONITOR_LOG="$SCRIPT_DIR/monitor.log"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$MONITOR_LOG"
}

check_service_health() {
    if [ ! -f "$PID_FILE" ]; then
        log_message "警告: PID文件不存在"
        return 1
    fi
    
    local pid=$(cat "$PID_FILE")
    
    # 检查进程是否存在
    if ! ps -p $pid > /dev/null 2>&1; then
        log_message "警告: 服务进程 (PID: $pid) 不存在"
        return 1
    fi
    
    # 检查进程是否是我们的Python服务
    local process_info=$(ps -p $pid -o command= 2>/dev/null)
    if [[ ! "$process_info" == *"python"* ]] || [[ ! "$process_info" == *"main.py"* ]]; then
        log_message "警告: 进程 (PID: $pid) 不是预期的Python服务"
        return 1
    fi
    
    # 检查日志文件是否在更新（最近30分钟内有更新表示服务活跃）
    if [ -f "$LOG_FILE" ]; then
        local last_update=$(stat -c %Y "$LOG_FILE" 2>/dev/null || stat -f %m "$LOG_FILE" 2>/dev/null)
        local current_time=$(date +%s)
        local time_diff=$((current_time - last_update))
        
        # 如果日志文件超过30分钟没更新，可能服务卡住了
        if [ $time_diff -gt 1800 ]; then
            log_message "警告: 服务日志超过30分钟未更新，可能服务已卡住"
            return 1
        fi
    fi
    
    return 0
}

restart_service() {
    log_message "正在重启服务..."
    
    # 停止服务
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if ps -p $pid > /dev/null 2>&1; then
            log_message "停止进程 (PID: $pid)..."
            kill $pid
            sleep 5
            
            # 如果进程还在运行，强制终止
            if ps -p $pid > /dev/null 2>&1; then
                log_message "强制终止进程 (PID: $pid)..."
                kill -9 $pid
            fi
        fi
        rm -f "$PID_FILE"
    fi
    
    # 重新启动服务（使用默认配置）
    log_message "重新启动服务..."
    ./start_service.sh start 5 > /dev/null 2>&1
    
    sleep 3
    
    # 验证重启是否成功
    if check_service_health; then
        log_message "服务重启成功"
        return 0
    else
        log_message "错误: 服务重启失败"
        return 1
    fi
}

main() {
    # 清理旧的监控日志（保留最近7天）
    if [ -f "$MONITOR_LOG" ]; then
        # 只保留最近1000行
        tail -n 1000 "$MONITOR_LOG" > "$MONITOR_LOG.tmp" && mv "$MONITOR_LOG.tmp" "$MONITOR_LOG"
    fi
    
    # 检查服务健康状态
    if check_service_health; then
        # 服务正常，静默退出（不写日志避免日志过多）
        exit 0
    else
        # 服务异常，尝试重启
        log_message "检测到服务异常，尝试重启..."
        
        if restart_service; then
            log_message "服务监控: 自动重启成功"
        else
            log_message "错误: 服务监控: 自动重启失败，请手动检查"
        fi
    fi
}

# 确保只有一个监控实例运行
LOCK_FILE="/tmp/${SERVICE_NAME}_monitor.lock"
if [ -f "$LOCK_FILE" ]; then
    # 检查锁文件是否过期（超过10分钟）
    local lock_time=$(stat -c %Y "$LOCK_FILE" 2>/dev/null || stat -f %m "$LOCK_FILE" 2>/dev/null)
    local current_time=$(date +%s)
    if [ $((current_time - lock_time)) -lt 600 ]; then
        exit 0  # 另一个监控实例正在运行
    fi
fi

# 创建锁文件
echo $$ > "$LOCK_FILE"

# 运行监控
main

# 清理锁文件
rm -f "$LOCK_FILE"