#!/bin/bash
# API 调用统计快速查看脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR" && pwd)"

# 颜色输出
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_header() {
    echo -e "${GREEN}$1${NC}"
}

print_warning() {
    echo -e "${YELLOW}$1${NC}"
}

LOG_FILE="$PROJECT_ROOT/service_scripts/service_project_twitterapi.log"

case "$1" in
    "today")
        print_header "📅 今日 API 调用统计"
        python3 "$PROJECT_ROOT/api_cost_monitor.py" --mode report --report-type today
        ;;
    "month")
        print_header "📊 本月 API 调用统计"
        python3 "$PROJECT_ROOT/api_cost_monitor.py" --mode report --report-type month
        ;;
    "total")
        print_header "📈 累计 API 调用统计"
        python3 "$PROJECT_ROOT/api_cost_monitor.py" --mode report --report-type total
        ;;
    "watch")
        print_info "进入实时监控模式..."
        python3 "$PROJECT_ROOT/api_cost_monitor.py" --mode watch --interval ${2:-5}
        ;;
    "reset")
        print_warning "⚠️ 将重置所有统计数据"
        python3 "$PROJECT_ROOT/api_cost_monitor.py" --mode reset
        ;;
    "log")
        if [ -f "$LOG_FILE" ]; then
            print_header "📋 最近 API 调用日志 (最新 ${2:-20} 条)"
            grep -E "\[API调用\]|获取.*推文" "$LOG_FILE" | tail -n ${2:-20}
            echo ""
            print_info "请求总数:"
            grep -c "\[API调用\]" "$LOG_FILE" || echo "0"
        else
            print_warning "日志文件不存在: $LOG_FILE"
        fi
        ;;
    "stats")
        if [ -f "$LOG_FILE" ]; then
            print_header "📊 当前日志文件统计"
            echo "API 请求总数: $(grep -c '\[API调用\]' "$LOG_FILE" 2>/dev/null || echo 0)"
            echo "获取推文记录: $(grep -c '获取.*推文' "$LOG_FILE" 2>/dev/null || echo 0)"
            echo "错误记录: $(grep -c 'ERROR' "$LOG_FILE" 2>/dev/null || echo 0)"
            echo ""

            print_header "💰 成本报告"
            python3 "$PROJECT_ROOT/api_cost_monitor.py" --mode report --report-type all
        else
            print_warning "日志文件不存在: $LOG_FILE"
        fi
        ;;
    "count")
        # 快速显示当前日志中的 API 调用次数
        if [ -f "$LOG_FILE" ]; then
            count=$(grep -c '\[API调用\]' "$LOG_FILE" 2>/dev/null || echo 0)
            print_header "🔢 API 调用计数: $count"
        else
            print_warning "日志文件不存在"
        fi
        ;;
    *)
        echo "API 调用统计查看工具"
        echo ""
        echo "用法: $0 [命令] [参数]"
        echo ""
        echo "命令:"
        echo "  today         - 显示今日统计"
        echo "  month         - 显示本月统计"
        echo "  total         - 显示累计统计"
        echo "  stats         - 显示完整统计报告"
        echo "  count         - 快速显示当前调用次数"
        echo "  log [行数]    - 查看最近的 API 调用日志 (默认 20 行)"
        echo "  watch [间隔]  - 实时监控模式 (默认 5 秒)"
        echo "  reset         - 重置统计数据"
        echo ""
        echo "示例:"
        echo "  $0 stats          # 查看完整统计"
        echo "  $0 count          # 快速查看调用次数"
        echo "  $0 log 50         # 查看最近 50 条调用日志"
        echo "  $0 watch 3        # 每 3 秒刷新监控"
        exit 1
        ;;
esac
