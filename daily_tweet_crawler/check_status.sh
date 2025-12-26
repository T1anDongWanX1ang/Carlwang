#!/bin/bash

# 项目推文爬取服务 - 状态监控脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo ""
echo "=================================================="
echo -e "${CYAN}📊 Twitter项目推文爬取服务 - 运行状态${NC}"
echo "=================================================="
echo ""

# 1. 检查 PID 文件中的服务
echo -e "${BLUE}【1】PID 文件记录的服务：${NC}"
echo "--------------------------------------------------"

PID_FILE="../service_scripts/twitter-crawler-project-twitterapi.pid"
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null 2>&1; then
        # 获取进程详细信息
        PROCESS_INFO=$(ps -p $PID -o pid,pcpu,pmem,etime,command | tail -1)
        echo -e "${GREEN}✅ 服务正在运行${NC}"
        echo "   PID:      $PID"
        echo "   CPU:      $(echo "$PROCESS_INFO" | awk '{print $2}')%"
        echo "   内存:     $(echo "$PROCESS_INFO" | awk '{print $3}')%"
        echo "   运行时长: $(echo "$PROCESS_INFO" | awk '{print $4}')"
        echo ""
    else
        echo -e "${RED}❌ PID文件存在但进程不存在 (PID: $PID)${NC}"
        echo "   建议运行: ./start_service_project_twitterapi.sh stop"
        echo ""
    fi
else
    echo -e "${YELLOW}⚠️  未找到PID文件，服务可能未启动${NC}"
    echo ""
fi

# 2. 搜索所有相关的 Python 进程
echo -e "${BLUE}【2】所有相关的 Python 进程：${NC}"
echo "--------------------------------------------------"

PYTHON_PROCESSES=$(ps aux | grep -E "python.*main.py.*project" | grep -v grep)
if [ -n "$PYTHON_PROCESSES" ]; then
    echo "$PYTHON_PROCESSES" | while read line; do
        PID=$(echo $line | awk '{print $2}')
        CPU=$(echo $line | awk '{print $3}')
        MEM=$(echo $line | awk '{print $4}')
        COMMAND=$(echo $line | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')

        echo -e "${GREEN}🟢 PID: $PID${NC}"
        echo "   CPU: ${CPU}% | 内存: ${MEM}%"
        echo "   命令: $COMMAND"
        echo ""
    done
else
    echo -e "${YELLOW}⚠️  未发现相关 Python 进程${NC}"
    echo ""
fi

# 3. 检查 caffeinate 进程（macOS 防休眠）
echo -e "${BLUE}【3】防休眠进程 (caffeinate)：${NC}"
echo "--------------------------------------------------"

CAFFEINATE_PROCESSES=$(ps aux | grep caffeinate | grep -v grep)
if [ -n "$CAFFEINATE_PROCESSES" ]; then
    echo "$CAFFEINATE_PROCESSES" | while read line; do
        PID=$(echo $line | awk '{print $2}')
        echo -e "${GREEN}🟢 caffeinate PID: $PID${NC}"
    done
    echo ""
else
    echo -e "${YELLOW}⚠️  未发现 caffeinate 进程${NC}"
    echo ""
fi

# 4. Cron 监控任务
echo -e "${BLUE}【4】Cron 自动监控任务：${NC}"
echo "--------------------------------------------------"

MONITOR_SCRIPT="../service_scripts/service_project_monitor.sh"
EXISTING_CRON=$(crontab -l 2>/dev/null | grep -F "$MONITOR_SCRIPT")
if [ -n "$EXISTING_CRON" ]; then
    echo -e "${GREEN}✅ 监控定时任务已启用${NC}"
    echo "   $EXISTING_CRON"
    echo ""
else
    echo -e "${YELLOW}⚠️  监控定时任务未启用${NC}"
    echo ""
fi

# 5. 最近运行日志
echo -e "${BLUE}【5】最近运行日志（最新5条）：${NC}"
echo "--------------------------------------------------"

LOG_FILE="../service_scripts/service_project_twitterapi.log"
if [ -f "$LOG_FILE" ]; then
    tail -n 5 "$LOG_FILE" | sed 's/^/   /'
    echo ""
else
    echo -e "${YELLOW}⚠️  日志文件不存在${NC}"
    echo ""
fi

# 6. 快捷操作提示
echo "=================================================="
echo -e "${CYAN}💡 快捷操作${NC}"
echo "=================================================="
echo ""
echo "  启动服务:   ./start_service_project_twitterapi.sh start"
echo "  停止服务:   ./start_service_project_twitterapi.sh stop"
echo "  查看日志:   ./start_service_project_twitterapi.sh logs 100"
echo "  成本统计:   ./monitor_daily_cost.sh"
echo "  交互菜单:   ./quick_start.sh"
echo ""
echo "=================================================="
echo ""
