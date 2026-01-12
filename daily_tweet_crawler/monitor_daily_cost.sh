#!/bin/bash

# 日常成本监控脚本 (增强版)
# 统计 service_project_twitterapi.log 和 service_update_metrics.log 中的成本数据

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE_DAILY="$SCRIPT_DIR/service_project_twitterapi.log"
LOG_FILE_UPDATE="$SCRIPT_DIR/service_update_metrics.log"

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "=================================================="
echo -e "${BLUE}📊 项目推文爬取服务 - 成本统计 (全量)${NC}"
echo "=================================================="
echo ""

# 函数：计算单个日志文件的总成本
calc_cost() {
    local file=$1
    if [ -f "$file" ]; then
        # 提取所有 "总成本: $0.123456" (兼容 "本次总成本" 和 "总成本") 中的数字并累加
        grep "总成本:" "$file" | grep -oE '\$[0-9]+\.[0-9]+' | sed 's/\$//' | awk '{sum+=$1} END {printf "%.6f", sum}'
    else
        echo "0"
    fi
}

# 函数：计算今日成本
calc_today_cost() {
    local file=$1
    local today=$(date +%Y-%m-%d)
    if [ -f "$file" ]; then
        # 仅匹配包含今日日期的行
        grep "$today" "$file" | grep "总成本:" | grep -oE '\$[0-9]+\.[0-9]+' | sed 's/\$//' | awk '{sum+=$1} END {printf "%.6f", sum}'
    else
        echo "0"
    fi
}

# 1. 日常抓取任务 (Discovery)
COST_DAILY=$(calc_cost "$LOG_FILE_DAILY")
COST_DAILY_TODAY=$(calc_today_cost "$LOG_FILE_DAILY")
echo -e "${YELLOW}[日常抓取任务]${NC}"
echo -e "  累计总成本: \$${COST_DAILY}"
echo -e "  今日已消费: \$${COST_DAILY_TODAY}"

# 2. 指标更新任务 (Update Metrics)
COST_UPDATE=$(calc_cost "$LOG_FILE_UPDATE")
COST_UPDATE_TODAY=$(calc_today_cost "$LOG_FILE_UPDATE")
echo -e "\n${YELLOW}[指标更新任务]${NC}"
echo -e "  累计总成本: \$${COST_UPDATE}"
echo -e "  今日已消费: \$${COST_UPDATE_TODAY}"

# 3. 汇总
TOTAL_ALL=$(echo "$COST_DAILY + $COST_UPDATE" | bc)
TOTAL_TODAY=$(echo "$COST_DAILY_TODAY + $COST_UPDATE_TODAY" | bc)

echo ""
echo "=================================================="
echo -e "${GREEN}💰 综合汇总${NC}"
echo "=================================================="
echo -e "历史总投入: ${RED}\$${TOTAL_ALL} USD${NC}"
echo -e "今日总消费: ${RED}\$${TOTAL_TODAY} USD${NC}"
echo "=================================================="

# 4. 显示最近运行记录 (只显示更新任务的，因为那个不常看)
if [ -f "$LOG_FILE_UPDATE" ]; then
    echo -e "\n${BLUE}🔄 指标更新任务 - 最近 5 次记录${NC}"
    grep "总成本:" "$LOG_FILE_UPDATE" | tail -5 | while read line; do
        # 尝试提取时间戳 (日志格式: YYYY-MM-DD HH:MM:SS ...)
        TIMESTAMP=$(echo "$line" | awk '{print $1, $2}')
        COST=$(echo "$line" | grep -oE '\$[0-9]+\.[0-9]+')
        echo "  [$TIMESTAMP] 成本: $COST"
    done
fi

echo ""
echo "=================================================="
echo -e "${CYAN}ℹ️  说明${NC}"
echo "数据来源: 本地日志文件实时统计"
echo "API 计费标准: \$0.15 / 1000 requests (twitterapi.io)"
echo "=================================================="

