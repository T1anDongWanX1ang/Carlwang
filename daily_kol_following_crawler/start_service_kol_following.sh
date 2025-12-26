#!/bin/bash

# KOL Following 数据爬取服务启动脚本
# 使用方法: ./start_service_kol_following.sh [start|stop|restart|status|once|logs|monitor]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$SCRIPT_DIR"

SERVICE_NAME="twitter-crawler-kol-following"
PID_FILE="$SCRIPT_DIR/${SERVICE_NAME}.pid"
LOG_FILE="$SCRIPT_DIR/service_kol_following.log"
PYTHON_SCRIPT="$SCRIPT_DIR/fetch_kol_followings_new.py"

# 默认配置
DEFAULT_INTERVAL=1440      # 1440分钟 = 24小时（每天运行一次）
DEFAULT_LIMIT=50           # 每次处理n个KOL（可根据需要调整）
DEFAULT_SLEEP=0.5          # API调用间隔0.5秒

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
    # 1. 首先检查 PID 文件记录的进程
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            print_info "KOL Following 服务正在运行 (PID: $PID)"
            return 0
        else
            print_warning "PID文件存在但进程不存在，清理PID文件"
            rm -f "$PID_FILE"
        fi
    fi

    # 2. 即使没有 PID 文件，也检查是否有实际运行的进程（防止重复启动）
    RUNNING_PROCS=$(ps -ef | grep "[P]ython.*fetch_kol_followings" | wc -l | tr -d ' ')
    if [ "$RUNNING_PROCS" -gt 0 ]; then
        print_warning "发现 $RUNNING_PROCS 个运行中的 KOL Following 爬虫进程（无PID文件追踪）"
        # 显示这些进程
        ps -ef | grep "[P]ython.*fetch_kol_followings" | while read line; do
            ORPHAN_PID=$(echo $line | awk '{print $2}')
            START_TIME=$(echo $line | awk '{print $5}')
            print_warning "  - PID $ORPHAN_PID (启动时间: $START_TIME)"
        done
        return 0
    fi

    print_info "KOL Following 服务未运行"
    return 1
}

stop_service() {
    print_info "正在停止 KOL Following 数据爬取服务..."
    pkill -f "python.*fetch_kol_followings" 2>/dev/null
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            kill $PID
            sleep 3
            if ps -p $PID > /dev/null 2>&1; then
                print_warning "进程未响应，强制终止"
                kill -9 $PID
            fi
        fi
        rm -f "$PID_FILE"
    fi
    remove_monitoring
    print_success "KOL Following 服务已停止"
}

start_service() {
    local interval=${1:-$DEFAULT_INTERVAL}
    local limit=${2:-$DEFAULT_LIMIT}
    local sleep_time=${3:-$DEFAULT_SLEEP}

    # 1. 检查是否有服务在运行
    if check_status > /dev/null 2>&1; then
        print_error "KOL Following 服务已在运行，请先停止服务"
        echo ""
        print_info "提示: 运行 './start_service_kol_following.sh stop' 停止服务"
        return 1
    fi

    # 2. 检查 Python 脚本是否存在
    if [ ! -f "$PYTHON_SCRIPT" ]; then
        print_error "Python脚本不存在: $PYTHON_SCRIPT"
        return 1
    fi

    # 3. 清理 Python 字节码缓存（防止加载旧代码）
    print_info "清理Python字节码缓存..."
    find "$PROJECT_ROOT" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
    find "$PROJECT_ROOT" -name "*.pyc" -delete 2>/dev/null

    print_info "启动 KOL Following 数据爬取服务..."
    print_info "配置: 间隔=${interval}分钟, 每次处理${limit}个KOL, API间隔${sleep_time}秒"
    print_info "数据源: twitter_list_members_seed 表"
    print_info "目标表: twitter_kol_all 表"
    print_info "API Key: new1_038536908c7f4960812ee7d601f620a1"

    mkdir -p "$(dirname "$LOG_FILE")"

    # 创建包装脚本，实现定时循环
    WRAPPER_SCRIPT=$(mktemp)
    cat > "$WRAPPER_SCRIPT" << 'WRAPPER_EOF'
#!/bin/bash
INTERVAL_MINUTES=$1
LIMIT=$2
SLEEP_TIME=$3
PYTHON_SCRIPT=$4
LOG_FILE=$5
PROJECT_ROOT=$6

while true; do
    echo "$(date '+%Y-%m-%d %H:%M:%S') - 开始执行 KOL Following 爬取..." >> "$LOG_FILE"

    cd "$PROJECT_ROOT" && "$PROJECT_ROOT/venv/bin/python" "$PYTHON_SCRIPT" \
        --limit "$LIMIT" \
        --sleep "$SLEEP_TIME" >> "$LOG_FILE" 2>&1

    EXIT_CODE=$?
    if [ $EXIT_CODE -eq 0 ]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') - KOL Following 爬取完成" >> "$LOG_FILE"
    else
        echo "$(date '+%Y-%m-%d %H:%M:%S') - KOL Following 爬取失败 (退出码: $EXIT_CODE)" >> "$LOG_FILE"
    fi

    echo "$(date '+%Y-%m-%d %H:%M:%S') - 等待 ${INTERVAL_MINUTES} 分钟后执行下一次..." >> "$LOG_FILE"
    sleep $((INTERVAL_MINUTES * 60))
done
WRAPPER_EOF

    chmod +x "$WRAPPER_SCRIPT"

    if [[ "$OSTYPE" == "darwin"* ]]; then
        print_info "检测到macOS，使用防休眠启动..."
        caffeinate -i nohup bash "$WRAPPER_SCRIPT" "$interval" "$limit" "$sleep_time" "$PYTHON_SCRIPT" "$LOG_FILE" "$PROJECT_ROOT" > /dev/null 2>&1 &
    else
        nohup nice -n -5 bash "$WRAPPER_SCRIPT" "$interval" "$limit" "$sleep_time" "$PYTHON_SCRIPT" "$LOG_FILE" "$PROJECT_ROOT" > /dev/null 2>&1 &
    fi

    local pid=$!
    echo $pid > "$PID_FILE"
    sleep 3
    if ps -p $pid > /dev/null 2>&1; then
        print_success "KOL Following 服务启动成功 (PID: $pid)"
        print_info "日志文件: $LOG_FILE"
        print_info "PID文件: $PID_FILE"
        print_info "临时包装脚本: $WRAPPER_SCRIPT"
        setup_monitoring
    else
        print_error "KOL Following 服务启动失败"
        rm -f "$PID_FILE"
        rm -f "$WRAPPER_SCRIPT"
        return 1
    fi
}

setup_monitoring() {
    local monitor_script="$SCRIPT_DIR/service_kol_following_monitor.sh"
    if [ ! -f "$monitor_script" ]; then
        print_warning "监控脚本不存在: $monitor_script"
        return 1
    fi
    local cron_entry="*/5 * * * * $monitor_script >/dev/null 2>&1"
    local existing_cron=$(crontab -l 2>/dev/null | grep -F "$monitor_script" | head -1)
    if [ -n "$existing_cron" ]; then
        print_info "KOL Following 监控定时任务已存在: $existing_cron"
        return 0
    fi
    print_info "设置 KOL Following 监控定时任务 (每5分钟检查一次)..."
    local temp_cron=$(mktemp)
    crontab -l 2>/dev/null > "$temp_cron"
    echo "# Twitter KOL Following Crawler Service Monitor" >> "$temp_cron"
    echo "$cron_entry" >> "$temp_cron"
    if crontab "$temp_cron" 2>/dev/null; then
        print_success "KOL Following 监控定时任务设置成功"
        print_info "监控频率: 每5分钟检查一次服务状态"
        print_info "监控日志: $SCRIPT_DIR/monitor_kol_following.log"
    else
        print_error "设置 KOL Following 监控定时任务失败"
        print_info "请手动添加以下cron任务:"
        print_info "$cron_entry"
    fi
    rm -f "$temp_cron"
}

remove_monitoring() {
    local monitor_script="$SCRIPT_DIR/service_kol_following_monitor.sh"
    local temp_cron=$(mktemp)
    if crontab -l 2>/dev/null > "$temp_cron"; then
        grep -vF "$monitor_script" "$temp_cron" > "$temp_cron.new"
        if ! cmp -s "$temp_cron" "$temp_cron.new"; then
            if crontab "$temp_cron.new" 2>/dev/null; then
                print_info "KOL Following 监控定时任务已移除"
            else
                print_warning "移除 KOL Following 监控定时任务失败"
            fi
        fi
        rm -f "$temp_cron.new"
    fi
    rm -f "$temp_cron"
}

restart_service() {
    print_info "重启 KOL Following 数据爬取服务..."
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

run_once() {
    local limit=${1:-$DEFAULT_LIMIT}
    local sleep_time=${2:-$DEFAULT_SLEEP}

    print_info "开始执行单次 KOL Following 数据爬取..."
    print_info "配置: 处理${limit}个KOL, API间隔${sleep_time}秒"
    print_info "数据源: twitter_list_members_seed 表"
    print_info "目标表: twitter_kol_all 表"

    mkdir -p "$(dirname "$LOG_FILE")"

    print_info "正在爬取 KOL Following 数据，请稍候..."
    cd "$PROJECT_ROOT" && "$PROJECT_ROOT/venv/bin/python" "$PYTHON_SCRIPT" \
        --limit "$limit" \
        --sleep "$sleep_time" 2>&1 | tee -a "$LOG_FILE"

    local exit_code=${PIPESTATUS[0]}
    if [ $exit_code -eq 0 ]; then
        print_success "单次 KOL Following 爬取完成"
    else
        print_error "单次 KOL Following 爬取失败 (退出码: $exit_code)"
        return 1
    fi
}

show_monitor() {
    local monitor_script="$SCRIPT_DIR/service_kol_following_monitor.sh"
    local monitor_log="$SCRIPT_DIR/monitor_kol_following.log"
    print_info "=== KOL Following 监控状态 ==="
    local existing_cron=$(crontab -l 2>/dev/null | grep -F "$monitor_script")
    if [ -n "$existing_cron" ]; then
        print_success "KOL Following 监控定时任务: 已启用"
        echo "  $existing_cron"
    else
        print_warning "KOL Following 监控定时任务: 未启用"
    fi
    if [ -f "$monitor_log" ]; then
        print_info "最近监控日志 (最新10行):"
        echo "----------------------------------------"
        tail -n 10 "$monitor_log"
    else
        print_info "监控日志: 无记录"
    fi
}

show_help() {
    echo "Twitter KOL Following 数据爬取服务管理脚本"
    echo ""
    echo "使用方法:"
    echo "  $0 [命令] [参数]"
    echo ""
    echo "命令:"
    echo "  start [间隔分钟] [KOL数量] [API间隔]  启动服务 (默认: 1440分钟/24小时, 10个KOL, 0.5秒)"
    echo "  stop                               停止服务"
    echo "  restart [间隔分钟] [KOL数量] [API间隔] 重启服务"
    echo "  status                             查看服务状态"
    echo "  once [KOL数量] [API间隔]             执行单次爬取"
    echo "  logs [行数]                         查看日志"
    echo "  monitor                            查看监控状态和日志"
    echo "  help                               显示帮助"
    echo ""
    echo "示例:"
    echo "  $0 start                    # 使用默认配置启动（每天运行一次）"
    echo "  $0 start 720                # 每12小时运行一次"
    echo "  $0 start 1440 20 1.0        # 每24小时运行一次，每次处理20个KOL，API间隔1秒"
    echo "  $0 once                     # 执行单次爬取"
    echo "  $0 once 50 0.5              # 单次爬取50个KOL，API间隔0.5秒"
    echo "  $0 logs 100                 # 查看最新100行日志"
    echo "  $0 monitor                  # 查看监控状态"
}

case "$1" in
    "start")
        start_service "$2" "$3" "$4"
        ;;
    "stop")
        stop_service
        ;;
    "restart")
        restart_service "$2" "$3" "$4"
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
        run_once "$2" "$3"
        ;;
    "logs")
        show_logs "$2"
        ;;
    "monitor")
        show_monitor
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
