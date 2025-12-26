#!/bin/bash

# Twitter项目推文数据爬取服务启动脚本（TwitterAPI版）
# 使用方法: ./start_service_project_twitterapi.sh [start|stop|restart|status] [interval]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$SCRIPT_DIR"

SERVICE_NAME="twitter-crawler-project-twitterapi"
PID_FILE="$SCRIPT_DIR/${SERVICE_NAME}.pid"
LOG_FILE="$SCRIPT_DIR/service_project_twitterapi.log"

# 默认配置
DEFAULT_INTERVAL=15        # 15分钟跑一次
DEFAULT_MAX_PAGES=2        # 每次只抓2页（节省成本）
DEFAULT_PAGE_SIZE=20       # API固定返回20条
DEFAULT_HOURS_LIMIT=0.25   # 15分钟时间窗口（0.25小时）

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
            print_info "项目推文服务 (TwitterAPI) 正在运行 (PID: $PID)"
            return 0
        else
            print_warning "PID文件存在但进程不存在，清理PID文件"
            rm -f "$PID_FILE"
        fi
    fi

    # 2. 即使没有 PID 文件，也检查是否有实际运行的进程（防止重复启动）
    RUNNING_PROCS=$(ps -ef | grep "[P]ython.*main.py.*project-schedule" | wc -l | tr -d ' ')
    if [ "$RUNNING_PROCS" -gt 0 ]; then
        print_warning "发现 $RUNNING_PROCS 个运行中的项目推文爬虫进程（无PID文件追踪）"
        # 显示这些进程
        ps -ef | grep "[P]ython.*main.py.*project-schedule" | while read line; do
            ORPHAN_PID=$(echo $line | awk '{print $2}')
            START_TIME=$(echo $line | awk '{print $5}')
            print_warning "  - PID $ORPHAN_PID (启动时间: $START_TIME)"
        done
        return 0
    fi

    print_info "项目推文服务 (TwitterAPI) 未运行"
    return 1
}

stop_service() {
    print_info "正在停止项目推文数据爬取服务 (TwitterAPI)..."
    pkill -f "python.*main.py.*project-schedule" 2>/dev/null
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
    print_success "项目推文服务 (TwitterAPI) 已停止"
}

start_service() {
    local interval=${1:-$DEFAULT_INTERVAL}
    local max_pages=${2:-$DEFAULT_MAX_PAGES}
    local page_size=${3:-$DEFAULT_PAGE_SIZE}
    local hours_limit=${4:-$DEFAULT_HOURS_LIMIT}

    # 1. 检查是否有服务在运行
    if check_status > /dev/null 2>&1; then
        print_error "项目推文服务 (TwitterAPI) 已在运行，请先停止服务"
        echo ""
        print_info "提示: 运行 './start_service_project_twitterapi.sh stop' 停止服务"
        return 1
    fi

    # 2. 检查是否有旧代码进程（max-pages >= 50）仍在运行
    OLD_PROCS=$(ps -ef | grep "[P]ython.*main.py.*project-schedule" | grep -E "max-pages (50|100)" | wc -l | tr -d ' ')
    if [ "$OLD_PROCS" -gt 0 ]; then
        print_warning "⚠️  检测到 $OLD_PROCS 个旧代码进程（max-pages >= 50）仍在运行！"
        print_warning "这些进程会消耗大量API成本，建议先清理"
        echo ""
        ps -ef | grep "[P]ython.*main.py.*project-schedule" | grep -E "max-pages (50|100)" | while read line; do
            ORPHAN_PID=$(echo $line | awk '{print $2}')
            START_TIME=$(echo $line | awk '{print $5}')
            MAX_P=$(echo $line | grep -oE 'max-pages [0-9]+' | awk '{print $2}')
            print_warning "  - PID $ORPHAN_PID (启动: $START_TIME, max-pages: $MAX_P)"
        done
        echo ""
        print_error "请先运行以下命令清理旧进程:"
        print_error "  ps -ef | grep '[P]ython.*main.py.*project-schedule' | grep -E 'max-pages (50|100)' | awk '{print \$2}' | xargs kill -9"
        return 1
    fi

    # 3. 清理 Python 字节码缓存（防止加载旧代码）
    print_info "清理Python字节码缓存..."
    find "$PROJECT_ROOT" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
    find "$PROJECT_ROOT" -name "*.pyc" -delete 2>/dev/null

    print_info "启动项目推文数据爬取服务 (TwitterAPI)..."
    print_info "配置: 间隔=${interval}分钟, 最多抓${max_pages}页（实际按时间智能停止）, 每页约20条"
    print_info "智能时间检测: 拉取过去${hours_limit}小时数据"
    print_info "⏱️ 智能早停: 检测到超时间窗口自动停止翻页 ✅"
    print_info "数据表: twitter_tweet_back_test_cmc300"
    print_info "数据源: config.json中的list_ids_project列表"

    mkdir -p "$(dirname "$LOG_FILE")"

    if [[ "$OSTYPE" == "darwin"* ]]; then
        print_info "检测到macOS，使用防休眠启动..."
        TWITTER_API_BACKEND=twitterapi caffeinate -i nohup bash -c "cd '$PROJECT_ROOT' && '$PROJECT_ROOT/venv/bin/python' '$PROJECT_ROOT/main.py' --mode project-schedule \
            --interval $interval \
            --max-pages $max_pages \
            --page-size $page_size \
            --hours-limit $hours_limit" > "$LOG_FILE" 2>&1 &
    else
        TWITTER_API_BACKEND=twitterapi nohup nice -n -5 bash -c "cd '$PROJECT_ROOT' && '$PROJECT_ROOT/venv/bin/python' '$PROJECT_ROOT/main.py' --mode project-schedule \
            --interval $interval \
            --max-pages $max_pages \
            --page-size $page_size \
            --hours-limit $hours_limit" > "$LOG_FILE" 2>&1 &
    fi

    local pid=$!
    echo $pid > "$PID_FILE"
    sleep 3
    if ps -p $pid > /dev/null 2>&1; then
        print_success "项目推文服务 (TwitterAPI) 启动成功 (PID: $pid)"
        print_info "日志文件: $LOG_FILE"
        print_info "PID文件: $PID_FILE"
        setup_monitoring
    else
        print_error "项目推文服务 (TwitterAPI) 启动失败"
        rm -f "$PID_FILE"
        return 1
    fi
}

setup_monitoring() {
    local monitor_script="$SCRIPT_DIR/service_project_monitor.sh"
    if [ ! -f "$monitor_script" ]; then
        print_warning "监控脚本不存在: $monitor_script"
        return 1
    fi
    local cron_entry="*/5 * * * * $monitor_script >/dev/null 2>&1"
    local existing_cron=$(crontab -l 2>/dev/null | grep -F "$monitor_script" | head -1)
    if [ -n "$existing_cron" ]; then
        print_info "项目推文监控定时任务已存在: $existing_cron"
        return 0
    fi
    print_info "设置项目推文监控定时任务 (每5分钟检查一次)..."
    local temp_cron=$(mktemp)
    crontab -l 2>/dev/null > "$temp_cron"
    echo "# Twitter Project Crawler Service Monitor (TwitterAPI)" >> "$temp_cron"
    echo "$cron_entry" >> "$temp_cron"
    if crontab "$temp_cron" 2>/dev/null; then
        print_success "项目推文监控定时任务设置成功"
        print_info "监控频率: 每5分钟检查一次服务状态"
        print_info "监控日志: $SCRIPT_DIR/monitor_project.log"
    else
        print_error "设置项目推文监控定时任务失败"
        print_info "请手动添加以下cron任务:"
        print_info "$cron_entry"
    fi
    rm -f "$temp_cron"
}

remove_monitoring() {
    local monitor_script="$SCRIPT_DIR/service_project_monitor.sh"
    local temp_cron=$(mktemp)
    if crontab -l 2>/dev/null > "$temp_cron"; then
        grep -vF "$monitor_script" "$temp_cron" > "$temp_cron.new"
        if ! cmp -s "$temp_cron" "$temp_cron.new"; then
            if crontab "$temp_cron.new" 2>/dev/null; then
                print_info "项目推文监控定时任务已移除"
            else
                print_warning "移除项目推文监控定时任务失败"
            fi
        fi
        rm -f "$temp_cron.new"
    fi
    rm -f "$temp_cron"
}

restart_service() {
    print_info "重启项目推文数据爬取服务 (TwitterAPI)..."
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

    print_info "开始执行单次项目推文数据爬取 (TwitterAPI)..."
    print_info "配置: 最多抓${max_pages}页（实际按时间智能停止）, 每页约20条"
    print_info "智能时间检测: 拉取过去${hours_limit}小时数据"
    print_info "⏱️ 智能早停: 检测到超时间窗口自动停止翻页 ✅"
    print_info "数据表: twitter_tweet_back_test_cmc300"
    print_info "数据源: config.json中的list_ids_project列表"

    mkdir -p "$(dirname "$LOG_FILE")"

    print_info "正在爬取项目推文数据，请稍候..."
    TWITTER_API_BACKEND=twitterapi bash -c "cd '$PROJECT_ROOT' && '$PROJECT_ROOT/venv/bin/python' '$PROJECT_ROOT/main.py' --mode project-once \
        --max-pages $max_pages \
        --page-size $page_size \
        --hours-limit $hours_limit" 2>&1 | tee -a "$LOG_FILE"

    local exit_code=${PIPESTATUS[0]}
    if [ $exit_code -eq 0 ]; then
        print_success "单次项目推文爬取完成"
    else
        print_error "单次项目推文爬取失败 (退出码: $exit_code)"
        return 1
    fi
}

show_monitor() {
    local monitor_script="$SCRIPT_DIR/service_project_monitor.sh"
    local monitor_log="$SCRIPT_DIR/monitor_project.log"
    print_info "=== 项目推文监控状态 (TwitterAPI) ==="
    local existing_cron=$(crontab -l 2>/dev/null | grep -F "$monitor_script")
    if [ -n "$existing_cron" ]; then
        print_success "项目推文监控定时任务: 已启用"
        echo "  $existing_cron"
    else
        print_warning "项目推文监控定时任务: 未启用"
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
    echo "Twitter项目推文数据爬取服务管理脚本 (TwitterAPI版)"
    echo ""
    echo "使用方法:"
    echo "  $0 [命令] [参数]"
    echo ""
    echo "命令:"
    echo "  start [间隔] [页数] [每页条数] [小时限制]  启动服务 (默认: 60分钟, 50页, 100条, 3小时)"
    echo "  stop                                   停止服务"
    echo "  restart [间隔] [页数] [每页条数] [小时限制] 重启服务"
    echo "  status                                 查看服务状态"
    echo "  once [页数] [每页条数] [小时限制]         执行单次爬取"
    echo "  logs [行数]                            查看日志"
    echo "  monitor                                查看监控状态和日志"
    echo "  help                                   显示帮助"
    echo ""
    echo "示例:"
    echo "  $0 start                    # 使用默认配置启动"
    echo "  $0 start 10                 # 10分钟间隔启动"
    echo "  $0 start 60 50 100 24       # 60分钟间隔，50页，每页100条，24小时时间限制"
    echo "  $0 once                     # 执行单次爬取"
    echo "  $0 once 50 100 12           # 单次爬取50页，每页100条，12小时时间限制"
    echo "  $0 logs 100                 # 查看最新100行日志"
    echo "  $0 monitor                  # 查看监控状态"
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
