#!/bin/bash

# 检查所有Twitter爬虫相关进程
# 使用方法: ./check_all_processes.sh

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 动态检测当前脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/twitter-crawler-project-twitterapi.pid"

echo "========================================================"
echo -e "${BLUE}🔍 Twitter爬虫进程监控${NC}"
echo "========================================================"
echo ""

# 1. 查找所有Python主进程
echo -e "${YELLOW}【1】所有Python爬虫进程:${NC}"
echo "--------------------------------------------------------"

PYTHON_PROCS=$(ps -ef | grep "[P]ython.*main.py" | grep -v grep)

if [ -z "$PYTHON_PROCS" ]; then
    echo -e "${RED}❌ 未发现任何Python爬虫进程${NC}"
else
    echo "$PYTHON_PROCS" | while read line; do
        PID=$(echo $line | awk '{print $2}')
        START=$(echo $line | awk '{print $5}')
        CMD=$(echo $line | awk '{for(i=8;i<=NF;i++) printf $i" "; print ""}')

        # 检查是否是project-schedule模式
        if echo "$CMD" | grep -q "project-schedule"; then
            # 提取关键参数
            MAX_PAGES=$(echo "$CMD" | grep -oE 'max-pages [0-9]+' | awk '{print $2}')
            PAGE_SIZE=$(echo "$CMD" | grep -oE 'page-size [0-9]+' | awk '{print $2}')
            HOURS=$(echo "$CMD" | grep -oE 'hours-limit [0-9.]+' | awk '{print $2}')
            INTERVAL=$(echo "$CMD" | grep -oE 'interval [0-9]+' | awk '{print $2}')

            # 判断是新代码还是旧代码
            if [ "$MAX_PAGES" == "2" ] || [ "$MAX_PAGES" == "1" ]; then
                echo -e "${GREEN}✅ PID $PID${NC} | 启动: $START | ${GREEN}新代码${NC}"
                echo "   参数: max-pages=$MAX_PAGES, page-size=$PAGE_SIZE, hours=$HOURS, interval=$INTERVAL"
            else
                echo -e "${RED}🔴 PID $PID${NC} | 启动: $START | ${RED}旧代码 (需停止)${NC}"
                echo "   参数: max-pages=$MAX_PAGES, page-size=$PAGE_SIZE, hours=$HOURS, interval=$INTERVAL"
            fi
        else
            echo -e "${YELLOW}⚠️  PID $PID${NC} | 启动: $START | 其他模式"
            echo "   命令: $(echo $CMD | cut -c1-80)..."
        fi
        echo ""
    done
fi

echo ""
echo "--------------------------------------------------------"
echo -e "${YELLOW}【2】PID文件记录的官方服务:${NC}"
echo "--------------------------------------------------------"

echo "当前目录: $SCRIPT_DIR"
echo "PID文件: $PID_FILE"
echo ""

if [ -f "$PID_FILE" ]; then
    OFFICIAL_PID=$(cat "$PID_FILE")
    if ps -p $OFFICIAL_PID > /dev/null 2>&1; then
        echo -e "${GREEN}✅ 官方服务正在运行 (PID: $OFFICIAL_PID)${NC}"
        ps -o pid,ppid,user,start,etime,%cpu,%mem,command -p $OFFICIAL_PID | tail -1
    else
        echo -e "${RED}❌ PID文件记录的进程不存在 (PID: $OFFICIAL_PID)${NC}"
    fi
else
    echo -e "${RED}❌ PID文件不存在: $PID_FILE${NC}"
fi

echo ""
echo "--------------------------------------------------------"
echo -e "${YELLOW}【3】进程统计:${NC}"
echo "--------------------------------------------------------"

TOTAL_COUNT=$(ps -ef | grep "[P]ython.*main.py.*project-schedule" | wc -l | tr -d ' ')
OLD_COUNT=$(ps -ef | grep "[P]ython.*main.py.*project-schedule" | grep -E "max-pages (50|100)" | wc -l | tr -d ' ')
NEW_COUNT=$(ps -ef | grep "[P]ython.*main.py.*project-schedule" | grep -E "max-pages [0-2]" | wc -l | tr -d ' ')

echo "总进程数: $TOTAL_COUNT"
echo -e "${GREEN}新代码进程 (max-pages ≤ 2): $NEW_COUNT${NC}"
echo -e "${RED}旧代码进程 (max-pages ≥ 50): $OLD_COUNT${NC}"

if [ "$OLD_COUNT" -gt 0 ]; then
    echo ""
    echo -e "${RED}⚠️  警告: 发现 $OLD_COUNT 个旧代码进程，建议立即停止！${NC}"
    echo ""
    echo "停止旧进程命令:"
    echo "  ps -ef | grep '[P]ython.*main.py.*project-schedule' | grep -E 'max-pages (50|100)' | awk '{print \$2}' | xargs kill -9"
fi

if [ "$NEW_COUNT" -gt 1 ]; then
    echo ""
    echo -e "${YELLOW}⚠️  警告: 发现 $NEW_COUNT 个新代码进程，可能有重复！${NC}"
fi

echo ""
echo "--------------------------------------------------------"
echo -e "${YELLOW}【4】Caffeinate防休眠进程:${NC}"
echo "--------------------------------------------------------"

CAFFEINE_PROCS=$(ps -ef | grep "[c]affeinate.*main.py" | wc -l | tr -d ' ')
echo "防休眠进程数: $CAFFEINE_PROCS"

echo ""
echo "--------------------------------------------------------"
echo -e "${YELLOW}【5】Cron定时监控任务:${NC}"
echo "--------------------------------------------------------"

CRON_TASKS=$(crontab -l 2>/dev/null | grep "service_project_monitor.sh" | wc -l | tr -d ' ')
if [ "$CRON_TASKS" -gt 0 ]; then
    echo -e "${GREEN}✅ Cron监控任务已设置 ($CRON_TASKS 个)${NC}"
    crontab -l 2>/dev/null | grep "service_project_monitor.sh"
else
    echo -e "${YELLOW}⚠️  未发现Cron监控任务${NC}"
fi

echo ""
echo "========================================================"
echo -e "${BLUE}💡 快捷命令 (当前目录)${NC}"
echo "========================================================"
echo "当前监控目录: $SCRIPT_DIR"
echo ""
echo "查看实时日志: tail -f $SCRIPT_DIR/service_project_twitterapi.log"
echo "查看服务状态: $SCRIPT_DIR/start_service_project_twitterapi.sh status"
echo "查看成本统计: $SCRIPT_DIR/monitor_daily_cost.sh"
echo "停止所有进程: ps -ef | grep '[P]ython.*main.py' | grep 'project-schedule' | awk '{print \$2}' | xargs kill -9"
echo "========================================================"
