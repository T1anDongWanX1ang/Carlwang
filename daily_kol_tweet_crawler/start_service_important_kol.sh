#!/bin/bash

# 重点KOL推文数据爬取服务启动脚本
# 针对特定List ID: 2009544306269548633 (20个重要KOL)
# 使用方法: ./start_service_important_kol.sh [start|stop|restart|status|once|logs|monitor]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$SCRIPT_DIR"

SERVICE_NAME="twitter-crawler-important-kol"
PID_FILE="$SCRIPT_DIR/${SERVICE_NAME}.pid"
LOG_FILE="$SCRIPT_DIR/service_important_kol.log"
TARGET_LIST_ID="2009544306269548633"

# 仅匹配“本项目目录 + 重点KOL List ID”进程
EXPECTED_MODE="--list-id $TARGET_LIST_ID"

# 默认配置
DEFAULT_INTERVAL=20    # 20分钟一次
DEFAULT_MAX_PAGES=5    # 重点KOL数量少，5页足够
DEFAULT_PAGE_SIZE=20   # 
DEFAULT_HOURS_LIMIT=0.5 # 只抓取过去30分钟

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
        if ps -p "$PID" > /dev/null 2>&1; then
            # 进一步校验：PID 必须是本项目的 重点KOL 进程
            CMDLINE=$(ps -p "$PID" -o command= 2>/dev/null)
            if [[ "$CMDLINE" == *"$PROJECT_ROOT/main.py"* ]] && [[ "$CMDLINE" == *"$EXPECTED_MODE"* ]]; then
                print_info "重点KOL推文爬取服务正在运行 (PID: $PID)"
                return 0
            fi
            print_warning "PID文件指向的进程不是预期重点KOL爬虫，清理PID文件"
            print_warning "当前进程命令: $CMDLINE"
            rm -f "$PID_FILE"
        else
            print_warning "PID文件存在但进程不存在，清理PID文件"
            rm -f "$PID_FILE"
        fi
    fi

    # 2. 即使没有 PID 文件，也检查是否有实际运行的进程（防止重复启动）
    # 注意 grep 参数中需要包含 list-id 以区分普通爬虫
    RUNNING_LINES=$(ps -ef | grep -E "[Pp]ython.*$PROJECT_ROOT/.*main.py" | grep -F -- "$EXPECTED_MODE" 2>/dev/null || true)
    if [ -n "$RUNNING_LINES" ]; then
        RUNNING_PROCS=$(echo "$RUNNING_LINES" | wc -l | tr -d ' ')
        print_warning "发现 $RUNNING_PROCS 个运行中的重点KOL爬虫进程（无PID文件追踪）"
        echo "$RUNNING_LINES" | while read -r line; do
            ORPHAN_PID=$(echo "$line" | awk '{print $2}')
            START_TIME=$(echo "$line" | awk '{print $5}')
            print_warning "  - PID $ORPHAN_PID (启动时间: $START_TIME)"
        done
        return 0
    fi

    print_info "重点KOL推文爬取服务未运行"
    return 1
}

stop_service() {
    print_info "正在停止重点KOL推文爬取服务..."

    # 停止现有的所有相关爬虫进程
    pkill -f "$PROJECT_ROOT/.*main.py.*$EXPECTED_MODE" 2>/dev/null || true

    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            kill "$PID" 2>/dev/null || true
            sleep 3
            if ps -p "$PID" > /dev/null 2>&1; then
                print_warning "进程未响应，强制终止"
                kill -9 "$PID" 2>/dev/null || true
            fi
        fi

        # macOS 防休眠等待进程兜底清理
        pkill -f "caffeinate.*-w[[:space:]]*$PID" 2>/dev/null || true
        rm -f "$PID_FILE"
    fi

    # 移除监控定时任务
    remove_monitoring

    print_success "重点KOL推文爬取服务已停止"
}

start_service() {
    local interval=${1:-$DEFAULT_INTERVAL}
    local max_pages=${2:-$DEFAULT_MAX_PAGES}
    local page_size=${3:-$DEFAULT_PAGE_SIZE}
    local hours_limit=${4:-$DEFAULT_HOURS_LIMIT}

    # 1. 检查服务是否已在运行
    if check_status > /dev/null 2>&1; then
        print_error "重点KOL推文爬取服务已在运行，请先停止服务"
        echo ""
        print_info "提示: 运行 './start_service_important_kol.sh stop' 停止服务"
        return 1
    fi

    print_info "启动重点KOL推文爬取服务..."
    print_info "配置: ListID=${TARGET_LIST_ID}, 间隔=${interval}分钟, 页数=${max_pages}, 时间限制=${hours_limit}小时"

    # 创建日志目录
    mkdir -p "$(dirname "$LOG_FILE")"

    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS系统
        print_info "检测到macOS，使用防休眠启动..."
        TWITTER_API_BACKEND=twitterapi nohup bash -c "cd '$PROJECT_ROOT' && exec '$PROJECT_ROOT/venv/bin/python' '$PROJECT_ROOT/main.py' --mode schedule \
            --interval $interval \
            --max-pages $max_pages \
            --page-size $page_size \
            --hours-limit $hours_limit \
            --list-id $TARGET_LIST_ID" > "$LOG_FILE" 2>&1 &
    else
        # Linux系统
        TWITTER_API_BACKEND=twitterapi nohup nice -n -5 bash -c "cd '$PROJECT_ROOT' && exec '$PROJECT_ROOT/venv/bin/python' '$PROJECT_ROOT/main.py' --mode schedule \
            --interval $interval \
            --max-pages $max_pages \
            --page-size $page_size \
            --hours-limit $hours_limit \
            --list-id $TARGET_LIST_ID" > "$LOG_FILE" 2>&1 &
    fi

    local pid=$!
    echo $pid > "$PID_FILE"

    # macOS 防休眠：仅等待 python PID
    if [[ "$OSTYPE" == "darwin"* ]]; then
        caffeinate -i -w "$pid" >/dev/null 2>&1 &
    fi

    # 等待服务启动
    sleep 3
    if ps -p $pid > /dev/null 2>&1; then
        print_success "重点KOL推文爬取服务启动成功 (PID: $pid)"
        print_info "日志文件: $LOG_FILE"
        print_info "PID文件: $PID_FILE"

        # 设置监控定时任务
        setup_monitoring
    else
        print_error "重点KOL推文爬取服务启动失败"
        rm -f "$PID_FILE"
        return 1
    fi
}

setup_monitoring() {
    local monitor_script="$SCRIPT_DIR/service_important_kol_monitor.sh"

    if [ ! -f "$monitor_script" ]; then
        print_warning "监控脚本不存在: $monitor_script"
        return 1
    fi

    # 检查是否已有监控任务
    local cron_entry="*/5 * * * * $monitor_script >/dev/null 2>&1"
    local existing_cron=$(crontab -l 2>/dev/null | grep -F "$monitor_script" | head -1)

    if [ -n "$existing_cron" ]; then
        print_info "重点KOL监控定时任务已存在: $existing_cron"
        return 0
    fi

    # 添加监控定时任务
    print_info "设置重点KOL监控定时任务 (每5分钟检查一次)..."

    # 获取当前crontab
    local temp_cron=$(mktemp)
    crontab -l 2>/dev/null > "$temp_cron"

    # 添加新的监控任务
    echo "# Important KOL Tweet Crawler Monitor" >> "$temp_cron"
    echo "$cron_entry" >> "$temp_cron"

    # 安装新的crontab
    if crontab "$temp_cron" 2>/dev/null; then
        print_success "重点KOL监控定时任务设置成功"
    else
        print_error "设置重点KOL监控定时任务失败"
    fi

    rm -f "$temp_cron"
}

remove_monitoring() {
    local monitor_script="$SCRIPT_DIR/service_important_kol_monitor.sh"

    # 获取当前crontab
    local temp_cron=$(mktemp)
    if crontab -l 2>/dev/null > "$temp_cron"; then
        # 移除包含监控脚本的行
        grep -vF "$monitor_script" "$temp_cron" > "$temp_cron.new"

        # 如果有变化，更新crontab
        if ! cmp -s "$temp_cron" "$temp_cron.new"; then
            if crontab "$temp_cron.new" 2>/dev/null; then
                print_info "重点KOL监控定时任务已移除"
            fi
        fi

        rm -f "$temp_cron.new"
    fi

    rm -f "$temp_cron"
}

restart_service() {
    print_info "重启重点KOL推文爬取服务..."
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
    local max_pages=${1:-$DEFAULT_MAX_PAGES}
    local page_size=${2:-$DEFAULT_PAGE_SIZE}
    local hours_limit=${3:-$DEFAULT_HOURS_LIMIT}

    print_info "开始执行单次重点KOL推文数据爬取..."
    print_info "配置: ListID=${TARGET_LIST_ID}, 页数=${max_pages}, 时间限制=${hours_limit}小时"

    # 创建日志目录
    mkdir -p "$(dirname "$LOG_FILE")"

    # 执行单次爬取
    cd "$PROJECT_ROOT" && export TWITTER_API_BACKEND=twitterapi && "$PROJECT_ROOT/venv/bin/python" "$PROJECT_ROOT/main.py" --mode once \
        --max-pages $max_pages \
        --page-size $page_size \
        --hours-limit $hours_limit \
        --list-id $TARGET_LIST_ID 2>&1 | tee -a "$LOG_FILE"

    local exit_code=${PIPESTATUS[0]}

    if [ $exit_code -eq 0 ]; then
        print_success "单次爬取完成"
    else
        print_error "单次爬取失败 (退出码: $exit_code)"
        return 1
    fi
}

show_monitor() {
    local monitor_script="$SCRIPT_DIR/service_important_kol_monitor.sh"
    local monitor_log="$SCRIPT_DIR/monitor_important_kol.log"

    print_info "=== 重点KOL推文爬取监控状态 ==="

    # 检查监控定时任务
    local existing_cron=$(crontab -l 2>/dev/null | grep -F "$monitor_script")
    if [ -n "$existing_cron" ]; then
        print_success "监控定时任务: 已启用"
        echo "  $existing_cron"
    else
        print_warning "监控定时任务: 未启用"
    fi

    # 显示监控日志
    if [ -f "$monitor_log" ]; then
        print_info "���近监控日志 (最新10行):"
        echo "----------------------------------------"
        tail -n 10 "$monitor_log"
    else
        print_info "监控日志: 无记录"
    fi
}

case "$1" in
    "start")
        start_service "$2" "$3" "$4" "$5"
        ;;
    "stop")
        stop_service
        ;;
    "restart")
        restart_service "$2" "$3" "$4" "$5"
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
        run_once "$2" "$3" "$4"
        ;;
    "logs")
        show_logs "$2"
        ;;
    "monitor")
        show_monitor
        ;;
    "help"|"-h"|"--help"|"")
        echo "重点KOL推文数据爬取服务 (List ID: $TARGET_LIST_ID)"
        echo "使用方法: $0 [start|stop|restart|status|once|logs|monitor]"
        echo "默认配置: 20分钟间隔, 5页, 30分钟数据"
        ;;
    *)
        print_error "未知命令: $1"
        exit 1
        ;;
esac
