#!/bin/bash

# Marco数据处理服务启动脚本
# 使用方法: ./start_marco_service.sh [start|stop|restart|status] [interval]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

SERVICE_NAME="marco-processor"
PID_FILE="$SCRIPT_DIR/${SERVICE_NAME}.pid"
LOG_FILE="$SCRIPT_DIR/marco_service.log"

# 默认配置
DEFAULT_INTERVAL=30

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

# 检查服务状态
check_status() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            print_info "Marco服务正在运行 (PID: $PID)"
            return 0
        else
            print_warning "PID文件存在但进程不存在，清理PID文件"
            rm -f "$PID_FILE"
            return 1
        fi
    else
        print_info "Marco服务未运行"
        return 1
    fi
}

# 停止服务
stop_service() {
    print_info "正在停止Marco数据处理服务..."
    
    # 停止现有的所有Marco进程
    pkill -f "python.*run_marco.py.*timer" 2>/dev/null
    pkill -f "python.*run_marco.py.*schedule" 2>/dev/null
    
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
    
    # 移除监控定时任务
    remove_monitoring
    
    print_success "Marco服务已停止"
}

# 启动服务 - 定时器模式
start_timer_service() {
    local interval=${1:-$DEFAULT_INTERVAL}
    
    # 检查服务是否已在运行
    if check_status > /dev/null 2>&1; then
        print_error "Marco服务已在运行，请先停止服务"
        return 1
    fi
    
    print_info "启动Marco数据处理服务 (定时器模式)..."
    print_info "配置: 间隔=${interval}分钟"
    
    # 创建日志目录
    mkdir -p "$(dirname "$LOG_FILE")"
    
    # 启动服务（防止系统待机时停止）
    # 1. 使用caffeinate防止系统休眠影响进程
    # 2. 设置高优先级
    # 3. 禁用App Nap (macOS)
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS系统
        print_info "检测到macOS，使用防休眠启动..."
        caffeinate -i nohup "$SCRIPT_DIR/venv/bin/python" run_marco.py schedule $interval > "$LOG_FILE" 2>&1 &
    else
        # Linux系统
        nohup nice -n -5 "$SCRIPT_DIR/venv/bin/python" run_marco.py schedule $interval > "$LOG_FILE" 2>&1 &
    fi
    
    local pid=$!
    echo $pid > "$PID_FILE"
    
    # 等待服务启动
    sleep 3
    if ps -p $pid > /dev/null 2>&1; then
        print_success "Marco服务启动成功 (PID: $pid)"
        print_info "运行模式: 定时器模式 (每${interval}分钟)"
        print_info "日志文件: $LOG_FILE"
        print_info "PID文件: $PID_FILE"
        
        # 设置监控定时任务
        setup_monitoring
    else
        print_error "Marco服务启动失败"
        rm -f "$PID_FILE"
        return 1
    fi
}

# 启动服务 - 守护进程模式
start_daemon_service() {
    # 检查服务是否已在运行
    if check_status > /dev/null 2>&1; then
        print_error "Marco服务已在运行，请先停止服务"
        return 1
    fi
    
    print_info "启动Marco数据处理服务 (守护进程模式)..."
    print_info "配置: 守护进程模式 (每30分钟)"
    
    # 创建日志目录
    mkdir -p "$(dirname "$LOG_FILE")"
    
    # 启动服务（防止系统待机时停止）
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS系统
        print_info "检测到macOS，使用防休眠启动..."
        caffeinate -i nohup "$SCRIPT_DIR/venv/bin/python" run_marco.py daemon > "$LOG_FILE" 2>&1 &
    else
        # Linux系统
        nohup nice -n -5 "$SCRIPT_DIR/venv/bin/python" run_marco.py daemon > "$LOG_FILE" 2>&1 &
    fi
    
    local pid=$!
    echo $pid > "$PID_FILE"
    
    # 等待服务启动
    sleep 3
    if ps -p $pid > /dev/null 2>&1; then
        print_success "Marco服务启动成功 (PID: $pid)"
        print_info "运行模式: 守护进程模式 (每30分钟)"
        print_info "日志文件: $LOG_FILE"
        print_info "PID文件: $PID_FILE"
        
        # 设置监控定时任务
        setup_monitoring
    else
        print_error "Marco服务启动失败"
        rm -f "$PID_FILE"
        return 1
    fi
}

# 设置监控定时任务
setup_monitoring() {
    local monitor_script="$SCRIPT_DIR/marco_service_monitor.sh"
    
    # 如果监控脚本不存在，创建它
    if [ ! -f "$monitor_script" ]; then
        create_monitor_script "$monitor_script"
    fi
    
    # 检查是否已有监控任务
    local cron_entry="*/5 * * * * $monitor_script >/dev/null 2>&1"
    local existing_cron=$(crontab -l 2>/dev/null | grep -F "$monitor_script" | head -1)
    
    if [ -n "$existing_cron" ]; then
        print_info "Marco监控定时任务已存在: $existing_cron"
        return 0
    fi
    
    # 添加监控定时任务
    print_info "设置Marco监控定时任务 (每5分钟检查一次)..."
    
    # 获取当前crontab
    local temp_cron=$(mktemp)
    crontab -l 2>/dev/null > "$temp_cron"
    
    # 添加新的监控任务
    echo "# Marco Processor Service Monitor" >> "$temp_cron"
    echo "$cron_entry" >> "$temp_cron"
    
    # 安装新的crontab
    if crontab "$temp_cron" 2>/dev/null; then
        print_success "Marco监控定时任务设置成功"
        print_info "监控频率: 每5分钟检查一次服务状态"
        print_info "监控日志: $SCRIPT_DIR/marco_monitor.log"
    else
        print_error "设置Marco监控定时任务失败"
        print_info "请手动添加以下cron任务:"
        print_info "$cron_entry"
    fi
    
    rm -f "$temp_cron"
}

# 创建监控脚本
create_monitor_script() {
    local monitor_script="$1"
    
    print_info "创建Marco监控脚本: $monitor_script"
    
    cat > "$monitor_script" << 'EOF'
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
EOF
    
    chmod +x "$monitor_script"
}

# 移除监控定时任务
remove_monitoring() {
    local monitor_script="$SCRIPT_DIR/marco_service_monitor.sh"
    
    # 获取当前crontab
    local temp_cron=$(mktemp)
    if crontab -l 2>/dev/null > "$temp_cron"; then
        # 移除包含监控脚本的行
        grep -vF "$monitor_script" "$temp_cron" > "$temp_cron.new"
        
        # 如果有变化，更新crontab
        if ! cmp -s "$temp_cron" "$temp_cron.new"; then
            if crontab "$temp_cron.new" 2>/dev/null; then
                print_info "Marco监控定时任务已移除"
            else
                print_warning "移除Marco监控定时任务失败"
            fi
        fi
        
        rm -f "$temp_cron.new"
    fi
    
    rm -f "$temp_cron"
}

# 重启服务
restart_service() {
    print_info "重启Marco数据处理服务..."
    stop_service
    sleep 2
    start_timer_service "$@"
}

# 显示服务日志
show_logs() {
    local lines=${1:-50}
    if [ -f "$LOG_FILE" ]; then
        print_info "显示Marco服务最新 $lines 行日志:"
        echo "----------------------------------------"
        tail -n $lines "$LOG_FILE"
    else
        print_warning "Marco服务日志文件不存在"
    fi
}

# 执行单次Marco数据生成
run_once() {
    print_info "开始执行单次Marco数据生成..."
    
    # 创建日志目录
    mkdir -p "$(dirname "$LOG_FILE")"
    
    # 执行单次生成
    print_info "正在生成Marco数据，请稍候..."
    "$SCRIPT_DIR/venv/bin/python" run_marco.py now 2>&1 | tee -a "$LOG_FILE"
    
    local exit_code=${PIPESTATUS[0]}
    
    if [ $exit_code -eq 0 ]; then
        print_success "Marco数据生成完成"
    else
        print_error "Marco数据生成失败 (退出码: $exit_code)"
        return 1
    fi
}

# 显示监控状态
show_monitor() {
    local monitor_script="$SCRIPT_DIR/marco_service_monitor.sh"
    local monitor_log="$SCRIPT_DIR/marco_monitor.log"
    
    print_info "=== Marco监控状态 ==="
    
    # 检查监控定时任务
    local existing_cron=$(crontab -l 2>/dev/null | grep -F "$monitor_script")
    if [ -n "$existing_cron" ]; then
        print_success "Marco监控定时任务: 已启用"
        echo "  $existing_cron"
    else
        print_warning "Marco监控定时任务: 未启用"
    fi
    
    # 显示监控日志
    if [ -f "$monitor_log" ]; then
        print_info "Marco最近监控日志 (最新10行):"
        echo "----------------------------------------"
        tail -n 10 "$monitor_log"
    else
        print_info "Marco监控日志: 无记录"
    fi
}

# 显示帮助信息
show_help() {
    echo "Marco数据处理服务管理脚本"
    echo ""
    echo "使用方法:"
    echo "  $0 [命令] [参数]"
    echo ""
    echo "命令:"
    echo "  start-timer [间隔]              启动定时器模式服务 (默认: 30分钟)"
    echo "  start-daemon                   启动守护进程模式服务"
    echo "  start [间隔]                   启动定时器模式服务 (默认: 30分钟)"
    echo "  stop                          停止服务"
    echo "  restart [间隔]                重启定时器模式服务"
    echo "  status                        查看服务状态"
    echo "  once                          执行单次Marco数据生成"
    echo "  logs [行数]                    查看日志 (默认50行)"
    echo "  monitor                       查看监控状态和日志"
    echo "  help                          显示帮助"
    echo ""
    echo "示例:"
    echo "  $0 start                      # 使用默认配置启动定时器模式"
    echo "  $0 start-timer 15             # 15分钟间隔启动定时器模式"
    echo "  $0 start-daemon               # 启动守护进程模式"
    echo "  $0 once                       # 执行单次Marco数据生成"
    echo "  $0 logs 100                   # 查看最新100行日志"
    echo "  $0 monitor                    # 查看监控状态"
    echo ""
    echo "运行模式说明:"
    echo "  • timer模式:   非阻塞定时器，适合脚本控制和灵活调度"
    echo "  • daemon模式:  阻塞守护进程，适合长期稳定运行"
    echo ""
    echo "防待机功能:"
    echo "  • macOS: 使用caffeinate防止系统休眠影响服务"
    echo "  • Linux: 使用nice设置高优先级"  
    echo "  • 自动设置每5分钟的监控检查，确保服务持续运行"
    echo ""
    echo "文件位置:"
    echo "  PID文件: $PID_FILE"
    echo "  日志文件: $LOG_FILE"
    echo "  监控日志: $SCRIPT_DIR/marco_monitor.log"
}

# 主程序
case "$1" in
    "start-timer")
        start_timer_service "$2"
        ;;
    "start-daemon")
        start_daemon_service
        ;;
    "start")
        start_timer_service "$2"
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
            print_info "Marco服务最新日志:"
            echo "----------------------------------------"
            tail -n 5 "$LOG_FILE"
        fi
        ;;
    "once")
        run_once
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