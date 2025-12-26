#!/bin/bash

# Marco数据处理服务监控脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="marco-processor"
PID_FILE="$SCRIPT_DIR/${SERVICE_NAME}.pid"
LOG_FILE="$SCRIPT_DIR/marco_service.log"
MONITOR_LOG="$SCRIPT_DIR/marco_monitor.log"

# 记录监控日志
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$MONITOR_LOG"
}

# 检查服务状态
check_service() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            # 检查进程是否是Marco进程
            if ps -p $PID -o command= | grep -q "run_marco.py"; then
                return 0  # 服务正常运行
            else
                # PID存在但不是Marco进程
                rm -f "$PID_FILE"
                return 1
            fi
        else
            # PID不存在
            rm -f "$PID_FILE"
            return 1
        fi
    else
        return 1  # PID文件不存在
    fi
}

# 重启服务
restart_service() {
    log_message "Marco服务异常，尝试重启..."
    
    # 停止可能残留的进程
    pkill -f "python.*run_marco.py" 2>/dev/null
    
    # 等待进程完全停止
    sleep 5
    
    # 检查是否有配置文件确定启动模式
    cd "$SCRIPT_DIR"
    
    # 默认使用定时器模式启动
    if [[ "$OSTYPE" == "darwin"* ]]; then
        caffeinate -i nohup "$SCRIPT_DIR/venv/bin/python" run_marco.py timer > "$LOG_FILE" 2>&1 &
    else
        nohup nice -n -5 "$SCRIPT_DIR/venv/bin/python" run_marco.py timer > "$LOG_FILE" 2>&1 &
    fi
    
    local new_pid=$!
    echo $new_pid > "$PID_FILE"
    
    # 验证重启是否成功
    sleep 3
    if ps -p $new_pid > /dev/null 2>&1; then
        log_message "Marco服务重启成功 (PID: $new_pid)"
        return 0
    else
        log_message "Marco服务重启失败"
        rm -f "$PID_FILE"
        return 1
    fi
}

# 主监控逻辑
if ! check_service; then
    restart_service
else
    # 记录服务正常运行（每小时记录一次，避免日志过多）
    if [ $(($(date +%M) % 60)) -eq 0 ]; then
        PID=$(cat "$PID_FILE")
        log_message "Marco服务运行正常 (PID: $PID)"
    fi
fi
