#!/bin/bash

# Twitter项目推文历史指标更新服务启动脚本（守护进程版）
# 使用方法: ./start_service_update_metrics.sh [start|stop|restart|status|logs]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$SCRIPT_DIR"

SERVICE_NAME="twitter-update-metrics-daemon"
PID_FILE="$SCRIPT_DIR/${SERVICE_NAME}.pid"
LOG_FILE="$SCRIPT_DIR/service_update_metrics.log"

# 默认配置
DEFAULT_DAYS=7             # 更新过去7天的数据

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_status() {
    if [ ! -f "$PID_FILE" ]; then
        print_info "指标更新服务 (Update Metrics) 未运行"
        return 1
    fi

    PID=$(cat "$PID_FILE")
    if ! ps -p "$PID" > /dev/null 2>&1; then
        print_warning "PID文件存在但进程不存在，清理PID文件"
        rm -f "$PID_FILE"
        return 1
    fi

    # 进一步校验
    local cmdline
    cmdline=$(ps -p "$PID" -o command= 2>/dev/null)
    if [[ "$cmdline" != *"main.py"* ]] || [[ "$cmdline" != *"update-metrics-daemon"* ]]; then
        print_warning "PID文件指向的进程不是预期服务，清理PID文件"
        print_warning "当前进程命令: $cmdline"
        rm -f "$PID_FILE"
        return 1
    fi

    print_info "指标更新服务 (Update Metrics) 正在运行 (PID: $PID)"
    return 0
}

stop_service() {
    print_info "正在停止指标更新服务..."

    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            kill "$PID" 2>/dev/null || true
            sleep 3
            if ps -p "$PID" > /dev/null 2>&1; then
                print_warning "进程未响应，强制终止 (PID: $PID)"
                kill -9 "$PID" 2>/dev/null || true
            fi
        fi
        rm -f "$PID_FILE"
    fi

    # 清理残留
    pkill -f "$PROJECT_ROOT/.*main.py.*update-metrics-daemon" 2>/dev/null || true

    print_success "指标更新服务已停止"
}

run_once() {
    local days=${1:-$DEFAULT_DAYS}

    print_info "开始执行单次指标更新任务..."
    print_info "配置: 更新过去 ${days} 天的数据"
    print_info "数据表: twitter_tweet_back_test_cmc300"
    
    mkdir -p "$(dirname "$LOG_FILE")"

    # 设置环境变量，确保使用 twitterapi 后端
    export TWITTER_API_BACKEND=twitterapi

    print_info "正在更新数据，请稍候 (进度请查看日志)..."
    "$PROJECT_ROOT/venv/bin/python" "$PROJECT_ROOT/main.py" --mode update-metrics \
        --days $days 2>&1 | tee -a "$LOG_FILE"

    local exit_code=${PIPESTATUS[0]}
    if [ $exit_code -eq 0 ]; then
        print_success "单次指标更新完成"
    else
        print_error "单次指标更新失败 (退出码: $exit_code)"
        return 1
    fi
}

start_service() {
    local days=${1:-$DEFAULT_DAYS}

    if check_status > /dev/null 2>&1; then
        print_error "指标更新服务已在运行，请先停止服务"
        return 1
    fi

    print_info "启动指标更新服务 (守护进程模式)..."
    print_info "配置: 每天12:00自动运行, 更新过去 ${days} 天的数据"
    print_info "数据表: twitter_tweet_back_test_cmc300"
    
    mkdir -p "$(dirname "$LOG_FILE")"

    # 设置环境变量，确保使用 twitterapi 后端
    export TWITTER_API_BACKEND=twitterapi

    if [[ "$OSTYPE" == "darwin"* ]]; then
        print_info "检测到macOS，使用防休眠启动..."
        nohup bash -c "cd '$PROJECT_ROOT' && exec '$PROJECT_ROOT/venv/bin/python' '$PROJECT_ROOT/main.py' --mode update-metrics-daemon \
            --days $days" > "$LOG_FILE" 2>&1 &
    else
        nohup nice -n 0 bash -c "cd '$PROJECT_ROOT' && exec '$PROJECT_ROOT/venv/bin/python' '$PROJECT_ROOT/main.py' --mode update-metrics-daemon \
            --days $days" > "$LOG_FILE" 2>&1 &
    fi

    local pid=$!
    echo "$pid" > "$PID_FILE"

    if [[ "$OSTYPE" == "darwin"* ]]; then
        caffeinate -i -w "$pid" >/dev/null 2>&1 &
    fi

    sleep 3
    if ps -p "$pid" > /dev/null 2>&1; then
        print_success "指标更新服务启动成功 (PID: $pid)"
        print_info "日志文件: $LOG_FILE"
        print_info "PID文件: $PID_FILE"
        print_info "⏳ 服务已进入等待状态，将于每天 12:00 自动执行"
    else
        print_error "指标更新服务启动失败"
        rm -f "$PID_FILE"
        return 1
    fi
}

restart_service() {
    print_info "重启指标更新服务..."
    stop_service
    sleep 2
    start_service "$@"
}

show_logs() {
    local lines=${1:-50}
    if [ -f "$LOG_FILE" ]; then
        print_info "显示最新 $lines 行日志:"
        echo "----------------------------------------"
        tail -n $lines "$LOG_FILE"
    else
        print_warning "日志文件不存在"
    fi
}

show_help() {
    echo "Twitter项目推文指标更新服务管理脚本 (守护进程版)"
    echo ""
    echo "使用方法:"
    echo "  $0 [命令] [参数]"
    echo ""
    echo "命令:"
    echo "  start [天数]      启动服务 (每天12:00运行)"
    echo "  stop              停止服务"
    echo "  restart [天数]    重启服务"
    echo "  status            查看服务状态"
    echo "  once [天数]       立即执行一次更新"
    echo "  logs [行数]       查看日志 (默认50行)"
    echo "  help              显示帮助"
    echo ""
    echo "示例:"
    echo "  $0 start          # 启动后台服务"
    echo "  $0 once           # 立即手动更新一次"
    echo "  $0 once 3         # 立即手动更新过去3天的数据"
    echo "  $0 logs 100       # 查看日志"
}

case "$1" in
    "start")
        start_service "$2"
        ;;
    "stop")
        stop_service
        ;;
    "restart")
        restart_service "$2"
        ;;
    "status")
        check_status
        if [ -f "$LOG_FILE" ]; then
            print_info "最新日志:"
            echo "----------------------------------------"
            tail -n 5 "$LOG_FILE"
        fi
        ;;
    "once")
        run_once "$2"
        ;;
    "logs")
        show_logs "$2"
        ;;
    "help"|"-h"|"--help")
        show_help
        ;;
    *)
        print_error "未知命令: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
