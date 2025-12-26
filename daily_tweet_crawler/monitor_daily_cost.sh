#!/bin/bash

# 日常成本监控脚本
# 统计 service_project_twitterapi.log 中的成本数据

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$SCRIPT_DIR/service_project_twitterapi.log"

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

if [ ! -f "$LOG_FILE" ]; then
    echo -e "${RED}错误: 日志文件不存在${NC}"
    exit 1
fi

echo "=================================================="
echo -e "${BLUE}📊 项目推文爬取服务 - 成本统计${NC}"
echo "=================================================="
echo ""

# 1. 统计总运行次数
TOTAL_RUNS=$(grep "开始爬取项目推文数据" "$LOG_FILE" | wc -l | tr -d ' ')
echo -e "${GREEN}总运行次数:${NC} $TOTAL_RUNS 次"

# 2. 统计总成本（取最后一次的累计值，因为日志中"本次总成本"本身就是累计的）
TOTAL_COST=$(grep "本次总成本:" "$LOG_FILE" | grep -oE '\$[0-9]+\.[0-9]+' | sed 's/\$//' | tail -1)
if [ -z "$TOTAL_COST" ]; then
    TOTAL_COST="0.000000"
fi
echo -e "${GREEN}累计总成本:${NC} \$$TOTAL_COST USD"

# 3. 统计总推文数（取最后一次的累计值，因为日志中"获取推文数"本身就是累计的）
TOTAL_TWEETS=$(grep -E "crawl_project_tweets.*获取推文数: [0-9]+$" "$LOG_FILE" | grep -oE '[0-9]+$' | tail -1)
if [ -z "$TOTAL_TWEETS" ]; then
    TOTAL_TWEETS=0
fi
echo -e "${GREEN}累计获取推文:${NC} $TOTAL_TWEETS 条"

# 4. 统计入库推文数
SAVED_TWEETS=$(grep "成功保存.*条项目推文到数据库" "$LOG_FILE" | grep -oE "[0-9]+ 条" | awk '{sum+=$1} END {print sum}')
if [ -z "$SAVED_TWEETS" ]; then
    SAVED_TWEETS=0
fi
echo -e "${GREEN}累计入库推文:${NC} $SAVED_TWEETS 条"

# 5. 计算平均成本
if [ "$SAVED_TWEETS" -gt 0 ]; then
    AVG_COST=$(echo "scale=6; $TOTAL_COST / $SAVED_TWEETS" | bc)
    echo -e "${GREEN}平均每条推文成本:${NC} \$$AVG_COST USD"
fi

echo ""
echo "=================================================="
echo -e "${BLUE}📈 最近 10 次运行记录${NC}"
echo "=================================================="

# 6. 显示最近10次的详细信息
grep -B 1 "本次总成本:" "$LOG_FILE" | tail -20 | while read line; do
    if [[ $line == *"开始爬取项目推文数据"* ]]; then
        TIMESTAMP=$(echo $line | awk '{print $1, $2}')
        echo -e "\n${YELLOW}[$TIMESTAMP]${NC}"
    elif [[ $line == *"本次总成本:"* ]]; then
        COST=$(echo $line | awk '{print $3}')
        echo -e "  成本: ${GREEN}$COST${NC}"
    fi
done

echo ""
echo "=================================================="
echo -e "${BLUE}💡 今日预估${NC}"
echo "=================================================="

# 7. 计算今天的成本（取今日最后一次的累计值）
TODAY=$(date +%Y-%m-%d)
TODAY_COST=$(grep "$TODAY" "$LOG_FILE" | grep "本次总成本:" | grep -oE '\$[0-9]+\.[0-9]+' | sed 's/\$//' | tail -1)
if [ -z "$TODAY_COST" ]; then
    TODAY_COST="0.000000"
fi
echo -e "${GREEN}今日已消费:${NC} \$$TODAY_COST USD"

# 8. 根据运行频率估算月成本
# 默认每15分钟一次 = 每天96次
RUNS_PER_DAY=96
if [ "$TOTAL_RUNS" -gt 0 ] && [ "$TOTAL_COST" != "0.000000" ]; then
    AVG_COST_PER_RUN=$(echo "scale=6; $TOTAL_COST / $TOTAL_RUNS" | bc 2>/dev/null)
    if [ -n "$AVG_COST_PER_RUN" ]; then
        DAILY_ESTIMATE=$(echo "scale=6; $AVG_COST_PER_RUN * $RUNS_PER_DAY" | bc 2>/dev/null)
        MONTHLY_ESTIMATE=$(echo "scale=2; $DAILY_ESTIMATE * 30" | bc 2>/dev/null)
        if [ -n "$MONTHLY_ESTIMATE" ]; then
            echo -e "${YELLOW}预估每日成本:${NC} \$$DAILY_ESTIMATE USD (按每15分钟运行)"
            echo -e "${YELLOW}预估月成本:${NC} \$$MONTHLY_ESTIMATE USD (按每15分钟运行)"
        fi
    fi
fi

echo ""
echo "=================================================="
echo -e "${BLUE}🔍 实时监控命令${NC}"
echo "=================================================="
echo "  当前目录: $SCRIPT_DIR"
echo "  实时日志: tail -f $LOG_FILE"
echo "  查看状态: $SCRIPT_DIR/start_service_project_twitterapi.sh status"
echo "  查看日志: $SCRIPT_DIR/start_service_project_twitterapi.sh logs 100"
echo "=================================================="
