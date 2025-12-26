#!/bin/bash
###############################################################################
# KOL 关注列表获取服务管理脚本
# 带防待机保护，支持后台运行和日志记录
###############################################################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_NAME="fetch_kol_followings.py"
SCRIPT_PATH="${SCRIPT_DIR}/${SCRIPT_NAME}"
PID_FILE="${SCRIPT_DIR}/kol_fetch.pid"
LOG_FILE="${SCRIPT_DIR}/kol_fetch.log"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检测操作系统
OS_TYPE=$(uname -s)

###############################################################################
# 函数定义
###############################################################################

# 打印带颜色的消息
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否正在运行
is_running() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            return 0
        else
            rm -f "$PID_FILE"
            return 1
        fi
    fi
    return 1
}

# 启动服务（带防待机保护）
start_service() {
    local limit=$1
    local sleep_interval=$2
    local extra_args="${@:3}"

    # 默认值
    limit=${limit:-50}
    sleep_interval=${sleep_interval:-0.5}

    if is_running; then
        print_warn "服务已在运行中 (PID: $(cat $PID_FILE))"
        return 1
    fi

    print_info "启动 KOL 关注列表获取服务..."
    print_info "参数: --limit $limit --sleep $sleep_interval $extra_args"

    # 根据操作系统选择防待机命令
    if [[ "$OS_TYPE" == "Darwin" ]]; then
        # macOS: 使用 caffeinate 防止系统休眠
        print_info "使用 caffeinate 防止系统休眠 (macOS)"
        nohup caffeinate -i python3 "$SCRIPT_PATH" --limit "$limit" --sleep "$sleep_interval" $extra_args >> "$LOG_FILE" 2>&1 &
    elif [[ "$OS_TYPE" == "Linux" ]]; then
        # Linux: 使用 nice 提高优先级
        print_info "使用 nice 提高进程优先级 (Linux)"
        nohup nice -n -5 python3 "$SCRIPT_PATH" --limit "$limit" --sleep "$sleep_interval" $extra_args >> "$LOG_FILE" 2>&1 &
    else
        # 其他系统：普通后台运行
        print_warn "未知操作系统，使用普通后台运行"
        nohup python3 "$SCRIPT_PATH" --limit "$limit" --sleep "$sleep_interval" $extra_args >> "$LOG_FILE" 2>&1 &
    fi

    PID=$!
    echo $PID > "$PID_FILE"

    sleep 2

    if is_running; then
        print_info "✓ 服务启动成功 (PID: $PID)"
        print_info "日志文件: $LOG_FILE"
        return 0
    else
        print_error "✗ 服务启动失败，请查看日志: $LOG_FILE"
        rm -f "$PID_FILE"
        return 1
    fi
}

# 停止服务
stop_service() {
    if ! is_running; then
        print_warn "服务未运行"
        return 1
    fi

    PID=$(cat "$PID_FILE")
    print_info "停止服务 (PID: $PID)..."

    kill "$PID"

    # 等待进程结束（最多10秒）
    for i in {1..10}; do
        if ! ps -p "$PID" > /dev/null 2>&1; then
            rm -f "$PID_FILE"
            print_info "✓ 服务已停止"
            return 0
        fi
        sleep 1
    done

    # 强制结束
    print_warn "进程未响应，强制结束..."
    kill -9 "$PID" 2>/dev/null
    rm -f "$PID_FILE"
    print_info "✓ 服务已强制停止"
}

# 查看服务状态
status_service() {
    echo "=========================================="
    echo "KOL 关注列表获取服务状态"
    echo "=========================================="

    if is_running; then
        PID=$(cat "$PID_FILE")
        print_info "状态: ${GREEN}运行中${NC}"
        echo "PID: $PID"
        echo "日志文件: $LOG_FILE"
        echo ""
        echo "进程信息:"
        ps -p "$PID" -o pid,ppid,%cpu,%mem,etime,command
    else
        print_warn "状态: ${YELLOW}未运行${NC}"
    fi

    echo "=========================================="
}

# 查看日志
view_logs() {
    local lines=${1:-50}

    if [ ! -f "$LOG_FILE" ]; then
        print_warn "日志文件不存在"
        return 1
    fi

    print_info "显示最后 $lines 行日志:"
    echo "=========================================="
    tail -n "$lines" "$LOG_FILE"
    echo "=========================================="
}

# 实时监控日志
follow_logs() {
    if [ ! -f "$LOG_FILE" ]; then
        print_warn "日志文件不存在"
        return 1
    fi

    print_info "实时监控日志 (Ctrl+C 退出):"
    tail -f "$LOG_FILE"
}

# 重启服务
restart_service() {
    print_info "重启服务..."
    stop_service
    sleep 2
    start_service "$@"
}

# 显示帮助
show_help() {
    cat << EOF
KOL 关注列表获取服务管理脚本

用法: $0 <command> [options]

命令:
  start [limit] [sleep]     启动服务（默认: limit=50, sleep=0.5）
  start-fast                启动服务（无延迟模式: sleep=0）
  start-slow                启动服务（慢速模式: sleep=2）
  stop                      停止服务
  restart [limit] [sleep]   重启服务
  status                    查看服务状态
  logs [lines]              查看日志（默认: 50行）
  follow                    实时监控日志
  cache-status              查看缓存状态
  resume                    从缓存恢复（不调用API）

示例:
  # 启动服务，处理50个KOL，间隔0.5秒
  $0 start

  # 启动服务，处理100个KOL，间隔1秒
  $0 start 100 1

  # 快速模式（无延迟）
  $0 start-fast

  # 慢速模式（间隔2秒）
  $0 start-slow

  # 查看日志
  $0 logs 100

  # 实时监控
  $0 follow

  # 查看缓存状态
  $0 cache-status

  # 从缓存恢复
  $0 resume

特性:
  - macOS: 使用 caffeinate 防止系统休眠
  - Linux: 使用 nice 提高进程优先级
  - 后台运行，日志记录
  - 支持启动/停止/重启/状态查看
  - 缓存机制，避免重复API调用

EOF
}

###############################################################################
# 主程序
###############################################################################

case "$1" in
    start)
        start_service "${2:-50}" "${3:-0.5}" "${@:4}"
        ;;
    start-fast)
        print_info "启动快速模式（无延迟）"
        start_service "${2:-50}" "0" "${@:3}"
        ;;
    start-slow)
        print_info "启动慢速模式（间隔2秒）"
        start_service "${2:-50}" "2" "${@:3}"
        ;;
    stop)
        stop_service
        ;;
    restart)
        restart_service "${2:-50}" "${3:-0.5}" "${@:4}"
        ;;
    status)
        status_service
        ;;
    logs)
        view_logs "${2:-50}"
        ;;
    follow)
        follow_logs
        ;;
    cache-status)
        python3 "$SCRIPT_PATH" --cache-status
        ;;
    resume)
        print_info "从缓存恢复模式..."
        start_service "${2:-50}" "0" "--resume" "${@:3}"
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "未知命令: $1"
        echo ""
        show_help
        exit 1
        ;;
esac

exit 0
