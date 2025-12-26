#!/bin/bash

# KOL Following 服务状态检查脚本
# 显示详细的服务运行状态和进程信息

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/twitter-crawler-kol-following.pid"
LOG_FILE="$SCRIPT_DIR/service_kol_following.log"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo ""
echo "========================================"
echo "   KOL Following 服务状态检查"
echo "========================================"
echo ""

# 【1】PID 文件记录的服务
echo -e "${CYAN}【1】PID 文件记录的服务：${NC}"
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null 2>&1; then
        echo -e "${GREEN}✅ 服务正在运行${NC}"
        echo "   PID:      $PID"

        if [[ "$OSTYPE" == "darwin"* ]]; then
            CPU=$(ps -p $PID -o %cpu | tail -n 1 | tr -d ' ')
            MEM=$(ps -p $PID -o %mem | tail -n 1 | tr -d ' ')
            ELAPSED=$(ps -p $PID -o etime | tail -n 1 | tr -d ' ')
            echo "   CPU:      ${CPU}%"
            echo "   内存:     ${MEM}%"
            echo "   运行时长: $ELAPSED"
        else
            ps -p $PID -o pid,pcpu,pmem,etime,cmd --no-headers
        fi
    else
        echo -e "${RED}❌ PID 文件存在但进程已停止${NC}"
        echo "   PID文件: $PID_FILE"
        echo "   记录PID: $PID"
    fi
else
    echo -e "${YELLOW}⚠️  PID 文件不存在${NC}"
    echo "   路径: $PID_FILE"
fi

echo ""

# 【2】所有相关的 Python 进程
echo -e "${CYAN}【2】所有相关的 Python 进程：${NC}"
PROCS=$(ps -ef | grep "[P]ython.*fetch_kol_followings")
if [ -n "$PROCS" ]; then
    echo "$PROCS" | while IFS= read -r line; do
        PROC_PID=$(echo "$line" | awk '{print $2}')
        echo -e "${GREEN}🟢 PID: $PROC_PID${NC}"

        if [[ "$OSTYPE" == "darwin"* ]]; then
            CPU=$(ps -p $PROC_PID -o %cpu | tail -n 1 | tr -d ' ')
            MEM=$(ps -p $PROC_PID -o %mem | tail -n 1 | tr -d ' ')
            echo "   CPU: ${CPU}% | 内存: ${MEM}%"
        fi

        CMD=$(echo "$line" | awk '{for(i=8;i<=NF;i++) printf $i" "; print ""}')
        echo "   命令: $CMD"
        echo ""
    done
else
    echo -e "${YELLOW}⚠️  没有找到运行中的 KOL Following 进程${NC}"
fi

echo ""

# 【3】防休眠进程 (caffeinate)
echo -e "${CYAN}【3】防休眠进程 (macOS)：${NC}"
if [[ "$OSTYPE" == "darwin"* ]]; then
    CAFFEINATE_PROCS=$(ps -ef | grep "[c]affeinate.*fetch_kol_followings")
    if [ -n "$CAFFEINATE_PROCS" ]; then
        echo "$CAFFEINATE_PROCS" | while IFS= read -r line; do
            PROC_PID=$(echo "$line" | awk '{print $2}')
            echo -e "${GREEN}🟢 Caffeinate PID: $PROC_PID${NC}"
        done
    else
        echo -e "${YELLOW}⚠️  没有找到 caffeinate 进程${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  当前系统非 macOS，无需 caffeinate${NC}"
fi

echo ""

# 【4】Cron 自动监控任务
echo -e "${CYAN}【4】Cron 自动监控任务：${NC}"
MONITOR_SCRIPT="$SCRIPT_DIR/service_kol_following_monitor.sh"
CRON_TASK=$(crontab -l 2>/dev/null | grep "$MONITOR_SCRIPT")
if [ -n "$CRON_TASK" ]; then
    echo -e "${GREEN}✅ 监控任务已启用${NC}"
    echo "   $CRON_TASK"
else
    echo -e "${YELLOW}⚠️  监控任务未启用${NC}"
    echo "   提示: 启动服务时会自动设置监控任务"
fi

echo ""

# 【5】最近运行日志
echo -e "${CYAN}【5】最近运行日志（最新 10 行）：${NC}"
if [ -f "$LOG_FILE" ]; then
    tail -n 10 "$LOG_FILE" | while IFS= read -r line; do
        echo "   $line"
    done
else
    echo -e "${YELLOW}⚠️  日志文件不存在${NC}"
    echo "   路径: $LOG_FILE"
fi

echo ""
echo "========================================"
echo ""

# 返回状态码
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null 2>&1; then
        exit 0  # 服务正常运行
    fi
fi

exit 1  # 服务未运行
