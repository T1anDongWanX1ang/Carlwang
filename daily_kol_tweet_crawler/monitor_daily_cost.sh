#!/bin/bash

# KOL推文爬取服务 - 成本统计脚本
# 显示 API 调用成本、推文获取统计等

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$SCRIPT_DIR/service_kol_tweet.log"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

echo ""
echo "=================================================="
echo -e "${CYAN}📊 KOL推文爬取服务 - 成本统计${NC}"
echo "=================================================="
echo ""

# 检查日志文件
if [ ! -f "$LOG_FILE" ]; then
    echo -e "${RED}❌ 日志文件不存在: $LOG_FILE${NC}"
    exit 1
fi

# 统计数据
TOTAL_RUNS=$(grep -c "开始执行 KOL 推文爬取" "$LOG_FILE" 2>/dev/null || true)
TOTAL_RUNS=${TOTAL_RUNS:-0}
SUCCESS_RUNS=$(grep -c "KOL 推文爬取完成" "$LOG_FILE" 2>/dev/null || true)
SUCCESS_RUNS=${SUCCESS_RUNS:-0}
FAILED_RUNS=$(grep -c "KOL 推文爬取失败" "$LOG_FILE" 2>/dev/null || true)
FAILED_RUNS=${FAILED_RUNS:-0}

# API 调用统计 - 查找最后一次的累计请求序号
LAST_API_REQUEST=$(grep "\[API调用\] 请求 #" "$LOG_FILE" 2>/dev/null | tail -1 | grep -oE "#[0-9]+" | sed 's/#//')
if [ -z "$LAST_API_REQUEST" ]; then
    LAST_API_REQUEST=0
fi

# 推文获取统计 - 查找最后一次的累计推文数
TOTAL_TWEETS=$(grep "获取.*条推文 (累计:" "$LOG_FILE" 2>/dev/null | tail -1 | grep -oE "累计: [0-9]+" | grep -oE "[0-9]+")
if [ -z "$TOTAL_TWEETS" ]; then
    TOTAL_TWEETS=0
fi

# 成本统计 - 查找最后一次的累计成本（只提取"累计成本:"后面的值）
TOTAL_COST=$(grep "累计成本:" "$LOG_FILE" 2>/dev/null | tail -1 | grep -oE '累计成本: \$[0-9]+\.[0-9]+' | grep -oE '[0-9]+\.[0-9]+')
if [ -z "$TOTAL_COST" ]; then
    TOTAL_COST="0.000000"
fi

# 入库推文数
SAVED_TWEETS=$(grep "成功保存.*条推文到数据库" "$LOG_FILE" 2>/dev/null | grep -oE "[0-9]+ 条" | awk '{sum+=$1} END {print sum+0}')

# 智能早停触发次数
EARLY_STOP_COUNT=$(grep -c "智能早停触发" "$LOG_FILE" 2>/dev/null || true)
EARLY_STOP_COUNT=${EARLY_STOP_COUNT:-0}

echo -e "${GREEN}总运行次数:${NC} $TOTAL_RUNS 次"
echo -e "${GREEN}  - 成功:${NC} $SUCCESS_RUNS 次"
echo -e "${GREEN}  - 失败:${NC} $FAILED_RUNS 次"
echo ""

echo "=================================================="
echo -e "${MAGENTA}💰 API 调用统计${NC}"
echo "=================================================="
echo ""
echo -e "${GREEN}API 调用次数:${NC} $LAST_API_REQUEST 次"
echo -e "${GREEN}智能早停触发:${NC} $EARLY_STOP_COUNT 次（节省成本）"

# 格式化成本显示
TOTAL_COST_FORMATTED=$(printf "%.6f" $TOTAL_COST 2>/dev/null || echo "0.000000")
echo -e "${GREEN}累计总成本:${NC} \$$TOTAL_COST_FORMATTED USD"
echo ""

if [ "$LAST_API_REQUEST" -gt 0 ]; then
    AVG_COST_PER_REQUEST=$(echo "scale=6; $TOTAL_COST / $LAST_API_REQUEST" | bc -l 2>/dev/null || echo "0")
    AVG_COST_FORMATTED=$(printf "%.6f" $AVG_COST_PER_REQUEST)
    echo -e "${YELLOW}平均每次请求成本:${NC} \$$AVG_COST_FORMATTED USD"
fi

if [ "$TOTAL_RUNS" -gt 0 ]; then
    AVG_COST_PER_RUN=$(echo "scale=6; $TOTAL_COST / $TOTAL_RUNS" | bc -l 2>/dev/null || echo "0")
    AVG_COST_FORMATTED=$(printf "%.6f" $AVG_COST_PER_RUN)
    echo -e "${YELLOW}平均每次运行成本:${NC} \$$AVG_COST_FORMATTED USD"
fi

echo ""
echo "=================================================="
echo -e "${BLUE}📱 推文数据统计${NC}"
echo "=================================================="
echo ""
echo -e "${GREEN}累计获取推文:${NC} $TOTAL_TWEETS 条"
echo -e "${GREEN}累计入库推文:${NC} $SAVED_TWEETS 条"
echo ""

if [ $TOTAL_TWEETS -gt 0 ] && [ "$TOTAL_COST" != "0" ]; then
    COST_PER_TWEET=$(echo "scale=6; $TOTAL_COST / $TOTAL_TWEETS" | bc -l 2>/dev/null || echo "0")
    COST_PER_TWEET_FORMATTED=$(printf "%.6f" $COST_PER_TWEET)
    echo -e "${YELLOW}平均每条推文成本:${NC} \$$COST_PER_TWEET_FORMATTED USD"
fi

if [ $TOTAL_TWEETS -gt 0 ] && [ $LAST_API_REQUEST -gt 0 ]; then
    AVG_TWEETS_PER_REQUEST=$(echo "scale=2; $TOTAL_TWEETS / $LAST_API_REQUEST" | bc -l 2>/dev/null || echo "0")
    echo -e "${YELLOW}平均每次请求推文数:${NC} $AVG_TWEETS_PER_REQUEST 条"
fi

echo ""
echo "=================================================="
echo -e "${MAGENTA}💡 成本预估${NC}"
echo "=================================================="
echo ""

# 按当前配置预估月成本（默认每60分钟一次 = 每天24次）
RUNS_PER_DAY=24
DAYS_PER_MONTH=30

if [ "$TOTAL_RUNS" -gt 0 ] && [ "$TOTAL_COST" != "0" ]; then
    MONTHLY_COST=$(echo "scale=2; $AVG_COST_PER_RUN * $RUNS_PER_DAY * $DAYS_PER_MONTH" | bc -l 2>/dev/null || echo "0")
    MONTHLY_COST_FORMATTED=$(printf "%.2f" $MONTHLY_COST)
    echo -e "${YELLOW}预估月成本:${NC} \$$MONTHLY_COST_FORMATTED USD (按每60分钟运行)"
fi

# 今日成本
TODAY=$(date +%Y-%m-%d)
TODAY_COST=$(grep "$TODAY" "$LOG_FILE" 2>/dev/null | grep "累计成本:" | tail -1 | grep -oE '累计成本: \$[0-9]+\.[0-9]+' | grep -oE '[0-9]+\.[0-9]+')
if [ -z "$TODAY_COST" ]; then
    TODAY_COST="0.000000"
fi
TODAY_COST_FORMATTED=$(printf "%.6f" $TODAY_COST)
echo -e "${YELLOW}今日已消费:${NC} \$$TODAY_COST_FORMATTED USD"

echo ""

# 最近一次运行的详细信息
echo "=================================================="
echo -e "${CYAN}🔍 最近一次运行详情${NC}"
echo "=================================================="
echo ""

LAST_START=$(grep "开始执行 KOL 推文爬取" "$LOG_FILE" 2>/dev/null | tail -1)
LAST_END=$(grep "KOL 推文爬取完成\|KOL 推文爬取失败" "$LOG_FILE" 2>/dev/null | tail -1)

if [ -n "$LAST_START" ]; then
    echo -e "${GREEN}最近开始时间:${NC}"
    echo "  $LAST_START"
fi

if [ -n "$LAST_END" ]; then
    echo -e "${GREEN}最近结束状态:${NC}"
    echo "  $LAST_END"
fi

echo ""
echo "=================================================="

# 记录到数据库
echo -e "${CYAN}📝 正在记录成本数据到数据库...${NC}"

# 获取当前运行ID
RUN_ID=$(date +%Y%m%d_%H%M%S)

# 调用 Python 脚本记录到数据库
PYTHON_LOGGER="$SCRIPT_DIR/../src/utils/cost_db_logger.py"
if [ -f "$PYTHON_LOGGER" ]; then
    cd "$SCRIPT_DIR/.." && venv/bin/python "$PYTHON_LOGGER" \
        --task-name "kol_tweet" \
        --run-id "$RUN_ID" \
        --total-requests "$LAST_API_REQUEST" \
        --total-cost "$TOTAL_COST" \
        --tweets-fetched "$TOTAL_TWEETS" \
        --error-count "$FAILED_RUNS" 2>&1

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ 成本数据已记录到数据库 tp_alarm.api_cost_tracking${NC}"
    else
        echo -e "${YELLOW}⚠ 记录到数据库失败（不影响统计显示）${NC}"
    fi
else
    echo -e "${YELLOW}⚠ 未找到数据库记录器: $PYTHON_LOGGER${NC}"
fi

echo ""
echo "=================================================="
echo ""
